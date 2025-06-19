#!/bin/bash

echo "Stopping old backend process..."
# Find and kill the process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo "Waiting for port to be released..."
sleep 2

echo "Starting new backend..."
cd /Users/tramsay/Desktop/_ORGANIZED/01_Development/telly-chat/backend
python main.py