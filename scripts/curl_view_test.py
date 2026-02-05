import requests
import time

def check_view():
    url = "http://127.0.0.1:5050/view/material/outbound"
    print(f"Checking VIEW URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response Length:", len(response.text))
            print("Contains '拟出库计划':", "拟出库计划" in response.text)
        else:
            print("Error Response:")
            print(response.text[:500])
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_view()
