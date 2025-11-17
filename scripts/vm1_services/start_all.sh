#!/bin/bash

# VM1 - Start All API Services
# Runs on API server with ports 9000-9002

echo "🚀 Starting All API Services (VM1)"
echo "===================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS - Opening in separate Terminal tabs..."
    
    # Search API - Port 9001
    osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python3 scripts/vm1_services/start_search_api.py\""
    
    # Property API - Port 9002
    osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT' && ./scripts/vm1_services/start_property_api.sh\""
    
    # Report API - Port 9003
    osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT/services/report_api' && ./start_api.sh\""
    
    echo "✅ All APIs started in separate Terminal tabs!"
    
else
    echo "🐧 Detected Linux - Starting in background..."
    
    # Start each API in the background
    cd "$PROJECT_ROOT" && python3 scripts/vm1_services/start_search_api.py &
    PID_SEARCH=$!
    
    cd "$PROJECT_ROOT" && ./scripts/vm1_services/start_property_api.sh &
    PID_PROPERTY=$!
    
    cd "$PROJECT_ROOT/services/report_api" && ./start_api.sh &
    PID_REPORT=$!
    
    echo "✅ All APIs started in background!"
    echo ""
    echo "Process IDs:"
    echo "  Search API:     $PID_SEARCH"
    echo "  Property API:   $PID_PROPERTY"
    echo "  Report API:     $PID_REPORT"
    echo ""
    echo "To stop all services, run:"
    echo "  kill $PID_SEARCH $PID_PROPERTY $PID_REPORT"
fi

echo ""
    echo "API Endpoints:"
    echo "  🗺️  Martin Tile Server:  http://localhost:9000"
    echo "  🔍 Search API:          http://localhost:9001"
    echo "  📋 Property API:        http://localhost:9002"
    echo "  📊 Report API:          http://localhost:9003"

