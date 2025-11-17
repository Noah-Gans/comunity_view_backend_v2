#!/bin/bash
# Setup script for Teton County Idaho data download automation

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create a cron job to run the download script every night at 2 AM
CRON_JOB="0 2 * * * cd $SCRIPT_DIR && python3 download_and_process.py >> teton_download_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "download_and_process.py"; then
    echo "Cron job already exists. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "download_and_process.py" | crontab -
fi

# Add the new cron job
echo "Adding cron job to run every night at 2 AM..."
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job setup complete!"
echo "The script will run every night at 2 AM"
echo "Logs will be written to: $SCRIPT_DIR/teton_download_cron.log"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove cron job: crontab -r"
echo ""
echo "To test the script manually:"
echo "cd $SCRIPT_DIR && python3 download_and_process.py" 