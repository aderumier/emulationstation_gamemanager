#!/bin/bash

# Start Selenium Docker container for Google Images scraping
echo "🚀 Starting Selenium Docker container for Google Images scraping..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing Selenium container
echo "🛑 Stopping any existing Selenium container..."
docker stop gamemanager-selenium 2>/dev/null || true
docker rm gamemanager-selenium 2>/dev/null || true

# Start the Selenium container
echo "🐳 Starting Selenium standalone Chrome container..."
docker run -d \
    --name gamemanager-selenium \
    --restart unless-stopped \
    -p 4444:4444 \
    -p 7900:7900 \
    -e SE_NODE_MAX_SESSIONS=2 \
    -e SE_NODE_SESSION_TIMEOUT=300 \
    -e SE_NODE_OVERRIDE_MAX_SESSIONS=true \
    --shm-size=2g \
    selenium/standalone-chrome:latest

# Wait for Selenium to be ready
echo "⏳ Waiting for Selenium to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:4444/wd/hub/status > /dev/null 2>&1; then
        echo "✅ Selenium is ready!"
        echo "🌐 Selenium WebDriver available at: http://localhost:4444/wd/hub"
        echo "🖥️  VNC viewer available at: http://localhost:7900 (password: secret)"
        echo ""
        echo "📝 To use with GameManager, set these environment variables:"
        echo "   export SELENIUM_HOST=localhost"
        echo "   export SELENIUM_PORT=4444"
        echo ""
        echo "🛑 To stop Selenium: docker stop gamemanager-selenium"
        echo "🗑️  To remove Selenium: docker rm gamemanager-selenium"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo "❌ Selenium failed to start within 60 seconds"
echo "🔍 Check logs with: docker logs gamemanager-selenium"
exit 1