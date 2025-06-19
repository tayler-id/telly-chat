# Telly Chat Project Memory

## Project Overview
**Purpose**: A chat application that extracts YouTube transcripts, analyzes them intelligently, and maintains a searchable knowledge base.

**Current Status**: Simplified architecture focusing on core functionality with enhanced content analysis.

## Directory Structure

```
telly-chat/
├── backend/
│   ├── main.py                    # ✅ CURRENT: Primary API with all features
│   ├── agents/
│   │   ├── enhanced_chat_agent.py # ✅ CURRENT: Main agent with MCP support
│   │   ├── simple_chat_agent.py   # Simplified fallback agent
│   │   └── tools/
│   │       └── enhanced_telly_tool.py # Smart YouTube analysis
│   ├── services/
│   │   ├── mcp/                   # ✅ NEW: MCP client implementation
│   │   │   ├── mcp_client.py      # MCP client and session management
│   │   │   ├── mcp_protocol.py    # JSON-RPC 2.0 protocol
│   │   │   ├── mcp_transport.py   # Transport layers (stdio, WebSocket)
│   │   │   └── mcp_registry.py    # Server configuration management
│   │   ├── session_manager.py     # Session management
│   │   └── transcript_service.py  # Transcript API services
│   ├── memory/
│   │   ├── transcript_store.py    # Full transcript storage with FAISS
│   │   ├── episodic_store.py      # Episode-based memory
│   │   ├── context_manager.py     # Context loading for LLM
│   │   ├── short_term.py          # Short-term memory
│   │   ├── long_term.py           # Long-term memory
│   │   └── vector_store.py        # FAISS vector storage
│   ├── workflows/                 # Workflow system (optional)
│   ├── tests/                     # ✅ All test files moved here
│   └── data/
│       └── memory/
│           └── transcripts/       # Saved transcripts + vector index
│
├── frontend/
│   ├── components/
│   │   ├── ChatInterface.tsx      # Main chat UI
│   │   ├── SaveButton.tsx         # Save transcript button
│   │   ├── MemoryToggle.tsx       # Memory on/off toggle
│   │   ├── ConversationHistory.tsx # Episode history sidebar
│   │   └── WorkflowButton.tsx     # Workflow trigger
│   └── .env.local                 # Frontend configuration
│
├── start.sh                      # ✅ CURRENT: Unified startup script
├── PROJECT_MEMORY.md             # ✅ This file - comprehensive docs
└── .env                          # API keys and configuration
```

## Key Components

### Current Active Files

1. **main.py** - Primary FastAPI backend
   - Full-featured with memory, episodes, workflows, and MCP support
   - Endpoints for chat, transcripts, episodes, memory, workflows, and MCP
   - WebSocket support for real-time communication

2. **enhanced_chat_agent.py** - Main agent with all features
   - Memory system integration (short-term, long-term, episodic)
   - Workflow support for complex tasks
   - MCP client support for external integrations
   - Transcript storage with semantic search

3. **simple_chat_agent.py** - Simplified fallback agent
   - Core YouTube transcript extraction
   - Basic transcript storage
   - No advanced features (kept as backup)

4. **enhanced_telly_tool.py** - Smart YouTube analysis
   - Detects content type (tutorial, news, review, etc.)
   - Generates appropriate summaries
   - AI-content detection
   - Saves full transcripts with hidden metadata

5. **MCP Support** (NEW)
   - **services/mcp/** - Complete MCP client implementation
   - JSON-RPC 2.0 protocol support
   - Multiple transport layers (stdio, WebSocket)
   - Tool discovery and integration
   - Server registry for managing connections

### Inactive/Legacy Components

- **Enhanced Agent System**: Complex memory with episodes
- **Workflow Engine**: Over-engineered automation system
- **Thread Manager**: Multi-context conversations
- **Dynamic Prompts**: Caused compatibility issues

## API Endpoints

### Core Endpoints
```
GET  /                          # API info
GET  /health                   # Health check
GET  /features                 # Available features
GET  /chat/stream              # Streaming chat (SSE)
WS   /ws                       # WebSocket chat
```

### YouTube & Transcripts
```
POST /youtube/process          # Process & save YouTube video
GET  /transcripts/search       # Semantic search
GET  /transcripts/recent       # Recent transcripts
GET  /transcripts/{id}         # Get specific transcript
GET  /transcripts/by-url       # Get transcript by URL
GET  /transcripts/related/{id} # Get related transcripts
```

### Memory System
```
POST /features/memory/toggle   # Toggle memory on/off
GET  /memory/stats            # Memory statistics
GET  /memory/export           # Export memory state
POST /memory/import           # Import memory state
```

### Episodes
```
GET  /episodes/active         # List active episodes
GET  /episodes/history        # Episode history
GET  /episodes/session/{id}   # Episodes for session
POST /episodes/end/{id}       # End an episode
GET  /episodes/search         # Search episodes
```

### MCP Support (NEW)
```
GET  /mcp/servers             # List available MCP servers
POST /mcp/servers/{name}/connect    # Connect to MCP server
POST /mcp/servers/{name}/disconnect # Disconnect from server
POST /mcp/servers/auto-connect      # Auto-connect enabled servers
GET  /mcp/tools               # List available MCP tools
```

### Workflows
```
POST /workflows/execute       # Execute a workflow
GET  /workflows/status/{id}   # Get workflow status
GET  /workflows/templates     # List workflow templates
```

## Key Features

### What Works Now
1. **Smart YouTube Analysis**
   - Content type detection
   - AI-generated content detection
   - Type-specific summaries (tutorials → steps, news → key points)

2. **Transcript Storage**
   - Full transcripts saved locally
   - Semantic search with FAISS
   - Fallback to keyword search

3. **Simple Chat**
   - Paste YouTube URL → Auto-extract & analyze
   - Search saved transcripts
   - No complex state management

### Known Issues
1. **Virtual Environment**: Using system Python vs venv confusion
2. **Import Paths**: Relative imports cause issues
3. **FAISS Initialization**: Needs manual setup first time
4. **Memory Toggle**: UI shows but doesn't affect simple system

## Common Tasks

### Start the Application
```bash
./start_simple.sh
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Process a Video
```python
# In chat: Just paste the YouTube URL
# Via API: POST /youtube/process?url=https://youtube.com/watch?v=...
```

### Search Transcripts
```python
# In chat: "Search for videos about machine learning"
# Via API: GET /transcripts/search?query=machine+learning
```

## Configuration

### Environment Variables (.env)
```
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...  # For embeddings
PORT=8000
```

### Frontend Config (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Recent Changes

1. **Fixed Full Transcript Saving** - Enhanced tools now save complete transcripts with hidden metadata
2. **Major Cleanup** - Removed unused files, consolidated agents, moved tests to tests/
3. **Unified Startup Script** - Single start.sh with better process management
4. **MCP Client Support** - Complete Model Context Protocol implementation
   - JSON-RPC 2.0 protocol
   - Multiple transport support (stdio, WebSocket)
   - Tool discovery and integration
   - Server registry for configuration
5. **Enhanced YouTube Tool** - Smart content type and AI detection
6. **Simplified Imports** - Removed fallback logic, using enhanced agent as primary

## Next Steps

1. **NLP Agent** - Chat with all saved transcripts
2. **Transcript Management UI** - View/delete saved items  
3. **Export Feature** - Download transcripts as markdown
4. **Batch Processing** - Multiple videos at once

## Debugging Tips

1. **Backend Won't Start**
   - Check: `source venv/bin/activate`
   - Check: Port 8000 free
   - Check: API keys in .env

2. **Chat Errors**
   - Use main_simple.py not main.py
   - Check enhanced_telly_tool imports
   - Verify FAISS initialized

3. **Search Not Working**
   - Need OPENAI_API_KEY for embeddings
   - Check data/memory/transcripts/vectors/

## Architecture Philosophy

**Current**: "Do one thing well" - Extract, analyze, save, search YouTube videos
**Previous**: Over-engineered with workflows, threads, complex memory

The simplified system is more reliable and easier to maintain.