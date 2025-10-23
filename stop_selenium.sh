#!/bin/bash

# Stop Selenium Docker container
echo "🛑 Stopping Selenium Docker container..."

# Stop the container
docker stop gamemanager-selenium 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Selenium container stopped successfully"
    
    # Ask if user wants to remove the container
    read -p "🗑️  Do you want to remove the container? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rm gamemanager-selenium 2>/dev/null
        echo "🗑️  Selenium container removed"
    else
        echo "📦 Selenium container kept (can be restarted with: docker start gamemanager-selenium)"
    fi
else
    echo "❌ Failed to stop Selenium container (it may not be running)"
    echo "🔍 Check running containers with: docker ps"
fi

