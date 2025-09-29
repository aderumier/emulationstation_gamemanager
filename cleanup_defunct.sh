#!/bin/bash

# Script to clean up defunct Python processes
# This script finds and removes defunct processes that might be left behind

echo "🔄 Cleaning up defunct Python processes..."

# Find defunct processes
DEFUNCT_PIDS=$(ps aux | grep -E '\[python3\] <defunct>' | awk '{print $2}')

if [ -z "$DEFUNCT_PIDS" ]; then
    echo "✅ No defunct Python processes found"
    exit 0
fi

echo "📋 Found defunct processes: $DEFUNCT_PIDS"

# Try to clean them up by sending SIGCHLD to parent processes
for PID in $DEFUNCT_PIDS; do
    echo "🔄 Attempting to clean up defunct process $PID..."
    
    # Get the parent process ID
    PARENT_PID=$(ps -o ppid= -p $PID 2>/dev/null | tr -d ' ')
    
    if [ -n "$PARENT_PID" ] && [ "$PARENT_PID" != "1" ]; then
        echo "  Parent PID: $PARENT_PID"
        # Send SIGCHLD to parent to trigger cleanup
        kill -CHLD $PARENT_PID 2>/dev/null || true
    fi
done

# Wait a moment for cleanup
sleep 2

# Check if defunct processes still exist
REMAINING_DEFUNCT=$(ps aux | grep -E '\[python3\] <defunct>' | awk '{print $2}')

if [ -z "$REMAINING_DEFUNCT" ]; then
    echo "✅ All defunct processes cleaned up"
else
    echo "⚠️  Some defunct processes remain: $REMAINING_DEFUNCT"
    echo "   These will be cleaned up when their parent processes exit"
fi
