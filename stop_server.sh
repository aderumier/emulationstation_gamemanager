#!/bin/bash

# Graceful shutdown script for GameManager
# This script sends SIGTERM to allow proper cleanup instead of SIGKILL

echo "🔄 Stopping GameManager server gracefully..."

# Find the main Python process
MAIN_PID=$(pgrep -f "python3.*app.py" | head -1)

if [ -z "$MAIN_PID" ]; then
    echo "❌ No GameManager process found"
    exit 1
fi

echo "📋 Found GameManager process (PID: $MAIN_PID)"

# Send SIGTERM for graceful shutdown
echo "🔄 Sending SIGTERM signal for graceful shutdown..."
kill -TERM $MAIN_PID

# Wait for graceful shutdown (up to 30 seconds)
echo "⏳ Waiting for graceful shutdown (max 30 seconds)..."
for i in {1..30}; do
    if ! kill -0 $MAIN_PID 2>/dev/null; then
        echo "✅ Server stopped gracefully"
        exit 0
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "⚠️  Graceful shutdown timeout, forcing termination..."

# If still running, force kill
if kill -0 $MAIN_PID 2>/dev/null; then
    echo "🔄 Sending SIGKILL signal..."
    kill -KILL $MAIN_PID
    sleep 2
    
    if kill -0 $MAIN_PID 2>/dev/null; then
        echo "❌ Failed to stop server"
        exit 1
    else
        echo "✅ Server stopped (forced)"
    fi
else
    echo "✅ Server stopped gracefully"
fi
