#!/usr/bin/env python3
"""Debug why endpoints aren't working"""

import requests

# Test various endpoints
endpoints = [
    ("/", "GET"),
    ("/docs", "GET"),  # FastAPI auto-generated docs
    ("/openapi.json", "GET"),  # OpenAPI schema
    ("/episodes/active", "GET"),
    ("/memory/stats", "GET"),
    ("/features", "GET"),
]

print("Testing endpoints...\n")

base_url = "http://localhost:8000"

for endpoint, method in endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{base_url}{endpoint}")
        print(f"{endpoint:<25} -> {r.status_code}")
        
        # If it's the OpenAPI schema, check for episodes endpoints
        if endpoint == "/openapi.json" and r.status_code == 200:
            data = r.json()
            paths = data.get("paths", {})
            episode_paths = [p for p in paths if "episode" in p]
            print(f"\nEpisode endpoints in OpenAPI schema: {len(episode_paths)}")
            for ep in episode_paths[:5]:
                print(f"  - {ep}")
                
    except Exception as e:
        print(f"{endpoint:<25} -> ERROR: {e}")

# Also check the root response
print("\nChecking root endpoint response:")
r = requests.get(f"{base_url}/")
if r.status_code == 200:
    print(r.json())