#!/usr/bin/env python3
"""Create test episodes for demonstration"""

import json
import os
from datetime import datetime, timedelta
import uuid

# Create directories
os.makedirs("./data/memory/episodes", exist_ok=True)

# Create episode index
episode_index = {
    "episodes": {},
    "sessions": {},
    "patterns": {},
    "metadata": {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }
}

# Test session ID
session_id = "test-session-123"
episode_index["sessions"][session_id] = []

# Create some test episodes
test_episodes = [
    {
        "title": "Chat: Hello! I'm learning about Python programming...",
        "type": "learning",
        "messages": [
            ("user", "Hello! I'm learning about Python programming"),
            ("assistant", "Hi! I'd be happy to help you learn Python. Python is a versatile, beginner-friendly programming language. What specific aspect would you like to start with?"),
            ("user", "What are Python decorators?"),
            ("assistant", "Python decorators are a powerful feature that allow you to modify or enhance functions without changing their code. They use the @symbol syntax...")
        ]
    },
    {
        "title": "Chat: Can you help me debug this React component?...",
        "type": "problem_solving",
        "messages": [
            ("user", "Can you help me debug this React component?"),
            ("assistant", "Of course! I'd be happy to help debug your React component. Could you share the code and describe what issue you're experiencing?"),
            ("user", "It's showing 'undefined is not a function' error"),
            ("assistant", "That error typically means you're trying to call something that isn't a function. Let me help you track down the issue...")
        ]
    },
    {
        "title": "Chat: Analyze this YouTube video about machine learning...",
        "type": "task_completion",
        "messages": [
            ("user", "Analyze this YouTube video about machine learning: https://youtube.com/watch?v=example"),
            ("assistant", "I'll analyze that YouTube video for you. Let me extract the transcript and create an action plan..."),
            ("user", "What are the key concepts covered?"),
            ("assistant", "Based on the video analysis, here are the key machine learning concepts covered:\n1. Supervised vs Unsupervised Learning\n2. Neural Networks\n3. Training and Validation...")
        ]
    }
]

# Create episode files
for i, episode_data in enumerate(test_episodes):
    episode_id = f"episode_{uuid.uuid4().hex[:12]}"
    start_time = datetime.now() - timedelta(hours=i+1)
    
    # Build events from messages
    events = []
    for j, (role, content) in enumerate(episode_data["messages"]):
        event_time = start_time + timedelta(minutes=j*2)
        if role == "user":
            events.append({
                "timestamp": event_time.isoformat(),
                "event_type": "user_message",
                "actor": "user",
                "action": "sent_message",
                "data": {"content": content},
                "impact_score": 0.5
            })
        else:
            events.append({
                "timestamp": event_time.isoformat(),
                "event_type": "assistant_response",
                "actor": "assistant",
                "action": "sent_response",
                "data": {"content": content},
                "impact_score": 0.6
            })
    
    # Add episode start and end events
    events.insert(0, {
        "timestamp": start_time.isoformat(),
        "event_type": "episode_start",
        "actor": "system",
        "action": "started_episode",
        "data": {"title": episode_data["title"], "type": episode_data["type"]},
        "impact_score": 0.5
    })
    
    end_time = start_time + timedelta(minutes=len(episode_data["messages"])*2 + 5)
    events.append({
        "timestamp": end_time.isoformat(),
        "event_type": "episode_end",
        "actor": "system",
        "action": "ended_episode",
        "data": {
            "outcome": "completed",
            "duration": (end_time - start_time).total_seconds(),
            "event_count": len(events) + 1
        },
        "impact_score": 0.5
    })
    
    # Create episode object
    episode = {
        "id": episode_id,
        "type": episode_data["type"],
        "title": episode_data["title"],
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "participants": ["user", "assistant"],
        "context": {
            "session_id": session_id,
            "thread_id": None,
            "initial_message": episode_data["messages"][0][1]
        },
        "events": events,
        "outcome": "completed",
        "success_metrics": {"completion": 1.0},
        "memories_created": [f"ltm_{uuid.uuid4().hex[:12]}"],
        "metadata": {
            "auto_close_timeout": 7200.0,
            "pattern": "normal_conversation"
        }
    }
    
    # Save episode file
    filename = f"episode_{start_time.strftime('%Y%m%d_%H%M%S')}_{episode_id}.json"
    filepath = os.path.join("./data/memory/episodes", filename)
    
    with open(filepath, 'w') as f:
        json.dump(episode, f, indent=2)
    
    # Update index
    episode_index["episodes"][episode_id] = {
        "file": filepath,
        "title": episode_data["title"],
        "type": episode_data["type"],
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "is_active": False,
        "participants": ["user", "assistant"],
        "event_count": len(events)
    }
    
    episode_index["sessions"][session_id].append(episode_id)
    
    print(f"Created episode: {episode_data['title'][:50]}...")

# Save index
index_path = "./data/memory/episodes/episode_index.json"
with open(index_path, 'w') as f:
    json.dump(episode_index, f, indent=2)

print(f"\nCreated {len(test_episodes)} test episodes in ./data/memory/episodes/")
print(f"Session ID: {session_id}")

# Also create one active episode
active_episode_id = f"episode_{uuid.uuid4().hex[:12]}"
active_start = datetime.now() - timedelta(minutes=5)

active_episode = {
    "id": active_episode_id,
    "type": "conversation",
    "title": "Chat: What's the weather like today?...",
    "start_time": active_start.isoformat(),
    "end_time": None,  # Still active
    "participants": ["user", "assistant"],
    "context": {
        "session_id": "active-session-456",
        "thread_id": None,
        "initial_message": "What's the weather like today?"
    },
    "events": [
        {
            "timestamp": active_start.isoformat(),
            "event_type": "episode_start",
            "actor": "system",
            "action": "started_episode",
            "data": {"title": "Chat: What's the weather like today?...", "type": "conversation"},
            "impact_score": 0.5
        },
        {
            "timestamp": (active_start + timedelta(seconds=10)).isoformat(),
            "event_type": "user_message",
            "actor": "user",
            "action": "sent_message",
            "data": {"content": "What's the weather like today?"},
            "impact_score": 0.5
        }
    ],
    "outcome": None,
    "success_metrics": {},
    "memories_created": [],
    "metadata": {
        "auto_close_timeout": 7200.0
    }
}

# Save active episode
active_filename = f"episode_{active_start.strftime('%Y%m%d_%H%M%S')}_{active_episode_id}.json"
active_filepath = os.path.join("./data/memory/episodes", active_filename)

with open(active_filepath, 'w') as f:
    json.dump(active_episode, f, indent=2)

# Update index with active episode
episode_index["episodes"][active_episode_id] = {
    "file": active_filepath,
    "title": active_episode["title"],
    "type": active_episode["type"],
    "start_time": active_start.isoformat(),
    "end_time": None,
    "is_active": True,
    "participants": ["user", "assistant"],
    "event_count": len(active_episode["events"])
}

if "active-session-456" not in episode_index["sessions"]:
    episode_index["sessions"]["active-session-456"] = []
episode_index["sessions"]["active-session-456"].append(active_episode_id)

# Save updated index
with open(index_path, 'w') as f:
    json.dump(episode_index, f, indent=2)

print(f"\nAlso created 1 active episode")
print("\nTest data created successfully!")