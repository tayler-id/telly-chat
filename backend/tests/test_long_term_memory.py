#!/usr/bin/env python3
"""Test long-term memory consolidation"""

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import memory components
from memory.short_term import ShortTermMemory, MemoryPriority
from memory.long_term import LongTermMemory
from memory.vector_store import VectorStoreConfig

def test_long_term_memory():
    """Test long-term memory storage and retrieval"""
    print("=== Testing Long-Term Memory ===\n")
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set in .env file")
        print("Long-term memory requires OpenAI API for embeddings")
        return
    
    # Create memory components
    short_term = ShortTermMemory(capacity=10)
    
    vector_config = VectorStoreConfig(
        store_type="faiss",
        embedding_provider="openai",
        persist_directory="./data/memory/test"
    )
    
    try:
        long_term = LongTermMemory(vector_config)
        print("✅ Long-term memory initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize long-term memory: {e}")
        return
    
    # Test 1: Store some memories
    print("1. Storing test memories...")
    
    test_data = [
        ("My name is Tayler and I'm a software developer", "personal_info", 0.9),
        ("I prefer Python over Java for backend development", "preferences", 0.7),
        ("I'm working on an AI chat application with memory", "projects", 0.8),
        ("I like to use VS Code as my editor", "preferences", 0.6),
        ("My favorite color is blue", "personal_info", 0.5),
    ]
    
    stored_ids = []
    for content, category, importance in test_data:
        try:
            memory_id = long_term.store(
                content=content,
                summary=content[:50] + "...",
                category=category,
                importance_score=importance,
                metadata={"test": True}
            )
            stored_ids.append(memory_id)
            print(f"  ✅ Stored: {content[:50]}... (ID: {memory_id})")
        except Exception as e:
            print(f"  ❌ Failed to store: {e}")
    
    # Test 2: Retrieve by similarity
    print("\n2. Testing semantic search...")
    
    queries = [
        "What is my name?",
        "What programming language do I use?",
        "What editor do I use?",
        "Tell me about myself",
        "What am I working on?"
    ]
    
    for query in queries:
        print(f"\n  Query: '{query}'")
        try:
            results = long_term.retrieve(query, k=2)
            if results:
                for memory, score in results:
                    print(f"    Found (score: {score:.3f}): {memory.content[:60]}...")
            else:
                print("    No results found")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Test 3: Get statistics
    print("\n3. Memory statistics:")
    stats = long_term.get_statistics()
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Categories: {stats['categories']}")
    print(f"  Average importance: {stats['average_importance']:.2f}")
    
    # Test 4: Test persistence
    print("\n4. Testing persistence...")
    print("  Creating new instance...")
    
    long_term2 = LongTermMemory(vector_config)
    stats2 = long_term2.get_statistics()
    print(f"  Memories after reload: {stats2['total_memories']}")
    
    if stats2['total_memories'] > 0:
        print("  ✅ Persistence working!")
        # Try a search
        results = long_term2.retrieve("What is my name?", k=1)
        if results:
            print(f"  Retrieved: {results[0][0].content}")
    else:
        print("  ❌ Persistence not working")
    
    print("\n✅ Long-term memory test complete!")

def test_consolidation_flow():
    """Test the full consolidation flow"""
    print("\n\n=== Testing Memory Consolidation Flow ===\n")
    
    # Create memories
    short_term = ShortTermMemory(capacity=10)
    vector_config = VectorStoreConfig(
        store_type="faiss",
        embedding_provider="openai",
        persist_directory="./data/memory/consolidation_test"
    )
    
    try:
        long_term = LongTermMemory(vector_config)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Simulate conversation with repeated access
    print("1. Simulating conversation...")
    
    # Add initial memory
    short_term.add(
        content="User: My name is Tayler",
        priority=MemoryPriority.HIGH
    )
    
    # Access it multiple times (simulating lookups)
    print("2. Accessing memory multiple times...")
    for i in range(3):
        results = short_term.search("name", limit=1)
        if results:
            print(f"  Access {i+1}: Found '{results[0].content}'")
            print(f"  Access count: {results[0].access_count}")
    
    # Check what should be consolidated
    print("\n3. Checking consolidation candidates...")
    all_memories = short_term.get_all()
    
    for memory in all_memories:
        if memory.access_count >= 3 or memory.priority.value >= 3:
            print(f"  Should consolidate: {memory.content} (accessed {memory.access_count} times)")
            
            # Perform consolidation
            try:
                memory_id = long_term.store(
                    content=memory.content,
                    summary=memory.content,
                    category="personal_info",
                    importance_score=0.8,
                    metadata={
                        "access_count": memory.access_count,
                        "consolidated_from": "short_term"
                    }
                )
                print(f"  ✅ Consolidated to long-term (ID: {memory_id})")
            except Exception as e:
                print(f"  ❌ Consolidation failed: {e}")
    
    # Verify consolidation worked
    print("\n4. Verifying consolidation...")
    results = long_term.retrieve("What is my name?", k=1)
    if results:
        print(f"  ✅ Found in long-term: {results[0][0].content}")
    else:
        print("  ❌ Not found in long-term memory")

if __name__ == "__main__":
    # Run tests
    test_long_term_memory()
    test_consolidation_flow()