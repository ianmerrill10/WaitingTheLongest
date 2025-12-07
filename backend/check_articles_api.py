import requests
import sys

try:
    print("Testing API endpoint...")
    response = requests.get("http://127.0.0.1:8000/api/articles")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}...")
    
    if response.status_code == 200:
        print("SUCCESS: API is working.")
    else:
        print("FAILURE: API returned error.")
        
except Exception as e:
    print(f"ERROR: Could not connect to API. {e}")
