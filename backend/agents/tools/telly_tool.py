"""Telly tool wrapper for LangChain integration"""
import sys
import os
from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json

# Add the telly directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../telly'))

from telly_agent import TellyAgent, YouTubeTranscriptTool


class TellyToolInput(BaseModel):
    """Input for the Telly YouTube transcript tool"""
    url: str = Field(..., description="YouTube video URL to extract transcript from")
    generate_action_plan: bool = Field(
        default=True, 
        description="Whether to generate an action plan from the transcript"
    )


class TellyTool(BaseTool):
    """Tool for extracting YouTube transcripts and generating action plans"""
    
    name: str = "youtube_transcript"
    description: str = """Extract transcript from a YouTube video and optionally generate an action plan.
    Use this tool when the user asks about YouTube videos, wants transcripts, or needs video content analysis.
    The tool returns the full transcript and can create actionable plans from the video content."""
    
    args_schema: type[BaseModel] = TellyToolInput
    agent: Any = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize the agent after Pydantic validation
        object.__setattr__(self, 'agent', TellyAgent())
    
    def _run(self, url: str, generate_action_plan: bool = True) -> str:
        """Run the tool synchronously"""
        try:
            # Process the video
            result = self.agent.process_video(url, generate_plan=generate_action_plan)
            
            if not result['success']:
                return f"Error extracting transcript: {result.get('error', 'Unknown error')}"
            
            # Format the response with markdown
            response_parts = []
            
            # Add video info
            response_parts.append(f"### 📹 Video Information")
            response_parts.append(f"- **Video ID:** `{result['video_id']}`")
            response_parts.append(f"- **Language:** {result['language']}")
            response_parts.append("")
            
            # Add transcript
            transcript = result['transcript']
            response_parts.append("### 📝 Transcript")
            
            # Always truncate for display
            display_limit = 1500
            
            if len(transcript) > display_limit:
                # For long transcripts, show truncated version
                response_parts.append(f"*Showing first {display_limit} characters of transcript:*")
                response_parts.append("")
                
                # Show truncated content in a code block for better formatting
                response_parts.append("```")
                response_parts.append(transcript[:display_limit].strip() + "...")
                response_parts.append("```")
                response_parts.append("")
                response_parts.append(f"📊 **Full transcript:** {len(transcript):,} characters • {len(transcript.split()):,} words")
                response_parts.append("")
                response_parts.append("💾 **Click 'Save Transcript & Action Plan' below to download the complete transcript**")
            else:
                # Short transcript - show in code block
                response_parts.append("")
                response_parts.append("```")
                response_parts.append(transcript.strip())
                response_parts.append("```")
                response_parts.append("")
            
            # Add action plan if generated
            if generate_action_plan and 'action_plan' in result:
                response_parts.append("")
                response_parts.append("---")
                response_parts.append("")
                
                if result['action_plan']['success']:
                    response_parts.append("### 📋 Action Plan")
                    response_parts.append("")
                    response_parts.append(result['action_plan']['content'])
                else:
                    response_parts.append(f"⚠️ *Note: Action plan generation failed: {result['action_plan']['error']}*")
            
            # Store full transcript in metadata for save functionality
            full_response = "\n".join(response_parts)
            
            # Don't append the full transcript to the response at all
            # The save button will fetch it separately from the backend
            return full_response
            
        except Exception as e:
            return f"Error using Telly tool: {str(e)}"
    
    async def _arun(self, url: str, generate_action_plan: bool = True) -> str:
        """Run the tool asynchronously"""
        # For now, just call the sync version
        # In a production system, you'd want to make this properly async
        return self._run(url, generate_action_plan)


def get_telly_tool() -> TellyTool:
    """Factory function to create a Telly tool instance"""
    return TellyTool()