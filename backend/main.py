"""FastAPI backend for Telly Chat"""
import os
import uuid
from typing import Dict, Optional
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
from agents.chat_agent import ChatAgent
from services.session_manager import SessionManager

# Load environment variables
load_dotenv()

# Initialize session manager
session_manager = SessionManager()

# Global agent instance (in production, you'd want per-session agents)
chat_agent: Optional[ChatAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the app"""
    global chat_agent
    
    # Startup
    print("Starting Telly Chat backend...")
    
    # Initialize the chat agent
    model_provider = os.getenv("MODEL_PROVIDER", "anthropic")
    chat_agent = ChatAgent(model_provider=model_provider)
    
    yield
    
    # Shutdown
    print("Shutting down Telly Chat backend...")
    await session_manager.cleanup()


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
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


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
    
    async for chunk in chat_agent.chat(
        message=request.message,
        history=session.messages[:-1],  # Exclude the message we just added
        stream=False
    ):
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
        tool_results=tool_results if tool_results else None
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
        
        # Collect response content and metadata
        response_content = ""
        tool_calls = []
        tool_results = []
        message_id = str(uuid.uuid4())
        
        try:
            async for chunk in chat_agent.chat(
                message=message,
                history=session.messages[:-1],
                stream=True
            ):
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
                tool_results=tool_results if tool_results else None
            )
            
            await session_manager.add_message(session_id, assistant_message)
            
            # Send completion event
            yield {
                "event": "done",
                "data": json.dumps({
                    "message_id": message_id,
                    "content": response_content
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
            
            async for chunk in chat_agent.chat(
                message=message,
                history=session.messages[:-1],
                stream=True
            ):
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
                tool_results=tool_results if tool_results else None
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
    """Direct endpoint to get YouTube transcript - returns FULL transcript"""
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)