"""Enhanced Telly tool with content type detection and custom generation"""

import sys
import os
import re
from typing import Dict, Any, Optional, Tuple
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Add the telly directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../telly'))

try:
    from telly_agent import TellyAgent
except ImportError:
    # If telly_agent is not available, we'll handle it gracefully
    TellyAgent = None


class EnhancedTellyToolInput(BaseModel):
    """Input for the Enhanced Telly YouTube transcript tool"""
    url: str = Field(..., description="YouTube video URL to extract transcript from")


class EnhancedTellyTool(BaseTool):
    """Enhanced tool for extracting YouTube transcripts with intelligent content generation"""
    
    name: str = "youtube_transcript"
    description: str = """Extract transcript from a YouTube video and generate appropriate content based on video type.
    Automatically detects video type (tutorial, news, entertainment, etc.) and generates relevant output.
    Also detects if content appears to be AI-generated."""
    
    args_schema: type[BaseModel] = EnhancedTellyToolInput
    agent: Any = Field(default=None, exclude=True)
    llm: Any = Field(default=None, exclude=True)
    
    def __init__(self, llm=None, **kwargs):
        super().__init__(**kwargs)
        # Initialize the telly agent if available
        if TellyAgent:
            object.__setattr__(self, 'agent', TellyAgent())
        else:
            object.__setattr__(self, 'agent', None)
        
        # Initialize LLM for content analysis
        if llm:
            object.__setattr__(self, 'llm', llm)
        else:
            # Default to Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                object.__setattr__(self, 'llm', ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    anthropic_api_key=api_key,
                    temperature=0.3
                ))
    
    def _detect_content_type(self, title: str, transcript: str) -> Tuple[str, bool]:
        """Detect the type of content and if it's AI-generated"""
        
        analysis_prompt = f"""Analyze this YouTube video based on its title and transcript excerpt.

Title: {title}
Transcript excerpt (first 1000 chars): {transcript[:1000]}

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
            
            response = self.llm.invoke(messages)
            content = response.content
            
            # Parse response
            content_type = "other"
            ai_generated = False
            
            type_match = re.search(r'CONTENT_TYPE:\s*(\w+)', content)
            if type_match:
                content_type = type_match.group(1).lower()
            
            ai_match = re.search(r'AI_GENERATED:\s*(yes|no)', content, re.IGNORECASE)
            if ai_match:
                ai_generated = ai_match.group(1).lower() == 'yes'
            
            return content_type, ai_generated
            
        except Exception as e:
            print(f"Error detecting content type: {e}")
            return "other", False
    
    def _generate_content_based_on_type(self, content_type: str, title: str, transcript: str, ai_generated: bool) -> str:
        """Generate appropriate content based on the video type"""
        
        prompts = {
            "tutorial": f"""Create a step-by-step tutorial guide from this video.

Title: {title}
Transcript: {transcript[:3000]}...

Format the output as:
OVERVIEW
Brief description of what will be learned

PREREQUISITES
- List any required knowledge or tools

STEPS
1. First step with clear instructions
2. Second step...
(continue for all major steps)

TIPS & BEST PRACTICES
- Helpful tips for success

COMMON ISSUES
- Potential problems and solutions""",

            "news": f"""Create a news summary from this video.

Title: {title}
Transcript: {transcript[:3000]}...

Format the output as:
HEADLINE
One-line summary

KEY POINTS
• Main point 1
• Main point 2
• Main point 3
(3-5 key points)

DETAILED SUMMARY
2-3 paragraphs with the full story

CONTEXT & BACKGROUND
Any relevant background information

IMPLICATIONS
What this means going forward""",

            "review": f"""Create a structured review summary from this video.

Title: {title}
Transcript: {transcript[:3000]}...

Format the output as:
PRODUCT/SERVICE REVIEWED
What is being reviewed

REVIEWER'S VERDICT
Overall rating or conclusion

PROS
• Positive point 1
• Positive point 2
(list all mentioned pros)

CONS
• Negative point 1
• Negative point 2
(list all mentioned cons)

KEY FEATURES DISCUSSED
- Feature 1: Description
- Feature 2: Description

RECOMMENDATION
Who should consider this and why""",

            "educational": f"""Create educational notes from this video.

Title: {title}
Transcript: {transcript[:3000]}...

Format the output as:
TOPIC
Main subject covered

KEY CONCEPTS
1. Concept 1: Explanation
2. Concept 2: Explanation
(list all major concepts)

MAIN POINTS
• Important point 1
• Important point 2
(comprehensive list)

EXAMPLES GIVEN
- Example 1
- Example 2

SUMMARY
2-3 paragraph summary of the content

FURTHER LEARNING
Suggested topics to explore next""",

            "default": f"""Create an action plan from this video content.

Title: {title}
Transcript: {transcript[:3000]}...

Format the output as:
SUMMARY
Brief overview of the video content

KEY TAKEAWAYS
• Main point 1
• Main point 2
• Main point 3

ACTION ITEMS
1. Specific action to take
2. Another actionable step
(list all actionable items)

RESOURCES MENTIONED
- Any tools, websites, or resources mentioned

NEXT STEPS
What to do after watching this video"""
        }
        
        # Choose appropriate prompt
        prompt_template = prompts.get(content_type, prompts["default"])
        
        # Add AI-generated warning if detected
        if ai_generated:
            prompt_template = f"""⚠️ AI-GENERATED CONTENT DETECTED ⚠️
This video appears to contain AI-generated content. Take the information with appropriate caution.

""" + prompt_template
        
        try:
            messages = [
                SystemMessage(content="You are an expert at extracting actionable information from video transcripts."),
                HumanMessage(content=prompt_template)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            return f"Error generating content: {str(e)}"
    
    def _extract_video_title(self, url: str, transcript: str) -> str:
        """Try to extract video title from transcript or URL"""
        # Try to extract from transcript first lines
        lines = transcript.split('\n')
        if lines and len(lines[0]) < 200:  # Reasonable title length
            return lines[0].strip()
        
        # Default to video ID from URL
        video_id_match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url)
        if video_id_match:
            return f"Video {video_id_match.group(1)}"
        
        return "YouTube Video"
    
    def _run(self, url: str) -> str:
        """Run the tool synchronously"""
        try:
            # First, extract the transcript using the original tool
            if not self.agent:
                return "Error: Telly agent not available. Please check your installation."
            
            result = self.agent.process_video(url, generate_plan=False)
            
            if not result['success']:
                return f"Error extracting transcript: {result.get('error', 'Unknown error')}"
            
            # Get video info
            video_id = result.get('video_id', 'unknown')
            language = result.get('language', 'unknown')
            transcript = result.get('transcript', '')
            
            # Try to get title from the Telly tool result or extract it
            title = result.get('title', self._extract_video_title(url, transcript))
            
            # Detect content type and AI generation
            content_type, ai_generated = self._detect_content_type(title, transcript)
            
            # Generate appropriate content
            generated_content = self._generate_content_based_on_type(
                content_type, title, transcript, ai_generated
            )
            
            # Format the response
            response_parts = []
            
            # Add video info
            response_parts.append(f"### 📹 Video Information")
            response_parts.append(f"- **Title:** {title}")
            response_parts.append(f"- **Video ID:** `{video_id}`")
            response_parts.append(f"- **Language:** {language}")
            response_parts.append(f"- **Content Type:** {content_type.title()}")
            if ai_generated:
                response_parts.append(f"- **⚠️ AI-Generated:** Likely (confidence: high)")
            response_parts.append("")
            
            # Add transcript preview
            response_parts.append("### 📝 Transcript")
            display_limit = 800
            
            if len(transcript) > display_limit:
                response_parts.append(f"*Showing first {display_limit} characters:*")
                response_parts.append("")
                response_parts.append("```")
                response_parts.append(transcript[:display_limit].strip() + "...")
                response_parts.append("```")
                response_parts.append("")
                response_parts.append(f"📊 **Full transcript:** {len(transcript):,} characters • {len(transcript.split()):,} words")
            else:
                response_parts.append("")
                response_parts.append("```")
                response_parts.append(transcript.strip())
                response_parts.append("```")
            
            response_parts.append("")
            response_parts.append("---")
            response_parts.append("")
            
            # Add generated content based on type
            if content_type == "tutorial":
                response_parts.append("### 🎓 Tutorial Guide")
            elif content_type == "news":
                response_parts.append("### 📰 News Summary")
            elif content_type == "review":
                response_parts.append("### ⭐ Review Summary")
            elif content_type == "educational":
                response_parts.append("### 📚 Educational Notes")
            else:
                response_parts.append("### 📋 Action Plan")
            
            response_parts.append("")
            response_parts.append(generated_content)
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"Error using Enhanced Telly tool: {str(e)}"
    
    async def _arun(self, url: str) -> str:
        """Run the tool asynchronously"""
        return self._run(url)


def get_enhanced_telly_tool(llm=None) -> EnhancedTellyTool:
    """Factory function to create an Enhanced Telly tool instance"""
    return EnhancedTellyTool(llm=llm)