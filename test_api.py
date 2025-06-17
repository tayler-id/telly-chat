#!/usr/bin/env python3
"""Test the API endpoints"""
import requests
import json

API_URL = "http://localhost:8000"

print("Testing Telly Chat API...")

# Test 1: Health check
print("\n1. Testing health endpoint...")
try:
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Root endpoint
print("\n2. Testing root endpoint...")
try:
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Chat endpoint
print("\n3. Testing chat endpoint...")
try:
    response = requests.post(
        f"{API_URL}/chat",
        json={"message": "Hello, this is a test", "stream": False},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Session ID: {data.get('session_id')}")
        print(f"Response: {data.get('message', {}).get('content', 'No content')}")
    else:
        print(f"Error response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: SSE endpoint
print("\n4. Testing SSE endpoint...")
try:
    # Just check if it connects
    response = requests.get(
        f"{API_URL}/chat/stream",
        params={"message": "test"},
        stream=True,
        timeout=2
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("SSE endpoint is accessible")
except Exception as e:
    print(f"Error: {e}")

print("\nTests completed!")