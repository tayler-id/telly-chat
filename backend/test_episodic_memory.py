#!/usr/bin/env python3
"""Test episodic memory implementation"""

import asyncio
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_episodic_memory():
    """Test episodic memory with full conversation sessions"""
    print("=== Testing Episodic Memory ===\n")
    
    # 1. Enable memory
    print("1. Enabling memory...")
    response = requests.post(f"{BASE_URL}/features/memory/toggle?enable=true")
    if response.status_code == 200:
        print("   ✅ Memory enabled")
    else:
        print(f"   ❌ Failed to enable memory: {response.text}")
        return
    
    # 2. Start a conversation session
    print("\n2. Starting conversation session...")
    
    # Get initial session
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={"message": "Hello! I'm learning about Python programming"},
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
                        break
                except:
                    pass
    
    print(f"   Session ID: {session_id}")
    
    # 3. Continue conversation with multiple turns
    print("\n3. Having multi-turn conversation...")
    
    test_messages = [
        "What are Python decorators?",
        "Can you show me an example of a decorator?",
        "How do I create my own decorator?",
        "What's the difference between @property and regular decorators?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n   Turn {i}: {message}")
        
        response = requests.get(
            f"{BASE_URL}/chat/stream",
            params={
                "message": message,
                "session_id": session_id
            },
            stream=True
        )
        
        # Consume response
        response_text = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data.get('type') == 'text':
                            response_text += data.get('content', '')
                    except:
                        pass
        
        print(f"   Response: {response_text[:100]}...")
        time.sleep(1)  # Give time for processing
    
    # 4. Check active episodes
    print("\n4. Checking active episodes...")
    response = requests.get(f"{BASE_URL}/episodes/active")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Active episodes: {len(data['active_episodes'])}")
        if data['active_episodes']:
            episode = data['active_episodes'][0]
            print(f"   Current episode: {episode['title']}")
            print(f"   Type: {episode['type']}")
            print(f"   Events: {len(episode['events'])}")
    
    # 5. Get session episodes
    print(f"\n5. Getting episodes for session {session_id}...")
    response = requests.get(f"{BASE_URL}/episodes/session/{session_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['total']} episodes")
        for ep in data['episodes']:
            print(f"      - {ep['title']} ({ep['type']})")
    
    # 6. Search episodes by content
    print("\n6. Searching episodes for 'Python decorators'...")
    response = requests.get(
        f"{BASE_URL}/episodes/search",
        params={"query": "Python decorators", "limit": 5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {data['count']} matching episodes")
        for ep in data['results']:
            print(f"      - {ep['title']}")
    
    # 7. Get learning insights
    print("\n7. Getting learning insights...")
    response = requests.get(f"{BASE_URL}/episodes/insights")
    
    if response.status_code == 200:
        insights = response.json()
        print(f"   Total episodes: {insights.get('total_episodes', 0)}")
        print(f"   Active episodes: {insights.get('active_episodes', 0)}")
        print(f"   Success rate: {insights.get('success_rate', 0):.0%}")
        print(f"   Common topics: {list(insights.get('common_topics', {}).keys())[:5]}")
    
    # 8. Export session for training
    print(f"\n8. Exporting session data...")
    response = requests.get(f"{BASE_URL}/episodes/export/{session_id}")
    
    if response.status_code == 200:
        export_data = response.json()
        print(f"   ✅ Exported {len(export_data.get('episodes', []))} episodes")
        print(f"   Total conversations: {export_data.get('conversation_count', 0)}")
        print(f"   Total duration: {export_data.get('total_duration', 0):.0f} seconds")
    
    # 9. Test persistence - ask about previous conversation
    print("\n9. Testing memory persistence...")
    response = requests.get(
        f"{BASE_URL}/chat/stream",
        params={
            "message": "What did we discuss about Python earlier?",
            "session_id": session_id
        },
        stream=True
    )
    
    response_text = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get('type') == 'text':
                        response_text += data.get('content', '')
                except:
                    pass
    
    if "decorator" in response_text.lower() or "python" in response_text.lower():
        print("   ✅ Agent remembers previous conversation!")
    else:
        print("   ❌ Agent doesn't seem to remember")
    
    print(f"   Response: {response_text[:200]}...")
    
    print("\n✅ Episodic memory test complete!")


def test_multiple_sessions():
    """Test handling multiple conversation sessions"""
    print("\n\n=== Testing Multiple Sessions ===\n")
    
    sessions = []
    
    # Create 3 different sessions on different topics
    topics = [
        "Help me learn about machine learning",
        "I need to debug a React application",
        "Can you teach me about database design?"
    ]
    
    for i, topic in enumerate(topics, 1):
        print(f"\n{i}. Starting session about: {topic[:30]}...")
        
        response = requests.get(
            f"{BASE_URL}/chat/stream",
            params={"message": topic},
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
                            sessions.append(session_id)
                            break
                    except:
                        pass
        
        print(f"   Session ID: {session_id}")
        time.sleep(1)
    
    # Check all active episodes
    print("\n\nChecking all active episodes...")
    response = requests.get(f"{BASE_URL}/episodes/active")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total active episodes: {len(data['active_episodes'])}")
        
        for ep in data['active_episodes']:
            print(f"\n   Episode: {ep['title']}")
            print(f"   Type: {ep['type']}")
            print(f"   Participants: {ep['participants']}")
            print(f"   Started: {ep['start_time']}")
    
    print("\n✅ Multiple sessions test complete!")


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
    test_episodic_memory()
    test_multiple_sessions()