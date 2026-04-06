import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_DIR = os.path.join(os.path.dirname(__file__), "db")

DB_PATHS = {
    "flights": os.path.join(DB_DIR, "flights.db"),
    "passenger": os.path.join(DB_DIR, "passenger.db"),
    "devices": os.path.join(DB_DIR, "devices.db"),
    "notifications": os.path.join(DB_DIR, "notifications.db"),
    "users": os.path.join(DB_DIR, "users.db"),
}


def _insert_rows(db_name: str, sql: str, rows: list):
    conn = sqlite3.connect(DB_PATHS[db_name])
    cursor = conn.cursor()
    cursor.executemany(sql, rows)
    conn.commit()
    conn.close()


def main():
    _insert_rows(
        "flights",
        "INSERT OR IGNORE INTO flights (flight_id, boarding_time, departure, gate, status, aircraft, origin, destination, display_time, last_update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("AI202", "18:30", "19:00", "Gate 12", "On Time", "Boeing 737", "Delhi", "Mumbai", "18:30", "2023-10-01 10:00:00"),
            ("AI305", "19:00", "19:30", "Gate 15", "Delayed", "Airbus A320", "Mumbai", "Bangalore", "19:15", "2023-10-01 10:30:00"),
        ],
    )

    _insert_rows(
        "passenger",
        "INSERT OR IGNORE INTO passenger (passenger_id, name, ticket_number, flight_id, boarding_status, seat_number, device_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("TB2376", "Thiru", "TB2376", "AI202", "Boarded", "12B", None),
            ("AB1234", "John Doe", "AB1234", "AI305", "Waiting", "14A", None),
        ],
    )

    devices = []
    for i in range(1, 31):
        device_id = f"DEV{i:03d}"
        mac_address = f"08:3A:F2:A8:31:{i:02X}"
        devices.append((device_id, mac_address, "active", 95, -45, "2023-10-01 10:00:00"))

    _insert_rows(
        "devices",
        "INSERT OR IGNORE INTO devices (device_id, mac_address, status, battery_level, signal_strength, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
        devices,
    )

    _insert_rows(
        "notifications",
        "INSERT OR IGNORE INTO notifications (message, type, created_at) VALUES (?, ?, ?)",
        [
            ("Flight AI202 boarding now", "info", "2023-10-01 10:00:00"),
            ("Device DEV001 battery low", "warning", "2023-10-01 09:30:00"),
        ],
    )

    _insert_rows(
        "users",
        "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
        [("Aerolinkers", generate_password_hash("Aerolinkers123"))],
    )

    print("Data inserted")


if __name__ == "__main__":
    main()
