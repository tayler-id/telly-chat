#!/usr/bin/env python3
"""Debug memory initialization"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.enhanced_chat_agent import EnhancedChatAgent
from config import get_agent_config

# Get config
config = get_agent_config()
print("Agent config:", config)

# Initialize agent
agent = EnhancedChatAgent(
    model_provider="anthropic",
    **config
)

print("\nAgent attributes:")
print(f"  memory_capability: {agent.memory_capability}")
print(f"  memory_enabled: {agent.memory_enabled}")
print(f"  episodic_memory: {agent.episodic_memory}")
print(f"  short_term_memory: {agent.short_term_memory}")
print(f"  long_term_memory: {agent.long_term_memory}")
print(f"  current_episode_id: {agent.current_episode_id}")

print("\nFeatures status:", agent.get_features_status())

# Check if episodic_memory has the required methods
if agent.episodic_memory:
    print("\nEpisodic memory methods:")
    print(f"  get_active_episodes: {hasattr(agent.episodic_memory, 'get_active_episodes')}")
    print(f"  get_session_episodes: {hasattr(agent.episodic_memory, 'get_session_episodes')}")
    print(f"  search_episodes_by_content: {hasattr(agent.episodic_memory, 'search_episodes_by_content')}")
else:
    print("\nNo episodic memory initialized!")