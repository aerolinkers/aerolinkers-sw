"""
WSGI entry point for PythonAnywhere deployment
"""
import sys
import os

# Add the project directory to the sys.path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import the Flask app
from server import app

# This is the application object used by PythonAnywhere/Gunicorn
application = app

if __name__ == "__main__":
    application.run()
