#!/bin/bash

# VM2 - Start Bulk Collector
# Heavy processing pipeline that collects data for all parcels

echo "🚀 Starting Bulk Collector Pipeline (VM2)"
echo "=========================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT/pipelines/bulk_collector"

echo "📁 Working directory: $(pwd)"
echo ""
echo "Starting bulk collection..."
echo "Press Ctrl+C to stop"
echo ""

# Run the bulk collector
python3 main.py "$@"









