# MCP (Model Context Protocol) Guide

## Overview

Telly Chat now supports MCP, allowing you to connect to external MCP servers that provide additional tools and context to the AI assistant.

## What is MCP?

MCP (Model Context Protocol) is a standardized way for AI models to interact with external tools and data sources. It uses JSON-RPC 2.0 for communication and supports various transport methods (stdio, WebSocket, HTTP).

## Available MCP Servers

The `mcp_servers.json` file contains pre-configured servers (all disabled by default):

1. **filesystem** - Access local files and directories
2. **github** - Interact with GitHub repositories, issues, and PRs
3. **web-search** - Search the web for current information
4. **memory** - Persistent memory across sessions
5. **postgres** - Connect to PostgreSQL databases

## Configuration

### 1. Edit mcp_servers.json

```json
{
  "servers": [
    {
      "name": "filesystem",
      "url": "stdio://npx/@modelcontextprotocol/server-filesystem",
      "description": "Access local filesystem",
      "enabled": true,  // Set to true to enable
      "environment": {
        "ALLOWED_DIRECTORIES": "/path/to/allowed/dirs"
      }
    }
  ]
}
```

### 2. Add Required Environment Variables

For servers that need authentication:

```bash
# GitHub
export GITHUB_TOKEN="your-github-token"

# Database
export DATABASE_URL="postgresql://user:pass@host:port/db"
```

## Using MCP in Telly Chat

### Auto-Connect on Startup

Enabled servers will automatically connect when the agent initializes.

### Manual Connection via API

```bash
# List available servers
curl http://localhost:8000/mcp/servers

# Connect to a server
curl -X POST http://localhost:8000/mcp/servers/filesystem/connect

# List available tools
curl http://localhost:8000/mcp/tools

# Disconnect
curl -X POST http://localhost:8000/mcp/servers/filesystem/disconnect
```

### Using MCP Tools in Chat

Once connected, MCP tools are automatically available to the AI. Just ask naturally:

- "Read the README.md file"
- "Search GitHub for issues about memory leaks"
- "Search the web for latest news about AI"

## Creating Custom MCP Servers

### Stdio Server Example

```javascript
// server.js
import { Server } from '@modelcontextprotocol/sdk';

const server = new Server({
  name: 'my-server',
  version: '1.0.0'
});

server.setRequestHandler('tools/list', async () => ({
  tools: [{
    name: 'my_tool',
    description: 'Does something useful',
    inputSchema: {
      type: 'object',
      properties: {
        input: { type: 'string' }
      }
    }
  }]
}));

server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;
  
  if (name === 'my_tool') {
    return {
      result: `Processed: ${args.input}`
    };
  }
});

server.connect(process.stdin, process.stdout);
```

### Configuration

```json
{
  "name": "my-server",
  "url": "stdio://node/path/to/server.js",
  "description": "My custom MCP server",
  "enabled": true
}
```

## Transport Options

### Stdio (Local Process)
```
stdio://command/arg1/arg2
stdio://python/my_server.py
stdio://node/server.js
```

### WebSocket
```
ws://localhost:8080/mcp
wss://api.example.com/mcp
```

### HTTP/SSE (Server-Sent Events)
```
https://api.example.com/mcp/sse
```

## Security Considerations

1. **Filesystem Access**: Limit `ALLOWED_DIRECTORIES` to specific paths
2. **Authentication**: Use environment variables for sensitive tokens
3. **Network Access**: Be cautious with servers that can make external requests
4. **Tool Permissions**: Review what each tool can do before enabling

## Troubleshooting

### Server Won't Connect
- Check if the command/URL is correct
- Verify environment variables are set
- Look at backend logs for errors

### Tools Not Available
- Ensure server is connected (`/mcp/servers` endpoint)
- Check if tools are listed (`/mcp/tools` endpoint)
- Verify the server implements tool discovery

### Performance Issues
- Stdio servers spawn new processes
- Consider connection pooling for frequently used servers
- Monitor resource usage of MCP server processes

## Examples

### GitHub Integration
```json
{
  "name": "github",
  "enabled": true,
  "environment": {
    "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxx"
  }
}
```

Then in chat: "Show me open issues in the telly-chat repository"

### Database Queries
```json
{
  "name": "postgres",
  "enabled": true,
  "environment": {
    "DATABASE_URL": "postgresql://localhost/myapp"
  }
}
```

Then in chat: "Show me all users created in the last week"

## API Reference

### GET /mcp/servers
List all configured MCP servers and their connection status

### POST /mcp/servers/{name}/connect
Connect to a specific MCP server

### POST /mcp/servers/{name}/disconnect
Disconnect from a specific MCP server

### POST /mcp/servers/auto-connect
Connect to all enabled servers

### GET /mcp/tools
List all available tools from connected servers