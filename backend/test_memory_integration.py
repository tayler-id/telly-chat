#!/usr/bin/env python3
"""Test full memory integration with chat"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_memory_conversation():
    """Test a full conversation with memory"""
    print("=== Testing Memory in Conversation ===\n")
    
    # 1. Enable memory
    print("1. Enabling memory...")
    response = requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    if response.status_code == 200:
        print("   ✅ Memory enabled")
    else:
        print(f"   ❌ Failed to enable memory: {response.text}")
        return
    
    # 2. Start conversation
    print("\n2. Starting conversation...")
    
    test_messages = [
        "Hello, my name is Tayler",
        "I'm a software developer who loves Python", 
        "I'm working on an AI chat application",
        "What's my name?",
        "What programming language do I like?",
        "What am I working on?",
    ]
    
    session_id = None
    
    for message in test_messages:
        print(f"\n   User: {message}")
        
        # Send message
        response = requests.get(
            f"{BASE_URL}/chat/stream",
            params={
                "message": message,
                "session_id": session_id
            },
            stream=True
        )
        
        # Parse SSE response
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data.get('type') == 'text':
                            full_response += data.get('content', '')
                        elif data.get('session_id'):
                            session_id = data['session_id']
                    except:
                        pass
        
        print(f"   Assistant: {full_response[:100]}...")
        time.sleep(1)  # Give memory time to process
    
    # 3. Check memory stats
    print("\n3. Checking memory statistics...")
    response = requests.get(f"{BASE_URL}/memory/stats")
    if response.status_code == 200:
        stats = response.json()
        if stats.get('enabled'):
            print(f"   ✅ Memory is active")
            if 'stats' in stats:
                st = stats['stats'].get('short_term', {})
                lt = stats['stats'].get('long_term', {})
                print(f"   Short-term: {st.get('statistics', {}).get('total_memories', 0)} memories")
                print(f"   Long-term: {lt.get('total_memories', 0)} memories")
    
    print("\n✅ Memory conversation test complete!")


def test_memory_persistence():
    """Test if memories persist across restarts"""
    print("\n\n=== Testing Memory Persistence ===\n")
    
    # 1. Store some information
    print("1. Storing information with memory enabled...")
    
    # Enable memory
    requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    
    # Send identifying information
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={"message": "My favorite programming language is Python and I love machine learning"},
        stream=True
    )
    
    # Wait for processing
    for line in response.iter_lines():
        pass
    
    time.sleep(2)
    
    # 2. Check what's stored
    print("\n2. Checking stored memories...")
    response = requests.get(f"{BASE_URL}/memory/stats")
    stats1 = response.json()
    
    print(f"   Memories before restart: {stats1}")
    
    # 3. Simulate restart (disable/enable memory)
    print("\n3. Simulating restart...")
    requests.post(f"{BASE_URL}/features/memory/toggle?enable=false")
    time.sleep(1)
    requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    
    # 4. Ask about stored information
    print("\n4. Asking about stored information...")
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={"message": "What's my favorite programming language?"},
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
    
    if "python" in full_response.lower():
        print("   ✅ Memory persisted!")
    else:
        print("   ❌ Memory did not persist")


def test_memory_consolidation():
    """Test memory consolidation from short to long term"""
    print("\n\n=== Testing Memory Consolidation ===\n")
    
    # Enable memory
    requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    
    # Clear existing memory
    print("1. Clearing existing memory...")
    requests.post(f"{BASE_URL}/memory/clear")
    
    # Send important information multiple times
    print("\n2. Sending important information...")
    important_info = "My email is tayler@example.com"
    
    # Send it 3 times to trigger consolidation
    for i in range(3):
        print(f"   Iteration {i+1}: Asking about email...")
        
        # First send the info
        if i == 0:
            response = requests.get(
                f"{BASE_URL}/chat/stream",
                params={"message": important_info},
                stream=True
            )
            for line in response.iter_lines():
                pass
        
        # Then ask about it (to increase access count)
        response = requests.get(
            f"{BASE_URL}/chat/stream", 
            params={"message": "What's my email address?"},
            stream=True
        )
        
        for line in response.iter_lines():
            pass
        
        time.sleep(1)
    
    # Check memory stats
    print("\n3. Checking if consolidated to long-term...")
    response = requests.get(f"{BASE_URL}/memory/stats")
    stats = response.json()
    
    if stats.get('enabled') and 'stats' in stats:
        lt = stats['stats'].get('long_term', {})
        if lt.get('total_memories', 0) > 0:
            print("   ✅ Memory consolidated to long-term!")
            print(f"   Long-term memories: {lt.get('total_memories')}")
        else:
            print("   ❌ No long-term memories found")


if __name__ == "__main__":
    print("Make sure the backend is running on http://localhost:8000\n")
    
    try:
        # Check if backend is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Backend is not running!")
            sys.exit(1)
    except:
        print("❌ Cannot connect to backend!")
        sys.exit(1)
    
    # Run tests
    test_memory_conversation()
    test_memory_persistence()
    test_memory_consolidation()
    
    print("\n\n✅ All memory integration tests complete!")