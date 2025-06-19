"""MCP Transport implementations - stdio and WebSocket"""

import asyncio
import json
import sys
import subprocess
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol
import logging

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    """Abstract base class for MCP transports"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect the transport"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect the transport"""
        pass
    
    @abstractmethod
    async def send(self, message: str) -> None:
        """Send a message"""
        pass
    
    @abstractmethod
    async def receive(self) -> str:
        """Receive a message"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected"""
        pass


class StdioTransport(MCPTransport):
    """Standard I/O transport for local MCP servers"""
    
    def __init__(self, command: str, args: Optional[list] = None):
        """Initialize stdio transport
        
        Args:
            command: Command to execute (e.g., 'node', 'python')
            args: Arguments for the command (e.g., ['server.js'])
        """
        self.command = command
        self.args = args or []
        self.process: Optional[subprocess.Popen] = None
        self._read_buffer = b""
        
    async def connect(self) -> None:
        """Start the subprocess"""
        try:
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # Use binary mode
            )
            logger.info(f"Started MCP server: {self.command} {' '.join(self.args)}")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Stop the subprocess"""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process()),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.process.kill()
            self.process = None
    
    async def _wait_for_process(self):
        """Wait for process to terminate"""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def send(self, message: str) -> None:
        """Send a message via stdin"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Transport not connected")
        
        # MCP uses line-delimited JSON
        data = message.encode('utf-8') + b'\n'
        self.process.stdin.write(data)
        self.process.stdin.flush()
        logger.debug(f"Sent message: {message}")
    
    async def receive(self) -> str:
        """Receive a message from stdout"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Transport not connected")
        
        # Read until we have a complete line
        while b'\n' not in self._read_buffer:
            chunk = await asyncio.create_task(
                asyncio.to_thread(self.process.stdout.read, 1024)
            )
            if not chunk:
                raise EOFError("Process terminated")
            self._read_buffer += chunk
        
        # Extract the line
        line, self._read_buffer = self._read_buffer.split(b'\n', 1)
        message = line.decode('utf-8').strip()
        logger.debug(f"Received message: {message}")
        return message
    
    def is_connected(self) -> bool:
        """Check if process is running"""
        return self.process is not None and self.process.poll() is None


class WebSocketTransport(MCPTransport):
    """WebSocket transport for remote MCP servers"""
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize WebSocket transport
        
        Args:
            url: WebSocket URL (e.g., 'ws://localhost:8080/mcp')
            headers: Optional headers for authentication
        """
        self.url = url
        self.headers = headers or {}
        self.websocket: Optional[WebSocketClientProtocol] = None
        
    async def connect(self) -> None:
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=self.headers
            )
            logger.info(f"Connected to MCP server at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def send(self, message: str) -> None:
        """Send a message via WebSocket"""
        if not self.websocket:
            raise RuntimeError("Transport not connected")
        
        await self.websocket.send(message)
        logger.debug(f"Sent message: {message}")
    
    async def receive(self) -> str:
        """Receive a message from WebSocket"""
        if not self.websocket:
            raise RuntimeError("Transport not connected")
        
        message = await self.websocket.recv()
        logger.debug(f"Received message: {message}")
        return message
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket is not None and not self.websocket.closed


class SSETransport(MCPTransport):
    """Server-Sent Events transport for HTTP-based MCP servers"""
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """Initialize SSE transport
        
        Args:
            url: SSE endpoint URL
            headers: Optional headers for authentication
        """
        self.url = url
        self.headers = headers or {}
        self._connected = False
        # SSE is typically one-way, so we'd need a separate endpoint for sending
        # This is a simplified implementation
        
    async def connect(self) -> None:
        """Connect to SSE endpoint"""
        # In a real implementation, you'd establish an SSE connection here
        self._connected = True
        logger.info(f"Connected to SSE endpoint at {self.url}")
    
    async def disconnect(self) -> None:
        """Disconnect from SSE"""
        self._connected = False
    
    async def send(self, message: str) -> None:
        """Send a message (would require separate HTTP endpoint)"""
        # In practice, SSE is receive-only, so you'd POST to a different endpoint
        raise NotImplementedError("SSE transport sending not implemented")
    
    async def receive(self) -> str:
        """Receive SSE events"""
        # Simplified - in practice you'd parse SSE format
        raise NotImplementedError("SSE transport receiving not implemented")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected


def create_transport(url: str, headers: Optional[Dict[str, str]] = None) -> MCPTransport:
    """Factory function to create appropriate transport based on URL
    
    Args:
        url: Connection URL (stdio://, ws://, wss://, http://, https://)
        headers: Optional headers for authentication
        
    Returns:
        Appropriate MCPTransport instance
    """
    if url.startswith("stdio://"):
        # Parse stdio URL: stdio://command/arg1/arg2
        parts = url[8:].split("/")
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return StdioTransport(command, args)
    
    elif url.startswith(("ws://", "wss://")):
        return WebSocketTransport(url, headers)
    
    elif url.startswith(("http://", "https://")):
        # Could be SSE or regular HTTP
        if "/sse" in url or "stream" in url:
            return SSETransport(url, headers)
        else:
            raise ValueError("HTTP transport requires SSE endpoint")
    
    else:
        raise ValueError(f"Unknown transport type for URL: {url}")