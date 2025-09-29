#!/bin/bash

# Graceful shutdown script for GameManager
# This script sends SIGTERM to allow proper cleanup instead of SIGKILL

echo "🔄 Stopping GameManager server gracefully..."

# Find all Python processes running app.py
PIDS=$(pgrep -f "python3.*app.py")

if [ -z "$PIDS" ]; then
    echo "❌ No GameManager process found"
    exit 1
fi

echo "📋 Found GameManager processes: $PIDS"

# Send SIGTERM to all processes
echo "🔄 Sending SIGTERM signal for graceful shutdown..."
for PID in $PIDS; do
    echo "  Sending SIGTERM to PID $PID"
    kill -TERM $PID 2>/dev/null || true
done

# Wait for graceful shutdown (up to 30 seconds)
echo "⏳ Waiting for graceful shutdown (max 30 seconds)..."
for i in {1..30}; do
    REMAINING_PIDS=""
    for PID in $PIDS; do
        if kill -0 $PID 2>/dev/null; then
            REMAINING_PIDS="$REMAINING_PIDS $PID"
        fi
    done
    
    if [ -z "$REMAINING_PIDS" ]; then
        echo ""
        echo "✅ All processes stopped gracefully"
        exit 0
    fi
    
    sleep 1
    echo -n "."
done

echo ""
echo "⚠️  Graceful shutdown timeout, forcing termination..."

# Force kill remaining processes
for PID in $PIDS; do
    if kill -0 $PID 2>/dev/null; then
        echo "🔄 Force killing PID $PID..."
        kill -KILL $PID 2>/dev/null || true
    fi
done

# Wait a moment and check if any are still running
sleep 2
REMAINING_PIDS=""
for PID in $PIDS; do
    if kill -0 $PID 2>/dev/null; then
        REMAINING_PIDS="$REMAINING_PIDS $PID"
    fi
done

if [ -n "$REMAINING_PIDS" ]; then
    echo "❌ Failed to stop processes: $REMAINING_PIDS"
    exit 1
else
    echo "✅ All processes stopped (forced)"
fi
