#!/bin/bash

# VM1 - Start All API Services with Load Balancing
# Starts Search API (single), Property API (3 instances), Report API (3 instances)

echo "🚀 Starting All API Services with Load Balancing (VM1)"
echo "========================================================"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Stop any existing services first
echo "🛑 Stopping any existing services..."
screen -S search_api -X quit 2>/dev/null
screen -S property_api -X quit 2>/dev/null
screen -S report_api -X quit 2>/dev/null
pkill -f "start_search_api.py" 2>/dev/null
pkill -f "start_property_multi" 2>/dev/null
pkill -f "start_report_multi" 2>/dev/null

sleep 2

# Start Martin Tile Server (port 9000) - only if PMTiles file exists
PMTILES_FILE=$(grep -A 5 "pmtiles:" "$PROJECT_ROOT/martin_config.yaml" 2>/dev/null | grep "combined_ownership" | awk '{print $2}' | tr -d '"' || echo "tiles/combined_ownership.pmtiles")
if [ -f "$PROJECT_ROOT/$PMTILES_FILE" ]; then
    echo "🗺️  Starting Martin Tile Server (port 9000)..."
    screen -S martin -d -m bash -c "cd '$PROJECT_ROOT' && ./scripts/vm1_services/start_martin.sh"
else
    echo "⚠️  Skipping Martin Tile Server - PMTiles file not found: $PMTILES_FILE"
    echo "   Generate PMTiles first, then start Martin separately."
fi

# Start Search API (single instance on port 9001)
echo "🔍 Starting Search API (port 9001)..."
screen -S search_api -d -m bash -c "cd '$PROJECT_ROOT' && source venv/bin/activate && python3 scripts/vm1_services/start_search_api.py"

# Start Property API (3 instances on ports 9011, 9012, 9013)
echo "📋 Starting Property API - Load Balanced (ports 9011, 9012, 9013)..."
screen -S property_api -d -m bash -c "cd '$PROJECT_ROOT' && source venv/bin/activate && ./scripts/vm1_services/start_property_multi.sh"

# Start Report API (3 instances on ports 9021, 9022, 9023)
echo "📊 Starting Report API - Load Balanced (ports 9021, 9022, 9023)..."
screen -S report_api -d -m bash -c "cd '$PROJECT_ROOT' && source venv/bin/activate && ./scripts/vm1_services/start_report_multi.sh"

sleep 3

echo ""
echo "✅ All services started!"
echo ""
echo "Screen Sessions:"
screen -ls
echo ""
echo "API Endpoints:"
echo "  🗺️  Martin Tile Server:  http://localhost:9000"
echo "  🔍 Search API:          http://localhost:9001"
echo "  📋 Property API (LB):   http://localhost:9011, 9012, 9013"
echo "  📊 Report API (LB):     http://localhost:9021, 9022, 9023"
echo ""
echo "To view logs:"
echo "  screen -r search_api"
echo "  screen -r property_api"
echo "  screen -r report_api"
echo ""
echo "To stop all services:"
echo "  ./scripts/vm1_services/stop_all.sh"

