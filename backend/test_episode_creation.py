#!/usr/bin/env python3
"""Quick test to verify episode creation"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# 1. Enable memory
print("1. Enabling memory...")
response = requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# 2. Send a message
print("\n2. Sending test message...")
response = requests.get(
    f"{BASE_URL}/chat/stream",
    params={"message": "Hello, this is a test message for episode creation"},
    stream=True
)

session_id = None
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if data.get('session_id'):
                    session_id = data['session_id']
                    print(f"   Session ID: {session_id}")
                    break
            except:
                pass

# Wait a bit
time.sleep(2)

# 3. Check active episodes
print("\n3. Checking active episodes...")
response = requests.get(f"{BASE_URL}/episodes/active")
print(f"   Status: {response.status_code}")
if response.ok:
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
else:
    print(f"   Error: {response.text}")

# 4. Check session episodes
if session_id:
    print(f"\n4. Checking episodes for session {session_id}...")
    response = requests.get(f"{BASE_URL}/episodes/session/{session_id}")
    print(f"   Status: {response.status_code}")
    if response.ok:
        data = response.json()
        print(f"   Found {data.get('total', 0)} episodes")
        if data.get('episodes'):
            for ep in data['episodes']:
                print(f"   - {ep['title']} ({ep['type']})")
    else:
        print(f"   Error: {response.text}")

# 5. Check episode files
print("\n5. Checking episode files...")
import os
episode_dir = "./data/memory/episodes"
if os.path.exists(episode_dir):
    files = os.listdir(episode_dir)
    print(f"   Found {len(files)} files in {episode_dir}")
    for f in files[:5]:  # Show first 5
        print(f"   - {f}")
else:
    print(f"   Directory {episode_dir} does not exist!")