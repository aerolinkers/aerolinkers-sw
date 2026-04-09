# ✈️ Airport Smart Band Management System

> A modern, professional web platform for managing airport smart bands, passenger boarding, flight operations, and device synchronization. Built with Flask, SQLite, and a sleek dark-theme UI.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-orange?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)](README.md)

## 📋 Overview

A comprehensive airport operations platform designed for managing smart band devices, flight schedules, passenger boarding information, and real-time device synchronization. The system provides an intuitive dashboard for airport staff and administrators to monitor operations, manage devices, track notifications, and maintain system audit logs.

Built with a modern tech stack and enterprise-grade features including role-based access control, comprehensive audit logging, secure API endpoints, and a professionally designed dark-theme interface.

## ✨ Key Features

### 📊 Analytics & Monitoring
- **Live Dashboard** - Real-time KPIs, flight statistics, revenue tracking, and on-time performance metrics
- **Device Monitoring** - Battery status, connectivity tracking, and sync timestamps for all smart bands
- **Activity Feed** - Real-time updates on system events and operational changes
- **Performance Charts** - Visual analytics with Chart.js integration (line charts, distribution graphs)

### 🛫 Flight & Passenger Management
- **Flight Management** - Complete flight schedule with status tracking, route information, and aircraft assignment
- **Passenger Directory** - Passenger list with PNR lookup, boarding status, and ticket information
- **Device Pairing** - Smart band synchronization and assignment to passengers
- **Boarding Tracking** - Real-time boarding status and gate information

### 🔐 Security & Administration
- **Role-Based Access Control** - Admin and Staff tier permissions with customizable restrictions
- **User Management** - Create, edit, and manage staff accounts with secure password handling
- **Audit Logging** - Complete activity trail with timestamps, user attribution, and action details
- **API Key Management** - Secure device authentication and regeneration capabilities

### 🎨 Modern User Interface
- **Professional Dark Theme** - Sleek, eye-friendly interface with consistent design language
- **Responsive Design** - Fully responsive across desktop, tablet, and mobile devices
- **Intuitive Navigation** - Quick access sidebar with main sections and system management tools
- **Search & Filtering** - Advanced search and multi-filter capabilities across all data tables
- **Real-time Interactions** - Smooth animations and instant UI feedback

### 🔌 Smart Band API
- **Device Sync Endpoint** - Secure device-to-server synchronization via `/sync` API
- **Authentication** - API key header validation for device requests
- **Boarding Data** - Automatic passenger profile resolution and boarding details delivery
- **Health Checks** - Built-in `/health` and `/diagnose` endpoints for system monitoring

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | [Flask](https://flask.palletsprojects.com/) 2.0+ |
| **Runtime** | Python 3.8+ |
| **Database** | SQLite (WAL mode for concurrency) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Visualization** | Chart.js 4.4.0 |
| **Deployment** | WSGI (PythonAnywhere compatible) |
| **Environment** | python-dotenv |

## 🚀 Quick Start

### Prerequisites
- **Python** 3.8 or higher ([Download](https://www.python.org/downloads/))
- **pip** package manager (included with Python)
- Git (for cloning the repository)

### Installation & Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/airport-smart-band.git
cd airport-smart-band
```

#### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
Create a `.env` file in the project root with the following variables:
```ini
FLASK_SECRET_KEY=your_secure_random_secret_key_here
API_KEY=airport-smart-band-api-key-change-in-production
DEFAULT_USERNAME=admin
DEFAULT_PASSWORD=SecurePassword123
FLASK_ENV=development
```

#### 5. Run the Application
```bash
python server.py
```

The application will start on `http://127.0.0.1:7000/`

#### 6. Login to Dashboard
```
Username: admin
Password: SecurePassword123
```
(Or use credentials specified in your `.env` file)

## 📁 Project Structure

```
airport-smart-band/
├── server.py                      # Main Flask application
├── wsgi.py                        # WSGI entry point (production)
├── requirements.txt               # Python dependencies
├── .env                          # Environment configuration
├── README.md                      # This file
│
├── template/                      # HTML templates
│   ├── base_layout.html          # Main app shell & navigation
│   ├── login.html                # Authentication page
│   ├── dashboard.html            # Main dashboard
│   ├── flights_new.html          # Flight management
│   ├── passengers_new.html       # Passenger directory
│   ├── devices_new.html          # Device monitoring
│   ├── notifications_new.html    # System notifications
│   ├── staff_new.html            # Staff management
│   ├── admin_users.html          # Admin panel
│   ├── audit_log.html            # Audit trail
│   ├── reports_new.html          # Analytics & reports
│   └── 404.html                  # Error page
│
├── static/                        # Frontend assets
│   ├── css/
│   │   └── main.css              # Complete design system (600+ lines)
│   └── js/
│       └── layout.js             # Interactive UI behaviors
│
├── db/                            # SQLite databases
│   ├── flights.db                # Flight schedules & data
│   ├── passenger.db              # Passenger & boarding info
│   ├── devices.db                # Smart band device data
│   ├── notifications.db          # System alerts
│   ├── users.db                  # Staff accounts & roles
│   └── audit.db                  # Activity logging
│
└── .gitignore                    # Git ignore rules
```

## 🔌 API Endpoints

### Device Synchronization
```http
POST /sync
X-API-Key: airport-smart-band-api-key-change-in-production

{
  "device_id": "AA:BB:CC:DD:EE:FF",
  "pnr": "AB123456"
}
```
**Response** - Returns passenger boarding details and gate information.

### System Health
```http
GET /health
```
Returns database connectivity status and system uptime.

```http
GET /diagnose
```
Returns detailed system diagnostics including database size, Python version, and execution paths.

### Authentication
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=SecurePassword123
```

## 📊 Database Schema

The application uses 6 separate SQLite databases for data partitioning:

| Database | Purpose |
|----------|---------|
| **flights.db** | Flight schedules, routes, aircraft assignments |
| **passenger.db** | Passenger information, PNRs, ticket data, boarding status |
| **devices.db** | Smart band device tracking, battery levels, connectivity |
| **notifications.db** | System alerts, event notifications, warnings |
| **users.db** | Staff accounts, roles, password hashes, API keys |
| **audit.db** | Complete activity log, user actions, timestamps |

## 🎨 Design System

### Color Palette
- **Primary Background:** `#0A0F1E` (Deep Navy)
- **Surface/Cards:** `#111827` (Dark Slate)
- **Accent:** `#0EA5E9` (Sky Blue)
- **Success:** `#10B981` (Green)
- **Warning:** `#F59E0B` (Orange)
- **Error:** `#EF4444` (Red)

### Typography
- **Font Family:** Inter, system-ui, -apple-system, sans-serif
- **Base Size:** 14px
- **Weights:** 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)

### Responsive Breakpoints
- **Mobile:** < 768px
- **Tablet:** 768px - 1280px
- **Desktop:** > 1280px

## 🌐 Deployment

### Local Development Server
```bash
python server.py
# Running on http://127.0.0.1:7000
```

### ☁️ PythonAnywhere Cloud Deployment

This project includes a `wsgi.py` file configured for seamless deployment on PythonAnywhere.

#### Step 1: Create PythonAnywhere Account
1. Sign up at [PythonAnywhere](https://www.pythonanywhere.com/)
2. Choose a free or paid plan (free tier includes limited resources)

#### Step 2: Upload Project Files
1. Login to your PythonAnywhere dashboard
2. Go to **Files** tab
3. Create a new directory: `/home/yourusername/mysite/`
4. Upload your project files or use Git:
   ```bash
   git clone https://github.com/yourusername/airport-smart-band.git mysite
   cd mysite
   ```

#### Step 3: Set Up Python Virtual Environment
1. Open **Bash console** from the dashboard
2. Run these commands:
   ```bash
   cd /home/yourusername/mysite
   mkvirtualenv --python=/usr/bin/python3.8 mysite
   pip install -r requirements.txt
   ```

#### Step 4: Configure Web Application
1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** → **Python 3.8**
4. In the **Code section**, update the WSGI configuration file:
   - Click the WSGI configuration file link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`)
   - Replace contents with:
   ```python
   import sys
   path = '/home/yourusername/mysite'
   if path not in sys.path:
       sys.path.append(path)
   
   from server import app as application
   ```

#### Step 5: Set Environment Variables
1. On the **Web** page, scroll to **Environment variables**
2. Click **Add** and create these variables:
   ```
   FLASK_SECRET_KEY=your_secure_random_secret_key_here
   API_KEY=airport-smart-band-api-key-change-in-production
   DEFAULT_USERNAME=admin
   DEFAULT_PASSWORD=SecurePassword123
   FLASK_ENV=production
   ```

#### Step 6: Configure Static Files (Optional)
For faster static file serving:
1. In the **Static files section**, click **Edit**
2. Set URL: `/static/` and Directory: `/home/yourusername/mysite/static`

#### Step 7: Reload & Access Your App
1. Click the green **Reload [yourusername].pythonanywhere.com** button
2. Wait for the server to restart (~1 minute)
3. Visit `https://yourusername.pythonanywhere.com` in your browser
4. Login with your configured credentials

#### PythonAnywhere Troubleshooting
| Issue | Solution |
|-------|----------|
| **500 Internal Server Error** | Check the **Error log** in Web tab for Python tracebacks |
| **Module not found** | Verify virtual environment is activated in WSGI: `workon mysite` |
| **Database permission denied** | Ensure `/home/yourusername/mysite/db/` has write permissions |
| **Static files not loading** | Reload the web app after configuring static files section |
| **Import errors on reload** | Check that all dependencies are installed: `pip list` |

### Production Deployment with Gunicorn

For self-hosted production servers:

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 worker processes
gunicorn -w 4 -b 0.0.0.0:8000 server:app

# With custom configuration
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile - server:app
```

### Docker Deployment

Create a `Dockerfile` in the project root:
```dockerfile
FROM python:3.8-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV FLASK_APP=server.py
ENV FLASK_SECRET_KEY=change-me-in-production
ENV FLASK_ENV=production

EXPOSE 7000

CMD ["python", "server.py"]
```

Build and run:
```bash
# Build the image
docker build -t airport-smart-band .

# Run the container
docker run -p 7000:7000 \
  -v $(pwd)/db:/app/db \
  -e FLASK_SECRET_KEY=your_secret_key \
  airport-smart-band

# Or with docker-compose
cat > docker-compose.yml << EOF
version: '3'
services:
  web:
    build: .
    ports:
      - "7000:7000"
    volumes:
      - ./db:/app/db
    environment:
      - FLASK_SECRET_KEY=your_secret_key
      - API_KEY=your_api_key
EOF

docker-compose up -d
```

### Environment Variables for Production

When deploying to production, ensure these are set securely:

```bash
FLASK_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
API_KEY=<secure-random-key>
DEFAULT_USERNAME=admin
DEFAULT_PASSWORD=<secure-password>
FLASK_ENV=production
```

✅ **Recommended:** Use a secrets management service (AWS Secrets Manager, HashiCorp Vault) for sensitive values.

## 🔌 API Endpoints

### Device Synchronization
```http
POST /sync
X-API-Key: airport-smart-band-api-key-change-in-production

{
  "device_id": "AA:BB:CC:DD:EE:FF",
  "pnr": "AB123456"
}
```
**Response** - Returns passenger boarding details and gate information.

### System Health
```http
GET /health
```
Returns database connectivity status and system uptime.

```http
GET /diagnose
```
Returns detailed system diagnostics including database size, Python version, and execution paths.

### Authentication
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=admin&password=SecurePassword123
```

## 📊 Database Schema

The application uses 6 separate SQLite databases for data partitioning:

| Database | Purpose |
|----------|---------|
| **flights.db** | Flight schedules, routes, aircraft assignments |
| **passenger.db** | Passenger information, PNRs, ticket data, boarding status |
| **devices.db** | Smart band device tracking, battery levels, connectivity |
| **notifications.db** | System alerts, event notifications, warnings |
| **users.db** | Staff accounts, roles, password hashes, API keys |
| **audit.db** | Complete activity log, user actions, timestamps |

## 🎨 Design System

### Color Palette
- **Primary Background:** `#0A0F1E` (Deep Navy)
- **Surface/Cards:** `#111827` (Dark Slate)
- **Accent:** `#0EA5E9` (Sky Blue)
- **Success:** `#10B981` (Green)
- **Warning:** `#F59E0B` (Orange)
- **Error:** `#EF4444` (Red)

### Typography
- **Font Family:** Inter, system-ui, -apple-system, sans-serif
- **Base Size:** 14px
- **Weights:** 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
