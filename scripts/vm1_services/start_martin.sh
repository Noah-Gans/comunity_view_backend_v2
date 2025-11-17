#!/bin/bash

# Start Martin Tile Server on port 9000

echo "🗺️  Starting Martin Tile Server..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Check if martin_config.yaml exists
if [ ! -f "martin_config.yaml" ]; then
    echo "❌ Error: martin_config.yaml not found in project root"
    exit 1
fi

# Check if port 9000 is available
if ss -tlnp | grep -q ":9000 "; then
    echo "⚠️  Warning: Port 9000 is already in use."
    echo "   Stopping existing service..."
    pkill -f "martin.*9000" 2>/dev/null
    sleep 2
fi

# Stop any old Martin instances on port 3000
if ss -tlnp | grep -q ":3000 "; then
    echo "🛑 Stopping old Martin server on port 3000..."
    pkill -f "martin.*3000" 2>/dev/null
    sleep 2
fi

# Start Martin on port 9000
echo "🌟 Starting Martin Tile Server on port 9000..."
echo "📖 Config: martin_config.yaml"
echo "🔗 Server will be available at: http://localhost:9000"
echo ""

martin --config martin_config.yaml --listen-addresses 0.0.0.0:9000

