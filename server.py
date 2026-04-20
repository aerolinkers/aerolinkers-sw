from functools import wraps
import logging

from flask import (
    Flask,
    request,
    jsonify,
    render_template_string,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)
from jinja2 import DictLoader
from werkzeug.security import check_password_hash, generate_password_hash
from gtts import gTTS
from pydub import AudioSegment
import io
import os
import sqlite3
import datetime
import pytz

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-to-a-secure-random-value")

# Default credentials
DEFAULT_USERNAME = "Aerolinkers"
DEFAULT_PASSWORD = "Aerolinkers123"

# Audio folder setup
BASE_DIR = os.path.dirname(__file__)
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# Timezone
IST = pytz.timezone('Asia/Kolkata')

# Templates stored in memory so the app works without a templates folder.
app.jinja_loader = DictLoader(
    {
        "base.html": """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{% block title %}Airport Smart Band{% endblock %}</title>

    <!-- Bootstrap (CDN) -->
    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css\" rel=\"stylesheet\" crossorigin=\"anonymous\"> 

    <style>
      body {
        min-height: 100vh;
        background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?ixlib=rb-4.0.3&auto=format&fit=crop&w=1950&q=80') no-repeat center center fixed;
        background-size: cover;
        color: #333;
      }

      .brand {
        font-weight: 700;
        letter-spacing: 0.07em;
      }

      .card {
        border: 0;
        border-radius: 14px;
        box-shadow: 0 10px 35px rgba(46, 61, 73, 0.12);
      }

      .form-control:focus {
        box-shadow: 0 0 0 0.2rem rgba(9, 132, 227, 0.25);
      }

      footer {
        font-size: 0.85rem;
        color: #6c757d;
      }
    </style>

    {% block extra_head %}{% endblock %}
  </head>
  <body>
    <nav class=\"navbar navbar-expand-lg navbar-light bg-white shadow-sm\">
      <div class=\"container-xl\">
        <a class=\"navbar-brand brand\" href=\"{{ url_for('dashboard') }}\">Airport Smart Band</a>
        <div class=\"collapse navbar-collapse\">
          <ul class=\"navbar-nav ms-auto\">
            {% if session.get('user') %}
            <li class=\"nav-item\">
              <a class=\"nav-link\" href=\"{{ url_for('logout') }}\">Logout</a>
            </li>
            {% endif %}
          </ul>
        </div>
      </div>
    </nav>

    <main class=\"container-xl py-5\">
      {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
      <div class=\"row justify-content-center mb-4\">
        <div class=\"col-md-8\">
          {% for category, message in messages %}
          <div class=\"alert alert-{{ category }} alert-dismissible fade show\" role=\"alert\">
            {{ message }}
            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %}
      {% endwith %}

      {% block content %}{% endblock %}
    </main>

    <footer class=\"text-center py-4\">
      <div class=\"container\">
        <span class=\"text-muted\">© {{ config.get('APP_NAME', 'Airport Smart Band') }} {{ current_year }}</span>
      </div>
    </footer>

    <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js\" crossorigin=\"anonymous\"></script>
    {% block extra_scripts %}{% endblock %}
  </body>
</html>
""",
        "login.html": """{% extends 'base.html' %}

{% block title %}Login – Airport Smart Band{% endblock %}

{% block content %}
<div class=\"row justify-content-center\">
  <div class=\"col-md-6 col-lg-5\">
    <div class=\"card p-4\">
      <h3 class=\"mb-3 text-center\">Sign in</h3>
      <form method=\"post\" novalidate>
        <div class=\"mb-3\">
          <label for=\"username\" class=\"form-label\">Username</label>
          <input
            id=\"username\"
            name=\"username\"
            type=\"text\"
            class=\"form-control\"
            placeholder="Enter username"
            autocomplete="username"
            required
          />
        </div>

        <div class=\"mb-3\">
          <label for=\"password\" class=\"form-label\">Password</label>
          <input
            id=\"password\"
            name=\"password\"
            type=\"password\"
            class=\"form-control\"
            placeholder="Enter password"
            autocomplete="current-password"
            required
          />
        </div>

        <button type=\"submit\" class=\"btn btn-primary w-100\">Login</button>
      </form>

      <div class=\"text-muted text-center mt-3\">
        Enter your login credentials.
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
        "dashboard.html": """{% extends 'base.html' %}

{% block title %}Dashboard – Airport Smart Band{% endblock %}

{% block content %}
<div class=\"row mb-4\">
  <div class=\"col-md-3\">
    <div class=\"card p-3 shadow-sm\">
      <div class=\"d-flex align-items-center\">
        <div class=\"me-3\">
          <div class=\"bg-primary rounded-circle text-white d-flex align-items-center justify-content-center\" style=\"width:44px;height:44px;\">
            <span class=\"fs-4\">📱</span>
          </div>
        </div>
        <div>
          <div class=\"text-muted\">Total Devices</div>
          <div class=\"fs-4 fw-bold\">{{ total_devices }}</div>
        </div>
      </div>
    </div>
  </div>
  <div class=\"col-md-3\">
    <div class=\"card p-3 shadow-sm\">
      <div class=\"d-flex align-items-center\">
        <div class=\"me-3\">
          <div class=\"bg-success rounded-circle text-white d-flex align-items-center justify-content-center\" style=\"width:44px;height:44px;\">
            <span class=\"fs-4\">✅</span>
          </div>
        </div>
        <div>
          <div class=\"text-muted\">Active Devices</div>
          <div class=\"fs-4 fw-bold\">{{ active_devices }}</div>
        </div>
      </div>
    </div>
  </div>
  <div class=\"col-md-3\">
    <div class=\"card p-3 shadow-sm\">
      <div class=\"d-flex align-items-center\">
        <div class=\"me-3\">
          <div class=\"bg-info rounded-circle text-white d-flex align-items-center justify-content-center\" style=\"width:44px;height:44px;\">
            <span class=\"fs-4\">✈️</span>
          </div>
        </div>
        <div>
          <div class=\"text-muted\">Total Flights</div>
          <div class=\"fs-4 fw-bold\">{{ total_flights }}</div>
        </div>
      </div>
    </div>
  </div>
  <div class=\"col-md-3\">
    <div class=\"card p-3 shadow-sm\">
      <div class=\"d-flex align-items-center\">
        <div class=\"me-3\">
          <div class=\"bg-warning rounded-circle text-white d-flex align-items-center justify-content-center\" style=\"width:44px;height:44px;\">
            <span class=\"fs-4\">🔔</span>
          </div>
        </div>
        <div>
          <div class=\"text-muted\">Notifications</div>
          <div class=\"fs-4 fw-bold\">{{ notifications|length }}</div>
        </div>
      </div>
    </div>
  </div>
</div>

{% if passenger %}
<div class=\"row mb-4\">
  <div class=\"col-12\">
    <div class=\"card\">
      <div class=\"card-header\">
        <h5>Passenger Search Result</h5>
      </div>
      <div class=\"card-body\">
        <p><strong>PNR:</strong> {{ passenger[0] }}</p>
        <p><strong>Name:</strong> {{ passenger[1] }}</p>
        <p><strong>Flight:</strong> {{ passenger[2] }}</p>
        <p><strong>Seat:</strong> {{ passenger[3] }}</p>
        <p><strong>Boarding Time:</strong> {{ passenger[4] }}</p>
        <p><strong>Device:</strong> {{ passenger[5] or '-' }}</p>
        <div class=\"mt-3\">
          <form method="post" action="{{ url_for('delete_passenger') }}" class="d-inline">
            <input type="hidden" name="passenger_id" value="{{ passenger[0] }}">
            <button class="btn btn-outline-danger btn-sm" type="submit" onclick="return confirm('Are you sure you want to delete this passenger?')">Delete Passenger</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
{% endif %}

<div class=\"row\">
  <div class=\"col-lg-8\">
    <div class=\"card mb-4\">
      <div class=\"card-header\">
        <ul class=\"nav nav-tabs card-header-tabs\" role=\"tablist\">
          <li class=\"nav-item\">
            <a class=\"nav-link active\" data-bs-toggle=\"tab\" href=\"#devices\" role=\"tab\">Devices</a>
          </li>
          <li class=\"nav-item\">
            <a class=\"nav-link\" data-bs-toggle=\"tab\" href=\"#flights\" role=\"tab\">Flights</a>
          </li>
          <li class=\"nav-item\">
            <a class=\"nav-link\" data-bs-toggle=\"tab\" href=\"#passengers\" role=\"tab\">Passengers</a>
          </li>
          <li class=\"nav-item\">
            <a class=\"nav-link\" data-bs-toggle=\"tab\" href=\"#notifications\" role=\"tab\">Notifications</a>
          </li>
        </ul>
      </div>
      <div class=\"card-body tab-content\">
        <div class=\"tab-pane fade show active\" id=\"devices\" role=\"tabpanel\">
          <h5 class=\"card-title\">Devices</h5>
          <p class=\"text-muted\">List of registered devices.</p>
          <div class=\"table-responsive\">
            <table class=\"table table-sm table-hover\">
              <thead>
                <tr>
                  <th>Device ID</th>
                  <th>MAC Address</th>
                  <th>Status</th>
                  <th>Battery</th>
                  <th>Signal</th>
                  <th>Last Seen</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {% for device in devices %}
                <tr>
                  <td>{{ device[0] }}</td>
                  <td>{{ device[1] }}</td>
                  <td>{{ device[2] or 'unknown' }}</td>
                  <td>{{ device[3] if device[3] is not none else '-' }}%</td>
                  <td>{{ device[4] if device[4] is not none else '-' }} dBm</td>
                  <td>{{ device[5][:16].replace('T', ' ') if device[5] else '-' }}</td>
                  <td>
                    <form method="post" action="{{ url_for('delete_device') }}" class="d-inline">
                      <input type="hidden" name="device_id" value="{{ device[0] }}">
                      <button class="btn btn-outline-danger btn-sm" type="submit" onclick="return confirm('Are you sure?')">Delete</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <hr>
          <h6>Add New Device</h6>
          <form method=\"post\" action=\"{{ url_for('add_device') }}\" class=\"row g-3\">
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"device_id\" class=\"form-control\" placeholder=\"Device ID\" required>
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"mac_address\" class=\"form-control\" placeholder=\"MAC Address\" required>
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"status\" class=\"form-control\" placeholder=\"Status\" value=\"active\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"number\" name=\"battery_level\" class=\"form-control\" placeholder=\"Battery Level\" min=\"0\" max=\"100\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"number\" name=\"signal_strength\" class=\"form-control\" placeholder=\"Signal Strength\" min=\"-100\" max=\"0\">
            </div>
            <div class=\"col-12\">
              <button type=\"submit\" class=\"btn btn-primary\">Add Device</button>
            </div>
          </form>
        </div>

        <div class=\"tab-pane fade\" id=\"flights\" role=\"tabpanel\">
          <h5 class=\"card-title\">Flights</h5>
          <div class=\"table-responsive\">
            <table class=\"table table-sm table-hover\">
              <thead>
                <tr>
                  <th>Flight</th>
                  <th>Departure</th>
                  <th>Gate</th>
                  <th>Status</th>
                  <th>Boarding</th>
                  <th class=\"text-end\">Update</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {% for flight, boarding, departure, gate, status in flights %}
                <tr>
                  <td>{{ flight }}</td>
                  <td>{{ departure or '-' }}</td>
                  <td>{{ gate or '-' }}</td>
                  <td>{{ status or '-' }}</td>
                  <td>{{ boarding }}</td>
                  <td class=\"text-end\">
                    <form method=\"post\" action=\"{{ url_for('update') }}\" class=\"d-inline\">
                      <input type=\"hidden\" name=\"flight\" value=\"{{ flight }}\">
                      <div class=\"input-group input-group-sm\">
                        <input type=\"text\" name=\"new_time\" class=\"form-control\" placeholder=\"HH:MM\" value=\"{{ boarding }}\" required>
                        <button class=\"btn btn-outline-primary btn-sm\" type=\"submit\">Update</button>
                      </div>
                    </form>
                  </td>
                  <td>
                    <form method="post" action="{{ url_for('delete_flight') }}" class="d-inline">
                      <input type="hidden" name="flight_id" value="{{ flight }}">
                      <button class="btn btn-outline-danger btn-sm" type="submit" onclick="return confirm('Are you sure?')">Delete</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <hr>
          <h6>Add New Flight</h6>
          <form method=\"post\" action=\"{{ url_for('add_flight') }}\" class=\"row g-3\">
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"flight_id\" class=\"form-control\" placeholder=\"Flight ID\" required>
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"boarding_time\" class=\"form-control\" placeholder=\"Boarding Time (HH:MM)\" required>
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"departure\" class=\"form-control\" placeholder=\"Departure\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"gate\" class=\"form-control\" placeholder=\"Gate\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"status\" class=\"form-control\" placeholder=\"Status\" value=\"On Time\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"aircraft\" class=\"form-control\" placeholder=\"Aircraft\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"origin\" class=\"form-control\" placeholder=\"Origin\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"destination\" class=\"form-control\" placeholder=\"Destination\">
            </div>
            <div class=\"col-md-3\">
              <input type=\"text\" name=\"display_time\" class=\"form-control\" placeholder=\"Display Time\">
            </div>
            <div class=\"col-12\">
              <button type=\"submit\" class=\"btn btn-primary\">Add Flight</button>
            </div>
          </form>
        </div>

        <div class=\"tab-pane fade\" id=\"passengers\" role=\"tabpanel\">
          <h5 class=\"card-title\">Passengers</h5>
          <p class=\"text-muted\">List of registered passengers.</p>
          <div class=\"table-responsive\">
            <table class=\"table table-sm table-hover\">
              <thead>
                <tr>
                  <th>Passenger ID</th>
                  <th>Name</th>
                  <th>Ticket Number</th>
                  <th>Flight ID</th>
                  <th>Boarding Status</th>
                  <th>Seat Number</th>
                  <th>Device ID</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {% for passenger in passengers %}
                <tr>
                  <td>{{ passenger[0] }}</td>
                  <td>{{ passenger[1] }}</td>
                  <td>{{ passenger[2] }}</td>
                  <td>{{ passenger[3] }}</td>
                  <td>{{ passenger[4] }}</td>
                  <td>{{ passenger[5] }}</td>
                  <td>{{ passenger[6] or '-' }}</td>
                  <td>
                    <form method="post" action="{{ url_for('delete_passenger') }}" class="d-inline">
                      <input type="hidden" name="passenger_id" value="{{ passenger[0] }}">
                      <button class="btn btn-outline-danger btn-sm" type="submit" onclick="return confirm('Are you sure?')">Delete</button>
                    </form>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <hr>
          <h6>Add New Passenger</h6>
          <form method=\"post\" action=\"{{ url_for('add_passenger') }}\" class=\"row g-3\">
            <div class=\"col-md-6\">
              <input type=\"text\" name=\"passenger_id\" class=\"form-control\" placeholder=\"Passenger ID\" required>
            </div>
            <div class=\"col-md-6\">
              <input type=\"text\" name=\"name\" class=\"form-control\" placeholder=\"Name\" required>
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"ticket_number\" class=\"form-control\" placeholder=\"Ticket Number\">
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"flight_id\" class=\"form-control\" placeholder=\"Flight ID\">
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"boarding_status\" class=\"form-control\" placeholder=\"Boarding Status\" value=\"Waiting\">
            </div>
            <div class=\"col-md-4\">
              <input type=\"text\" name=\"seat_number\" class=\"form-control\" placeholder=\"Seat Number\">
            </div>
            <div class=\"col-12\">
              <button type=\"submit\" class=\"btn btn-primary\">Add Passenger</button>
            </div>
          </form>
        </div>

        <div class=\"tab-pane fade\" id=\"notifications\" role=\"tabpanel\">
          <h5 class=\"card-title\">Recent Notifications</h5>
          {% if notifications %}
          <div class=\"list-group\">
            {% for n in notifications %}
            <div class=\"list-group-item list-group-item-action py-3\">
              <div class=\"d-flex w-100 justify-content-between\">
                <h6 class=\"mb-1\">{{ n[1] }}</h6>
                <div>
                  <small class=\"text-muted\">{{ n[3][:16].replace('T', ' ') }}</small>
                  <form method="post" action="{{ url_for('delete_notification') }}" class="d-inline ms-2">
                    <input type="hidden" name="notification_id" value="{{ n[0] }}">
                    <button class="btn btn-outline-danger btn-sm" type="submit" onclick="return confirm('Are you sure?')">Delete</button>
                  </form>
                </div>
              </div>
              <small class=\"text-muted\">Type: {{ n[2] }}</small>
            </div>
            {% endfor %}
          </div>
          {% else %}
          <p class=\"text-muted\">No notifications yet.</p>
          {% endif %}
          <hr>
          <h6>Add New Notification</h6>
          <form method=\"post\" action=\"{{ url_for('add_notification') }}\" class=\"row g-3\">
            <div class=\"col-md-8\">
              <input type=\"text\" name=\"message\" class=\"form-control\" placeholder=\"Notification Message\" required>
            </div>
            <div class=\"col-md-4\">
              <select name=\"type\" class=\"form-select\">
                <option value=\"info\">Info</option>
                <option value=\"warning\">Warning</option>
                <option value=\"error\">Error</option>
              </select>
            </div>
            <div class=\"col-12\">
              <button type=\"submit\" class=\"btn btn-primary\">Add Notification</button>
            </div>
          </form>
        </div>
{% endblock %}
""",
    }
)

# ── Database ──────────────────────────────────────────────────────────────────
DB_DIR = os.path.join(os.path.dirname(__file__), "db")
os.makedirs(DB_DIR, exist_ok=True)

DB_FILES = {
    "flights": os.path.join(DB_DIR, "flights.db"),
    "passenger": os.path.join(DB_DIR, "passenger.db"),
    "devices": os.path.join(DB_DIR, "devices.db"),
    "notifications": os.path.join(DB_DIR, "notifications.db"),
    "users": os.path.join(DB_DIR, "users.db"),
}

NO_AUTH_ENDPOINTS = {"login", "static", "sync", "get_device_notifications", "serve_audio", "device_init"}


def get_db_connection(db_name: str):
    path = DB_FILES.get(db_name)
    if not path:
        raise ValueError(f"Unknown database name: {db_name}")
    conn = sqlite3.connect(path)
    # Create indexes for faster lookups on passenger table
    if db_name == "passenger":
        conn.execute("CREATE INDEX IF NOT EXISTS idx_passenger_device ON passenger(device_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_passenger_flight ON passenger(flight_id)")
        conn.commit()
    return conn


def init_db():
    def init(db_name, create_stmts):
        conn = sqlite3.connect(DB_FILES[db_name])
        cursor = conn.cursor()
        for stmt in create_stmts:
            cursor.execute(stmt)
        conn.commit()
        conn.close()

    init("flights", ["CREATE TABLE IF NOT EXISTS flights(flight_id TEXT PRIMARY KEY, boarding_time TEXT, departure TEXT, gate TEXT, status TEXT, aircraft TEXT, origin TEXT, destination TEXT, display_time TEXT, last_update TEXT)"])
    init("passenger", ["CREATE TABLE IF NOT EXISTS passenger(passenger_id TEXT PRIMARY KEY, name TEXT, ticket_number TEXT, flight_id TEXT, boarding_status TEXT, seat_number TEXT, device_id TEXT)"])
    init("devices", ["CREATE TABLE IF NOT EXISTS devices(device_id TEXT PRIMARY KEY, mac_address TEXT, status TEXT, battery_level INTEGER, signal_strength INTEGER, last_seen TEXT)"])
    init("notifications", ["CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, type TEXT, created_at TEXT)"])
    init("users", ["CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password_hash TEXT)"])

    conn = get_db_connection("users")
    conn.cursor().execute("INSERT OR REPLACE INTO users(username, password_hash) VALUES (?, ?)", (DEFAULT_USERNAME, generate_password_hash(DEFAULT_PASSWORD)))
    conn.commit()
    conn.close()

    conn = get_db_connection("flights")
    conn.cursor().executemany(
        "INSERT OR IGNORE INTO flights (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("AI202", "18:30", "19:00", "Gate 12", "On Time", "Boeing 737", "Delhi", "Mumbai", "18:30", "2023-10-01 10:00:00"),
            ("AI305", "19:00", "19:30", "Gate 15", "Delayed", "Airbus A320", "Mumbai", "Bangalore", "19:15", "2023-10-01 10:30:00"),
        ],
    )
    conn.commit()
    conn.close()

    conn = get_db_connection("passenger")
    conn.cursor().executemany(
        "INSERT OR IGNORE INTO passenger (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("TB2376", "Thiru", "TB2376", "AI202", "Boarded", "12B", None),
            ("AB1234", "John Doe", "AB1234", "AI305", "Waiting", "14A", None),
        ],
    )
    conn.commit()
    conn.close()

    conn = get_db_connection("devices")
    devices_data = [(f"DEV{i:03d}", f"08:3A:F2:A8:31:{i:02X}", "active", 95, -45, datetime.datetime.now().isoformat()) for i in range(1, 31)]
    conn.cursor().executemany("INSERT OR IGNORE INTO devices (device_id, mac_address, status, battery_level, signal_strength, last_seen) VALUES (?, ?, ?, ?, ?, ?)", devices_data)
    conn.commit()
    conn.close()

    conn = get_db_connection("notifications")
    conn.cursor().executemany(
        "INSERT OR IGNORE INTO notifications (message, type, created_at) VALUES (?, ?, ?)",
        [
            ("Flight AI202 boarding now", "info", datetime.datetime.now().isoformat()),
            ("Device DEV001 battery low", "warning", datetime.datetime.now().isoformat()),
        ],
    )
    conn.commit()
    conn.close()


try:
    init_db()
except Exception as e:
    logger.error(f"DB init error: {e}")


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.before_request
def require_login():
    if request.endpoint in NO_AUTH_ENDPOINTS or request.endpoint is None:
        return
    if "user" not in session:
        return redirect(url_for("login"))


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


# ── TTS ───────────────────────────────────────────────────────────────────────
def get_audio_cache_path(audio_id):
    """Return a date-stamped WAV path so stale audio is refreshed daily."""
    date_str = datetime.datetime.now(IST).strftime("%Y%m%d")
    return os.path.join(AUDIO_FOLDER, f"{audio_id}_{date_str}.wav")


def generate_tts(message, filepath):
    """
    Generate TTS audio as a true WAV file.
    Uses gTTS to produce MP3 in memory, then converts to WAV via pydub.
    Requires ffmpeg installed on the system.
    Skips generation if the file already exists.
    """
    if not os.path.exists(filepath):
        try:
            tts = gTTS(text=message, lang='en')
            mp3_buffer = io.BytesIO()
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)
            audio = AudioSegment.from_mp3(mp3_buffer)
            audio.export(filepath, format="wav")
            logger.info(f"Audio saved: {filepath}")
        except Exception as e:
            logger.error(f"TTS Error: {e}")


# ── Boarding alert ────────────────────────────────────────────────────────────
def check_boarding_alert(flight_id, destination, gate, boarding_time_str):
    """
    Returns alert message if current IST time is within
    30 minutes before boarding time, else returns None.
    Supports formats: HH:MM / YYYY-MM-DD HH:MM / YYYY-MM-DD HH:MM:SS
    """
    try:
        now = datetime.datetime.now(IST)

        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M"):
            try:
                parsed = datetime.datetime.strptime(boarding_time_str, fmt)
                break
            except ValueError:
                continue

        if parsed is None:
            logger.warning(f"Could not parse boarding_time: {boarding_time_str}")
            return None

        if parsed.year == 1900:
            parsed = parsed.replace(year=now.year, month=now.month, day=now.day)

        boarding_time = IST.localize(parsed)
        trigger_time = boarding_time - datetime.timedelta(minutes=30)

        logger.info(f"Current Time:  {now} | Boarding: {boarding_time} | Trigger: {trigger_time}")

        if trigger_time <= now <= boarding_time:
            return f"Boarding starts soon for flight {flight_id} to {destination}. Please proceed to Gate {gate}."

        return None

    except Exception as e:
        logger.error(f"Boarding Alert Error: {e}")
        return None


# ── Device API ────────────────────────────────────────────────────────────────
@app.route("/api/notifications/<device_id>", methods=["GET"])
def get_device_notifications(device_id):
    """Get boarding alert notifications for a device."""
    try:
        notifications = []

        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute("SELECT flight_id FROM passenger WHERE device_id = ?", (device_id,))
        passenger = cursor.fetchone()
        conn.close()

        if passenger:
            flight_id = passenger[0]

            conn = get_db_connection("flights")
            cursor = conn.cursor()
            cursor.execute("SELECT flight_id, destination, gate, boarding_time FROM flights WHERE flight_id = ?", (flight_id,))
            flight = cursor.fetchone()
            conn.close()

            if flight:
                flight_id, destination, gate, boarding_time = flight
                message = check_boarding_alert(flight_id, destination, gate, boarding_time)

                if message:
                    audio_id = f"alert_{device_id}"
                    audio_filepath = get_audio_cache_path(audio_id)
                    generate_tts(message, audio_filepath)
                    audio_filename = os.path.basename(audio_filepath).replace(".wav", "")
                    notifications.append({
                        "id": audio_id,
                        "message": message,
                        "audio_url": f"/api/audio/{audio_filename}",
                        "priority": "high",
                        "poll_after_seconds": 60
                    })

        return jsonify(notifications), 200

    except Exception as e:
        logger.error(f"get_device_notifications error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audio/<file_id>", methods=["GET"])
def serve_audio(file_id):
    """Serve WAV audio files."""
    try:
        filename = f"{file_id}.wav"
        filepath = os.path.join(AUDIO_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Audio file not found"}), 404
        return send_from_directory(AUDIO_FOLDER, filename)
    except Exception as e:
        logger.error(f"serve_audio error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/device/init/<device_id>", methods=["GET"])
def device_init(device_id):
    """Initialize device — fetch passenger info and generate welcome TTS."""
    try:
        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute("SELECT name, passenger_id FROM passenger WHERE device_id = ?", (device_id,))
        passenger = cursor.fetchone()
        conn.close()

        if not passenger:
            return jsonify({"status": "not_found"}), 404

        name, pnr = passenger
        message = f"Welcome {name}. Your PNR number is {pnr}."
        audio_id = f"init_{device_id}"
        audio_filepath = get_audio_cache_path(audio_id)
        generate_tts(message, audio_filepath)
        audio_filename = os.path.basename(audio_filepath).replace(".wav", "")

        return jsonify({
            "name": name,
            "pnr": pnr,
            "message": message,
            "audio_url": f"/api/audio/{audio_filename}"
        }), 200

    except Exception as e:
        logger.error(f"device_init error: {e}")
        return jsonify({"error": str(e)}), 500


# ── Web routes ────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection("users")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["user"] = username
            return redirect(url_for("dashboard"))

        flash("Invalid username or password", "danger")

    return render_template_string(
        "{% include 'login.html' %}",
        current_year=datetime.datetime.now().year,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'active'")
    active_devices = cursor.fetchone()[0]
    cursor.execute("SELECT device_id, mac_address, status, battery_level, signal_strength, last_seen FROM devices")
    devices = cursor.fetchall()
    conn.close()

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    total_flights = cursor.fetchone()[0]
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status FROM flights ORDER BY flight_id")
    flights = cursor.fetchall()
    conn.close()

    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("SELECT id, message, type, created_at FROM notifications ORDER BY id DESC LIMIT 10")
    notifications = cursor.fetchall()
    conn.close()

    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id FROM passenger ORDER BY passenger_id")
    passengers = cursor.fetchall()
    conn.close()

    return render_template_string(
        "{% include 'dashboard.html' %}",
        total_devices=total_devices,
        active_devices=active_devices,
        total_flights=total_flights,
        devices=devices,
        notifications=notifications,
        flights=flights,
        passengers=passengers,
        passenger=None,
        current_year=datetime.datetime.now().year,
    )


@app.route("/search", methods=["POST"])
@login_required
def search():
    pnr = request.form.get("pnr")
    if not pnr:
        flash("PNR is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("devices")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM devices")
    total_devices = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'active'")
    active_devices = cursor.fetchone()[0]
    cursor.execute("SELECT device_id, mac_address, status, battery_level, signal_strength, last_seen FROM devices")
    devices = cursor.fetchall()
    conn.close()

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    total_flights = cursor.fetchone()[0]
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status FROM flights ORDER BY flight_id")
    flights = cursor.fetchall()
    conn.close()

    conn = get_db_connection("notifications")
    cursor = conn.cursor()
    cursor.execute("SELECT id, message, type, created_at FROM notifications ORDER BY id DESC LIMIT 10")
    notifications = cursor.fetchall()
    conn.close()

    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id FROM passenger ORDER BY passenger_id")
    passengers = cursor.fetchall()
    cursor.execute("SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?", (pnr,))
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

    return render_template_string(
        "{% include 'dashboard.html' %}",
        total_devices=total_devices,
        active_devices=active_devices,
        total_flights=total_flights,
        devices=devices,
        notifications=notifications,
        flights=flights,
        passengers=passengers,
        passenger=passenger,
        search_pnr=pnr,
        current_year=datetime.datetime.now().year,
    )


@app.route("/sync", methods=["POST"])
def sync():
    try:
        data = request.get_json(force=True, silent=True) or {}
        mac = data.get("device_id", "").strip()
        pnr = data.get("pnr", "").strip()

        if not mac or not pnr:
            return jsonify({"message": "device_id and pnr are required"}), 400

        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute("SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?", (pnr,))
        passenger = cursor.fetchone()
        conn.close()

        if not passenger:
            return jsonify({"message": "Passenger not found"}), 404

        conn = get_db_connection("flights")
        cursor = conn.cursor()
        cursor.execute("SELECT boarding_time FROM flights WHERE flight_id = ?", (passenger[2],))
        flight_row = cursor.fetchone()
        conn.close()

        return jsonify({
            "device_id": mac,
            "pnr": passenger[0],
            "name": passenger[1],
            "flight": passenger[2],
            "seat": passenger[3],
            "boarding_time": flight_row[0] if flight_row else None,
        })

    except Exception as e:
        logger.error(f"sync error: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500


@app.route("/flights")
@login_required
def flights():
    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update FROM flights")
    data = cursor.fetchall()
    conn.close()
    return jsonify([{"flight_id": f[0], "boarding_time": f[1], "departure": f[2], "gate": f[3], "status": f[4], "aircraft": f[5], "origin": f[6], "destination": f[7], "display_time": f[8], "last_update": f[9]} for f in data])


@app.route("/passenger/<pnr>")
@login_required
def passenger(pnr):
    conn = get_db_connection("passenger")
    cursor = conn.cursor()
    cursor.execute("SELECT passenger_id, name, flight_id, seat_number, device_id FROM passenger WHERE passenger_id = ?", (pnr,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return jsonify({"message": "Passenger not found"}), 404

    conn = get_db_connection("flights")
    cursor = conn.cursor()
    cursor.execute("SELECT boarding_time FROM flights WHERE flight_id = ?", (data[2],))
    flight_row = cursor.fetchone()
    conn.close()

    return jsonify({"pnr": data[0], "name": data[1], "flight": data[2], "seat": data[3], "boarding_time": flight_row[0] if flight_row else None, "device_id": data[4]})


@app.route("/add_flight", methods=["POST"])
@login_required
def add_flight():
    flight_id = request.form.get("flight_id")
    if not flight_id:
        flash("Flight ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    conn.cursor().execute(
        "INSERT OR REPLACE INTO flights (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (flight_id, request.form.get("boarding_time"), request.form.get("departure"), request.form.get("gate"),
         request.form.get("status"), request.form.get("aircraft"), request.form.get("origin"),
         request.form.get("destination"), request.form.get("display_time"), datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    flash(f"Flight {flight_id} added/updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_device", methods=["POST"])
@login_required
def add_device():
    device_id = request.form.get("device_id")
    mac_address = request.form.get("mac_address")
    if not device_id or not mac_address:
        flash("Device ID and MAC Address are required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("devices")
    conn.cursor().execute(
        "INSERT OR REPLACE INTO devices (device_id, mac_address, status, battery_level, signal_strength, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
        (device_id, mac_address, request.form.get("status"), request.form.get("battery_level"), request.form.get("signal_strength"), datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    flash(f"Device {device_id} added/updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_notification", methods=["POST"])
@login_required
def add_notification():
    message = request.form.get("message")
    if not message:
        flash("Message is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("notifications")
    conn.cursor().execute("INSERT INTO notifications (message, type, created_at) VALUES (?, ?, ?)", (message, request.form.get("type") or "info", datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    flash("Notification added", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_passenger", methods=["POST"])
@login_required
def add_passenger():
    passenger_id = request.form.get("passenger_id")
    name = request.form.get("name")
    if not passenger_id or not name:
        flash("Passenger ID and Name are required", "danger")
        return redirect(url_for("dashboard"))

    try:
        conn = get_db_connection("passenger")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO passenger (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number) VALUES (?, ?, ?, ?, ?, ?)",
            (passenger_id, name, request.form.get("ticket_number"), request.form.get("flight_id"), request.form.get("boarding_status"), request.form.get("seat_number")),
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
            flash(f"Passenger {passenger_id} added, but no available device to assign", "warning")

        conn.commit()
        conn_devices.commit()
        conn.close()
        conn_devices.close()

    except Exception as e:
        logger.error(f"add_passenger error: {e}")
        flash(f"Error adding passenger: {str(e)}", "danger")

    return redirect(url_for("dashboard"))


@app.route("/update", methods=["POST"])
@login_required
def update():
    flight = request.form.get("flight")
    new_time = request.form.get("new_time")
    if not flight or not new_time:
        flash("Flight and new time are required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    conn.cursor().execute("UPDATE flights SET boarding_time = ? WHERE flight_id = ?", (new_time, flight))
    conn.commit()
    conn.close()
    flash(f"Flight {flight} boarding time updated", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_device", methods=["POST"])
@login_required
def delete_device():
    device_id = request.form.get("device_id")
    if not device_id:
        flash("Device ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("devices")
    conn.cursor().execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()
    flash(f"Device {device_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_flight", methods=["POST"])
@login_required
def delete_flight():
    flight_id = request.form.get("flight_id")
    if not flight_id:
        flash("Flight ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("flights")
    conn.cursor().execute("DELETE FROM flights WHERE flight_id = ?", (flight_id,))
    conn.commit()
    conn.close()
    flash(f"Flight {flight_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_passenger", methods=["POST"])
@login_required
def delete_passenger():
    passenger_id = request.form.get("passenger_id")
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
        conn_devices.cursor().execute("UPDATE devices SET status = 'active' WHERE device_id = ?", (device_id,))
        conn_devices.commit()
        conn_devices.close()

    conn.commit()
    conn.close()
    flash(f"Passenger {passenger_id} deleted", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_notification", methods=["POST"])
@login_required
def delete_notification():
    notification_id = request.form.get("notification_id")
    if not notification_id:
        flash("Notification ID is required", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection("notifications")
    conn.cursor().execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()
    flash("Notification deleted", "success")
    return redirect(url_for("dashboard"))


# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    log_path = os.path.join(os.path.dirname(__file__), "error.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - 500\n{tb}\n---\n")
    except Exception:
        pass
    logger.error(f"500 error: {tb}")
    return f"<pre>{tb}</pre>", 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7000, debug=False)