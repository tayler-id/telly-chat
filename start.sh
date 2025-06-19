#!/bin/bash

# Telly Chat Unified Startup Script
# This script starts both the backend and frontend services

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to kill process on port
kill_port() {
    port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        print_color $YELLOW "Killing existing process on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Cleanup function
cleanup() {
    print_color $YELLOW "\nShutting down Telly Chat..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Clean up any remaining processes
    kill_port 8000
    kill_port 3000
    
    print_color $GREEN "Shutdown complete."
    exit 0
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Check prerequisites
print_color $BLUE "Checking prerequisites..."

if ! command_exists python3; then
    print_color $RED "Error: Python 3 is not installed"
    exit 1
fi

if ! command_exists npm; then
    print_color $RED "Error: Node.js/npm is not installed"
    exit 1
fi

# Clean up existing processes
print_color $YELLOW "Cleaning up existing processes..."
kill_port 8000
kill_port 3000

# Backend setup
print_color $BLUE "\n=== Setting up Backend ==="
cd backend

# Check for virtual environment
if [ ! -d "venv" ]; then
    print_color $YELLOW "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_color $GREEN "Activating virtual environment..."
source venv/bin/activate

# Check if requirements need to be installed/updated
if [ ! -f ".requirements.installed" ] || [ "requirements-core.txt" -nt ".requirements.installed" ]; then
    print_color $YELLOW "Installing/updating backend dependencies..."
    pip install --upgrade pip >/dev/null 2>&1
    pip install -r requirements-core.txt
    touch .requirements.installed
else
    print_color $GREEN "Backend dependencies up to date"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    print_color $RED "Error: backend/.env file not found"
    print_color $YELLOW "Please create backend/.env with the following:"
    echo "MODEL_PROVIDER=anthropic"
    echo "ANTHROPIC_API_KEY=your_api_key"
    echo "OPENAI_API_KEY=your_api_key  # For embeddings"
    echo "SUPADATA_API_KEY=your_api_key"
    exit 1
fi

# Initialize vector store if needed
if [ ! -f "data/memory/faiss_index/index.faiss" ]; then
    print_color $YELLOW "Initializing vector store..."
    python init_vector_store.py
fi

# Start backend
print_color $GREEN "Starting backend server..."
python main.py &
BACKEND_PID=$!

# Wait for backend to be ready
print_color $YELLOW "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_color $GREEN "✓ Backend is running"
        break
    fi
    if [ $i -eq 30 ]; then
        print_color $RED "✗ Backend failed to start"
        exit 1
    fi
    sleep 1
done

# Frontend setup
print_color $BLUE "\n=== Setting up Frontend ==="
cd ../frontend

# Check for node_modules
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.package-lock.json" ]; then
    print_color $YELLOW "Installing frontend dependencies..."
    npm install
    touch node_modules/.package-lock.json
else
    print_color $GREEN "Frontend dependencies up to date"
fi

# Check for .env.local file
if [ ! -f ".env.local" ]; then
    print_color $YELLOW "Creating frontend .env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
fi

# Start frontend
print_color $GREEN "Starting frontend server..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to be ready
print_color $YELLOW "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        print_color $GREEN "✓ Frontend is running"
        break
    fi
    if [ $i -eq 30 ]; then
        print_color $RED "✗ Frontend failed to start"
        exit 1
    fi
    sleep 1
done

# Success message
print_color $GREEN "\n======================================="
print_color $GREEN "  Telly Chat is running successfully!"
print_color $GREEN "======================================="
print_color $BLUE "Frontend: ${GREEN}http://localhost:3000"
print_color $BLUE "Backend API: ${GREEN}http://localhost:8000"
print_color $BLUE "API Docs: ${GREEN}http://localhost:8000/docs"
print_color $YELLOW "\nPress Ctrl+C to stop all services"

# Keep the script running
wait