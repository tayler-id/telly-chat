"""Data models for the chat application"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Represents a tool call made by the assistant"""
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str


class ToolResult(BaseModel):
    """Result from a tool execution"""
    call_id: str
    output: Any
    error: Optional[str] = None


class Message(BaseModel):
    """Chat message model"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    message: Message
    session_id: str


class Session(BaseModel):
    """Chat session model"""
    id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class ToolDefinition(BaseModel):
    """Definition of an available tool"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    
    
class TellyToolInput(BaseModel):
    """Input for the Telly YouTube transcript tool"""
    url: str = Field(..., description="YouTube video URL to extract transcript from")
    generate_action_plan: bool = Field(
        default=True, 
        description="Whether to generate an action plan from the transcript"
    )