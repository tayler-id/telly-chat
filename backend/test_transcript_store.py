#!/usr/bin/env python3
"""Test transcript storage and retrieval system"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from memory.transcript_store import TranscriptStore


async def test_transcript_store():
    """Test transcript storage functionality"""
    print("=== Testing Transcript Store ===\n")
    
    # Initialize store
    store = TranscriptStore(storage_dir="./test_transcripts")
    
    # 1. Save a test transcript
    print("1. Saving test transcript...")
    transcript_id = store.save_transcript(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Test Video - Never Gonna Give You Up",
        transcript="This is a test transcript. Rick Astley is singing about never giving you up, never letting you down, never running around and deserting you.",
        action_plan="1. Listen to the song\n2. Enjoy the melody\n3. Share with friends",
        summary="Classic Rick Astley song about commitment and loyalty",
        duration="3:32"
    )
    print(f"   ✅ Saved with ID: {transcript_id}")
    
    # 2. Retrieve the transcript
    print("\n2. Retrieving transcript...")
    record = store.get_transcript(transcript_id)
    if record:
        print(f"   ✅ Retrieved: {record.title}")
        print(f"   Access count: {record.accessed_count}")
    
    # 3. Search for transcripts
    print("\n3. Searching for 'Rick Astley'...")
    results = store.search_transcripts("Rick Astley", limit=5)
    print(f"   Found {len(results)} results")
    for record, score in results:
        print(f"   - {record.title} (score: {score:.2f})")
    
    # 4. Save another transcript
    print("\n4. Saving another transcript...")
    transcript_id2 = store.save_transcript(
        url="https://www.youtube.com/watch?v=abc123",
        title="Python Tutorial - Advanced Features",
        transcript="In this tutorial, we'll explore advanced Python features including decorators, generators, and context managers. These powerful tools will help you write more efficient and clean code.",
        action_plan="1. Learn about decorators\n2. Practice with generators\n3. Implement context managers\n4. Build a sample project",
        summary="Advanced Python programming concepts tutorial",
        duration="45:30"
    )
    print(f"   ✅ Saved with ID: {transcript_id2}")
    
    # 5. Get recent transcripts
    print("\n5. Getting recent transcripts...")
    recent = store.get_recent_transcripts(limit=5)
    print(f"   Found {len(recent)} recent transcripts:")
    for record in recent:
        print(f"   - {record.title} (saved: {record.saved_at.strftime('%Y-%m-%d %H:%M')})")
    
    # 6. Find related transcripts
    print("\n6. Finding related transcripts...")
    related = store.get_related_transcripts(transcript_id2, limit=3)
    print(f"   Found {len(related)} related transcripts:")
    for record, score in related:
        print(f"   - {record.title} (score: {score:.2f})")
    
    # 7. Get statistics
    print("\n7. Getting store statistics...")
    stats = store.get_statistics()
    print(f"   Total transcripts: {stats['total_transcripts']}")
    print(f"   Total size: {stats['total_size_mb']} MB")
    if stats['most_accessed']:
        print(f"   Most accessed: {stats['most_accessed']['title']} ({stats['most_accessed']['accessed_count']} times)")
    
    # 8. Test semantic search
    print("\n8. Testing semantic search...")
    
    # Add more test transcripts for better search testing
    test_transcripts = [
        {
            "url": "https://www.youtube.com/watch?v=vid1",
            "title": "Machine Learning Basics",
            "transcript": "Introduction to machine learning concepts including supervised learning, unsupervised learning, and neural networks.",
            "action_plan": "1. Understand ML fundamentals\n2. Implement basic algorithms\n3. Build a simple model",
            "summary": "ML basics tutorial"
        },
        {
            "url": "https://www.youtube.com/watch?v=vid2",
            "title": "Deep Learning with PyTorch",
            "transcript": "Advanced deep learning techniques using PyTorch framework. Building CNNs and RNNs for various applications.",
            "action_plan": "1. Install PyTorch\n2. Build CNN model\n3. Train on dataset\n4. Evaluate performance",
            "summary": "PyTorch deep learning guide"
        },
        {
            "url": "https://www.youtube.com/watch?v=vid3",
            "title": "Web Development with React",
            "transcript": "Building modern web applications with React. State management, hooks, and component lifecycle.",
            "action_plan": "1. Setup React environment\n2. Create components\n3. Manage state\n4. Deploy application",
            "summary": "React web development tutorial"
        }
    ]
    
    for transcript in test_transcripts:
        store.save_transcript(**transcript)
    
    # Search tests
    search_queries = [
        "machine learning neural networks",
        "React web development",
        "Python programming",
        "deep learning PyTorch"
    ]
    
    for query in search_queries:
        print(f"\n   Searching for: '{query}'")
        results = store.search_transcripts(query, limit=3)
        for record, score in results:
            print(f"     - {record.title} (score: {score:.2f})")
    
    print("\n✅ All transcript store tests completed!")
    
    # Cleanup test directory
    import shutil
    shutil.rmtree("./test_transcripts", ignore_errors=True)
    print("\n🧹 Test directory cleaned up")


if __name__ == "__main__":
    asyncio.run(test_transcript_store())