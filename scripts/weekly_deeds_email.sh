#!/bin/bash

set -e

# Weekly Deeds Email Runner
# Loads SMTP creds from environment or falls back to daily_update_pipeline.sh settings if available

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load SMTP/email vars from daily_update_pipeline.sh (lines 24-27) if not already set
if [[ -z "$SMTP_USER" || -z "$SMTP_PASS" || -z "$SMTP_FROM" || -z "$EMAIL_TO" ]]; then
  CFG_FILE="$SCRIPT_DIR/daily_update_pipeline.sh"
  if [[ -f "$CFG_FILE" ]]; then
    # Extract values safely without executing the script
    EMAIL_TO_VAL=$(awk -F'"' '/^EMAIL_TO=/ {print $2}' "$CFG_FILE")
    EMAIL_FROM_VAL=$(awk -F'"' '/^EMAIL_FROM=/ {print $2}' "$CFG_FILE")
    SMTP_USER_VAL=$(awk -F'"' '/^SMTP_USER=/ {print $2}' "$CFG_FILE")
    SMTP_PASS_VAL=$(awk -F'"' '/^SMTP_PASS=/ {print $2}' "$CFG_FILE")

    [[ -z "$EMAIL_TO" && -n "$EMAIL_TO_VAL" ]] && export EMAIL_TO="$EMAIL_TO_VAL"
    [[ -z "$SMTP_FROM" && -n "$EMAIL_FROM_VAL" ]] && export SMTP_FROM="$EMAIL_FROM_VAL"
    [[ -z "$SMTP_USER" && -n "$SMTP_USER_VAL" ]] && export SMTP_USER="$SMTP_USER_VAL"
    [[ -z "$SMTP_PASS" && -n "$SMTP_PASS_VAL" ]] && export SMTP_PASS="$SMTP_PASS_VAL"
  fi
fi

# Set map base URL (defaults to localhost, but should be production URL for email links)
# Webmail clients (Gmail, Outlook web) cannot access localhost links due to browser security
# Set MAP_BASE_URL to your production frontend URL, e.g.:
#   export MAP_BASE_URL="https://yourdomain.com"
# Or uncomment and set below:
# MAP_BASE_URL="https://yourdomain.com"

if [[ -z "$MAP_BASE_URL" ]]; then
  export MAP_BASE_URL="http://localhost:3000"
fi

# Activate venv if present
if [[ -d "$PROJECT_ROOT/venv" ]]; then
  source "$PROJECT_ROOT/venv/bin/activate"
fi

python3 "$PROJECT_ROOT/services/notifications/weekly_deeds_email.py"

echo "Weekly deeds email script completed."


