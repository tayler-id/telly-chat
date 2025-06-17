#!/usr/bin/env python3
"""Test the direct transcript endpoint"""

import requests
import json

# Test URL
test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# API endpoint
api_url = "http://localhost:8000/youtube/transcript"

print("Testing direct transcript endpoint...")
print(f"URL: {test_url}")
print("-" * 50)

try:
    # Make request
    response = requests.post(api_url, params={"url": test_url})
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        
        if data.get('success'):
            content = data.get('content', '')
            print(f"Content length: {len(content)} characters")
            print("\nFirst 500 characters:")
            print("-" * 50)
            print(content[:500])
            print("\n...")
            
            # Check for full transcript
            if "### 📝 Full Transcript" in content:
                print("\n✓ Found full transcript section")
                # Extract transcript length
                import re
                transcript_match = re.search(r'```\n([\s\S]*?)\n```', content)
                if transcript_match:
                    transcript = transcript_match.group(1)
                    print(f"✓ Full transcript length: {len(transcript)} characters")
                else:
                    print("✗ Could not extract transcript from code block")
            else:
                print("\n✗ No full transcript section found")
        else:
            print(f"Error: {data.get('error')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")