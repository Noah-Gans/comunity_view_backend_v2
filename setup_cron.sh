#!/bin/bash

# Setup script for daily update cron job
# This script sets up a cron job to run the daily update pipeline at 2 AM daily

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_JOB="0 2 * * * cd $SCRIPT_DIR && ./daily_update_pipeline.sh >> $SCRIPT_DIR/cron.log 2>&1"

echo "🚀 Setting up daily update cron job..."
echo "📁 Script directory: $SCRIPT_DIR"
echo "⏰ Cron schedule: 2:00 AM daily"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "daily_update_pipeline.sh"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "daily_update_pipeline.sh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job added successfully!"
echo ""
echo "📋 Current cron jobs:"
crontab -l
echo ""
echo "🔧 To manually run the pipeline:"
echo "   cd $SCRIPT_DIR && ./daily_update_pipeline.sh"
echo ""
echo "📝 To view logs:"
echo "   tail -f $SCRIPT_DIR/daily_update.log"
echo "   tail -f $SCRIPT_DIR/cron.log"
echo ""
echo "❌ To remove the cron job:"
echo "   crontab -e"
echo "   (then delete the line with daily_update_pipeline.sh)"
