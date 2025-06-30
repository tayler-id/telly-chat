#!/usr/bin/env python3
"""Demo script showing memory in action"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

# Check what's available
print("Checking available features...")

try:
    from memory.short_term import ShortTermMemory, MemoryPriority
    from memory.long_term import LongTermMemory
    from memory.vector_store import VectorStoreConfig
    print("✅ Memory modules available!")
    MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"❌ Memory modules not available: {e}")
    print("Run: pip install -r requirements-optional.txt")
    MEMORY_AVAILABLE = False
    sys.exit(1)


def demo_short_term_memory():
    """Demo short-term memory functionality"""
    print("\n=== Short-Term Memory Demo ===")
    
    # Create memory with small capacity for demo
    memory = ShortTermMemory(capacity=5)
    
    # Store a conversation
    conversation = [
        ("user", "Hi, my name is Alice"),
        ("assistant", "Hello Alice! Nice to meet you."),
        ("user", "I'm working on a Python project"),
        ("assistant", "That's great! What kind of Python project?"),
        ("user", "It's a machine learning project about image classification"),
        ("assistant", "Image classification is fascinating!"),
        ("user", "What was my name again?"),  # This should find the name
    ]
    
    print("\nStoring conversation in memory...")
    for role, content in conversation:
        memory.add(
            content=f"{role}: {content}",
            priority=MemoryPriority.HIGH if role == "user" else MemoryPriority.MEDIUM
        )
        print(f"  Stored: {role}: {content[:50]}...")
    
    # Search for memories
    print("\n🔍 Searching memories:")
    
    queries = ["name", "Python", "machine learning", "Alice"]
    for query in queries:
        results = memory.search(query, limit=2)
        print(f"\nQuery: '{query}'")
        if results:
            for mem in results:
                print(f"  Found: {mem.content[:60]}...")
        else:
            print("  No results found")
    
    # Show memory statistics
    stats = memory.get_statistics()
    print(f"\n📊 Memory Statistics:")
    print(f"  Total memories: {stats['total_memories']}")
    print(f"  Capacity utilization: {stats['utilization']:.0%}")
    print(f"  Context window size: {stats['context_window_size']}")


def demo_long_term_memory():
    """Demo long-term memory with vector search"""
    print("\n\n=== Long-Term Memory Demo ===")
    
    # Create vector store config (using FAISS for local demo)
    vector_config = VectorStoreConfig(
        store_type="faiss",
        embedding_provider="openai",  # Note: requires OpenAI API key
        persist_directory="./demo_memory"
    )
    
    # Check if we have OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No OpenAI API key found. Skipping vector store demo.")
        print("Set OPENAI_API_KEY environment variable to enable vector search.")
        return
    
    try:
        # Create long-term memory
        memory = LongTermMemory(vector_config)
        
        # Store some facts
        facts = [
            ("Alice likes Python programming", "preference"),
            ("Alice is working on machine learning", "fact"),
            ("The project involves image classification", "fact"),
            ("Alice prefers VS Code as her editor", "preference"),
            ("The deadline is next Friday", "task"),
        ]
        
        print("\nStoring facts in long-term memory...")
        for content, category in facts:
            memory_id = memory.store(
                content=content,
                summary=content,
                category=category,
                importance_score=0.8
            )
            print(f"  Stored ({category}): {content}")
        
        # Search with semantic similarity
        print("\n🔍 Semantic search in long-term memory:")
        
        queries = [
            "What programming language does Alice use?",
            "What is Alice working on?",
            "What are Alice's preferences?",
            "When is the deadline?"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            results = memory.retrieve(query, k=2)
            
            if results:
                for mem, score in results:
                    print(f"  Found (score: {score:.2f}): {mem.content}")
            else:
                print("  No results found")
        
        # Show memory statistics
        stats = memory.get_statistics()
        print(f"\n📊 Long-term Memory Statistics:")
        print(f"  Total memories: {stats['total_memories']}")
        print(f"  Average importance: {stats['average_importance']:.2f}")
        
    except Exception as e:
        print(f"Error in long-term memory demo: {e}")
        print("Make sure you have installed the optional dependencies.")


def demo_memory_in_conversation():
    """Demo how memory would work in a real conversation"""
    print("\n\n=== Memory-Enhanced Conversation Demo ===")
    
    # Create both memory types
    stm = ShortTermMemory(capacity=20)
    
    print("\n💬 Simulated Conversation with Memory:\n")
    
    # Simulate a conversation that spans time
    conversations = [
        # First conversation
        [
            ("user", "Hi, I'm Bob and I'm learning web development"),
            ("assistant", "Hello Bob! Web development is exciting. Are you focusing on frontend or backend?"),
            ("user", "I'm interested in React for frontend"),
            ("assistant", "React is a great choice! It's very popular for building dynamic UIs."),
        ],
        # Later conversation (simulating the user coming back)
        [
            ("user", "What framework was I asking about earlier?"),
            ("assistant", "[Checking memory...] You were asking about React for frontend development."),
            ("user", "Right! And what's my name?"),
            ("assistant", "[Checking memory...] Your name is Bob."),
        ]
    ]
    
    for i, conversation in enumerate(conversations):
        if i > 0:
            print("\n--- User returns later ---\n")
        
        for role, content in conversation:
            # Store in memory
            if not content.startswith("[Checking memory"):
                stm.add(
                    content=f"{role}: {content}",
                    priority=MemoryPriority.HIGH if role == "user" else MemoryPriority.MEDIUM
                )
            
            # If assistant needs to check memory
            if "[Checking memory...]" in content:
                # Extract the question
                if "framework" in content:
                    memories = stm.search("React frontend", limit=1)
                elif "name" in content:
                    memories = stm.search("Bob", limit=1)
                else:
                    memories = []
                
                if memories:
                    print(f"{role}: {content}")
                    print(f"  💭 Memory recalled: {memories[0].content}")
                else:
                    print(f"{role}: I don't remember that information.")
            else:
                print(f"{role}: {content}")
    
    print("\n✅ Memory allows the assistant to remember context across conversations!")


def main():
    """Run all demos"""
    print("="*60)
    print("Telly Chat Memory System Demo")
    print("="*60)
    
    # Run demos
    demo_short_term_memory()
    demo_long_term_memory()
    demo_memory_in_conversation()
    
    print("\n\n🎉 Memory system is working!")
    print("\nTo enable memory in the main app:")
    print("1. Set environment variable: export ENABLE_MEMORY=true")
    print("2. Make sure optional dependencies are installed")
    print("3. The chat agent will automatically use memory if available")


if __name__ == "__main__":
    main()