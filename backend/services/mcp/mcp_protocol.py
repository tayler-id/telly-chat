"""MCP Protocol implementation - JSON-RPC 2.0"""

import json
import uuid
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum


class MCPMethod(str, Enum):
    """MCP protocol methods"""
    # Initialization
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    
    # Tool discovery and execution
    GET_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    
    # Resource management
    GET_RESOURCES = "resources/list"
    GET_RESOURCE = "resources/get"
    SUBSCRIBE_RESOURCE = "resources/subscribe"
    UNSUBSCRIBE_RESOURCE = "resources/unsubscribe"
    
    # Sampling
    CREATE_SAMPLE = "sampling/createMessage"
    
    # Prompts
    GET_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    
    # Notifications
    RESOURCE_UPDATED = "notifications/resources/updated"
    TOOL_UPDATED = "notifications/tools/updated"
    PROGRESS = "notifications/progress"


@dataclass
class MCPMessage:
    """Base MCP message following JSON-RPC 2.0"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    
    def to_json(self) -> str:
        """Convert message to JSON"""
        data = asdict(self)
        # Remove None values
        return json.dumps({k: v for k, v in data.items() if v is not None})
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Create message from JSON"""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message"""
    method: str
    params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class MCPNotification(MCPMessage):
    """MCP notification message (no id)"""
    method: str
    params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        self.id = None  # Notifications don't have IDs


@dataclass
class MCPError:
    """MCP error object"""
    code: int
    message: str
    data: Optional[Any] = None


# Standard JSON-RPC error codes
class ErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    RESOURCE_NOT_FOUND = -32001
    TOOL_NOT_FOUND = -32002
    UNAUTHORIZED = -32003
    RATE_LIMITED = -32004


@dataclass
class Tool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_langchain_tool(self):
        """Convert to LangChain tool format"""
        from langchain.tools import BaseTool
        from pydantic import BaseModel, create_model
        
        # Create Pydantic model from input schema
        fields = {}
        for field_name, field_info in self.input_schema.get("properties", {}).items():
            field_type = str  # Default to string
            if field_info.get("type") == "integer":
                field_type = int
            elif field_info.get("type") == "boolean":
                field_type = bool
            elif field_info.get("type") == "number":
                field_type = float
            
            fields[field_name] = (field_type, field_info.get("description", ""))
        
        InputModel = create_model(f"{self.name}Input", **fields)
        
        # Create tool class
        class MCPToolAdapter(BaseTool):
            name: str = self.name
            description: str = self.description
            args_schema: type[BaseModel] = InputModel
            mcp_session: Any = None
            
            def _run(self, **kwargs) -> str:
                """Run the tool through MCP"""
                if not self.mcp_session:
                    return "Error: MCP session not connected"
                
                # Call tool through MCP
                result = self.mcp_session.call_tool(self.name, kwargs)
                return str(result)
            
            async def _arun(self, **kwargs) -> str:
                """Async run"""
                if not self.mcp_session:
                    return "Error: MCP session not connected"
                
                result = await self.mcp_session.call_tool_async(self.name, kwargs)
                return str(result)
        
        return MCPToolAdapter


@dataclass
class Resource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class Prompt:
    """MCP Prompt definition"""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPProtocol:
    """MCP Protocol handler"""
    
    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None) -> MCPRequest:
        """Create an MCP request"""
        return MCPRequest(method=method, params=params)
    
    @staticmethod
    def create_response(request_id: Union[str, int], result: Any) -> MCPResponse:
        """Create an MCP response"""
        return MCPResponse(id=request_id, result=result)
    
    @staticmethod
    def create_error_response(request_id: Union[str, int], code: int, message: str, data: Any = None) -> MCPResponse:
        """Create an MCP error response"""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return MCPResponse(id=request_id, error=error)
    
    @staticmethod
    def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> MCPNotification:
        """Create an MCP notification"""
        return MCPNotification(method=method, params=params)
    
    @staticmethod
    def parse_message(json_str: str) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """Parse a JSON-RPC message"""
        try:
            data = json.loads(json_str)
            
            if "method" in data and "id" in data:
                # It's a request
                return MCPRequest(**data)
            elif "method" in data and "id" not in data:
                # It's a notification
                return MCPNotification(**data)
            elif "result" in data or "error" in data:
                # It's a response
                return MCPResponse(**data)
            else:
                raise ValueError("Invalid MCP message format")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse MCP message: {e}")