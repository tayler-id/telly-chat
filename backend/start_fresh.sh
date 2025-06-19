#!/bin/bash

echo "Starting Telly Chat Backend (Fresh)..."

# Kill any existing process on port 8000
echo "Stopping any existing backend..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Clean Python cache
echo "Cleaning Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Verify endpoints exist
echo "Verifying endpoints in main.py..."
EPISODE_COUNT=$(grep -c "@app.get.*/episodes" main.py)
TRANSCRIPT_COUNT=$(grep -c "@app.get.*/transcripts" main.py)

echo "  Episode endpoints: $EPISODE_COUNT"
echo "  Transcript endpoints: $TRANSCRIPT_COUNT"

if [ $EPISODE_COUNT -eq 0 ]; then
    echo "ERROR: Episode endpoints not found!"
    exit 1
fi

# Set Python to not use cached bytecode
export PYTHONDONTWRITEBYTECODE=1

# Use system Python (not venv) to ensure fresh import
echo "Starting backend with system Python..."
/usr/bin/env python3 main.py