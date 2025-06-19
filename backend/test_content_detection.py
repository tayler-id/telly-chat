#!/usr/bin/env python3
"""Test content type detection logic"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage


def test_content_detection():
    """Test content type detection with sample titles and transcripts"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found")
        return
    
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        anthropic_api_key=api_key,
        temperature=0.3
    )
    
    # Test cases with expected content types
    test_cases = [
        {
            "title": "How to Build a React App - Complete Tutorial for Beginners",
            "transcript": "Welcome to this tutorial where I'll show you step by step how to build a React application from scratch. First, we need to install Node.js. Then we'll use create-react-app to bootstrap our project. Let me walk you through each step...",
            "expected": "tutorial"
        },
        {
            "title": "Breaking: Major Tech Company Announces Layoffs",
            "transcript": "In breaking news today, a major technology company has announced significant layoffs affecting thousands of employees. The CEO stated that due to economic conditions and restructuring efforts, the company will be reducing its workforce by 15%. This comes as a shock to many in the industry...",
            "expected": "news"
        },
        {
            "title": "iPhone 15 Pro Review - Is It Worth the Upgrade?",
            "transcript": "I've been using the iPhone 15 Pro for two weeks now, and here's my honest review. Let's start with the pros: the camera system is absolutely incredible, especially in low light. The titanium build feels premium. However, there are some cons to consider. The battery life hasn't improved much from the 14 Pro...",
            "expected": "review"
        },
        {
            "title": "Understanding Machine Learning: Neural Networks Explained",
            "transcript": "Today we're going to explore the fascinating world of neural networks. A neural network is a computational model inspired by the human brain. It consists of layers of interconnected nodes or neurons. Let me explain how these networks learn patterns from data through a process called backpropagation...",
            "expected": "educational"
        },
        {
            "title": "AI Generated Content Test Video",
            "transcript": "Greetings. Today I will discuss important topics. First topic is very interesting. It contains many useful information. Second topic is also important. It has significant value. Third topic completes our discussion. Thank you for watching this informative video. Please subscribe for more content.",
            "expected": "AI-generated"
        }
    ]
    
    print("🧪 Testing content type detection...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Title: {test['title']}")
        print(f"Expected: {test['expected']}")
        
        analysis_prompt = f"""Analyze this YouTube video based on its title and transcript excerpt.

Title: {test['title']}
Transcript excerpt (first 1000 chars): {test['transcript'][:1000]}

Determine:
1. Content type - Choose ONE from: tutorial, news, review, entertainment, educational, vlog, documentary, podcast, music, other
2. Is it likely AI-generated content? Look for:
   - Repetitive phrasing or unnatural speech patterns
   - Generic, template-like structure
   - Lack of personal anecdotes or human elements
   - Overly formal or robotic language
   - Mentions of being AI-generated

Respond in this exact format:
CONTENT_TYPE: [type]
AI_GENERATED: [yes/no]
AI_CONFIDENCE: [low/medium/high]
AI_INDICATORS: [brief explanation if yes]"""
        
        try:
            messages = [
                SystemMessage(content="You are an expert at analyzing video content and detecting AI-generated content."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = llm.invoke(messages)
            print("\nAnalysis:")
            print(response.content)
            
            # Parse results
            import re
            type_match = re.search(r'CONTENT_TYPE:\s*(\w+)', response.content)
            ai_match = re.search(r'AI_GENERATED:\s*(yes|no)', response.content, re.IGNORECASE)
            
            if type_match:
                detected_type = type_match.group(1).lower()
                print(f"\n✅ Detected: {detected_type}")
                
                if test['expected'] == 'AI-generated':
                    if ai_match and ai_match.group(1).lower() == 'yes':
                        print("✅ Correctly detected AI-generated content")
                    else:
                        print("❌ Failed to detect AI-generated content")
                elif detected_type == test['expected']:
                    print("✅ Matches expected type!")
                else:
                    print(f"⚠️  Expected {test['expected']}, got {detected_type}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n\n✅ Content detection test completed!")


def test_different_prompts():
    """Test how different content generates different outputs"""
    
    print("\n\n🧪 Testing output generation for different content types...\n")
    
    # This would be done by the enhanced tool, but we can simulate it here
    content_examples = {
        "tutorial": """OVERVIEW
Learn to build a complete React application from scratch

PREREQUISITES
- Basic JavaScript knowledge
- Node.js installed
- Text editor (VS Code recommended)

STEPS
1. Install Node.js and verify installation
2. Create new React app using create-react-app
3. Build component structure
4. Add state management
5. Style with CSS

TIPS & BEST PRACTICES
- Use functional components with hooks
- Keep components small and focused

COMMON ISSUES
- Node version conflicts - use nvm
- Port already in use - kill process on port 3000""",
        
        "news": """HEADLINE
Major tech company announces 15% workforce reduction

KEY POINTS
• 15,000 employees affected globally
• Restructuring focuses on AI and cloud services
• Severance packages include 3 months pay
• Stock price rose 5% on announcement

DETAILED SUMMARY
The technology giant announced today that it will be reducing its workforce by 15%, affecting approximately 15,000 employees worldwide. The CEO cited economic headwinds and the need to focus resources on high-growth areas like artificial intelligence and cloud computing.

IMPLICATIONS
This marks a significant shift in the tech industry's approach to growth, signaling a move from rapid expansion to efficiency-focused operations."""
    }
    
    for content_type, example in content_examples.items():
        print(f"\n--- {content_type.upper()} Output Example ---")
        print(example)
        print("\n" + "="*60)


if __name__ == "__main__":
    test_content_detection()
    test_different_prompts()