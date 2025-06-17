# Telly Chat - AI-Powered YouTube Transcript Assistant

A ChatGPT-like interface that integrates with the Telly agent to extract YouTube transcripts and generate actionable plans from video content.

## Features

- 🎥 **YouTube Transcript Extraction**: Automatically extract transcripts from any YouTube video
- 🤖 **AI-Powered Conversations**: Chat naturally with an AI assistant that understands video content
- 📋 **Action Plan Generation**: Create structured, actionable plans from video tutorials
- 🔧 **Tool Transparency**: See when the AI is using tools to fetch transcripts
- 💬 **Real-time Streaming**: Get responses as they're generated
- 📱 **Modern UI**: Clean, responsive interface similar to ChatGPT

## Architecture

```
telly-chat/
├── frontend/          # Next.js React application
│   ├── components/    # React components
│   ├── pages/        # Next.js pages
│   └── services/     # API services
└── backend/          # FastAPI Python backend
    ├── agents/       # LangChain agents and tools
    ├── models/       # Data models
    └── services/     # Business logic
```

## Prerequisites

- Python 3.8+
- Node.js 16+
- Anthropic API key (or OpenAI API key)
- Supadata API key (for YouTube transcripts)

## Quick Start

1. **Clone and navigate to the project:**
   ```bash
   cd /Users/tramsay/Desktop/_ORGANIZED/01_Development/telly-chat
   ```

2. **Set up environment variables:**
   
   Edit `backend/.env`:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key
   SUPADATA_API_KEY=your_supadata_api_key
   MODEL_PROVIDER=anthropic  # or "openai"
   ```

3. **Run the application:**
   ```bash
   ./start.sh
   ```

   This will:
   - Set up Python virtual environment
   - Install all dependencies
   - Start the backend server (http://localhost:8000)
   - Start the frontend dev server (http://localhost:3000)

4. **Open your browser:**
   Navigate to http://localhost:3000

## Manual Setup

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Usage

1. **Share a YouTube URL**: Simply paste a YouTube URL in the chat
2. **Ask questions**: "Can you get the transcript for [YouTube URL]?"
3. **Generate action plans**: "Create an action plan from this video"
4. **Follow-up questions**: Ask about specific parts of the video

## API Endpoints

- `GET /` - Health check
- `POST /chat` - Send a chat message (non-streaming)
- `GET /chat/stream` - Stream chat responses (SSE)
- `WebSocket /ws` - Real-time chat via WebSocket
- `GET /sessions` - List chat sessions
- `GET /sessions/{id}` - Get specific session
- `DELETE /sessions/{id}` - Delete session

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **LangChain** - AI agent orchestration
- **Anthropic/OpenAI** - LLM providers
- **Supadata API** - YouTube transcript extraction

### Frontend
- **Next.js** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **React Markdown** - Message rendering
- **Server-Sent Events** - Real-time streaming

## Configuration

### Model Provider

You can switch between Anthropic and OpenAI by changing `MODEL_PROVIDER` in the backend `.env` file.

### Custom Models

Specify custom models in the environment:
- Anthropic: Default is `claude-3-5-sonnet-20241022`
- OpenAI: Default is `gpt-4-turbo-preview`

## Development

### Backend Development

```bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm run dev
```

### Adding New Tools

1. Create a new tool in `backend/agents/tools/`
2. Follow the LangChain `BaseTool` interface
3. Register the tool in `ChatAgent._initialize_tools()`

## Troubleshooting

### Backend won't start
- Check Python version: `python3 --version` (need 3.8+)
- Verify API keys in `.env`
- Check port 8000 is available

### Frontend won't start
- Check Node version: `node --version` (need 16+)
- Clear Next.js cache: `rm -rf .next`
- Check port 3000 is available

### Connection issues
- Ensure both backend and frontend are running
- Check CORS settings if deploying to different domains
- Verify API_URL in frontend matches backend address

## License

MIT