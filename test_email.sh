#!/bin/bash

# Email configuration - UPDATE THESE VALUES
EMAIL_TO="noahgans@tetoncountygis.com"
EMAIL_FROM="noahgans@tetoncountygis.com"
SMTP_USER="noahgans@tetoncountygis.com"
SMTP_PASS="stvk ynra ssnl clov"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧪 Testing email functionality..."
echo "📧 Sending test email to: $EMAIL_TO"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Test success email
echo "Testing success notification..."
python3 "$SCRIPT_DIR/send_notification.py" success "$EMAIL_TO" "$EMAIL_FROM" "$SMTP_USER" "$SMTP_PASS" "$SCRIPT_DIR/daily_update.log" 120 "/test/tiles" "/test/symlink" "50MB"

echo ""
echo "Testing error notification..."
python3 "$SCRIPT_DIR/send_notification.py" error "$EMAIL_TO" "$EMAIL_FROM" "$SMTP_USER" "$SMTP_PASS" "$SCRIPT_DIR/daily_update.log" "Test error message" 60

echo "✅ Email tests completed!"
