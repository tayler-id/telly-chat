"""Main application with memory enabled (example)"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Check if we can use enhanced features
try:
    from agents.enhanced_chat_agent import EnhancedChatAgent
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
    print("Enhanced features not available. Using basic chat agent.")
    from agents.chat_agent import ChatAgent


def test_memory_integration():
    """Test that memory actually works"""
    
    if not ENHANCED_AVAILABLE:
        print("Enhanced agent not available. Install optional dependencies.")
        return
    
    print("=== Testing Memory Integration ===")
    
    # Create agent with memory enabled
    agent = EnhancedChatAgent(
        model_provider="anthropic",
        enable_memory=True,  # Enable memory
        enable_workflows=False,
        enable_threads=False,
        memory_config={
            "short_term_capacity": 100,
            "vector_store_type": "faiss",  # Use local FAISS
            "persist_directory": "./test_memory"
        }
    )
    
    print(f"Agent created with features: {agent.get_features_status()}")
    
    # Simulate some conversations
    test_conversations = [
        ("My name is Alice and I love Python programming", "assistant_response_1"),
        ("I also enjoy machine learning", "assistant_response_2"),
        ("What's my name?", "assistant_response_3"),  # This should trigger memory search
        ("What programming language do I like?", "assistant_response_4")  # This too
    ]
    
    print("\n--- Simulating Conversations ---")
    
    for user_msg, assistant_msg in test_conversations:
        print(f"\nUser: {user_msg}")
        
        # This would normally come from the actual chat
        # For testing, we'll manually update memory
        agent._update_memory(user_msg, assistant_msg)
        
        # Search for relevant memories
        memories = agent._search_memories(user_msg)
        if memories:
            print("Found relevant memories:")
            formatted = agent._format_memories(memories)
            print(formatted)
        else:
            print("No relevant memories found")
    
    # Check memory statistics
    print("\n--- Memory Statistics ---")
    if agent.memory_enabled:
        stats = agent.short_term_memory.get_statistics()
        print(f"Short-term memories: {stats['total_memories']}")
        print(f"Memory utilization: {stats['utilization']:.1%}")
        
        # Export memory state
        memory_export = agent.export_memory()
        print(f"\nMemory export available with {len(memory_export)} components")


def create_memory_enabled_app():
    """Create the FastAPI app with memory-enabled agent"""
    
    # This shows how to modify main.py to use memory
    
    # Import the original main app
    from main import app, chat_agent
    
    if ENHANCED_AVAILABLE:
        # Replace the global agent with enhanced version
        import main
        main.chat_agent = EnhancedChatAgent(
            model_provider=os.getenv("MODEL_PROVIDER", "anthropic"),
            enable_memory=True,
            enable_workflows=True,
            enable_threads=True,
            memory_config={
                "short_term_capacity": 200,
                "vector_store_type": "faiss",
                "embedding_provider": "openai",
                "persist_directory": "./production_memory"
            }
        )
        print("✅ Memory-enabled agent activated!")
        print("The chat will now remember conversations!")
    else:
        print("⚠️  Using basic agent without memory")
        print("Install optional dependencies to enable memory:")
        print("  pip install -r requirements-optional.txt")
    
    return app


if __name__ == "__main__":
    import asyncio
    
    # Test memory integration
    asyncio.run(test_memory_integration())
    
    print("\n" + "="*50)
    print("To run the app with memory enabled:")
    print("1. Install optional dependencies: pip install -r requirements-optional.txt")
    print("2. Use this file instead of main.py: python main_with_memory.py")
    print("3. Or import create_memory_enabled_app() in your main.py")
    print("="*50)