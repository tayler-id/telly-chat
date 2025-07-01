# Project Overview: Telly Chat

This document provides a high-level overview of the Telly Chat application, based on an analysis of the project's source code and documentation.

## 1. Project Purpose and Features

Telly Chat is an AI-powered chat application designed to interact with YouTube video content. Its primary features include:

*   **YouTube Transcript Extraction**: Fetches and processes transcripts from YouTube videos.
*   **AI-Powered Analysis**: Utilizes language models (Anthropic Claude or OpenAI GPT) to analyze transcripts, generate action plans, and answer user questions.
*   **Real-time Chat Interface**: A web-based interface for users to interact with the AI.
*   **Advanced Memory System (Optional)**: Includes short-term, long-term, and episodic memory capabilities to maintain context across conversations.
*   **Workflow Engine (Optional)**: An orchestration system for handling complex, multi-step tasks.

The project has two main configurations: a "simple" version focusing on core transcript and chat functionality, and a "complete" version that enables the advanced memory and workflow features.

## 2. Tech Stack

*   **Backend**:
    *   **Framework**: FastAPI (Python)
    *   **AI/ML**: LangChain, LangGraph
    *   **Language Models**: Anthropic Claude, OpenAI GPT
    *   **Vector Stores**: FAISS, Chroma, Pinecone
    *   **Database**: Redis (optional, for session management)
*   **Frontend**:
    *   **Framework**: Next.js (React) with TypeScript
    *   **Styling**: Tailwind CSS
    *   **API Communication**: Axios, Server-Sent Events (SSE) for streaming

## 3. Architecture

### Backend

The backend is modular, with a clear separation of concerns:

*   **`main.py`**: The main entry point for the FastAPI application. It initializes the agent, sets up CORS, and defines all API endpoints. There is a `main_simple.py` which seems to be the currently preferred entry point according to `PROJECT_MEMORY.md`.
*   **`agents/`**: Contains the core logic for the AI agents.
    *   `chat_agent.py`: A basic agent with tool-calling capabilities.
    *   `enhanced_chat_agent.py`: Extends the base agent with memory and workflow integration.
    *   `simple_chat_agent.py`: A streamlined agent that seems to be part of the "simple" setup.
*   **`services/`**: Provides business logic for different parts of the application.
    *   `session_manager.py`: Manages user sessions, either in-memory or using Redis.
    *   `transcript_service.py`: Handles all operations related to saving, fetching, and searching transcripts.
*   **`memory/`**: Implements the advanced memory system.
    *   `short_term.py`: A deque-based, in-memory store for recent interactions.
    *   `long_term.py`: A vector-based semantic store for durable memories.
    *   `episodic.py` & `episodic_store.py`: Records and manages entire conversation "episodes" for pattern analysis and recall.
    *   `transcript_store.py`: Manages the storage and retrieval of YouTube transcripts, including a FAISS vector index for semantic search.
    *   `vector_store.py`: A wrapper for different vector database implementations (FAISS, Chroma, Pinecone).
*   **`workflows/`**: Contains the engine for orchestrating complex tasks.
    *   `engine.py`: A stateful workflow engine built on LangGraph.
    *   `orchestrator.py`: Manages the execution of multiple concurrent workflows.
    *   `templates.py`: Provides pre-built templates for common workflow patterns like research and analysis.

### Frontend

The frontend is a standard Next.js application:

*   **`pages/index.tsx`**: The main page of the application, which renders the `ChatInterface`.
*   **`components/`**: Contains all the React components for the UI.
    *   `ChatInterface.tsx`: The main component that orchestrates the chat UI, including the message list and input box. It handles the streaming of responses from the backend via SSE.
    *   `MessageList.tsx`: Renders the list of messages in the conversation.
    *   `InputBox.tsx`: The text area and send button for user input.
    *   `ConversationHistory.tsx`: A sidebar component that displays past conversation episodes when the memory feature is enabled.
    *   `MemoryToggle.tsx`: A button to enable or disable the advanced memory features.
*   **`services/api.ts`**: Defines the TypeScript interfaces for API communication and provides functions for interacting with the backend REST API.

## 4. Setup and Execution

*   **Installation**: The project uses a `setup.py` script to install dependencies for both the backend (into a `venv`) and the frontend (`npm install`). It can install "core" or "optional" dependencies.
*   **Execution**: The `start.sh` script provides a convenient way to start both the backend and frontend servers concurrently. The `PROJECT_MEMORY.md` also mentions a `start_simple.sh` which is the preferred method for the simplified system.
*   **Configuration**: API keys and other settings are managed through `.env` files in the `backend` and `frontend` directories.

## 5. Key Takeaways

*   The project is well-structured, with a clear separation between the backend and frontend.
*   The backend is highly modular, allowing for features like memory and workflows to be toggled on or off.
*   The use of LangChain and LangGraph indicates a sophisticated approach to AI agent and workflow orchestration.
*   The frontend uses modern React practices and communicates with the backend via a REST API and Server-Sent Events for real-time streaming.
*   The `PROJECT_MEMORY.md` file is a critical piece of documentation, highlighting a shift from a complex, over-engineered system to a more streamlined, "simple" version that is currently active. This is a key insight for any developer working on the project.
