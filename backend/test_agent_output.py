#!/usr/bin/env python3
"""Test what the agent is actually outputting"""
import asyncio
import sys
sys.path.insert(0, '.')

from agents.chat_agent import ChatAgent
from dotenv import load_dotenv

load_dotenv()

async def test_agent():
    agent = ChatAgent(model_provider="anthropic")
    
    print("Testing agent output...")
    
    # Test simple message
    response_chunks = []
    async for chunk in agent.chat("Hello", stream=False):
        print(f"Chunk type: {chunk['type']}")
        print(f"Chunk content: {chunk['content']}")
        print(f"Content type: {type(chunk['content'])}")
        response_chunks.append(chunk)
    
    print("\nFull response:")
    full_text = ''.join(chunk['content'] for chunk in response_chunks if chunk['type'] == 'text')
    print(full_text)
    
    # Test the raw agent executor
    print("\n\nTesting raw agent executor...")
    inputs = {"input": "Hello", "chat_history": []}
    response = agent.agent.invoke(inputs)
    print(f"Raw response type: {type(response)}")
    print(f"Raw response keys: {response.keys() if isinstance(response, dict) else 'Not a dict'}")
    print(f"Raw output: {response.get('output') if isinstance(response, dict) else response}")
    print(f"Output type: {type(response.get('output')) if isinstance(response, dict) else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(test_agent())