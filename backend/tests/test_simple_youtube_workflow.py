#!/usr/bin/env python3
"""Simple test of YouTube workflow functionality"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.enhanced_chat_agent import EnhancedChatAgent
from agents.tools.telly_tool import get_telly_tool
from config import get_agent_config
from memory.transcript_store import TranscriptStore

# Load environment variables
load_dotenv()


async def simple_youtube_workflow(youtube_url: str):
    """
    Simple YouTube workflow without the complex workflow engine
    
    Steps:
    1. Extract transcript
    2. Analyze content
    3. Generate summary
    4. Save to store
    5. Display results
    """
    
    print("=== Simple YouTube Analysis Workflow ===\n")
    print(f"Video URL: {youtube_url}\n")
    
    # Initialize agent
    print("1. Initializing agent...")
    config = get_agent_config()
    agent = EnhancedChatAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "anthropic"),
        **config
    )
    
    # Get transcript store
    transcript_store = agent.transcript_store if hasattr(agent, 'transcript_store') else None
    
    try:
        # Step 1: Extract transcript
        print("\n2. Extracting transcript...")
        tool = get_telly_tool()
        transcript_result = await tool.arun(youtube_url)
        
        # Parse the result
        lines = transcript_result.split('\n')
        video_id = None
        title = "YouTube Video"
        transcript_text = []
        action_plan = []
        in_transcript = False
        in_action_plan = False
        
        for line in lines:
            if "Video ID:" in line and "`" in line:
                video_id = line.split("`")[1]
            elif "**Title:**" in line:
                title = line.replace("**Title:**", "").strip()
            elif "### 📝 Transcript" in line or "### 📝 Full Transcript" in line:
                in_transcript = True
                in_action_plan = False
            elif "### 📋 Action Plan" in line:
                in_transcript = False
                in_action_plan = True
            elif in_transcript and line.strip() and not line.startswith("```"):
                transcript_text.append(line)
            elif in_action_plan and line.strip():
                action_plan.append(line)
        
        full_transcript = "\n".join(transcript_text).strip()
        full_action_plan = "\n".join(action_plan).strip()
        
        print(f"✓ Extracted transcript ({len(full_transcript)} chars)")
        print(f"  Video ID: {video_id}")
        print(f"  Title: {title}")
        
        # Step 2: Analyze content
        print("\n3. Analyzing content...")
        analysis_prompt = f"""
        Analyze this YouTube video transcript and provide:
        1. Main topics (3-5 bullet points)
        2. Key takeaways
        3. Target audience
        4. Content quality (1-10 scale with reason)
        
        Title: {title}
        Transcript preview: {full_transcript[:1500]}...
        
        Keep the analysis concise and actionable.
        """
        
        analysis_response = ""
        async for chunk in agent.chat(analysis_prompt, [], stream=True):
            if chunk["type"] == "text":
                analysis_response += chunk["content"]
        
        print("✓ Content analyzed")
        
        # Step 3: Generate summary
        print("\n4. Generating summary...")
        summary_prompt = f"""
        Create a 2-3 sentence summary of this YouTube video.
        
        Title: {title}
        Analysis: {analysis_response[:500]}
        
        Summary should explain what the video is about and why it's valuable.
        """
        
        summary_response = ""
        async for chunk in agent.chat(summary_prompt, [], stream=True):
            if chunk["type"] == "text":
                summary_response += chunk["content"]
        
        print("✓ Summary generated")
        
        # Step 4: Save to store
        saved_id = None
        if transcript_store and full_transcript:
            print("\n5. Saving to transcript store...")
            try:
                saved_id = transcript_store.save_transcript(
                    url=youtube_url,
                    title=title,
                    transcript=full_transcript,
                    action_plan=full_action_plan,
                    summary=summary_response,
                    metadata={
                        "video_id": video_id,
                        "analysis": analysis_response,
                        "processed_at": datetime.now().isoformat()
                    }
                )
                print(f"✓ Saved with ID: {saved_id}")
            except Exception as e:
                print(f"✗ Failed to save: {e}")
        else:
            print("\n5. Skipping save (no transcript store available)")
        
        # Step 5: Display results
        print("\n" + "="*50)
        print("WORKFLOW RESULTS")
        print("="*50)
        
        print(f"\n📹 Video: {title}")
        print(f"🔗 URL: {youtube_url}")
        print(f"🆔 Video ID: {video_id}")
        
        print(f"\n📝 Summary:\n{summary_response}")
        
        print(f"\n🔍 Analysis:")
        print(analysis_response)
        
        if full_action_plan:
            print(f"\n📋 Action Plan Preview:")
            preview = full_action_plan[:500]
            if len(full_action_plan) > 500:
                preview += "..."
            print(preview)
        
        if saved_id:
            print(f"\n💾 Saved to store with ID: {saved_id}")
            
            # Try to retrieve it
            retrieved = transcript_store.get_transcript(saved_id)
            if retrieved:
                print(f"   ✓ Verified: Can retrieve saved transcript")
                print(f"   - Access count: {retrieved.accessed_count}")
        
        print("\n✅ Workflow completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()


if __name__ == "__main__":
    # Test URL - you can change this to any YouTube video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # You can also pass a URL as command line argument
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    # Run the workflow
    asyncio.run(simple_youtube_workflow(test_url))