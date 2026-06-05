# ✈️ Airport Smart Band — Server (`aerolinkers-sw`)

> A Flask-based backend system for managing airport smart wristband devices, enabling real-time flight updates, passenger tracking, and device synchronisation.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Server](#running-the-server)
- [Default Credentials](#default-credentials)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Utility Scripts](#utility-scripts)
- [Contributing](#contributing)

---

## Overview

**Airport Smart Band** is a wearable-device management platform designed for airport environments. The server component (`aerolinkers-sw`) provides a web dashboard and REST API that lets airport staff:

- Monitor and manage smart band devices worn by passengers
- Track passenger boarding status by PNR (Passenger Name Record)
- Manage live flight information (gate, status, boarding times)
- Deliver real-time notifications to devices
- Synchronise device data via an open `/sync` endpoint

---

## Features

- 🔐 **Session-based authentication** with hashed passwords (Werkzeug)
- 📊 **Admin dashboard** — tabbed UI for Devices, Flights, Passengers, and Notifications
- 🔎 **PNR search** — look up a passenger by their booking reference
- ✈️ **Flight management** — add, update, and delete flights; live boarding-time edits
- 📱 **Device management** — register, monitor, and remove smart band devices
- 👤 **Passenger management** — add/remove passenger records, track boarding status
- 🔔 **Notification centre** — create and dismiss operational alerts
- 🔗 **REST API** — `/sync`, `/flights`, `/passenger/<pnr>`, and more for device integration
- 🗄️ **SQLite persistence** — separate database files per entity for clean separation of concerns

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Python · Flask |
| Templating | Jinja2 (in-memory `DictLoader`) |
| Database | SQLite (via `sqlite3`) |
| Auth | Werkzeug (`generate_password_hash` / `check_password_hash`) |
| Frontend | Bootstrap 5.3 (CDN) |
| Language breakdown | HTML 65.7% · Python 22.9% · CSS 7.8% · JS 3.6% |

---

## Project Structure

```
aerolinkers-sw/
│
├── server.py            # Main Flask application — routes, templates, DB init
├── insert.py            # Standalone seed script for sample data
├── extract_files.py     # Utility for extracting/exporting DB content
├── table.py             # Helper for DB table operations
│
├── db/                  # SQLite database files (auto-created on first run)
│   ├── flights.db
│   ├── passenger.db
│   ├── devices.db
│   ├── notifications.db
│   └── users.db
│
├── template/            # Static HTML template assets
├── airport.db           # Legacy / reference database
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- `pip`

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/aerolinkers/aerolinkers-sw.git
cd aerolinkers-sw

# 2. (Recommended) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install flask werkzeug
```

### Running the Server

```bash
python server.py
```

The application will start on **http://localhost:5000** by default. The database files and all required tables are created automatically on first launch, along with sample seed data.

To pre-populate the databases independently, run:

```bash
python insert.py
```

> ⚠️ **Before going to production**, change the `secret_key` in `server.py` to a strong, randomly generated value and update the default credentials.

---

## Default Credentials

The following demo credentials are shown on the login page and seeded automatically:

| Field | Value |
|---|---|
| Username | `Aerolinkers` |
| Password | `Aerolinkers123` |

---

## API Reference

All endpoints except `/login` and `/sync` require an active session (cookie-based login).

### `POST /sync`
Synchronise a smart band device with a passenger record. **No authentication required** — designed for device firmware calls.

**Request body (JSON):**
```json
{
  "device_id": "08:3A:F2:A8:31:01",
  "pnr": "TB2376"
}
```

**Response (JSON):**
```json
{
  "device_id": "DEV001",
  "pnr": "TB2376",
  "name": "Thiru",
  "flight": "AI202",
  "seat": "12B",
  "boarding_time": "18:30"
}
```

---

### `GET /flights`
Returns all flights as a JSON array.

```json
[
  {
    "flight_id": "AI202",
    "boarding_time": "18:30",
    "departure": "19:00",
    "gate": "Gate 12",
    "status": "On Time",
    "aircraft": "Boeing 737",
    "origin": "Delhi",
    "destination": "Mumbai",
    "display_time": "18:30",
    "last_update": "2023-10-01 10:00:00"
  }
]
```

---

### `GET /passenger/<pnr>`
Returns passenger details for the given PNR.

---

### `POST /update`
Updates the boarding time for a flight. Requires form fields `flight` and `new_time`.

---

### `POST /add_device` · `POST /delete_device`
Add or remove a device record.

### `POST /add_flight` · `POST /delete_flight`
Add or remove a flight record.

### `POST /add_passenger` · `POST /delete_passenger`
Add or remove a passenger record.

### `POST /add_notification` · `POST /delete_notification`
Add or remove a notification.

---

## Database Schema

Each entity has its own SQLite file under `db/`.

**`flights`** — `flight_id`, `boarding_time`, `departure`, `gate`, `status`, `aircraft`, `origin`, `destination`, `display_time`, `last_update`

**`passenger`** — `passenger_id`, `name`, `ticket_number`, `flight_id`, `boarding_status`, `seat_number`, `device_id`

**`devices`** — `device_id`, `mac_address`, `status`, `battery_level`, `signal_strength`, `last_seen`

**`notifications`** — `id`, `message`, `type`, `created_at`

**`users`** — `username`, `password_hash`

---

## Utility Scripts

| Script | Purpose |
|---|---|
| `insert.py` | Seeds all databases with sample flights, passengers, devices, notifications, and the default admin user |
| `extract_files.py` | Exports or inspects database contents |
| `table.py` | Low-level table helpers used during development |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a Pull Request

