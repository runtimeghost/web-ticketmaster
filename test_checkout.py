import requests
import sys
import re

session = requests.Session()

print("1. Testing login...")
login_url = "http://127.0.0.1:5000/login"
login_data = {
    "email": "rimelhossain1109@gmail.com",
    "password": "11223344"
}
response = session.post(login_url, data=login_data)

if response.url != login_url:
    print("Login successful! Redirected to:", response.url)
else:
    print("Login failed! Still on login page. You might have invalid credentials.")
    sys.exit(1)

print("\n2. Testing Checkout Endpoint /checkout/3...")
checkout_url = "http://127.0.0.1:5000/checkout/3"
dash_response = session.get(checkout_url)

print(f"Status code: {dash_response.status_code}")
if dash_response.status_code == 200:
    content = dash_response.text
    # Search for remaining seconds in HTML
    match = re.search(r'data-remaining-seconds="([^"]+)"', content)
    if match:
        print(f"SUCCESS: Found data-remaining-seconds = {match.group(1)}")
    elif "Your reservation has expired" in content:
        print("FAILED: Flash message found: 'Your reservation has expired. Please try again.'")
    elif "Lock not found or access denied" in content:
        print("FAILED: Flash message found: 'Lock not found or access denied.'")
    else:
        print("WARNING: Could not find data-remaining-seconds. Page content snippet:")
        print(content[:500])
else:
    print(f"Request failed.")
