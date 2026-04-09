from functools import wraps
import os
import sys
import sqlite3
import datetime
import secrets
import re
import time
from collections import defaultdict

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import check_password_hash, generate_password_hash

# ============= LOAD ENVIRONMENT VARIABLES FROM .env =============
def load_env_file(filename=".env"):
    """Simple .env file loader."""
    env_vars = {}
    if os.path.exists(filename):
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
    return env_vars

# Load from .env file (for local development)
env_file_vars = load_env_file(".env")

# Priority: System env vars > .env file > defaults
def get_env(key, default=None):
    """Get environment variable with fallback to .env and defaults."""
    return os.environ.get(key) or env_file_vars.get(key) or default

# ============= CONFIGURATION =============
app = Flask(__name__, template_folder='template')

# Use env variable or generate secure default
app.secret_key = get_env("FLASK_SECRET_KEY") or secrets.token_hex(32)
API_KEY = get_env("API_KEY", "airport-smart-band-api-key-change-in-production")
DEFAULT_USERNAME = get_env("DEFAULT_USERNAME", "Aerolinkers")
DEFAULT_PASSWORD = get_env("DEFAULT_PASSWORD", "Aerolinkers123")
ENABLE_DEMO_MODE = get_env("ENABLE_DEMO_MODE", "True").lower() == "true"
APP_VERSION = "2.0.0"
START_TIME = datetime.datetime.now()

# Database configuration
DB_DIR = get_env("DB_DIR", "db")
os.makedirs(DB_DIR, exist_ok=True)

DB_FILES = {
    "flights": os.path.join(DB_DIR, "flights.db"),
    "passenger": os.path.join(DB_DIR, "passenger.db"),
    "devices": os.path.join(DB_DIR, "devices.db"),
    "notifications": os.path.join(DB_DIR, "notifications.db"),
    "users": os.path.join(DB_DIR, "users.db"),
    "audit": os.path.join(DB_DIR, "audit.db"),
}

NO_AUTH_ENDPOINTS = {"login", "static", "sync", "health", "diagnose"}

# ============= RATE LIMITING (In-Memory) =============
class RateLimiter:
    """Simple rate limiter for login and API requests."""
    def __init__(self):
        self.attempts = defaultdict(list)
    
    def is_allowed(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        """Check if action is allowed based on rate limit."""
        now = time.time()
        # Clean old attempts
        self.attempts[key] = [t for t in self.attempts[key] if now - t < window_seconds]
        
        if len(self.attempts[key]) >= max_attempts:
            return False
        
        self.attempts[key].append(now)
        return True
    
    def get_remaining(self, key: str, max_attempts: int, window_seconds: int) -> int:
        """Get remaining attempts before rate limit."""
        now = time.time()
        self.attempts[key] = [t for t in self.attempts[key] if now - t < window_seconds]
        return max(0, max_attempts - len(self.attempts[key]))

limiter = RateLimiter()

# ============= STRUCTURED LOGGING =============
def log_action(action: str, user: str, resource: str, status: str, details: str = ""):
    """Log user actions to audit database."""
    try:
        conn = get_db_connection("audit")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_log (timestamp, action, user, resource, status, details, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.datetime.now().isoformat(),
                action,
                user or "anonymous",
                resource,
                status,
                details,
                request.remote_addr if request else "127.0.0.1"
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Logging error: {str(e)}")

def log_login_attempt(username: str, status: str):
    """Log login attempts."""
    log_action("LOGIN", username, "auth", status, f"User: {username}")

def log_user_action(action: str, user: str, resource: str, details: str = ""):
    """Log regular user actions."""
    log_action(action, user, resource, "success", details)

# ============= UTILITY FUNCTIONS =============
def get_db_connection(db_name: str):
    """Return a new SQLite connection for the given db name."""
    path = DB_FILES.get(db_name)
    if not path:
        raise ValueError(f"Unknown database name: {db_name}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Create connection with timeout
    try:
        conn = sqlite3.connect(path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except Exception as e:
        print(f"Error connecting to {db_name} at {path}: {e}")
        raise


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format."""
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        return False, "Username can only contain alphanumeric characters, underscores, and hyphens"
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength - enhanced with complexity rules."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""


def validate_pnr(pnr: str) -> tuple[bool, str]:
    """Validate PNR format."""
    if not pnr or len(pnr) == 0:
        return False, "PNR is required"
    if len(pnr) > 20:
        return False, "PNR too long"
    return True, ""


def validate_device_id(device_id: str) -> tuple[bool, str]:
    """Validate device ID format."""
    if not device_id or len(device_id) == 0:
        return False, "Device ID is required"
    if len(device_id) > 50:
        return False, "Device ID too long"
    return True, ""


def get_user_role(username: str) -> str:
    """Get user role from database."""
    try:
        conn = get_db_connection("users")
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else "staff"
    except:
        return "staff"


def get_app_uptime() -> str:
    """Get application uptime."""
    uptime = datetime.datetime.now() - START_TIME
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    days = uptime.days
    return f"{days}d {hours}h {minutes}m"


def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def require_api_key(f):
    """Decorator to require API key in request headers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != API_KEY:
            return jsonify({"message": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        
        user_role = get_user_role(session["user"])
        if user_role != "admin":
            flash("You do not have permission to access this page. Admin role required.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function


# ============= DATABASE INITIALIZATION =============
def init_db():
    """Ensure required tables exist and seed data."""

    def init(db_name: str, create_stmts):
        path = DB_FILES[db_name]
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            conn = sqlite3.connect(path, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            
            for stmt in create_stmts:
                try:
                    cursor.execute(stmt)
                except sqlite3.OperationalError as e:
                    # Table already exists, that's okay
                    if "already exists" not in str(e):
                        raise
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not initialize {db_name} at {path}: {e}")
            # Don't crash on DB init errors

    # Create all tables
    init("flights", [
        """CREATE TABLE IF NOT EXISTS flights(
            flight_id TEXT PRIMARY KEY,
            boarding_time TEXT,
            departure TEXT,
            gate TEXT,
            status TEXT,
            aircraft TEXT,
            origin TEXT,
            destination TEXT,
            display_time TEXT,
            last_update TEXT
        )""",
    ])

    init("passenger", [
        """CREATE TABLE IF NOT EXISTS passenger(
            passenger_id TEXT PRIMARY KEY,
            name TEXT,
            ticket_number TEXT,
            flight_id TEXT,
            boarding_status TEXT,
            seat_number TEXT,
            device_id TEXT
        )""",
    ])

    init("devices", [
        """CREATE TABLE IF NOT EXISTS devices(
            device_id TEXT PRIMARY KEY,
            mac_address TEXT,
            status TEXT,
            battery_level INTEGER,
            signal_strength INTEGER,
            last_seen TEXT
        )""",
    ])

    init("notifications", [
        """CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            type TEXT,
            created_at TEXT
        )""",
    ])

    init("users", [
        """CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            role TEXT DEFAULT 'staff'
        )""",
    ])

    # UPGRADE 2 & 3: Audit Log + User Roles
    init("audit", [
        """CREATE TABLE IF NOT EXISTS audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action TEXT,
            user TEXT,
            resource TEXT,
            status TEXT,
            details TEXT,
            ip_address TEXT
        )""",
    ])

    # Seed default admin user with role
    try:
        conn = get_db_connection("users")
        cursor = conn.cursor()
        password_hash = generate_password_hash(DEFAULT_PASSWORD)
        cursor.execute(
            "INSERT OR REPLACE INTO users(username, password_hash, role) VALUES (?, ?, ?)",
            (DEFAULT_USERNAME, password_hash, "admin"),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not seed admin user: {e}")

    # Seed sample flights
    try:
        conn = get_db_connection("flights")
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO flights (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("AI202", "18:30", "19:00", "Gate 12", "On Time", "Boeing 737", "Delhi", "Mumbai", "18:30", datetime.datetime.now().isoformat()),
                ("AI305", "19:00", "19:30", "Gate 15", "Delayed", "Airbus A320", "Mumbai", "Bangalore", "19:15", datetime.datetime.now().isoformat()),
            ],
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not seed flights: {e}")

    # Seed sample passengers
    try:
        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO passenger (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("TB2376", "Thiru", "TB2376", "AI202", "Boarded", "12B", None),
                ("AB1234", "John Doe", "AB1234", "AI305", "Waiting", "14A", None),
            ],
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not seed passengers: {e}")

    # Seed sample devices
    try:
        conn = get_db_connection("devices")
        cursor = conn.cursor()
        devices_data = [(f"DEV{i:03d}", f"08:3A:F2:A8:31:{i:02X}", "active", 95, -45, datetime.datetime.now().isoformat()) for i in range(1, 31)]
        cursor.executemany(
            "INSERT OR IGNORE INTO devices (device_id, mac_address, status, battery_level, signal_strength, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
            devices_data,
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not seed devices: {e}")

    # Seed sample notifications
    try:
        conn = get_db_connection("notifications")
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT OR IGNORE INTO notifications (message, type, created_at) VALUES (?, ?, ?)",
            [
                ("Flight AI202 boarding now", "info", datetime.datetime.now().isoformat()),
                ("Device DEV001 battery low", "warning", datetime.datetime.now().isoformat()),
            ],
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not seed notifications: {e}")
    conn.close()


# Initialize DB on startup (non-blocking)
try:
    init_db()
    print("✓ Database initialization successful")
except Exception as e:
    print(f"⚠ Warning during database initialization: {e}")
    # IMPORTANT: Do not crash the app if DB init fails
    # Databases can be initialized later via db_migrate.py


# ============= MIDDLEWARE & DECORATORS =============
@app.before_request
def require_login():
    """Redirect to login unless authenticated or accessing allowed endpoints."""
    if request.endpoint in NO_AUTH_ENDPOINTS or request.endpoint is None:
        return

    if "user" not in session:
        return redirect(url_for("login"))


def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============= TEMPLATES HELPERS =============
@app.context_processor
def inject_config():
    """Inject configuration into templates."""
    user_role = get_user_role(session.get("user")) if session.get("user") else None
    return {
        "current_year": datetime.datetime.now().year,
        "api_key": API_KEY,
        "demo_mode": ENABLE_DEMO_MODE,
        "default_username": DEFAULT_USERNAME,
        "default_password": DEFAULT_PASSWORD,
        "user_role": user_role,
        "app_version": APP_VERSION,
    }


# ============= AUTHENTICATION ROUTES =============
@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # UPGRADE 1: Rate Limiting on login
        ip_address = request.remote_addr
        if not limiter.is_allowed(f"login_{ip_address}", max_attempts=5, window_seconds=300):
            log_login_attempt(username, "RATE_LIMITED")
            remaining = limiter.get_remaining(f"login_{ip_address}", 5, 300)
            flash(f"Too many login attempts. Try again in 5 minutes.", "danger")
            return redirect(url_for("login"))

        # Validate input
        valid, msg = validate_username(username)
        if not valid:
            flash(msg, "danger")
            return redirect(url_for("login"))

        conn = get_db_connection("users")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["user"] = username
            log_login_attempt(username, "SUCCESS")
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for("dashboard"))

        log_login_attempt(username, "FAILED")
        flash("Invalid username or password", "danger")

    return render_template(
        "login.html",
        default_username=DEFAULT_USERNAME,
        default_password=DEFAULT_PASSWORD,
    )


@app.route("/logout")
@login_required
def logout():
    username = session.get("user")
    session.clear()
    log_action("LOGOUT", username, "auth", "success")
    flash("You have been logged out", "info")
    return redirect(url_for("login"))


# ============= DASHBOARD ROUTE =============
@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard showing flights, devices, and notifications."""

    # Devices
    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]
    cursor.execute("SELECT device_id, mac_address, status, battery_level, signal_strength, last_seen FROM devices")
    devices = cursor.fetchall()
    conn.close()

    # Flights
    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    total_flights = cursor.fetchone()[0]
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status FROM flights ORDER BY flight_id")
    flights = cursor.fetchall()
    conn.close()

    # Notifications
    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("SELECT id, message, type, created_at FROM notifications ORDER BY id DESC LIMIT 10")
    notifications = cursor.fetchall()
    conn.close()

    # Passengers
    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id FROM passenger ORDER BY passenger_id")
    passengers = cursor.fetchall()
    conn.close()

    user_role = get_user_role(session.get("user"))
    
    return render_template(
        "dashboard.html",
        total_devices=total_devices,
        active_devices=total_devices,
        total_flights=total_flights,
        devices=devices,
        notifications=notifications,
        flights=flights,
        passengers=passengers,
        passenger=None,
        user_role=user_role,
    )


@app.route("/search", methods=["POST"])
@login_required
def search():
    pnr = request.form.get("pnr", "").strip()

    if not pnr:
        flash("PNR is required", "danger")
        return redirect(url_for("dashboard"))

    # Devices
    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]
    cursor.execute("SELECT device_id, mac_address, status, battery_level, signal_strength, last_seen FROM devices")
    devices = cursor.fetchall()
    conn.close()

    # Flights
    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    total_flights = cursor.fetchone()[0]
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status FROM flights ORDER BY flight_id")
    flights = cursor.fetchall()
    conn.close()

    # Notifications
    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("SELECT id, message, type, created_at FROM notifications ORDER BY id DESC LIMIT 10")
    notifications = cursor.fetchall()
    conn.close()

    # Passengers
    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id FROM passenger ORDER BY passenger_id")
    passengers = cursor.fetchall()

    cursor.execute(
        "SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?",
        (pnr,),
    )
    passenger = cursor.fetchone()
    conn.close()

    boarding_time = None
    if passenger:
        conn = get_db_connection("flights")
        cursor = conn.cursor()
        cursor.execute("SELECT boarding_time FROM flights WHERE flight_id = ?", (passenger[2],))
        row = cursor.fetchone()
        conn.close()
        boarding_time = row[0] if row else None
        passenger = (passenger[0], passenger[1], passenger[2], passenger[3], boarding_time, passenger[4])

    if not passenger:
        flash(f"No passenger found with PNR: {pnr}", "warning")

    log_user_action("SEARCH", session.get("user"), "passenger", f"PNR: {pnr}")

    user_role = get_user_role(session.get("user"))
    
    return render_template(
        "dashboard.html",
        total_devices=total_devices,
        active_devices=total_devices,
        total_flights=total_flights,
        devices=devices,
        notifications=notifications,
        flights=flights,
        passengers=passengers,
        passenger=passenger,
        search_pnr=pnr,
        user_role=user_role,
    )


# ============= API ENDPOINT - DEVICE SYNC (with API Key) =============
@app.route("/sync", methods=["POST"])
@require_api_key
def sync():
    """Device sync endpoint - requires API key authentication."""
    try:
        data = request.get_json(force=True, silent=True) or {}

        mac = data.get("device_id", "").strip()
        pnr = data.get("pnr", "").strip()

        # Validate input
        valid_mac, msg_mac = validate_device_id(mac)
        valid_pnr, msg_pnr = validate_pnr(pnr)

        if not valid_mac:
            return jsonify({"message": msg_mac}), 400
        if not valid_pnr:
            return jsonify({"message": msg_pnr}), 400

        # Passenger lookup
        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?",
            (pnr,),
        )
        passenger = cursor.fetchone()
        conn.close()

        if not passenger:
            return jsonify({"message": "Passenger not found"}), 404

        # Flight boarding time lookup
        conn = get_db_connection("flights")
        cursor = conn.cursor()
        cursor.execute("SELECT boarding_time FROM flights WHERE flight_id = ?", (passenger[2],))
        flight_row = cursor.fetchone()
        conn.close()

        boarding_time = flight_row[0] if flight_row else None

        log_action("DEVICE_SYNC", "device", mac, "success", f"PNR: {pnr}")

        return jsonify(
            {
                "device_id": mac,
                "pnr": passenger[0],
                "name": passenger[1],
                "flight": passenger[2],
                "seat": passenger[3],
                "boarding_time": boarding_time,
            }
        )

    except Exception as e:
        return jsonify({"message": "Server error", "error": str(e)}), 500


# ============= UPGRADE 4: HEALTH CHECK ENDPOINT =============
@app.route("/health")
def health():
    """Health check endpoint for monitoring."""
    try:
        # Check database connectivity
        conn = get_db_connection("users")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "version": APP_VERSION,
            "uptime": get_app_uptime(),
            "timestamp": datetime.datetime.now().isoformat(),
            "database": "connected",
            "users": user_count,
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat(),
        }), 500


@app.route("/diagnose")
def diagnose():
    """Diagnostic endpoint for troubleshooting (no auth required)."""
    diagnostics = {}
    
    # Check Python paths
    diagnostics['python_version'] = f"{sys.version}"
    diagnostics['python_executable'] = sys.executable
    
    # Check database files
    diagnostics['db_files'] = {}
    for name, path in DB_FILES.items():
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        diagnostics['db_files'][name] = {
            'path': path,
            'exists': exists,
            'size_bytes': size,
        }
    
    # Check database connectivity
    diagnostics['database_status'] = {}
    for db_name in DB_FILES.keys():
        try:
            conn = get_db_connection(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            diagnostics['database_status'][db_name] = 'connected'
        except Exception as e:
            diagnostics['database_status'][db_name] = f'error: {str(e)}'
    
    # Check configuration
    diagnostics['config'] = {
        'FLASK_ENV': os.getenv('FLASK_ENV', 'not set'),
        'DB_DIR': DB_DIR,
        'APP_VERSION': APP_VERSION,
        'DEBUG': app.debug,
    }
    
    return jsonify(diagnostics), 200


# ============= API ENDPOINTS =============
@app.route("/flights")
@login_required
def flights():
    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update FROM flights")
    data = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "flight_id": f[0],
            "boarding_time": f[1],
            "departure": f[2],
            "gate": f[3],
            "status": f[4],
            "aircraft": f[5],
            "origin": f[6],
            "destination": f[7],
            "display_time": f[8],
            "last_update": f[9],
        }
        for f in data
    ])


@app.route("/passenger/<pnr>")
@login_required
def passenger(pnr):
    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?",
        (pnr,),
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        return jsonify({"message": "Passenger not found"}), 404

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT boarding_time FROM flights WHERE flight_id = ?", (data[2],))
    flight_row = cursor.fetchone()
    conn.close()

    boarding_time = flight_row[0] if flight_row else None

    return jsonify({
        "pnr": data[0],
        "name": data[1],
        "flight": data[2],
        "seat": data[3],
        "boarding_time": boarding_time,
        "device_id": data[4],
    })


# ============= PAGE ROUTES (HTML Views) =============
@app.route("/flight")
@login_required
def flight_page():
    """Flight management page."""
    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status FROM flights ORDER BY flight_id LIMIT 50")
    flights_data = cursor.fetchall()
    conn.close()

    return render_template(
        "flights_new.html",
        flights=flights_data,
    )

@app.route("/passenger")
@login_required
def passenger_page():
    """Passenger management page."""
    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id FROM passenger ORDER BY passenger_id")
    passengers_data = cursor.fetchall()
    conn.close()

    return render_template(
        "passengers_new.html",
        passengers=passengers_data,
    )

@app.route("/devices")
@login_required
def devices_page():
    """Devices management page."""
    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("SELECT device_id, device_type, status, last_sync FROM devices ORDER BY device_id LIMIT 50")
    devices_data = cursor.fetchall()
    conn.close()

    return render_template(
        "devices_new.html",
        devices=devices_data,
    )

@app.route("/notification")
@login_required
def notification_page():
    """Notifications page."""
    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("SELECT notification_id, message, notification_type, created_at FROM notifications ORDER BY created_at DESC LIMIT 100")
    notifications_data = cursor.fetchall()
    conn.close()

    return render_template(
        "notifications_new.html",
        notifications=notifications_data,
    )

@app.route("/staff")
@login_required
def staff_page():
    """Staff management page."""
    conn = get_db_connection("users")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, role, last_login FROM users ORDER BY user_id")
    staff_data = cursor.fetchall()
    conn.close()

    return render_template(
        "staff_new.html",
        staff=staff_data,
    )

@app.route("/reports")
@login_required
def reports():
    """Reports and analytics page."""
    return render_template("reports_new.html")


# ============= ADMIN USER MANAGEMENT (NOW WITH ROLE CHECK) =============
@app.route("/admin/users")
@require_admin
def admin_users():
    """Admin panel for user management."""
    conn = get_db_connection("users")
    cursor = conn.cursor()
    cursor.execute("SELECT username, role FROM users ORDER BY username")
    users = cursor.fetchall()
    conn.close()

    user_role = get_user_role(session.get("user"))
    
    return render_template("admin_users.html", users=users, api_key=API_KEY, user_role=user_role)


@app.route("/admin/add_user", methods=["POST"])
@require_admin
def add_user():
    """Add a new user."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "staff")

    # Validate
    valid_user, msg_user = validate_username(username)
    if not valid_user:
        flash(msg_user, "danger")
        return redirect(url_for("admin_users"))

    valid_pass, msg_pass = validate_password(password)
    if not valid_pass:
        flash(msg_pass, "danger")
        return redirect(url_for("admin_users"))

    conn = get_db_connection("users")
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        flash(f"User '{username}' already exists", "warning")
        conn.close()
        return redirect(url_for("admin_users"))

    password_hash = generate_password_hash(password)
    cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
    conn.commit()
    conn.close()

    log_user_action("ADD_USER", session.get("user"), "user", f"Username: {username}, Role: {role}")
    flash(f"User '{username}' created successfully with role '{role}'", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/delete_user", methods=["POST"])
@require_admin
def delete_user():
    """Delete a user."""
    username = request.form.get("username", "").strip()
    current_user = session.get("user")

    if username == current_user:
        flash("Cannot delete your own account", "danger")
        return redirect(url_for("admin_users"))

    conn = get_db_connection("users")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    log_user_action("DELETE_USER", session.get("user"), "user", f"Username: {username}")
    flash(f"User '{username}' deleted", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/change_password", methods=["POST"])
@require_admin
def change_password():
    """Change user password."""
    username = request.form.get("username", "").strip()
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("Passwords do not match", "danger")
        return redirect(url_for("admin_users"))

    valid_pass, msg_pass = validate_password(new_password)
    if not valid_pass:
        flash(msg_pass, "danger")
        return redirect(url_for("admin_users"))

    password_hash = generate_password_hash(new_password)
    conn = get_db_connection("users")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
    conn.commit()
    conn.close()

    log_user_action("CHANGE_PASSWORD", session.get("user"), "user", f"Username: {username}")
    flash(f"Password changed for user '{username}'", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/regenerate_api_key", methods=["POST"])
@require_admin
def regenerate_api_key():
    """Regenerate API key."""
    global API_KEY
    API_KEY = generate_api_key()
    
    # Update .env file
    env_content = open(".env", "r").read() if os.path.exists(".env") else ""
    lines = env_content.split("\n")
    updated_lines = []
    found = False
    
    for line in lines:
        if line.startswith("API_KEY="):
            updated_lines.append(f"API_KEY={API_KEY}")
            found = True
        else:
            updated_lines.append(line)
    
    if not found:
        updated_lines.append(f"API_KEY={API_KEY}")
    
    with open(".env", "w") as f:
        f.write("\n".join(updated_lines))
    
    log_user_action("REGENERATE_API_KEY", session.get("user"), "api", f"New key generated")
    flash(f"API Key regenerated", "success")
    return redirect(url_for("admin_users"))


# ============= UPGRADE 2: AUDIT LOG VIEWER =============
@app.route("/admin/audit_log")
@require_admin
def audit_log():
    """View audit log."""
    page = request.args.get("page", 1, type=int)
    limit = 50
    offset = (page - 1) * limit

    conn = get_db_connection("audit")
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM audit_log")
    total = cursor.fetchone()[0]
    
    # Get paginated logs
    cursor.execute(
        "SELECT id, timestamp, action, user, resource, status, details FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    logs = cursor.fetchall()
    conn.close()

    total_pages = (total + limit - 1) // limit

    user_role = get_user_role(session.get("user"))
    
    return render_template(
        "audit_log.html",
        logs=logs,
        current_page=page,
        total_pages=total_pages,
        total_logs=total,
        user_role=user_role
    )


# ============= DATA MANAGEMENT ROUTES (with role checks) =============
@app.route("/add_flight", methods=["POST"])
@login_required
def add_flight():
    flight_id = request.form.get("flight_id", "").strip()
    boarding_time = request.form.get("boarding_time", "").strip()
    departure = request.form.get("departure", "").strip()
    gate = request.form.get("gate", "").strip()
    status = request.form.get("status", "").strip()
    aircraft = request.form.get("aircraft", "").strip()
    origin = request.form.get("origin", "").strip()
    destination = request.form.get("destination", "").strip()
    display_time = request.form.get("display_time", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to add flights", "danger")
        return redirect(url_for("dashboard"))

    if not flight_id:
        flash("Flight ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO flights (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    log_user_action("ADD_FLIGHT", session.get("user"), "flight", f"Flight ID: {flight_id}")
    flash(f"Flight {flight_id} added/updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_device", methods=["POST"])
@login_required
def add_device():
    device_id = request.form.get("device_id", "").strip()
    mac_address = request.form.get("mac_address", "").strip()
    status = request.form.get("status", "").strip()
    battery_level = request.form.get("battery_level", "")
    signal_strength = request.form.get("signal_strength", "")

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to add devices", "danger")
        return redirect(url_for("dashboard"))

    if not device_id or not mac_address:
        flash("Device ID and MAC Address are required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO devices (device_id, mac_address, status, battery_level, signal_strength, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
        (device_id, mac_address, status, battery_level if battery_level else None, signal_strength if signal_strength else None, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    log_user_action("ADD_DEVICE", session.get("user"), "device", f"Device ID: {device_id}")
    flash(f"Device {device_id} added/updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_notification", methods=["POST"])
@login_required
def add_notification():
    message = request.form.get("message", "").strip()
    n_type = request.form.get("notification_type", "info")

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to add notifications", "danger")
        return redirect(url_for("dashboard"))

    if not message:
        flash("Message is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (message, type, created_at) VALUES (?, ?, ?)",
        (message, n_type, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    log_user_action("ADD_NOTIFICATION", session.get("user"), "notification", f"Type: {n_type}")
    flash("Notification added", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_passenger", methods=["POST"])
@login_required
def add_passenger():
    passenger_id = request.form.get("passenger_id", "").strip()
    name = request.form.get("name", "").strip()
    ticket_number = request.form.get("ticket_number", "").strip()
    flight_id = request.form.get("flight_id", "").strip()
    boarding_status = request.form.get("boarding_status", "").strip()
    seat_number = request.form.get("seat_number", "").strip()

    if not passenger_id or not name:
        flash("Passenger ID and Name are required", "danger")
        return redirect(url_for("dashboard"))

    try:
        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO passenger (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number) VALUES (?, ?, ?, ?, ?, ?)",
            (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number),
        )
        conn.commit()

        conn_devices = get_db_connection("devices")
        cursor_devices = conn_devices.cursor()
        cursor_devices.execute("SELECT device_id FROM devices WHERE status = 'active' LIMIT 1")
        available_device = cursor_devices.fetchone()
        
        if available_device:
            device_id = available_device[0]
            cursor.execute("UPDATE passenger SET device_id = ? WHERE passenger_id = ?", (device_id, passenger_id))
            cursor_devices.execute("UPDATE devices SET status = 'assigned' WHERE device_id = ?", (device_id,))
            flash(f"Passenger {passenger_id} added and assigned device {device_id}", "success")
        else:
            flash(f"Passenger {passenger_id} added, but no available device", "warning")

        conn.commit()
        conn_devices.commit()
        conn.close()
        conn_devices.close()

        log_user_action("ADD_PASSENGER", session.get("user"), "passenger", f"ID: {passenger_id}")

    except Exception as e:
        flash(f"Error adding passenger: {str(e)}", "danger")

    return redirect(url_for("dashboard"))


@app.route("/update", methods=["POST"])
@login_required
def update():
    flight = request.form.get("flight", "").strip()
    new_time = request.form.get("new_time", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to update flights", "danger")
        return redirect(url_for("dashboard"))

    if not flight or not new_time:
        flash("Flight and new time are required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("UPDATE flights SET boarding_time = ? WHERE flight_id = ?", (new_time, flight))
    conn.commit()
    conn.close()

    log_user_action("UPDATE_FLIGHT", session.get("user"), "flight", f"Flight: {flight}, Time: {new_time}")
    flash(f"Flight {flight} boarding time updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_device", methods=["POST"])
@login_required
def delete_device():
    device_id = request.form.get("device_id", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to delete devices", "danger")
        return redirect(url_for("dashboard"))

    if not device_id:
        flash("Device ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()

    log_user_action("DELETE_DEVICE", session.get("user"), "device", f"Device ID: {device_id}")
    flash(f"Device {device_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_flight", methods=["POST"])
@login_required
def delete_flight():
    flight_id = request.form.get("flight_id", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to delete flights", "danger")
        return redirect(url_for("dashboard"))

    if not flight_id:
        flash("Flight ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flights WHERE flight_id = ?", (flight_id,))
    conn.commit()
    conn.close()

    log_user_action("DELETE_FLIGHT", session.get("user"), "flight", f"Flight ID: {flight_id}")
    flash(f"Flight {flight_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_passenger", methods=["POST"])
@login_required
def delete_passenger():
    passenger_id = request.form.get("passenger_id", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to delete passengers", "danger")
        return redirect(url_for("dashboard"))

    if not passenger_id:
        flash("Passenger ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("passenger")
    cursor = conn.cursor()

    cursor.execute("SELECT device_id FROM passenger WHERE passenger_id = ?", (passenger_id,))
    row = cursor.fetchone()
    device_id = row[0] if row else None

    cursor.execute("DELETE FROM passenger WHERE passenger_id = ?", (passenger_id,))

    if device_id:
        conn_devices = get_db_connection("devices")
        cursor_devices = conn_devices.cursor()
        cursor_devices.execute("UPDATE devices SET status = 'active' WHERE device_id = ?", (device_id,))
        conn_devices.commit()
        conn_devices.close()

    conn.commit()
    conn.close()

    log_user_action("DELETE_PASSENGER", session.get("user"), "passenger", f"ID: {passenger_id}")
    flash(f"Passenger {passenger_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_notification", methods=["POST"])
@login_required
def delete_notification():
    notification_id = request.form.get("notification_id", "").strip()

    user_role = get_user_role(session.get("user"))
    if user_role == "staff":
        flash("You do not have permission to delete notifications", "danger")
        return redirect(url_for("dashboard"))

    if not notification_id:
        flash("Notification ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()

    log_user_action("DELETE_NOTIFICATION", session.get("user"), "notification", f"ID: {notification_id}")
    flash("Notification deleted", "success")
    return redirect(url_for("dashboard"))


# ============= ERROR HANDLING =============
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Log unhandled errors."""
    import traceback
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    log_path = os.path.join(os.path.dirname(__file__), "error.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - 500\n{tb}\n---\n")
    except:
        pass

    return f"<pre>{tb}</pre>", 500


# ============= MAIN =============
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7000, debug=False)
