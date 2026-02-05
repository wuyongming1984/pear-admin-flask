import requests
import sys

def fetch_error():
    base_url = "http://127.0.0.1:5050"
    s = requests.Session()
    
    # Login
    print("Logging in...")
    login_resp = s.post(f"{base_url}/login", data={"username": "wym", "password": "12345678"})
    # print("Login status:", login_resp.status_code)
    
    # Access page
    print("Accessing outbound page...")
    resp = s.get(f"{base_url}/view/material/outbound")
    print("Page status:", resp.status_code)
    
    if resp.status_code == 500:
        print("Captured Traceback:")
        print(resp.text)
    else:
        print("No 500 error captured. Content snippet (Middle):")
        lines = resp.text.splitlines()
        for i, line in enumerate(lines[200:240], 201):
            print(f"{i}: {line}")

if __name__ == "__main__":
    fetch_error()
