#!/bin/bash

# VM1 - Stop All API Services

echo "🛑 Stopping All API Services..."

# Stop screen sessions
screen -S search_api -X quit 2>/dev/null && echo "✅ Stopped Search API screen session"
screen -S property_api -X quit 2>/dev/null && echo "✅ Stopped Property API screen session"
screen -S report_api -X quit 2>/dev/null && echo "✅ Stopped Report API screen session"

# Kill processes on ports (using ss if lsof not available)
if command -v lsof &> /dev/null; then
    lsof -ti :9000 | xargs kill 2>/dev/null && echo "✅ Stopped Martin Tile Server (9000)"
    lsof -ti :9001 | xargs kill 2>/dev/null && echo "✅ Stopped Search API (9001)"
    lsof -ti :9002 | xargs kill 2>/dev/null && echo "✅ Stopped Property API (9002)"
    lsof -ti :9003 | xargs kill 2>/dev/null && echo "✅ Stopped Report API (9003)"
    lsof -ti :9011 | xargs kill 2>/dev/null && echo "✅ Stopped Property API instance (9011)"
    lsof -ti :9012 | xargs kill 2>/dev/null && echo "✅ Stopped Property API instance (9012)"
    lsof -ti :9013 | xargs kill 2>/dev/null && echo "✅ Stopped Property API instance (9013)"
    lsof -ti :9021 | xargs kill 2>/dev/null && echo "✅ Stopped Report API instance (9021)"
    lsof -ti :9022 | xargs kill 2>/dev/null && echo "✅ Stopped Report API instance (9022)"
    lsof -ti :9023 | xargs kill 2>/dev/null && echo "✅ Stopped Report API instance (9023)"
else
    # Fallback using pkill
    pkill -f "start_search_api.py" 2>/dev/null && echo "✅ Stopped Search API"
    pkill -f "start_property" 2>/dev/null && echo "✅ Stopped Property API instances"
    pkill -f "start_report" 2>/dev/null && echo "✅ Stopped Report API instances"
fi

echo ""
echo "✅ All services stopped!"

