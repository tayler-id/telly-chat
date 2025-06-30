#!/usr/bin/env python3
"""Check if enhanced features are available"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check what main.py sees
try:
    from agents.enhanced_chat_agent import EnhancedChatAgent
    from config import get_agent_config, MEMORY_CONFIG
    print("✅ EnhancedChatAgent imported successfully")
    print("ENHANCED_AVAILABLE would be True")
except ImportError as e:
    print("❌ EnhancedChatAgent import failed:", e)
    print("ENHANCED_AVAILABLE would be False")

# Test the imports that might fail
print("\nTesting memory imports:")
try:
    from memory.short_term import ShortTermMemory, MemoryPriority
    from memory.long_term import LongTermMemory
    from memory.episodic import EpisodicMemory, EpisodeType
    from memory.episodic_store import EpisodicStore
    print("✅ All memory imports successful")
except ImportError as e:
    print("❌ Memory import failed:", e)

# Check config
from config import get_agent_config
config = get_agent_config()
print("\nAgent config:", config)