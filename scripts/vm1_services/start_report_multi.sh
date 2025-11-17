#!/bin/bash

# Start multiple Report API instances for load balancing
# Uses ports 9021, 9022, 9023

echo "🚀 Starting Multiple Report API Instances (Load Balanced)"
echo "==========================================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT/services/report_api"

echo "📁 Working directory: $(pwd)"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

echo "Starting 3 instances on ports 9021, 9022, 9023..."
echo "Press Ctrl+C to stop all instances"
echo ""

# Run the multiple instance script
python3 "$SCRIPT_DIR/start_report_multi.py"

