#!/bin/bash

echo "Starting Telly Chat Application (Complete)..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Kill any existing processes
echo -e "${BLUE}Cleaning up existing processes...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 2

# Clean Python cache to ensure fresh code
echo -e "${BLUE}Cleaning Python cache...${NC}"
cd backend
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Verify endpoints exist
echo -e "${BLUE}Verifying backend endpoints...${NC}"
EPISODE_COUNT=$(grep -c "@app.get.*/episodes" main.py)
TRANSCRIPT_COUNT=$(grep -c "@app.get.*/transcripts" main.py)

echo "  Episode endpoints found: $EPISODE_COUNT"
echo "  Transcript endpoints found: $TRANSCRIPT_COUNT"

if [ $EPISODE_COUNT -eq 0 ]; then
    echo -e "${RED}ERROR: Episode endpoints not found in main.py!${NC}"
    echo "The backend code may be outdated."
else
    echo -e "${GREEN}✓ Episode endpoints verified${NC}"
fi

# Don't use Python bytecode cache
export PYTHONDONTWRITEBYTECODE=1

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Test if backend is running with correct endpoints
echo -e "${BLUE}Testing backend endpoints...${NC}"
if curl -s http://localhost:8000/episodes/active > /dev/null 2>&1; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/episodes/active)
    if [ "$STATUS" = "404" ]; then
        echo -e "${RED}WARNING: Episode endpoints returning 404${NC}"
    else
        echo -e "${GREEN}✓ Episode endpoints accessible (status: $STATUS)${NC}"
    fi
else
    echo -e "${RED}Backend not responding${NC}"
fi

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd ../frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Print success message
echo -e "\n${GREEN}===================================${NC}"
echo -e "${GREEN}Telly Chat is running!${NC}"
echo -e "${GREEN}===================================${NC}"
echo -e "Frontend: ${BLUE}http://localhost:3000${NC}"
echo -e "Backend API: ${BLUE}http://localhost:8000${NC}"
echo -e "API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "\nMemory is stored in: backend/data/memory/"
echo -e "Episodes are in: backend/data/memory/episodes/"
echo -e "\nPress Ctrl+C to stop all services"

# Show current episodes
echo -e "\n${BLUE}Current test episodes:${NC}"
if [ -d "backend/data/memory/episodes" ]; then
    EPISODE_COUNT=$(find backend/data/memory/episodes -name "*.json" | grep -v index.json | wc -l)
    echo "  Found $EPISODE_COUNT episode files"
fi

# Wait for processes
wait