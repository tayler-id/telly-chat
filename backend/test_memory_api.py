#!/usr/bin/env python3
"""Test memory API endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_memory_toggle():
    """Test the memory toggle endpoint"""
    print("Testing Memory Toggle API...")
    
    # Check features first
    print("\n1. Checking available features...")
    response = requests.get(f"{BASE_URL}/features")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Try to enable memory
    print("\n2. Attempting to enable memory...")
    try:
        response = requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Check memory stats
    print("\n3. Checking memory stats...")
    try:
        response = requests.get(f"{BASE_URL}/memory/stats")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_memory_toggle()