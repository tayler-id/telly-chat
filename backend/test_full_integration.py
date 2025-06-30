#!/usr/bin/env python3
"""Test full integration of transcript storage with chat"""

import asyncio
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_transcript_workflow():
    """Test the complete transcript workflow"""
    print("=== Testing Full Transcript Workflow ===\n")
    
    # 1. Enable memory
    print("1. Enabling memory...")
    response = requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    if response.status_code == 200:
        print("   ✅ Memory enabled")
    else:
        print(f"   ❌ Failed to enable memory: {response.text}")
        return
    
    # 2. Process a YouTube video
    print("\n2. Processing YouTube video...")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={
            "message": f"Analyze this video and create an action plan: {test_url}"
        },
        stream=True
    )
    
    print("   Streaming response...")
    full_response = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'text':
                        full_response += data.get('content', '')
                except:
                    pass
    
    print(f"   ✅ Received response ({len(full_response)} chars)")
    
    # 3. Save the transcript (simulate what SaveButton does)
    print("\n3. Saving transcript to store...")
    
    # First get the full transcript
    transcript_response = requests.post(
        f"{BASE_URL}/youtube/transcript?url={test_url}"
    )
    
    if transcript_response.status_code == 200:
        data = transcript_response.json()
        if data['success']:
            content = data['content']
            
            # Extract components
            import re
            
            title_match = re.search(r'### 📹 Video Information[\s\S]*?- \*\*Title:\*\* (.+)', content)
            title = title_match.group(1) if title_match else "Unknown Video"
            
            transcript_match = re.search(r'### 📝 Full Transcript\s*\n\s*```\s*\n([\s\S]*?)\n```', content)
            transcript = transcript_match.group(1).strip() if transcript_match else "No transcript"
            
            action_plan_match = re.search(r'### 📋 Action Plan\s*\n\s*([\s\S]*?)(?=\n\n###|$)', content)
            action_plan = action_plan_match.group(1).strip() if action_plan_match else "No action plan"
            
            # Save to transcript store
            save_response = requests.post(
                f"{BASE_URL}/transcripts/save",
                params={
                    "url": test_url,
                    "title": title,
                    "transcript": transcript,
                    "action_plan": action_plan,
                    "summary": transcript[:500] + "..."
                }
            )
            
            if save_response.status_code == 200:
                result = save_response.json()
                print(f"   ✅ Transcript saved: {result.get('transcript_id')}")
            else:
                print(f"   ❌ Failed to save: {save_response.text}")
    
    # 4. Search for the transcript
    print("\n4. Searching for saved transcript...")
    search_response = requests.get(
        f"{BASE_URL}/transcripts/search",
        params={"query": "Rick Astley", "limit": 3}
    )
    
    if search_response.status_code == 200:
        results = search_response.json()
        if results['success'] and results['results']:
            print(f"   ✅ Found {len(results['results'])} transcripts:")
            for result in results['results']:
                print(f"      - {result['transcript']['title']} (score: {result['score']:.2f})")
        else:
            print("   ❌ No transcripts found")
    
    # 5. Test memory retrieval in chat
    print("\n5. Testing memory retrieval in chat...")
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={
            "message": "What videos have I analyzed about Rick Astley?"
        },
        stream=True
    )
    
    full_response = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'text':
                        full_response += data.get('content', '')
                except:
                    pass
    
    print(f"   Response: {full_response[:200]}...")
    
    # 6. Get transcript statistics
    print("\n6. Getting transcript statistics...")
    stats_response = requests.get(f"{BASE_URL}/transcripts/stats")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"   ✅ Stats retrieved:")
        print(f"      Total transcripts: {stats['stats']['total_transcripts']}")
        print(f"      Total size: {stats['stats']['total_size_mb']} MB")
        if stats['stats']['most_accessed']:
            print(f"      Most accessed: {stats['stats']['most_accessed']['title']}")
    
    print("\n✅ Full workflow test complete!")


def test_multiple_transcripts():
    """Test with multiple YouTube videos"""
    print("\n\n=== Testing Multiple Transcripts ===\n")
    
    test_videos = [
        {
            "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",
            "query": "Analyze this K-pop video"
        },
        {
            "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
            "query": "What can you tell me about this music video?"
        }
    ]
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n{i}. Processing: {video['url']}")
        
        response = requests.get(
            f"{BASE_URL}/chat/stream",
            params={"message": f"{video['query']}: {video['url']}"},
            stream=True
        )
        
        # Consume response
        for line in response.iter_lines():
            pass
        
        print("   ✅ Processed")
        time.sleep(2)  # Give time for processing
    
    # Search across all transcripts
    print("\n\nSearching across all transcripts...")
    search_queries = ["music video", "Korean", "song"]
    
    for query in search_queries:
        print(f"\nSearching for: '{query}'")
        response = requests.get(
            f"{BASE_URL}/transcripts/search",
            params={"query": query, "limit": 5}
        )
        
        if response.status_code == 200:
            results = response.json()
            if results['success']:
                print(f"   Found {len(results['results'])} results")


if __name__ == "__main__":
    print("Make sure the backend is running on http://localhost:8000\n")
    
    try:
        # Check if backend is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Backend is not running!")
            exit(1)
    except:
        print("❌ Cannot connect to backend!")
        exit(1)
    
    # Run tests
    test_transcript_workflow()
    # test_multiple_transcripts()  # Uncomment to test with real videos