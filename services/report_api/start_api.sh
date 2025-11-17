#!/bin/bash

# Report API Startup Script
# This script starts the Report API with proper environment setup

echo "🚀 Starting Report API..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to the report_api directory
cd "$PROJECT_ROOT/services/report_api"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found in services/report_api/"
    exit 1
fi

# Use project root venv if it exists, otherwise create one in service directory
PROJECT_ROOT="$(cd "$(dirname "$SCRIPT_DIR")/../.." && pwd)"
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "🔧 Activating project root virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
elif [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if port 9003 is available
if lsof -Pi :9003 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Warning: Port 9003 is already in use."
    echo "   The API might already be running or another service is using the port."
    echo "   You can access the API at: http://localhost:9003"
    echo "   Or stop the existing service and restart."
    exit 1
fi

# Start the API
echo "🌟 Starting API server on port 9003..."
echo "📖 API Documentation will be available at: http://localhost:9003/docs"
echo "🔗 API will be available at: http://localhost:9003"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py

