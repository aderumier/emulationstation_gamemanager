#!/bin/bash

# Restart GameManager server gracefully
echo "🔄 Restarting GameManager server..."

# Use the graceful stop script
./stop_server.sh

# Wait a moment for cleanup
sleep 2

# Start the server
echo "🚀 Starting GameManager server..."
python3 app.py
