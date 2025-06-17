# Telly Chat

An AI-powered chat application with YouTube transcript extraction capabilities and advanced agent orchestration.

## Features

- 🎥 YouTube transcript extraction using Supadata API
- 💬 Real-time streaming chat interface
- 🤖 LangChain-powered agent orchestration
- 📝 Action plan generation from video content
- 💾 Export transcripts and action plans as markdown
- 🔄 Session management with conversation history

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

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
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