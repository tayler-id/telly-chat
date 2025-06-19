"""Simplified chat agent with core functionality only"""

import os
import re
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from agents.tools.enhanced_telly_tool import get_enhanced_telly_tool
from memory.transcript_store import TranscriptStore
from models.schemas import Message, MessageRole


SYSTEM_PROMPT = """You are a helpful AI assistant with advanced YouTube video analysis capabilities.

When a user shares a YouTube URL, you can:
- Extract and analyze the transcript
- Detect the type of content (tutorial, news, review, educational, etc.)
- Generate appropriate summaries based on content type
- Detect if the content is AI-generated
- Search through saved transcripts
- Answer questions about video content

Your analysis adapts to the video type:
- **Tutorials**: Step-by-step guides with prerequisites and tips
- **News**: Key points, summaries, and implications
- **Reviews**: Pros/cons, features, and recommendations
- **Educational**: Concepts, examples, and learning points
- **Other content**: Action plans and key takeaways

IMPORTANT: When you use the youtube_transcript tool, include the tool output in your response as-is.

Be conversational and helpful. Use markdown formatting for clarity."""


class SimpleChatAgent:
    """Simplified agent focused on core functionality"""
    
    def __init__(
        self, 
        model_provider: str = "anthropic",
        model_name: Optional[str] = None,
        enable_transcript_store: bool = True
    ):
        """Initialize the simple chat agent"""
        self.model_provider = model_provider
        
        # Initialize LLM
        if model_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found")
            
            self.llm = ChatAnthropic(
                model=model_name or "claude-3-5-sonnet-20241022",
                anthropic_api_key=api_key,
                temperature=0.7,
                max_tokens=4000
            )
        elif model_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            
            self.llm = ChatOpenAI(
                model=model_name or "gpt-4-turbo-preview",
                openai_api_key=api_key,
                temperature=0.7,
                max_tokens=4000
            )
        else:
            raise ValueError(f"Unknown model provider: {model_provider}")
        
        # Initialize tools
        self.telly_tool = get_enhanced_telly_tool(self.llm)
        
        # Initialize transcript store if enabled
        self.transcript_store = None
        if enable_transcript_store:
            try:
                self.transcript_store = TranscriptStore(
                    storage_dir="./data/memory/transcripts"
                )
            except Exception as e:
                print(f"Warning: Could not initialize transcript store: {e}")
    
    def get_features_status(self) -> Dict[str, bool]:
        """Get status of available features"""
        return {
            "base_functional": True,
            "transcript_extraction": True,
            "transcript_store": self.transcript_store is not None,
            "memory": False,  # No complex memory system
            "workflows": False,  # No workflows
            "threads": False  # No threads
        }
    
    async def chat(
        self,
        message: str,
        history: List[Message] = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a chat message"""
        
        # Build messages for LLM
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        # Add history if provided
        if history:
            for msg in history:
                if msg.role == MessageRole.USER:
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == MessageRole.ASSISTANT:
                    messages.append(AIMessage(content=msg.content))
        
        # Add current message
        messages.append(HumanMessage(content=message))
        
        # Check if message contains YouTube URL
        youtube_url = None
        if "youtube.com/watch" in message or "youtu.be/" in message:
            # Extract URL
            import re
            url_match = re.search(
                r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
                message
            )
            if url_match:
                youtube_url = url_match.group(0)
        
        # If YouTube URL found, use tool first
        if youtube_url:
            try:
                # Extract transcript
                yield {"type": "tool_call", "content": {
                    "tool": "youtube_transcript",
                    "input": youtube_url,
                    "id": "call_1"
                }}
                
                tool_result = await self.telly_tool.arun(youtube_url)
                
                yield {"type": "tool_result", "content": {
                    "id": "call_1",
                    "output": tool_result
                }}
                
                # Save to transcript store if available
                if self.transcript_store:
                    try:
                        # First try to extract metadata with full transcript
                        metadata_match = re.search(r'<!-- METADATA_START\n(.*?)\nMETADATA_END -->', tool_result, re.DOTALL)
                        
                        if metadata_match:
                            # Extract full transcript from metadata
                            metadata_json = metadata_match.group(1)
                            metadata = json.loads(metadata_json)
                            
                            title = metadata.get('title', 'YouTube Video')
                            transcript = metadata.get('full_transcript', '')
                            video_id = metadata.get('video_id', '')
                            language = metadata.get('language', 'unknown')
                            
                            # Extract action plan from the visible content
                            action_plan = ""
                            lines = tool_result.split('\n')
                            in_action_plan = False
                            
                            for line in lines:
                                if any(marker in line for marker in ["### 🎓 Tutorial Guide", "### 📰 News Summary", 
                                                                     "### ⭐ Review Summary", "### 📚 Educational Notes", 
                                                                     "### 📋 Action Plan"]):
                                    in_action_plan = True
                                elif line.startswith("<!-- METADATA_START"):
                                    break
                                elif in_action_plan and line.strip():
                                    action_plan += line + "\n"
                        
                        else:
                            # Fallback to old parsing method
                            lines = tool_result.split('\n')
                            title = "YouTube Video"
                            transcript = ""
                            action_plan = ""
                            
                            in_transcript = False
                            in_action_plan = False
                            
                            for line in lines:
                                if "**Title:**" in line:
                                    title = line.replace("**Title:**", "").strip()
                                elif "### 📝" in line and "Transcript" in line:
                                    in_transcript = True
                                    in_action_plan = False
                                elif any(marker in line for marker in ["### 🎓", "### 📰", "### ⭐", "### 📚", "### 📋"]):
                                    in_transcript = False
                                    in_action_plan = True
                                elif in_transcript and line.strip() and not line.startswith("*Showing first"):
                                    # Skip metadata lines
                                    if not ("```" in line or "📊 **Full transcript:**" in line):
                                        transcript += line + "\n"
                                elif in_action_plan and line.strip():
                                    action_plan += line + "\n"
                        
                        # Save if we have content
                        if transcript:
                            self.transcript_store.save_transcript(
                                url=youtube_url,
                                title=title,
                                transcript=transcript.strip(),
                                action_plan=action_plan.strip(),
                                summary=f"Extracted from {youtube_url}"
                            )
                    except Exception as e:
                        print(f"Failed to save transcript: {e}")
                
                # The tool result already contains the complete analysis and action plan
                # Just return it directly
                yield {"type": "text", "content": tool_result}
                return
            
            except Exception as e:
                yield {"type": "error", "content": f"Error processing YouTube URL: {str(e)}"}
        
        # Generate response
        if stream:
            async for chunk in self.llm.astream(messages):
                yield {"type": "text", "content": chunk.content}
        else:
            response = await self.llm.ainvoke(messages)
            yield {"type": "text", "content": response.content}
    
    async def search_transcripts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search saved transcripts"""
        if not self.transcript_store:
            return []
        
        results = self.transcript_store.search_transcripts(query, limit)
        return [
            {
                "id": record.id,
                "title": record.title,
                "url": record.url,
                "summary": record.summary,
                "score": score
            }
            for record, score in results
        ]
    
    async def process_youtube_video(self, url: str) -> Dict[str, Any]:
        """Simple function to process a YouTube video"""
        try:
            # Extract transcript
            tool_result = await self.telly_tool.arun(url)
            
            # First try to extract metadata with full transcript
            metadata_match = re.search(r'<!-- METADATA_START\n(.*?)\nMETADATA_END -->', tool_result, re.DOTALL)
            
            if metadata_match:
                # Extract full transcript from metadata
                metadata_json = metadata_match.group(1)
                metadata = json.loads(metadata_json)
                
                title = metadata.get('title', 'YouTube Video')
                transcript = metadata.get('full_transcript', '')
                
                # Extract action plan from the visible content
                action_plan = ""
                lines = tool_result.split('\n')
                in_action_plan = False
                
                for line in lines:
                    if any(marker in line for marker in ["### 🎓 Tutorial Guide", "### 📰 News Summary", 
                                                         "### ⭐ Review Summary", "### 📚 Educational Notes", 
                                                         "### 📋 Action Plan"]):
                        in_action_plan = True
                    elif line.startswith("<!-- METADATA_START"):
                        break
                    elif in_action_plan and line.strip():
                        action_plan += line + "\n"
            
            else:
                # Fallback to old parsing method
                lines = tool_result.split('\n')
                title = "YouTube Video"
                transcript = ""
                action_plan = ""
                
                in_transcript = False
                in_action_plan = False
                
                for line in lines:
                    if "**Title:**" in line:
                        title = line.replace("**Title:**", "").strip()
                    elif "### 📝" in line and "Transcript" in line:
                        in_transcript = True
                        in_action_plan = False
                    elif any(marker in line for marker in ["### 🎓", "### 📰", "### ⭐", "### 📚", "### 📋"]):
                        in_transcript = False
                        in_action_plan = True
                    elif in_transcript and line.strip() and not line.startswith("*Showing first"):
                        # Skip metadata lines
                        if not ("```" in line or "📊 **Full transcript:**" in line):
                            transcript += line + "\n"
                    elif in_action_plan and line.strip():
                        action_plan += line + "\n"
            
            # Generate summary
            summary_prompt = f"Summarize this video in 2-3 sentences: {title}\n\n{transcript[:500]}..."
            messages = [
                SystemMessage(content="You are a helpful assistant that creates concise summaries."),
                HumanMessage(content=summary_prompt)
            ]
            summary_response = await self.llm.ainvoke(messages)
            summary = summary_response.content
            
            # Save to store
            saved_id = None
            if self.transcript_store and transcript:
                saved_id = self.transcript_store.save_transcript(
                    url=url,
                    title=title,
                    transcript=transcript.strip(),
                    action_plan=action_plan.strip(),
                    summary=summary
                )
            
            return {
                "success": True,
                "id": saved_id,
                "title": title,
                "summary": summary,
                "has_action_plan": bool(action_plan),
                "transcript_length": len(transcript)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        # Simple agent doesn't need cleanup
        pass