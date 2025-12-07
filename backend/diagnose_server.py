import requests
import time

def check_endpoint(url, name):
    try:
        print(f"Checking {name} ({url})...")
        response = requests.get(url)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print("  Success")
        else:
            print(f"  Failed: {response.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")

print("Waiting for server to start...")
time.sleep(5)

base_url = "http://127.0.0.1:8000"
check_endpoint(f"{base_url}/api/docs", "Docs")
check_endpoint(f"{base_url}/api/test_articles", "Test Articles Endpoint")
check_endpoint(f"{base_url}/api/articles", "Articles API")
check_endpoint(f"{base_url}/home", "Home Page")
check_endpoint(f"{base_url}/app.js", "App JS (Root)")
check_endpoint(f"{base_url}/static/app.js", "App JS (Static)")
