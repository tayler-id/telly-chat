#!/usr/bin/env python3
"""Test the simplified Telly Chat system"""

import asyncio
import os
from dotenv import load_dotenv
from agents.simple_chat_agent import SimpleChatAgent

# Load environment variables
load_dotenv()


async def test_simple_agent():
    """Test the simplified agent"""
    
    print("=== Testing Simplified Telly Chat ===\n")
    
    # Initialize agent
    print("1. Initializing agent...")
    agent = SimpleChatAgent(model_provider="anthropic")
    print(f"   Features: {agent.get_features_status()}")
    
    # Test 1: Simple chat
    print("\n2. Testing simple chat...")
    response = ""
    async for chunk in agent.chat("Hello! What can you help me with?"):
        if chunk["type"] == "text":
            response += chunk["content"]
    print(f"   Response: {response[:100]}...")
    
    # Test 2: YouTube processing
    print("\n3. Testing YouTube video processing...")
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    result = await agent.process_youtube_video(test_url)
    
    if result["success"]:
        print(f"   ✓ Success!")
        print(f"   - ID: {result['id']}")
        print(f"   - Title: {result['title']}")
        print(f"   - Summary: {result['summary'][:100]}...")
        print(f"   - Transcript length: {result['transcript_length']} chars")
    else:
        print(f"   ✗ Failed: {result['error']}")
    
    # Test 3: Search transcripts
    if agent.transcript_store:
        print("\n4. Testing transcript search...")
        search_results = await agent.search_transcripts("elephant")
        print(f"   Found {len(search_results)} results")
        for i, result in enumerate(search_results[:3]):
            print(f"   {i+1}. {result['title']} (score: {result['score']:.2f})")
    
    # Test 4: Chat with YouTube URL
    print("\n5. Testing chat with YouTube URL...")
    response = ""
    tool_used = False
    async for chunk in agent.chat(f"What is this video about? {test_url}"):
        if chunk["type"] == "text":
            response += chunk["content"]
        elif chunk["type"] == "tool_call":
            tool_used = True
            print(f"   → Using tool: {chunk['content']['tool']}")
    
    print(f"   Tool used: {tool_used}")
    print(f"   Response preview: {response[:200]}...")
    
    print("\n✅ All tests completed!")


async def test_api_endpoints():
    """Test API endpoints"""
    import aiohttp
    
    print("\n=== Testing API Endpoints ===\n")
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test health
        async with session.get(f"{base_url}/health") as resp:
            if resp.status == 200:
                print("✓ Health check passed")
            else:
                print("✗ Health check failed")
        
        # Test features
        async with session.get(f"{base_url}/features") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✓ Features: {data['features']}")
            else:
                print("✗ Features check failed")
        
        # Test YouTube processing
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        async with session.post(f"{base_url}/youtube/process?url={test_url}") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✓ YouTube processing: {data['title']}")
            else:
                print("✗ YouTube processing failed")


if __name__ == "__main__":
    # Run agent tests
    asyncio.run(test_simple_agent())
    
    # Uncomment to test API endpoints (requires server running)
    # asyncio.run(test_api_endpoints())