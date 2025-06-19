"""FastAPI backend for Telly Chat"""
import os
import uuid
from typing import Dict, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schemas import (
    ChatRequest, ChatResponse, Message, MessageRole, 
    Session, ToolCall, ToolResult
)
from services.session_manager import SessionManager
from services.transcript_service import (
    save_transcript, get_transcript, search_transcripts,
    get_recent_transcripts, get_transcript_by_url,
    get_related_transcripts, get_transcript_stats
)

# Load environment variables
load_dotenv()

# Initialize session manager
session_manager = SessionManager()

# Global agent instance (in production, you'd want per-session agents)
chat_agent: Optional[Any] = None
memory_enabled = False

# Try to import enhanced agent
try:
    from agents.enhanced_chat_agent import EnhancedChatAgent
    from config import get_agent_config, MEMORY_CONFIG
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
    from agents.chat_agent import ChatAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the app"""
    global chat_agent
    
    # Startup
    print("Starting Telly Chat backend...")
    
    # Initialize the chat agent
    model_provider = os.getenv("MODEL_PROVIDER", "anthropic")
    
    if ENHANCED_AVAILABLE:
        # Use enhanced agent with optional features
        config = get_agent_config()
        chat_agent = EnhancedChatAgent(
            model_provider=model_provider,
            **config
        )
        print(f"Enhanced agent initialized with features: {chat_agent.get_features_status()}")
    else:
        # Fallback to basic agent
        chat_agent = ChatAgent(model_provider=model_provider)
        print("Basic agent initialized (install optional dependencies for advanced features)")
    
    yield
    
    # Shutdown
    print("Shutting down Telly Chat backend...")
    await session_manager.cleanup()
    
    if ENHANCED_AVAILABLE and hasattr(chat_agent, 'cleanup'):
        await chat_agent.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Telly Chat API",
    description="Chat interface with YouTube transcript extraction capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Telly Chat API",
        "version": "1.0.0",
        "status": "running",
        "features": chat_agent.get_features_status() if hasattr(chat_agent, 'get_features_status') else {"base_functional": True}
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/features")
async def get_features():
    """Get available features and their status"""
    if hasattr(chat_agent, 'get_features_status'):
        features = chat_agent.get_features_status()
    else:
        features = {
            "memory": False,
            "workflows": False,
            "threads": False,
            "base_functional": True
        }
    
    return {
        "available": ENHANCED_AVAILABLE,
        "features": features,
        "memory_config": MEMORY_CONFIG if ENHANCED_AVAILABLE else None
    }


@app.post("/features/memory/toggle")
async def toggle_memory(enable: bool):
    """Toggle memory on/off at runtime"""
    global chat_agent, memory_enabled
    
    if not ENHANCED_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Enhanced features not available. Install optional dependencies."
        )
    
    # Check if agent has memory capability
    if not hasattr(chat_agent, 'memory_enabled'):
        raise HTTPException(
            status_code=501,
            detail="Current agent does not support memory features."
        )
    
    # Toggle memory
    chat_agent.memory_enabled = enable
    memory_enabled = enable
    
    # Re-initialize memory components if enabling
    if enable and not chat_agent.short_term_memory:
        chat_agent._init_memory(MEMORY_CONFIG)
    
    return {
        "memory_enabled": chat_agent.memory_enabled,
        "message": f"Memory {'enabled' if enable else 'disabled'} successfully"
    }


@app.get("/memory/stats")
async def get_memory_stats():
    """Get memory statistics"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'memory_enabled'):
        raise HTTPException(
            status_code=501,
            detail="Memory features not available"
        )
    
    if not chat_agent.memory_enabled:
        return {
            "enabled": False,
            "message": "Memory is currently disabled"
        }
    
    try:
        stats = await chat_agent.export_memory()
        return {
            "enabled": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "enabled": True,
            "error": str(e)
        }


@app.post("/memory/clear")
async def clear_memory():
    """Clear all memories"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'memory_enabled'):
        raise HTTPException(
            status_code=501,
            detail="Memory features not available"
        )
    
    if not chat_agent.memory_enabled:
        raise HTTPException(
            status_code=400,
            detail="Memory is currently disabled"
        )
    
    # Clear memories
    if chat_agent.short_term_memory:
        chat_agent.short_term_memory.clear()
    
    return {
        "message": "Memory cleared successfully"
    }


# Transcript Management Endpoints

@app.post("/transcripts/save")
async def save_transcript_endpoint(
    url: str,
    title: str,
    transcript: str,
    action_plan: str,
    summary: Optional[str] = None,
    duration: Optional[str] = None
):
    """Save a YouTube transcript"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    result = await save_transcript(
        chat_agent,
        url=url,
        title=title,
        transcript=transcript,
        action_plan=action_plan,
        summary=summary,
        duration=duration
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.get("/transcripts/{transcript_id}")
async def get_transcript_endpoint(transcript_id: str):
    """Get a specific transcript"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    result = await get_transcript(chat_agent, transcript_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@app.get("/transcripts/search")
async def search_transcripts_endpoint(query: str, limit: int = 5):
    """Search transcripts semantically"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    result = await search_transcripts(chat_agent, query, limit)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.get("/transcripts/recent")
async def get_recent_transcripts_endpoint(limit: int = 10):
    """Get recent transcripts"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    return await get_recent_transcripts(chat_agent, limit)


@app.get("/transcripts/by-url")
async def get_transcript_by_url_endpoint(url: str):
    """Get transcript by YouTube URL"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    result = await get_transcript_by_url(chat_agent, url)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@app.get("/transcripts/{transcript_id}/related")
async def get_related_transcripts_endpoint(transcript_id: str, limit: int = 3):
    """Get transcripts related to a given one"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    result = await get_related_transcripts(chat_agent, transcript_id, limit)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.get("/transcripts/stats")
async def get_transcript_stats_endpoint():
    """Get transcript store statistics"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'transcript_store'):
        raise HTTPException(
            status_code=501,
            detail="Transcript store not available"
        )
    
    return await get_transcript_stats(chat_agent)


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint"""
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = await session_manager.get_or_create_session(session_id)
    
    # Create user message
    user_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.USER,
        content=request.message
    )
    
    # Add to session
    await session_manager.add_message(session_id, user_message)
    
    # Get response from agent
    response_content = ""
    tool_calls = []
    tool_results = []
    
    # Check if we should use memory
    use_memory = memory_enabled if ENHANCED_AVAILABLE else False
    
    # Use enhanced chat if available
    if hasattr(chat_agent, 'chat') and hasattr(chat_agent, 'memory_enabled'):
        kwargs = {
            "message": request.message,
            "history": session.messages[:-1],
            "stream": False,
            "use_memory": use_memory
        }
    else:
        kwargs = {
            "message": request.message,
            "history": session.messages[:-1],
            "stream": False
        }
    
    async for chunk in chat_agent.chat(**kwargs):
        if chunk["type"] == "text":
            response_content += chunk["content"]
        elif chunk["type"] == "tool_call":
            tool_calls.append(ToolCall(
                tool_name=chunk["content"]["tool"],
                parameters=chunk["content"]["input"],
                call_id=chunk["content"]["id"]
            ))
        elif chunk["type"] == "tool_result":
            tool_results.append(ToolResult(
                call_id=chunk["content"]["id"],
                output=chunk["content"]["output"]
            ))
    
    # Create assistant message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.ASSISTANT,
        content=response_content,
        tool_calls=tool_calls if tool_calls else None,
        tool_results=tool_results if tool_results else None,
        metadata={"memory_used": use_memory} if ENHANCED_AVAILABLE else None
    )
    
    # Add to session
    await session_manager.add_message(session_id, assistant_message)
    
    return ChatResponse(
        message=assistant_message,
        session_id=session_id
    )


@app.get("/chat/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    """Streaming chat endpoint using Server-Sent Events"""
    # Get or create session
    session_id = session_id or str(uuid.uuid4())
    session = await session_manager.get_or_create_session(session_id)
    
    # Create user message
    user_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.USER,
        content=message
    )
    
    # Add to session
    await session_manager.add_message(session_id, user_message)
    
    async def generate():
        """Generate SSE events"""
        # Send session ID first
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session_id})
        }
        
        # Send memory status if enhanced
        if ENHANCED_AVAILABLE and hasattr(chat_agent, 'memory_enabled'):
            yield {
                "event": "features",
                "data": json.dumps({
                    "memory_enabled": chat_agent.memory_enabled,
                    "features": chat_agent.get_features_status()
                })
            }
        
        # Collect response content and metadata
        response_content = ""
        tool_calls = []
        tool_results = []
        message_id = str(uuid.uuid4())
        
        # Check if we should use memory
        use_memory = memory_enabled if ENHANCED_AVAILABLE else False
        
        try:
            # Use enhanced chat if available
            if hasattr(chat_agent, 'chat') and hasattr(chat_agent, 'memory_enabled'):
                kwargs = {
                    "message": message,
                    "history": session.messages[:-1],
                    "stream": True,
                    "use_memory": use_memory,
                    "session_id": session_id
                }
            else:
                kwargs = {
                    "message": message,
                    "history": session.messages[:-1],
                    "stream": True
                }
            
            async for chunk in chat_agent.chat(**kwargs):
                if chunk["type"] == "text":
                    response_content += chunk["content"]
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "text",
                            "content": chunk["content"]
                        })
                    }
                elif chunk["type"] == "tool_call":
                    tool_calls.append(ToolCall(
                        tool_name=chunk["content"]["tool"],
                        parameters=chunk["content"]["input"],
                        call_id=chunk["content"]["id"]
                    ))
                    yield {
                        "event": "tool_call",
                        "data": json.dumps(chunk["content"])
                    }
                elif chunk["type"] == "tool_result":
                    tool_results.append(ToolResult(
                        call_id=chunk["content"]["id"],
                        output=chunk["content"]["output"]
                    ))
                    yield {
                        "event": "tool_result",
                        "data": json.dumps({
                            "id": chunk["content"]["id"],
                            "output": str(chunk["content"]["output"])[:1000]  # Truncate for SSE
                        })
                    }
                elif chunk["type"] == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": chunk["content"]})
                    }
            
            # Create and save complete assistant message
            assistant_message = Message(
                id=message_id,
                role=MessageRole.ASSISTANT,
                content=response_content,
                tool_calls=tool_calls if tool_calls else None,
                tool_results=tool_results if tool_results else None,
                metadata={"memory_used": use_memory} if ENHANCED_AVAILABLE else None
            )
            
            await session_manager.add_message(session_id, assistant_message)
            
            # Send completion event
            yield {
                "event": "done",
                "data": json.dumps({
                    "message_id": message_id,
                    "content": response_content,
                    "memory_used": use_memory if ENHANCED_AVAILABLE else False
                })
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(generate())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            # Extract message and session
            message = data.get("message", "")
            session_id = data.get("session_id") or session_id or str(uuid.uuid4())
            
            # Get or create session
            session = await session_manager.get_or_create_session(session_id)
            
            # Send session ID if new
            if not data.get("session_id"):
                await websocket.send_json({
                    "type": "session",
                    "session_id": session_id
                })
            
            # Send feature status
            if ENHANCED_AVAILABLE and hasattr(chat_agent, 'memory_enabled'):
                await websocket.send_json({
                    "type": "features",
                    "memory_enabled": chat_agent.memory_enabled,
                    "features": chat_agent.get_features_status()
                })
            
            # Create user message
            user_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.USER,
                content=message
            )
            
            # Add to session
            await session_manager.add_message(session_id, user_message)
            
            # Send user message confirmation
            await websocket.send_json({
                "type": "user_message",
                "message": user_message.model_dump(mode="json")
            })
            
            # Generate response
            response_content = ""
            message_id = str(uuid.uuid4())
            tool_calls = []
            tool_results = []
            
            # Check if we should use memory
            use_memory = memory_enabled if ENHANCED_AVAILABLE else False
            
            # Use enhanced chat if available
            if hasattr(chat_agent, 'chat') and hasattr(chat_agent, 'memory_enabled'):
                kwargs = {
                    "message": message,
                    "history": session.messages[:-1],
                    "stream": True,
                    "use_memory": use_memory,
                    "session_id": session_id
                }
            else:
                kwargs = {
                    "message": message,
                    "history": session.messages[:-1],
                    "stream": True
                }
            
            async for chunk in chat_agent.chat(**kwargs):
                if chunk["type"] == "text":
                    response_content += chunk["content"]
                    await websocket.send_json({
                        "type": "stream",
                        "content": chunk["content"]
                    })
                elif chunk["type"] == "tool_call":
                    tool_calls.append(ToolCall(
                        tool_name=chunk["content"]["tool"],
                        parameters=chunk["content"]["input"],
                        call_id=chunk["content"]["id"]
                    ))
                    await websocket.send_json({
                        "type": "tool_call",
                        **chunk["content"]
                    })
                elif chunk["type"] == "tool_result":
                    tool_results.append(ToolResult(
                        call_id=chunk["content"]["id"],
                        output=chunk["content"]["output"]
                    ))
                    await websocket.send_json({
                        "type": "tool_result",
                        "id": chunk["content"]["id"],
                        "output": str(chunk["content"]["output"])[:1000]
                    })
                elif chunk["type"] == "error":
                    await websocket.send_json({
                        "type": "error",
                        "error": chunk["content"]
                    })
            
            # Create complete assistant message
            assistant_message = Message(
                id=message_id,
                role=MessageRole.ASSISTANT,
                content=response_content,
                tool_calls=tool_calls if tool_calls else None,
                tool_results=tool_results if tool_results else None,
                metadata={"memory_used": use_memory} if ENHANCED_AVAILABLE else None
            )
            
            # Save to session
            await session_manager.add_message(session_id, assistant_message)
            
            # Send completion
            await websocket.send_json({
                "type": "complete",
                "message": assistant_message.model_dump(mode="json")
            })
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions")
async def list_sessions():
    """List all sessions"""
    sessions = await session_manager.list_sessions()
    return {"sessions": sessions}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = await session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@app.post("/youtube/transcript")
async def get_youtube_transcript(url: str):
    """Direct endpoint to get YouTube transcript"""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../telly'))
    from telly_agent import TellyAgent
    
    try:
        # Use TellyAgent directly to get full transcript
        agent = TellyAgent()
        result = agent.process_video(url, generate_plan=True)
        
        if not result['success']:
            return {
                "success": False,
                "error": result.get('error', 'Unknown error')
            }
        
        # Format the full response without truncation
        response_parts = []
        
        # Add video info
        response_parts.append(f"### 📹 Video Information")
        response_parts.append(f"- **Video ID:** `{result['video_id']}`")
        response_parts.append(f"- **Language:** {result['language']}")
        response_parts.append("")
        
        # Add FULL transcript without truncation
        response_parts.append("### 📝 Full Transcript")
        response_parts.append("")
        response_parts.append("```")
        response_parts.append(result['transcript'].strip())
        response_parts.append("```")
        response_parts.append("")
        
        # Add action plan if generated
        if 'action_plan' in result and result['action_plan']['success']:
            response_parts.append("### 📋 Action Plan")
            response_parts.append("")
            response_parts.append(result['action_plan']['content'])
        
        return {
            "success": True,
            "content": "\n".join(response_parts)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Episodic Memory Endpoints

@app.get("/episodes/active")
async def get_active_episodes():
    """Get currently active episodes"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    episodes = chat_agent.episodic_memory.get_active_episodes()
    return {
        "active_episodes": [ep.to_dict() for ep in episodes],
        "current_episode_id": chat_agent.current_episode_id
    }


@app.get("/episodes/{episode_id}")
async def get_episode(episode_id: str):
    """Get a specific episode"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    episode = chat_agent.episodic_memory.get_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    return episode.to_dict()


@app.get("/episodes/session/{session_id}")
async def get_session_episodes(session_id: str):
    """Get all episodes from a session"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    episodes = chat_agent.episodic_memory.get_session_episodes(session_id)
    return {
        "session_id": session_id,
        "episodes": [ep.to_dict() for ep in episodes],
        "total": len(episodes)
    }


@app.get("/episodes/search")
async def search_episodes(query: str, limit: int = 10):
    """Search episodes by content"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    episodes = chat_agent.episodic_memory.search_episodes_by_content(query, limit)
    return {
        "query": query,
        "results": [ep.to_dict() for ep in episodes],
        "count": len(episodes)
    }


@app.post("/episodes/{episode_id}/end")
async def end_episode(episode_id: str, outcome: str = "completed"):
    """End an active episode"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    success = chat_agent.episodic_memory.end_episode(episode_id, outcome=outcome)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to end episode")
    
    return {"message": f"Episode {episode_id} ended with outcome: {outcome}"}


@app.get("/episodes/insights")
async def get_learning_insights():
    """Get learning insights from episodes"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    insights = chat_agent.episodic_memory.get_learning_insights()
    return insights


@app.get("/episodes/export/{session_id}")
async def export_session_for_training(session_id: str):
    """Export session data for training"""
    if not ENHANCED_AVAILABLE or not hasattr(chat_agent, 'episodic_memory'):
        raise HTTPException(
            status_code=501,
            detail="Episodic memory not available"
        )
    
    data = chat_agent.episodic_memory.export_session_for_training(session_id)
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)