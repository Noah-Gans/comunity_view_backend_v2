#!/bin/bash

# VM1 - Stop All API Services

echo "🛑 Stopping All API Services..."

# Kill processes on ports 9000-9003
lsof -ti :9000 | xargs kill 2>/dev/null && echo "✅ Stopped Martin Tile Server (9000)"
lsof -ti :9001 | xargs kill 2>/dev/null && echo "✅ Stopped Search API (9001)"
lsof -ti :9002 | xargs kill 2>/dev/null && echo "✅ Stopped Property API (9002)"
lsof -ti :9003 | xargs kill 2>/dev/null && echo "✅ Stopped Report API (9003)"

echo ""
echo "✅ All services stopped!"

