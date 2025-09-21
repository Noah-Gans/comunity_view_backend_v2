#!/bin/bash

# Property Info API Startup Script
# This script starts the Property Info API with proper environment setup

echo "🚀 Starting Property Info API..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the property_info_api directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if port 8001 is available
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Warning: Port 8001 is already in use."
    echo "   The API might already be running or another service is using the port."
    echo "   You can access the API at: http://localhost:8001"
    echo "   Or stop the existing service and restart."
    exit 1
fi

# Start the API
echo "🌟 Starting API server on port 8001..."
echo "📖 API Documentation will be available at: http://localhost:8001/docs"
echo "🔗 API will be available at: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
