#!/usr/bin/env python3
"""Test the YouTube tool directly"""
import sys
sys.path.insert(0, '.')

from agents.tools.telly_tool import get_telly_tool
from dotenv import load_dotenv

load_dotenv()

def test_direct_tool():
    tool = get_telly_tool()
    
    print("Testing YouTube tool directly...")
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=OC04sP_QgTI"
    
    print(f"\nExtracting transcript for: {test_url}")
    
    result = tool._run(url=test_url, generate_action_plan=False)
    
    print("\nResult:")
    print(result[:2000] + "..." if len(result) > 2000 else result)
    
    print(f"\nFull result length: {len(result)} characters")

if __name__ == "__main__":
    test_direct_tool()