#!/usr/bin/env python3
"""Test YouTube Analysis Workflow"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows.youtube_workflow import run_youtube_analysis, create_youtube_workflow
from agents.enhanced_chat_agent import EnhancedChatAgent
from config import get_agent_config

# Load environment variables
load_dotenv()


async def test_youtube_workflow():
    """Test the YouTube analysis workflow"""
    
    print("=== YouTube Analysis Workflow Test ===\n")
    
    # Initialize agent
    print("Initializing agent...")
    config = get_agent_config()
    agent = EnhancedChatAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "anthropic"),
        **config
    )
    
    # Get transcript store if available
    transcript_store = None
    if hasattr(agent, 'transcript_store'):
        transcript_store = agent.transcript_store
        print("✓ Transcript store available")
    else:
        print("✗ No transcript store available")
    
    # Test URL (you can change this to any YouTube video)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example URL
    
    print(f"\nAnalyzing video: {test_url}")
    print("This will:")
    print("1. Extract transcript")
    print("2. Analyze content")
    print("3. Generate summary")
    print("4. Save to store")
    print("5. Generate report")
    print("\nStarting workflow...\n")
    
    try:
        # Run the workflow
        results = await run_youtube_analysis(
            youtube_url=test_url,
            agent=agent,
            transcript_store=transcript_store
        )
        
        # Display results
        print(f"\n=== Workflow Results ===")
        print(f"Workflow ID: {results['workflow_id']}")
        print(f"Status: {results['status']}")
        
        if results['errors']:
            print(f"\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error['node']}: {error['error']}")
        
        if results['report']:
            print(f"\n=== Generated Report ===")
            print(results['report'])
        
        # Show what was saved
        if transcript_store and results['all_results'].get('save_to_store', {}).get('saved'):
            transcript_id = results['all_results']['save_to_store']['transcript_id']
            print(f"\n✓ Transcript saved with ID: {transcript_id}")
            
            # Try to retrieve it
            saved_transcript = transcript_store.get_transcript(transcript_id)
            if saved_transcript:
                print(f"  Title: {saved_transcript.title}")
                print(f"  URL: {saved_transcript.url}")
                print(f"  Saved at: {saved_transcript.saved_at}")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    if hasattr(agent, 'cleanup'):
        await agent.cleanup()


async def test_workflow_with_multiple_videos():
    """Test workflow with multiple videos"""
    
    print("\n=== Batch YouTube Analysis ===\n")
    
    # Initialize agent
    config = get_agent_config()
    agent = EnhancedChatAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "anthropic"),
        **config
    )
    
    # List of videos to analyze
    video_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        # Add more URLs here
    ]
    
    # Create workflow once
    workflow = create_youtube_workflow(agent, agent.transcript_store)
    
    # Process each video
    for url in video_urls:
        print(f"\nProcessing: {url}")
        try:
            state = await workflow.execute({"youtube_url": url})
            print(f"  Status: {state.status.value}")
            if state.errors:
                print(f"  Errors: {len(state.errors)}")
        except Exception as e:
            print(f"  Failed: {e}")
    
    print("\n✓ Batch processing complete")


if __name__ == "__main__":
    # Run single video test
    asyncio.run(test_youtube_workflow())
    
    # Uncomment to test batch processing
    # asyncio.run(test_workflow_with_multiple_videos())