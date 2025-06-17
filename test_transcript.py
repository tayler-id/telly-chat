#!/usr/bin/env python3
"""Test script to verify transcript display behavior"""

import requests
import json
import time

# Test YouTube URL
test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# API endpoint
api_url = "http://localhost:8000/chat/stream"

# Test message
params = {
    "message": f"Please extract the transcript from this video: {test_url}",
    "session_id": "test-session-" + str(int(time.time()))
}

print("Testing transcript extraction...")
print(f"URL: {test_url}")
print(f"Session: {params['session_id']}")
print("-" * 50)

try:
    # Make request
    response = requests.get(api_url, params=params, stream=True)
    
    # Process SSE stream
    full_content = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'content' in data:
                        content = data['content']
                        if isinstance(content, str):
                            full_content += content
                            print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "-" * 50)
    print("\nChecking for duplicate transcript sections...")
    
    # Check for duplicate transcript sections
    transcript_count = full_content.count("### 📝 Transcript")
    print(f"Number of '### 📝 Transcript' sections: {transcript_count}")
    
    # Check for unformatted transcript after action plan
    if "### 📋 Action Plan" in full_content:
        after_action_plan = full_content.split("### 📋 Action Plan")[1]
        # Look for signs of unformatted transcript
        if len(after_action_plan) > 5000 and "```" not in after_action_plan[:1000]:
            print("WARNING: Found large unformatted text after action plan!")
        else:
            print("✓ No unformatted transcript found after action plan")
    
    # Check for hidden transcript markers
    if "TRANSCRIPT_FULL_START" in full_content or "​​​" in full_content:
        print("WARNING: Found hidden transcript markers in output!")
    else:
        print("✓ No hidden transcript markers found")
    
except Exception as e:
    print(f"Error: {e}")