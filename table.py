import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(__file__), "db")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATHS = {
    "flights": os.path.join(DB_DIR, "flights.db"),
    "passenger": os.path.join(DB_DIR, "passenger.db"),
    "devices": os.path.join(DB_DIR, "devices.db"),
    "notifications": os.path.join(DB_DIR, "notifications.db"),
    "users": os.path.join(DB_DIR, "users.db"),
}

for name, path in DB_PATHS.items():
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    if name == "flights":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights(
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
        )
        """)

    elif name == "passenger":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS passenger(
            passenger_id TEXT PRIMARY KEY,
            name TEXT,
            ticket_number TEXT,
            flight_id TEXT,
            boarding_status TEXT,
            seat_number TEXT,
            device_id TEXT
        )
        """)

    elif name == "devices":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices(
            device_id TEXT PRIMARY KEY,
            mac_address TEXT,
            status TEXT,
            battery_level INTEGER,
            signal_strength INTEGER,
            last_seen TEXT
        )
        """)

    elif name == "notifications":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            type TEXT,
            created_at TEXT
        )
        """)

    elif name == "users":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
        """)

    conn.commit()
    conn.close()

print("Tables created")