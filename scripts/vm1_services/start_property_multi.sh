#!/bin/bash

# Start multiple Property API instances for load balancing
# Uses ports 9011, 9012, 9013

echo "🚀 Starting Multiple Property API Instances (Load Balanced)"
echo "==========================================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT/services/property_api"

echo "📁 Working directory: $(pwd)"
echo ""
echo "Starting 3 instances on ports 9011, 9012, 9013..."
echo "Press Ctrl+C to stop all instances"
echo ""

# Run the multiple instance script
python3 "$SCRIPT_DIR/start_property_multi.py"

