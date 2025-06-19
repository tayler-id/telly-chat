# Telly Chat - Simplified Version

## Overview

This is a simplified version of Telly Chat that focuses on core functionality:
- Extract YouTube transcripts
- Save them for later reference
- Search through saved transcripts
- Chat about the content

## Quick Start

```bash
# Start the application
./start_simple.sh

# Or manually:
cd backend
source venv/bin/activate
python3 main_simple.py

# In another terminal:
cd frontend
npm run dev
```

## Features

### 1. YouTube Transcript Extraction
- Paste any YouTube URL in chat
- Automatically extracts transcript and generates action plan
- Saves to local storage for future reference

### 2. Transcript Search
- Search through all saved transcripts
- Semantic search using vector embeddings
- Returns relevant transcripts with scores

### 3. Simple Chat Interface
- Clean, straightforward chat experience
- No complex memory systems or workflows
- Just works

## API Endpoints

### Core Endpoints
- `GET /` - API info
- `GET /health` - Health check
- `GET /chat/stream?message=...` - Streaming chat

### YouTube Processing
- `POST /youtube/process?url=...` - Process and save a YouTube video
- `GET /transcripts/search?query=...` - Search saved transcripts
- `GET /transcripts/recent` - Get recent transcripts

## Architecture

```
Frontend (React/Next.js)
    ↓
Simple API (FastAPI)
    ↓
SimpleChatAgent
    ├── LLM (Anthropic/OpenAI)
    ├── Telly Tool (YouTube extraction)
    └── Transcript Store (FAISS + JSON)
```

## Key Differences from Complex Version

### What We Kept
✓ YouTube transcript extraction
✓ Transcript storage and search
✓ Basic chat functionality
✓ Clean API

### What We Removed
✗ Complex workflow engine
✗ Dynamic prompt modification
✗ Thread management
✗ Episodic memory
✗ Agent routing
✗ Complex dependencies

## File Structure

```
backend/
├── main_simple.py          # Simplified API
├── agents/
│   └── simple_chat_agent.py   # Core agent logic
├── memory/
│   └── transcript_store.py    # Transcript storage
└── data/
    └── memory/
        └── transcripts/       # Saved transcripts

frontend/
└── components/
    └── SimpleYouTubeButton.tsx  # One-click processing
```

## Common Tasks

### Process a YouTube Video
```python
# Via API
POST /youtube/process?url=https://youtube.com/watch?v=...

# Response
{
  "success": true,
  "id": "transcript_abc123",
  "title": "Video Title",
  "summary": "2-3 sentence summary",
  "transcript_length": 5000
}
```

### Search Transcripts
```python
# Via API
GET /transcripts/search?query=machine+learning

# Response
{
  "query": "machine learning",
  "results": [...],
  "count": 5
}
```

### Chat with Context
Just paste a YouTube URL in the chat, and the agent will:
1. Extract the transcript
2. Save it automatically
3. Provide analysis
4. Answer questions about it

## Troubleshooting

### Backend won't start
- Check Python virtual environment: `source venv/bin/activate`
- Check API keys in `.env` file
- Check port 8000 is free: `lsof -i :8000`

### Frontend connection issues
- Ensure backend is running on port 8000
- Check CORS settings in main_simple.py
- Check `NEXT_PUBLIC_API_URL` in frontend/.env.local

### Transcript search not working
- Ensure OPENAI_API_KEY is set (for embeddings)
- Check data/memory/transcripts/vectors directory exists
- Try keyword search if semantic search fails

## Future Improvements

1. **Better error handling** - More informative error messages
2. **Transcript management UI** - View/delete saved transcripts
3. **Export functionality** - Export transcripts as markdown
4. **Batch processing** - Process multiple videos at once
5. **Simple analytics** - Most viewed transcripts, etc.

## Philosophy

This simplified version follows the principle of "do one thing well":
- Extract YouTube transcripts
- Save them
- Search them
- Chat about them

No complex abstractions, just straightforward functionality that works reliably.