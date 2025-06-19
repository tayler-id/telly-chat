#!/usr/bin/env python3
"""Test YouTube tool calling"""
import asyncio
import sys
sys.path.insert(0, '.')

from agents.chat_agent import ChatAgent
from dotenv import load_dotenv

load_dotenv()

async def test_youtube():
    agent = ChatAgent(model_provider="anthropic")
    
    print("Testing YouTube URL processing...")
    
    # Test with a YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    response_chunks = []
    async for chunk in agent.chat(f"Can you get the transcript for {test_url}", stream=True):
        if chunk['type'] == 'tool_call':
            print(f"\nTool called: {chunk['content']['tool']}")
            print(f"Tool input: {chunk['content']['input']}")
        elif chunk['type'] == 'tool_result':
            print(f"\nTool result received (truncated): {str(chunk['content']['output'])[:200]}...")
        elif chunk['type'] == 'text':
            response_chunks.append(chunk['content'])
    
    print("\n\nFull response:")
    full_text = ''.join(response_chunks)
    print(full_text[:1000] + "..." if len(full_text) > 1000 else full_text)

if __name__ == "__main__":
    asyncio.run(test_youtube())