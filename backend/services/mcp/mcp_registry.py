"""MCP Registry for managing server configurations"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    url: str
    description: Optional[str] = None
    enabled: bool = True
    headers: Optional[Dict[str, str]] = None
    environment: Optional[Dict[str, str]] = None
    capabilities: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """Create from dictionary"""
        return cls(**data)


class MCPRegistry:
    """Registry for managing MCP server configurations"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize registry
        
        Args:
            config_path: Path to configuration file (defaults to .env or mcp_servers.json)
        """
        self.config_path = config_path or self._get_default_config_path()
        self.servers: Dict[str, MCPServerConfig] = {}
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        # Check for mcp_servers.json in current directory
        if os.path.exists("mcp_servers.json"):
            return "mcp_servers.json"
        
        # Check for .mcp/servers.json in home directory
        home_config = Path.home() / ".mcp" / "servers.json"
        if home_config.exists():
            return str(home_config)
        
        # Default to local mcp_servers.json
        return "mcp_servers.json"
    
    def _load_config(self) -> None:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            # Create default configuration
            self._create_default_config()
            return
        
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            # Load servers
            for server_data in data.get("servers", []):
                server = MCPServerConfig.from_dict(server_data)
                self.servers[server.name] = server
                
        except Exception as e:
            print(f"Error loading MCP configuration: {e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """Create default configuration"""
        # Add example servers
        self.servers = {
            "filesystem": MCPServerConfig(
                name="filesystem",
                url="stdio://npx/@modelcontextprotocol/server-filesystem",
                description="Access local filesystem",
                capabilities=["read", "write", "list"]
            ),
            "github": MCPServerConfig(
                name="github",
                url="stdio://npx/@modelcontextprotocol/server-github",
                description="Access GitHub repositories",
                environment={"GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")},
                capabilities=["repos", "issues", "pulls"]
            ),
            "slack": MCPServerConfig(
                name="slack",
                url="stdio://npx/@modelcontextprotocol/server-slack",
                description="Access Slack workspace",
                environment={"SLACK_TOKEN": os.getenv("SLACK_TOKEN", "")},
                capabilities=["messages", "channels", "users"],
                enabled=False  # Disabled by default
            ),
            "google-drive": MCPServerConfig(
                name="google-drive",
                url="stdio://npx/@modelcontextprotocol/server-gdrive",
                description="Access Google Drive files",
                environment={
                    "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET", "")
                },
                capabilities=["files", "folders", "search"],
                enabled=False
            )
        }
        
        # Save default configuration
        self.save_config()
    
    def save_config(self) -> None:
        """Save configuration to file"""
        # Ensure directory exists
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Save configuration
        data = {
            "servers": [server.to_dict() for server in self.servers.values()]
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_server(self, config: MCPServerConfig) -> None:
        """Add or update a server configuration"""
        self.servers[config.name] = config
        self.save_config()
    
    def remove_server(self, name: str) -> bool:
        """Remove a server configuration"""
        if name in self.servers:
            del self.servers[name]
            self.save_config()
            return True
        return False
    
    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get a server configuration"""
        return self.servers.get(name)
    
    def list_servers(self, enabled_only: bool = False) -> List[MCPServerConfig]:
        """List all server configurations"""
        servers = list(self.servers.values())
        if enabled_only:
            servers = [s for s in servers if s.enabled]
        return servers
    
    def enable_server(self, name: str) -> bool:
        """Enable a server"""
        if name in self.servers:
            self.servers[name].enabled = True
            self.save_config()
            return True
        return False
    
    def disable_server(self, name: str) -> bool:
        """Disable a server"""
        if name in self.servers:
            self.servers[name].enabled = False
            self.save_config()
            return True
        return False
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled servers"""
        return {name: config for name, config in self.servers.items() if config.enabled}
    
    def update_server_environment(self, name: str, env: Dict[str, str]) -> bool:
        """Update server environment variables"""
        if name in self.servers:
            if self.servers[name].environment is None:
                self.servers[name].environment = {}
            self.servers[name].environment.update(env)
            self.save_config()
            return True
        return False


# Global registry instance
_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance"""
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry


def configure_mcp_server(name: str, url: str, **kwargs) -> None:
    """Configure an MCP server (convenience function)"""
    registry = get_mcp_registry()
    config = MCPServerConfig(name=name, url=url, **kwargs)
    registry.add_server(config)