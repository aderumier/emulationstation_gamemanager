#!/bin/bash

# Game Collection Manager - Dependency Installation Script
# This script installs missing Python dependencies

echo "🔧 Installing Game Collection Manager dependencies..."

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install Python pip first."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt

# Check if pyrate_limiter is available (it's deployed locally)
if python3 -c "import sys; sys.path.insert(0, '.'); import pyrate_limiter; print('✅ Local pyrate_limiter found')" 2>/dev/null; then
    echo "✅ All dependencies installed successfully!"
    echo "✅ Local pyrate_limiter is available for IGDB rate limiting"
else
    echo "⚠️  Local pyrate_limiter not found. IGDB scraping will work without rate limiting."
fi

echo "🎉 Installation complete!"
