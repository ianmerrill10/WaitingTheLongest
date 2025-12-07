import requests
import json

try:
    response = requests.get('http://127.0.0.1:8000/api/animals/14')
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Exception: {e}")
