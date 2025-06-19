#!/usr/bin/env python3
"""Test which endpoints are available"""

import requests

BASE_URL = "http://localhost:8000"

endpoints = [
    "/",
    "/health",
    "/features",
    "/memory/stats",
    "/episodes/active",
    "/episodes/insights",
    "/transcripts/stats"
]

print("Testing endpoints...\n")

for endpoint in endpoints:
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"{endpoint:<25} -> {response.status_code}")
    except Exception as e:
        print(f"{endpoint:<25} -> ERROR: {e}")