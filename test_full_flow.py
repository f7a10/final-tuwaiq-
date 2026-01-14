import requests
import json
import os

base_url = "http://127.0.0.1:8005"

# 1. Register/Login to get token
# Try to register a test user
auth_data = {
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
}

print("1. Registering/Logging in...")
# Try login first
login_resp = requests.post(f"{base_url}/api/auth/login", json={"email": auth_data["email"], "password": auth_data["password"]})

if login_resp.status_code != 200:
    # Try register
    print("   Login failed, trying registration...")
    reg_resp = requests.post(f"{base_url}/api/auth/register", json=auth_data)
    print(f"DEBUG: Register URL: {base_url}/api/auth/register")
    print(f"DEBUG: Register Status: {reg_resp.status_code}")
    print(f"DEBUG: Register Response: {reg_resp.text.encode('utf-8')}")
    if reg_resp.status_code == 200:
        print("   Registration successful!")
        # Login again
        login_resp = requests.post(f"{base_url}/api/auth/login", json={"email": auth_data["email"], "password": auth_data["password"]})
    else:
        print(f"   Registration failed: {reg_resp.text}")
        exit()

if login_resp.status_code != 200:
    print(f"   Login failed: {login_resp.text}")
    exit()

token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("   Authenticated successfully.")

# 2. Upload Image
print("\n2. Uploading Plan...")
file_path = "test_plan_real.png"
# Create dummy if needed
if not os.path.exists(file_path):
    from PIL import Image
    img = Image.new('RGB', (100, 100), color = 'white')
    img.save(file_path)

files = {'file': open(file_path, 'rb')}
data = {'settings': json.dumps({"title": "Test Plan Automation"})}

upload_resp = requests.post(f"{base_url}/api/upload", files=files, data=data, headers=headers)
print(f"   Upload Status: {upload_resp.status_code}")

if upload_resp.status_code == 200:
    result = upload_resp.json()
    task_id = result.get("task_id")
    print(f"   Task ID: {task_id}")
    
    # 3. Check Analysis Status
    print(f"\n3. Checking Analysis Status for {task_id}...")
    status_resp = requests.get(f"{base_url}/api/analysis/{task_id}")
    print(f"   Status: {status_resp.json().get('status')}")
    
    # 4. Check DXF Generation
    print("\n4. Testing Generative DXF Endpoint...")
    gen_data = {
        "rooms": [
            { "type": "Majlis", "width": 5.0, "length": 7.0 },
            { "type": "Bedroom", "width": 4.0, "length": 4.0 }
        ]
    }
    dxf_resp = requests.post(f"{base_url}/api/generate-dxf", json=gen_data, headers=headers)
    print(f"   DXF Generation Status: {dxf_resp.status_code}")
    if dxf_resp.status_code == 200:
        print("   DXF file generated successfully (binary content received).")
    else:
        print(f"   DXF Generation Failed: {dxf_resp.text}")

else:
    print(f"   Upload Failed: {upload_resp.text}")
