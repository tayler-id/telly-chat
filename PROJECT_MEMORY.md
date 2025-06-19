# Telly Chat Project Memory

## Project Overview
**Purpose**: A chat application that extracts YouTube transcripts, analyzes them intelligently, and maintains a searchable knowledge base.

**Current Status**: Simplified architecture focusing on core functionality with enhanced content analysis.

## Directory Structure

```
telly-chat/
├── backend/
│   ├── main.py                    # Original complex API (episodes, memory, workflows)
│   ├── main_simple.py            # ✅ CURRENT: Simplified API with core endpoints
│   ├── agents/
│   │   ├── chat_agent.py         # Base agent with LangChain
│   │   ├── enhanced_chat_agent.py # Complex agent with memory systems
│   │   ├── simple_chat_agent.py  # ✅ CURRENT: Simplified agent
│   │   └── tools/
│   │       ├── telly_tool.py      # Original YouTube tool
│   │       └── enhanced_telly_tool.py # ✅ NEW: Smart content detection
│   ├── memory/
│   │   ├── transcript_store.py    # Stores full transcripts with FAISS search
│   │   ├── episodic_store.py      # Episode-based memory (unused in simple)
│   │   ├── context_manager.py     # Context loading for LLM
│   │   └── vector_store.py        # FAISS vector storage
│   ├── workflows/                 # Complex workflow system (unused in simple)
│   │   ├── youtube_workflow.py    # YouTube analysis workflow
│   │   └── templates.py           # Workflow templates
│   └── data/
│       └── memory/
│           └── transcripts/       # Saved transcript JSONs + vector index
│
├── frontend/
│   ├── components/
│   │   ├── ChatInterface.tsx      # Main chat UI
│   │   ├── SaveButton.tsx         # Save transcript button
│   │   ├── MemoryToggle.tsx       # Memory on/off toggle
│   │   ├── ConversationHistory.tsx # Episode history sidebar
│   │   ├── WorkflowButton.tsx     # Workflow trigger (unused)
│   │   └── SimpleYouTubeButton.tsx # ✅ NEW: One-click processing
│   └── .env.local                 # NEXT_PUBLIC_API_URL=http://localhost:8000
│
├── start_complete.sh             # Complex startup (venv issues)
├── start_simple.sh              # ✅ CURRENT: Simple startup script
├── SIMPLIFIED_GUIDE.md          # Guide for simplified version
└── .env                         # API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
```

## Key Components

### Current Active Files (Simplified System)

1. **main_simple.py** - Simplified FastAPI backend
   - Endpoints: `/chat/stream`, `/youtube/process`, `/transcripts/search`
   - No complex memory or workflow endpoints
   - Clean error handling

2. **simple_chat_agent.py** - Core agent logic
   - Uses enhanced_telly_tool for smart analysis
   - Basic transcript storage
   - No complex memory systems

3. **enhanced_telly_tool.py** - Smart YouTube analysis
   - Detects content type (tutorial, news, review, etc.)
   - Generates appropriate summaries
   - AI-content detection
   - Adapts output format to video type

4. **transcript_store.py** - Persistent storage
   - Saves full transcripts as JSON
   - FAISS vector index for semantic search
   - Simple API for save/retrieve/search

### Inactive/Legacy Components

- **Enhanced Agent System**: Complex memory with episodes
- **Workflow Engine**: Over-engineered automation system
- **Thread Manager**: Multi-context conversations
- **Dynamic Prompts**: Caused compatibility issues

## API Endpoints

### Active (Simple System)
```
GET  /                    # API info
GET  /health             # Health check
GET  /features           # Available features
GET  /chat/stream        # Streaming chat (SSE)
POST /youtube/process    # Process & save YouTube video
GET  /transcripts/search # Semantic search
GET  /transcripts/recent # Recent transcripts
```

### Legacy (Complex System)
```
POST /features/memory/toggle
GET  /memory/stats
GET  /episodes/*
POST /workflows/*
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

1. **Simplified Architecture** - Removed workflows, complex memory
2. **Enhanced YouTube Tool** - Smart content type detection
3. **Fixed Chat** - Removed dynamic prompt modification
4. **Better Startup** - Simple script that works
5. **Clear Documentation** - SIMPLIFIED_GUIDE.md
6. **Content Type Detection** - Detects tutorial, news, review, educational content
7. **AI-Generated Detection** - Identifies potentially AI-generated videos
8. **Adaptive Output** - Different formats for different video types
9. **Test Scripts** - Added test_enhanced_tool.py and test_content_detection.py

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