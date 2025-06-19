#!/usr/bin/env python3
"""Test script to verify full transcript saving with a longer video"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.simple_chat_agent import SimpleChatAgent

async def test_long_transcript():
    """Test that full transcripts are being saved for longer videos"""
    
    # Initialize agent
    agent = SimpleChatAgent(enable_transcript_store=True)
    
    # Test with a longer video - use a popular educational video
    test_url = "https://www.youtube.com/watch?v=0NHCyq8bBcM"
    
    print("Testing YouTube transcript extraction with longer video...")
    print(f"URL: {test_url}")
    print("-" * 60)
    
    # Process through chat to see the tool output
    messages = []
    full_output = ""
    
    async for chunk in agent.chat(f"Please analyze this YouTube video: {test_url}", messages):
        if chunk['type'] == 'text':
            full_output += chunk['content']
        elif chunk['type'] == 'tool_result':
            print("\n📋 Tool output preview (first 1000 chars):")
            print(chunk['content']['output'][:1000])
            print("...")
    
    # Check if transcript was saved
    if agent.transcript_store:
        # Get the most recent transcript
        recent_transcripts = agent.transcript_store.get_recent_transcripts(1)
        if recent_transcripts:
            saved_record = recent_transcripts[0]
            print(f"\n✓ Retrieved saved transcript:")
            print(f"  Title: {saved_record.title}")
            print(f"  Transcript length: {len(saved_record.transcript)} characters")
            print(f"  Action plan length: {len(saved_record.action_plan)} characters")
            
            # Show a sample of the transcript
            print(f"\n📝 Transcript preview (first 500 chars):")
            print("-" * 60)
            print(saved_record.transcript[:500])
            print("...")
            print("-" * 60)
            
            # Check if we have a substantial transcript
            if len(saved_record.transcript) > 1000:
                print(f"\n✅ SUCCESS: Full transcript was saved ({len(saved_record.transcript):,} characters)!")
            else:
                print(f"\n❌ WARNING: Transcript seems truncated ({len(saved_record.transcript)} characters)")
        else:
            print("\n❌ ERROR: No recent transcripts found")
    else:
        print("\n❌ ERROR: Transcript store not available")
    
    # Cleanup
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(test_long_transcript())