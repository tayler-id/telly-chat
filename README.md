# Telly Chat

An AI-powered chat application with YouTube transcript extraction capabilities and advanced agent orchestration.

## Features

### Core Features (Always Available)
- 🎥 YouTube transcript extraction using Supadata API
- 💬 Real-time streaming chat interface
- 🤖 LangChain-powered agent orchestration
- 📝 Action plan generation from video content
- 💾 Export transcripts and action plans as markdown
- 🔄 Session management with conversation history

### Advanced Features (Optional)
- 🧠 **AI Memory System**: Short-term, long-term, and episodic memory
- 🔀 **Workflow Engine**: Complex task orchestration with LangGraph
- 🧵 **Threading System**: Multi-context conversation management
- 📄 **Document Parsing**: Support for PDF, HTML, Markdown, JSON
- 🔍 **Smart Chunking**: Semantic and recursive text chunking
- 🚀 **Pipe Agents**: Stream processing and agent chaining

## 🚀 Quick Start (Simplified Version)

For a simpler, more reliable experience, we now offer a **simplified version** that focuses on core functionality:

```bash
# Start the simplified version
./start_simple.sh
```

This will start:
- Backend on http://localhost:8000  
- Frontend on http://localhost:3000

The simplified version includes:
- ✅ YouTube transcript extraction
- ✅ Transcript storage and search
- ✅ Clean chat interface
- ✅ No complex dependencies

See [SIMPLIFIED_GUIDE.md](SIMPLIFIED_GUIDE.md) for details.

## Tech Stack

### Backend
- FastAPI for REST API and WebSocket support
- LangChain for agent orchestration
- Anthropic Claude / OpenAI GPT for language models
- Redis for session storage (optional)
- Python 3.11+

### Frontend
- Next.js with TypeScript
- React for UI components
- Tailwind CSS for styling
- Server-Sent Events for real-time streaming

## Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis (optional, for persistent sessions)

### Quick Setup

```bash
# Install core features only
python setup.py

# Install with all advanced features
python setup.py --with-optional
```

### Manual Setup

#### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Core dependencies only
pip install -r requirements-core.txt

# Optional: Install advanced features
pip install -r requirements-optional.txt
```

Create a `.env` file in the backend directory:
```env
ANTHROPIC_API_KEY=your_api_key_here
SUPADATA_API_KEY=your_supadata_key_here
# Or use OpenAI
# OPENAI_API_KEY=your_openai_key_here
# MODEL_PROVIDER=openai
```

### Frontend Setup

```bash
cd frontend
npm install
```

Create a `.env.local` file in the frontend directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running the Application

### Start Backend
```bash
cd backend
python main.py
```

### Start Frontend
```bash
cd frontend
npm run dev
```

Visit http://localhost:3000 to use the application.

## Usage

1. Enter a YouTube URL in the chat interface
2. The AI agent will extract the transcript and generate an action plan
3. Click "Save Transcript & Action Plan" to download as markdown
4. Continue chatting to ask questions about the video content

## Architecture

The application uses a modular architecture with:
- **Agent System**: LangChain-based agents with tool support
- **Memory Management**: Conversation history and session persistence
- **Tool Framework**: Extensible tool system for adding new capabilities
- **Streaming**: Real-time response streaming using SSE

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License