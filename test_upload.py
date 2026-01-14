import requests
import json
import os

# Create a dummy image for testing if one doesn't exist
file_path = "test_plan.png"
if not os.path.exists(file_path):
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'white')
    img.save(file_path)

url = "http://127.0.0.1:8005/api/upload"
files = {'file': open(file_path, 'rb')}
data = {'settings': json.dumps({"title": "Test Plan"})}

# Need authentication? The endpoint says "Requires authentication".
# Let's try without first to see if we get 401.
try:
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text.encode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
