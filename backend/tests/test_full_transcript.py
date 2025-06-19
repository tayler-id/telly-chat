#!/usr/bin/env python3
"""Test script to verify full transcript saving"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.simple_chat_agent import SimpleChatAgent
from memory.transcript_store import TranscriptStore

async def test_full_transcript():
    """Test that full transcripts are being saved"""
    
    # Initialize agent
    agent = SimpleChatAgent(enable_transcript_store=True)
    
    # Test URL - use a short video for testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    print("Testing YouTube transcript extraction and saving...")
    print(f"URL: {test_url}")
    print("-" * 60)
    
    # Process the video
    result = await agent.process_youtube_video(test_url)
    
    if result['success']:
        print(f"✓ Video processed successfully")
        print(f"  Title: {result['title']}")
        print(f"  Transcript length: {result['transcript_length']} characters")
        print(f"  Has action plan: {result['has_action_plan']}")
        print(f"  Saved ID: {result['id']}")
        
        # Now retrieve the saved transcript
        if result['id'] and agent.transcript_store:
            saved_record = agent.transcript_store.get_transcript(result['id'])
            if saved_record:
                print("\n✓ Retrieved saved transcript:")
                print(f"  Title: {saved_record.title}")
                print(f"  Transcript length: {len(saved_record.transcript)} characters")
                print(f"  Action plan length: {len(saved_record.action_plan)} characters")
                
                print("\n📝 Full transcript content:")
                print("-" * 60)
                print(saved_record.transcript)
                print("-" * 60)
                
                # Check if we have the full transcript
                if len(saved_record.transcript) > 100:
                    print("\n✅ SUCCESS: Full transcript was saved!")
                else:
                    print("\n❌ WARNING: Transcript seems truncated")
                    
            else:
                print("\n❌ ERROR: Could not retrieve saved transcript")
        else:
            print("\n❌ ERROR: No ID returned or transcript store not available")
    else:
        print(f"❌ Error processing video: {result['error']}")
    
    # Cleanup
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(test_full_transcript())