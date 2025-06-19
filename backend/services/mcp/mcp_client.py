"""MCP Client implementation"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from asyncio import Queue
import uuid

from .mcp_protocol import (
    MCPMethod, MCPRequest, MCPResponse, MCPNotification,
    MCPProtocol, Tool, Resource, Prompt, ErrorCode
)
from .mcp_transport import MCPTransport, create_transport

logger = logging.getLogger(__name__)


class MCPSession:
    """MCP client session - represents a connection to an MCP server"""
    
    def __init__(self, transport: MCPTransport):
        """Initialize MCP session
        
        Args:
            transport: Transport instance to use
        """
        self.transport = transport
        self.protocol = MCPProtocol()
        
        # Response handling
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._notification_handlers: Dict[str, List[Callable]] = {}
        
        # Cached server capabilities
        self._tools: Optional[List[Tool]] = None
        self._resources: Optional[List[Resource]] = None
        self._prompts: Optional[List[Prompt]] = None
        
        # Background task for receiving messages
        self._receive_task: Optional[asyncio.Task] = None
        
    async def connect(self) -> None:
        """Connect to MCP server and initialize"""
        await self.transport.connect()
        
        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        # Send initialize request
        init_request = self.protocol.create_request(
            MCPMethod.INITIALIZE,
            {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "sampling": {}
                }
            }
        )
        
        response = await self._send_request(init_request)
        if response.error:
            raise Exception(f"Failed to initialize: {response.error}")
        
        logger.info("MCP session initialized successfully")
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server"""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        await self.transport.disconnect()
        logger.info("MCP session disconnected")
    
    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        """Send a request and wait for response"""
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request.id] = future
        
        # Send request
        await self.transport.send(request.to_json())
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            del self._pending_requests[request.id]
            raise TimeoutError(f"Request {request.id} timed out")
    
    async def _receive_loop(self):
        """Background task to receive messages"""
        while self.transport.is_connected():
            try:
                message_str = await self.transport.receive()
                message = self.protocol.parse_message(message_str)
                
                if isinstance(message, MCPResponse):
                    # Handle response
                    request_id = message.id
                    if request_id in self._pending_requests:
                        self._pending_requests[request_id].set_result(message)
                        del self._pending_requests[request_id]
                    else:
                        logger.warning(f"Received response for unknown request: {request_id}")
                
                elif isinstance(message, MCPNotification):
                    # Handle notification
                    await self._handle_notification(message)
                
                elif isinstance(message, MCPRequest):
                    # Server-initiated requests (rare)
                    logger.warning(f"Received unexpected request from server: {message.method}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                # Continue loop unless transport is disconnected
                if not self.transport.is_connected():
                    break
    
    async def _handle_notification(self, notification: MCPNotification):
        """Handle incoming notification"""
        handlers = self._notification_handlers.get(notification.method, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification.params)
                else:
                    handler(notification.params)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
    
    def on_notification(self, method: str, handler: Callable):
        """Register a notification handler"""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)
    
    # Tool methods
    
    async def get_tools(self) -> List[Tool]:
        """Get available tools from server"""
        request = self.protocol.create_request(MCPMethod.GET_TOOLS)
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to get tools: {response.error}")
        
        self._tools = [
            Tool(**tool_data) for tool_data in response.result.get("tools", [])
        ]
        return self._tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server"""
        request = self.protocol.create_request(
            MCPMethod.CALL_TOOL,
            {"name": name, "arguments": arguments}
        )
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Tool call failed: {response.error}")
        
        return response.result.get("result")
    
    # Resource methods
    
    async def get_resources(self) -> List[Resource]:
        """Get available resources from server"""
        request = self.protocol.create_request(MCPMethod.GET_RESOURCES)
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to get resources: {response.error}")
        
        self._resources = [
            Resource(**res_data) for res_data in response.result.get("resources", [])
        ]
        return self._resources
    
    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a specific resource"""
        request = self.protocol.create_request(
            MCPMethod.GET_RESOURCE,
            {"uri": uri}
        )
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to get resource: {response.error}")
        
        return response.result
    
    # Prompt methods
    
    async def get_prompts(self) -> List[Prompt]:
        """Get available prompts from server"""
        request = self.protocol.create_request(MCPMethod.GET_PROMPTS)
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to get prompts: {response.error}")
        
        self._prompts = [
            Prompt(**prompt_data) for prompt_data in response.result.get("prompts", [])
        ]
        return self._prompts
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a specific prompt"""
        request = self.protocol.create_request(
            MCPMethod.GET_PROMPT,
            {"name": name, "arguments": arguments or {}}
        )
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to get prompt: {response.error}")
        
        return response.result.get("prompt", "")
    
    # Sampling methods
    
    async def create_sample(self, messages: List[Dict[str, Any]], max_tokens: int = 1000) -> Dict[str, Any]:
        """Request the server to create a sample/completion"""
        request = self.protocol.create_request(
            MCPMethod.CREATE_SAMPLE,
            {
                "messages": messages,
                "maxTokens": max_tokens
            }
        )
        response = await self._send_request(request)
        
        if response.error:
            raise Exception(f"Failed to create sample: {response.error}")
        
        return response.result


class MCPClient:
    """High-level MCP client for managing connections"""
    
    def __init__(self):
        """Initialize MCP client"""
        self.sessions: Dict[str, MCPSession] = {}
        
    async def connect_to_mcp(self, 
                           url: str,
                           name: Optional[str] = None,
                           headers: Optional[Dict[str, str]] = None) -> MCPSession:
        """Connect to an MCP server
        
        Args:
            url: Server URL (stdio://, ws://, etc.)
            name: Optional name for the session
            headers: Optional headers for authentication
            
        Returns:
            MCPSession instance
        """
        # Create transport
        transport = create_transport(url, headers)
        
        # Create session
        session = MCPSession(transport)
        await session.connect()
        
        # Store session
        session_name = name or url
        self.sessions[session_name] = session
        
        return session
    
    async def disconnect(self, name: str) -> None:
        """Disconnect a session"""
        if name in self.sessions:
            await self.sessions[name].disconnect()
            del self.sessions[name]
    
    async def disconnect_all(self) -> None:
        """Disconnect all sessions"""
        for session in list(self.sessions.values()):
            await session.disconnect()
        self.sessions.clear()
    
    def get_session(self, name: str) -> Optional[MCPSession]:
        """Get a session by name"""
        return self.sessions.get(name)
    
    async def discover_tools(self) -> Dict[str, List[Tool]]:
        """Discover all tools across all sessions"""
        tools_by_session = {}
        for name, session in self.sessions.items():
            tools_by_session[name] = await session.get_tools()
        return tools_by_session
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], session_name: Optional[str] = None) -> Any:
        """Call a tool, optionally specifying which session
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            session_name: Optional session name (searches all if not specified)
            
        Returns:
            Tool result
        """
        if session_name:
            session = self.sessions.get(session_name)
            if not session:
                raise ValueError(f"Session {session_name} not found")
            return await session.call_tool(tool_name, arguments)
        
        # Search all sessions for the tool
        for session in self.sessions.values():
            tools = await session.get_tools()
            if any(tool.name == tool_name for tool in tools):
                return await session.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool {tool_name} not found in any session")


# Convenience function
async def connect_to_mcp(url: str, headers: Optional[Dict[str, str]] = None) -> MCPSession:
    """Connect to an MCP server (convenience function)
    
    Args:
        url: Server URL
        headers: Optional headers
        
    Returns:
        MCPSession instance
    """
    client = MCPClient()
    return await client.connect_to_mcp(url, headers=headers)