#!/usr/bin/env python3
"""Test script for the enhanced YouTube tool"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.tools.enhanced_telly_tool import get_enhanced_telly_tool
from langchain_anthropic import ChatAnthropic


async def test_enhanced_tool():
    """Test the enhanced YouTube tool with different video types"""
    
    # Initialize the tool
    print("🔧 Initializing enhanced YouTube tool...")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        return
    
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=api_key,
        temperature=0.3
    )
    
    tool = get_enhanced_telly_tool(llm)
    
    # Test videos of different types
    test_videos = [
        {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "description": "Music video (Rick Astley)",
            "expected_type": "music or entertainment"
        },
        {
            "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",
            "description": "Music video (Gangnam Style)",
            "expected_type": "music or entertainment"
        },
        {
            "url": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
            "description": "Music video (Shape of You)",
            "expected_type": "music"
        }
    ]
    
    print("\n📺 Testing with sample videos...\n")
    
    for video in test_videos:
        print(f"➡️  Testing: {video['description']}")
        print(f"   URL: {video['url']}")
        print(f"   Expected type: {video['expected_type']}")
        print("\n" + "="*80 + "\n")
        
        try:
            # Run the tool
            result = await tool._arun(video['url'])
            
            # Extract content type from result
            if "**Content Type:**" in result:
                import re
                type_match = re.search(r'\*\*Content Type:\*\* ([^\n]+)', result)
                if type_match:
                    detected_type = type_match.group(1)
                    print(f"✅ Detected content type: {detected_type}")
            
            # Check for AI detection
            if "**⚠️ AI-Generated:**" in result:
                print("🤖 AI-generated content detected!")
            
            # Show first 500 chars of analysis
            print("\n📝 Analysis preview:")
            print(result[:500] + "..." if len(result) > 500 else result)
            
        except Exception as e:
            print(f"❌ Error processing video: {str(e)}")
        
        print("\n" + "="*80 + "\n")
        
        # Small delay between requests
        await asyncio.sleep(2)
    
    print("✅ Test completed!")


async def test_single_video(url: str):
    """Test a single video URL"""
    
    print(f"🔧 Testing single video: {url}")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        return
    
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=api_key,
        temperature=0.3
    )
    
    tool = get_enhanced_telly_tool(llm)
    
    try:
        result = await tool._arun(url)
        print("\n" + "="*80 + "\n")
        print(result)
        print("\n" + "="*80 + "\n")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Main entry point"""
    
    # Check for command line argument
    if len(sys.argv) > 1:
        # Test specific video
        url = sys.argv[1]
        asyncio.run(test_single_video(url))
    else:
        # Run default tests
        asyncio.run(test_enhanced_tool())


if __name__ == "__main__":
    main()