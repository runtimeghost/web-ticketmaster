import requests
import sys

session = requests.Session()

# 1. Test Login
print("Testing admin login...")
login_url = "http://127.0.0.1:5000/login"
login_data = {
    "email": "admin@ticketmaster.com",
    "password": "admin123"
}
response = session.post(login_url, data=login_data)

# Flask redirects on successful login
if response.url != login_url:
    print("Login successful! Redirected to:", response.url)
else:
    print("Login failed! Still on login page.")
    sys.exit(1)

# 2. Test Admin Dashboard
print("Testing Admin Dashboard...")
dashboard_url = "http://127.0.0.1:5000/admin/dashboard"
dash_response = session.get(dashboard_url)

if dash_response.status_code == 200:
    if b"Admin Dashboard" in dash_response.content and b"Total Events" in dash_response.content:
        print("Dashboard loaded successfully and contains expected widgets.")
    else:
        print("Dashboard loaded but doesn't seem to contain the correct widgets.")
else:
    print(f"Failed to load dashboard. Status code: {dash_response.status_code}")
    sys.exit(1)
