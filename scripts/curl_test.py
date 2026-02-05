import requests
import time

def check_url():
    url = "http://127.0.0.1:5050/api/v1/material/outbound?page=1&limit=10&status=pending"
    print(f"Checking URL: {url}")
    
    # Wait for server to restart
    time.sleep(3)
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response JSON Preview:")
            print(response.text[:500])
        else:
            print("Error Response:")
            print(response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_url()
