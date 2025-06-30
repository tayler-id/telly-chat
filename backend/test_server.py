#!/usr/bin/env python3
"""Test script to verify the server can start"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from models.schemas import Message
    print("✓ Models import successful")
except Exception as e:
    print(f"✗ Models import failed: {e}")

try:
    from services.session_manager import SessionManager
    print("✓ Session manager import successful")
except Exception as e:
    print(f"✗ Session manager import failed: {e}")

try:
    from agents.tools.telly_tool import get_telly_tool
    print("✓ Telly tool import successful")
except Exception as e:
    print(f"✗ Telly tool import failed: {e}")

try:
    from agents.chat_agent import ChatAgent
    print("✓ Chat agent import successful")
except Exception as e:
    print(f"✗ Chat agent import failed: {e}")

# Test creating instances
try:
    tool = get_telly_tool()
    print("✓ Telly tool creation successful")
except Exception as e:
    print(f"✗ Telly tool creation failed: {e}")

try:
    agent = ChatAgent(model_provider="anthropic")
    print("✓ Chat agent creation successful")
except Exception as e:
    print(f"✗ Chat agent creation failed: {e}")

print("\nAll tests completed!")