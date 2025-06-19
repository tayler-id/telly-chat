#!/usr/bin/env python3
"""Start backend with debug info"""

import subprocess
import os

print("Starting Telly Chat Backend...")
print(f"Working directory: {os.getcwd()}")
print(f"Main.py location: {os.path.abspath('main.py')}")

# Check if main.py has episode endpoints
with open('main.py', 'r') as f:
    content = f.read()
    episode_count = content.count('@app.get("/episodes')
    transcript_count = content.count('@app.get("/transcripts')
    
print(f"\nEndpoints found in main.py:")
print(f"  Episode endpoints: {episode_count}")
print(f"  Transcript endpoints: {transcript_count}")

if episode_count == 0:
    print("\n❌ ERROR: Episode endpoints not found in main.py!")
    print("The file might be an old version.")
else:
    print(f"\n✅ Found {episode_count} episode endpoints")

print("\nStarting server...")
print("-" * 50)

# Start the server
subprocess.run(["python", "main.py"])