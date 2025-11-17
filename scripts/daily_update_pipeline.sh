#!/bin/bash

# Daily Update Pipeline for Martin Server Backend
# This script runs the complete daily update process:
# 1. Run PMTiles pipeline to download data and generate tiles
# 2. Update Martin server with new PMTiles
# 3. Regenerate search index and reload search API
# 4. Clean up old files
# 5. Send email notification

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PMTILES_DIR="$PROJECT_ROOT/pipelines/pmtiles"
SEARCH_API_DIR="$PROJECT_ROOT/services/search_api"
TILES_DIR="$PROJECT_ROOT/tiles"
MARTIN_PM_TILES_RELATIVE="tiles/combined_ownership.pmtiles"
MARTIN_CONFIG="$PROJECT_ROOT/martin_config.yaml"
MARTIN_CONFIG_BACKUP_DIR="$PROJECT_ROOT/backups/martin"
LOG_FILE="$SCRIPT_DIR/daily_update.log"
VALIDATION_REPORT="$PMTILES_DIR/validation_report.txt"

# Email configuration - Backend email credentials
EMAIL_TO="noahgans@tetoncountygis.com"        # Recipient email
EMAIL_FROM="noahgans@tetoncountygis.com"      # Sender email  
SMTP_USER="noahgans@tetoncountygis.com"       # SMTP authentication user
SMTP_PASS="stvk ynra ssnl clov"               # SMTP app password

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Email notification function using Python script
send_email_notification() {
    local notification_type="$1"
    local additional_args="$2"
    
    # Check if email is configured
    if [[ "$EMAIL_TO" == "your-email@gmail.com" ]]; then
        warning "Email not configured - skipping email notification"
        return 0
    fi
    
    # Check if Python script exists
    if [[ ! -f "$SCRIPT_DIR/send_notification.py" ]]; then
        warning "Email script not found at $SCRIPT_DIR/send_notification.py"
        return 0
    fi
    
    # Activate virtual environment and run email script
    source "$PROJECT_ROOT/venv/bin/activate" || {
        warning "Could not activate virtual environment for email"
        return 0
    }
    
    log "📧 Sending $notification_type notification..."
    
    # Run the Python email script
    if python3 "$SCRIPT_DIR/send_notification.py" "$notification_type" "$EMAIL_TO" "$EMAIL_FROM" "$SMTP_USER" "$SMTP_PASS" "$LOG_FILE" $additional_args; then
        log "✅ Email notification sent successfully"
    else
        warning "Failed to send email notification"
    fi
}

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Enhanced error function with email notification
error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    
    # Calculate duration
    DURATION=$(($(date +%s) - START_TIME))
    
    # Send error email notification
    send_email_notification "error" "'$1' $DURATION"
    
    exit 1
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Martin server is running
check_martin_server() {
    if pgrep -f "martin" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to reload Martin server
restart_martin_server() {
    log "🔄 Restarting Martin server with new tiles..."
    
    # Stop existing Martin server
    pkill -f "martin" || log "No existing Martin server found"
    sleep 2
    
    # Start new Martin server with config file
    cd "$PROJECT_ROOT"
    nohup martin --config "$MARTIN_CONFIG" --listen-addresses 0.0.0.0:9000 > "$SCRIPT_DIR/martin.log" 2>&1 &
    
    # Wait for server to start
    sleep 5
    
    # Verify server is running
    if pgrep -f "martin" > /dev/null; then
        log "✅ Martin server restarted successfully with new tiles"
    else
        error "Failed to restart Martin server"
    fi
}

# Function to restart search API (ensures new index is loaded)
restart_search_api() {
    log "🔄 Restarting Search API to load new index..."
    
    # Stop existing Search API if running
    if pgrep -f "uvicorn.*app:app" > /dev/null; then
        log "🛑 Stopping existing Search API..."
        pkill -f "uvicorn.*app:app"
        sleep 3
        if pgrep -f "uvicorn.*app:app" > /dev/null; then
            warning "⚠️ Search API still running after stop command"
            pkill -9 -f "uvicorn.*app:app" 2>/dev/null || true
            sleep 2
        fi
    else
        log "📭 No existing Search API found"
    fi
    
    # Start Search API with new index
    cd "$SEARCH_API_DIR"
    log "🚀 Starting Search API on port 9001..."
    nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 9001 > "$SCRIPT_DIR/search_api.log" 2>&1 &
    SEARCH_PID=$!
    
    # Wait for server to start with better feedback
    log "⏳ Waiting for Search API to start..."
    for i in {1..10}; do
        sleep 1
        if pgrep -f "uvicorn.*app:app" > /dev/null; then
            log "✅ Search API started successfully (PID: $SEARCH_PID)"
            return 0
        fi
        echo -n "."
    done
    echo ""
    
    warning "⚠️ Search API may not have started properly (check search_api.log)"
    return 1
}


# Function to check Martin server health
check_martin_health() {
    local max_retries=5
    local retry_count=0
    
    log "🔍 Checking Martin server health..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "http://localhost:9000/health" > /dev/null 2>&1; then
            log "✅ Martin server health check passed"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "⏳ Martin health check attempt $retry_count/$max_retries failed, retrying in 3 seconds..."
            sleep 3
        fi
    done
    
    warning "❌ Martin server health check failed after $max_retries attempts"
    return 1
}

# Function to check Search API health
check_search_api_health() {
    local max_retries=5
    local retry_count=0
    
    log "🔍 Checking Search API health..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "http://localhost:9001/health" > /dev/null 2>&1; then
            log "✅ Search API health check passed"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "⏳ Search API health check attempt $retry_count/$max_retries failed, retrying in 3 seconds..."
            sleep 3
        fi
    done
    
    warning "❌ Search API health check failed after $max_retries attempts"
    return 1
}

# Function to test Martin tile server
test_martin_tiles() {
    log "🧪 Testing Martin tile server..."
    
    local tile_test=""
    
    # Test catalog endpoint
    if curl -s -f "http://localhost:9000/catalog" > /dev/null 2>&1; then
        tile_test+="✅ Martin Catalog: Responding\n"
        
        # Test actual tile request
        if curl -s -f "http://localhost:9000/tiles/combined_ownership/6/24/46" > /dev/null 2>&1; then
            tile_test+="✅ Martin Tiles: Serving tiles successfully\n"
        else
            tile_test+="❌ Martin Tiles: Failed to serve tiles\n"
        fi
    else
        tile_test+="❌ Martin Catalog: Not responding\n"
    fi
    
    echo -e "$tile_test"
}

# Function to perform comprehensive health checks
perform_health_checks() {
    log "🔍 Performing comprehensive health checks..."
    
    local health_results=""
    
    # Martin server health
    health_results+="\n=== MARTIN SERVER ===\n"
    if curl -s -f "http://localhost:9000/health" > /dev/null 2>&1; then
        health_results+="✅ Health endpoint: Responding\n"
        health_results+="$(curl -s "http://localhost:9000/health" 2>/dev/null || echo "Health data unavailable")\n"
    else
        health_results+="❌ Health endpoint: Not responding\n"
    fi
    
    # Martin tile testing
    health_results+="\n=== MARTIN TILES ===\n"
    health_results+="$(test_martin_tiles)"
    
    # Search API health
    health_results+="\n=== SEARCH API ===\n"
    if curl -s -f "http://localhost:9001/health" > /dev/null 2>&1; then
        health_results+="✅ Health endpoint: Responding\n"
        health_results+="$(curl -s "http://localhost:9001/health" 2>/dev/null || echo "Health data unavailable")\n"
        
        # Search API stats
        if curl -s -f "http://localhost:9001/stats" > /dev/null 2>&1; then
            health_results+="\n📊 Search API Stats:\n"
            health_results+="$(curl -s "http://localhost:9001/stats" 2>/dev/null || echo "Stats unavailable")\n"
        fi
        
        # Test search functionality
        health_results+="\n🔍 Search Test:\n"
        local search_test=$(curl -s "http://localhost:9001/search?q=test" 2>/dev/null || echo "Search test failed")
        if echo "$search_test" | grep -q "total_results"; then
            health_results+="✅ Search functionality: Working\n"
        else
            health_results+="❌ Search functionality: Failed\n"
        fi
    else
        health_results+="❌ Health endpoint: Not responding\n"
    fi
    
    echo -e "$health_results"
}

# Main execution
main() {
    START_TIME=$(date +%s)  # Record start time for duration calculation
    local pipeline_status="success"
    local error_message=""
    
    log "🚀 Starting daily update pipeline at $TIMESTAMP"
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv/bin/activate" || {
        pipeline_status="error"
        error_message="Could not activate virtual environment"
        error "$error_message"
    }
    
    # Step 1: Run PMTiles pipeline (Process, Validate, Upload, Generate Tiles)
    log "📥 Step 1: Running PMTiles ownership pipeline..."
    
    cd "$PMTILES_DIR" || {
        pipeline_status="error"
        error_message="Could not change to PMTiles directory"
        error "$error_message"
    }
    
    # Run full pipeline with validation
    log "🔄 Running: process → validate → upload → generate-tiles"
    if python3 main.py  --process  --generate-tiles; then
        log "✅ PMTiles pipeline completed successfully"
        
        # Check validation report
        if [ -f "$VALIDATION_REPORT" ]; then
            log "📄 Validation Report:"
            cat "$VALIDATION_REPORT" | tee -a "$LOG_FILE"
        fi
    else
        pipeline_status="error"
        error_message="PMTiles pipeline failed or validation blocked deployment"
        
        # Attach validation report to error email
        if [ -f "$VALIDATION_REPORT" ]; then
            log "❌ Validation report indicates issues:"
            cat "$VALIDATION_REPORT" | tee -a "$LOG_FILE"
        fi
        
        error "$error_message"
    fi
    
    # Step 2: Backup old tiles and update Martin config
    log "📦 Step 2: Backing up old tiles and updating Martin config..."
    
    # Backup old tiles if they exist
    if [ -f "$TILES_DIR/combined_ownership.pmtiles" ]; then
        cp "$TILES_DIR/combined_ownership.pmtiles" "$TILES_DIR/combined_ownership.pmtiles.backup.$TIMESTAMP"
        log "✅ Backed up old tiles to: combined_ownership.pmtiles.backup.$TIMESTAMP"
        
        # Keep only last 3 tile backups to save space
        cd "$TILES_DIR"
        ls -1t combined_ownership.pmtiles.backup.* 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
    fi
    
    # Backup current config
    mkdir -p "$MARTIN_CONFIG_BACKUP_DIR"
    cp "$MARTIN_CONFIG" "$MARTIN_CONFIG_BACKUP_DIR/martin_config.yaml.backup.$TIMESTAMP"
    # Keep only last 5 config backups
    ls -1t "$MARTIN_CONFIG_BACKUP_DIR"/martin_config.yaml.backup.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    
    # Update config to point to new tiles location (and ensure CORS headers are enabled)
    cd "$PROJECT_ROOT"

    cat > "$MARTIN_CONFIG" << EOF
cors: true

pmtiles:
  sources:
    combined_ownership: $MARTIN_PM_TILES_RELATIVE
EOF
    
    log "✅ Martin config updated to: $TILES_DIR/combined_ownership.pmtiles"
    
    # Step 3: Reload Martin server
    log "⚙️ Step 3: Restarting Martin server..."
    restart_martin_server
    
    # Health check Martin server
    if check_martin_health; then
        log "✅ Martin server is healthy"
    else
        warning "⚠️ Martin server health check failed"
    fi
    
    # Step 4: Regenerate search index
    log "🔍 Step 4: Regenerating search index..."
    
    cd "$SEARCH_API_DIR" || {
        pipeline_status="error"
        error_message="Could not change to search API directory"
        error "$error_message"
    }
    
    # Generate new search index (venv already activated)
    if python3 search_file_generator.py; then
        log "✅ Search index regenerated successfully"
    else
        pipeline_status="error"
        error_message="Search index generation failed"
        error "$error_message"
    fi
    
    # Step 5: Restart search API to load new index
    log "🔄 Step 5: Restarting Search API to load new index..."
    if restart_search_api; then
        log "✅ Search API restart completed"
    else
        warning "⚠️ Search API restart had issues (check search_api.log)"
    fi
    
    # Health check Search API
    if check_search_api_health; then
        log "✅ Search API is healthy"
    else
        warning "⚠️ Search API health check failed"
    fi
    
    # Calculate duration
    DURATION=$(($(date +%s) - START_TIME))
    
    # Perform comprehensive health checks for email
    log "📊 Performing comprehensive health checks for email..."
    HEALTH_STATUS=$(perform_health_checks)
    
    # Final status
    log "🎉 Daily update pipeline completed successfully!"
    log "📊 Summary:"
    log "   - Tiles generated in: $TILES_DIR"
    log "   - Martin server: http://localhost:9000"
    log "   - Search API: http://localhost:9001"
    log "   - Config updated: $MARTIN_CONFIG"
    
    # Show disk usage
    log "💾 Disk usage for tiles:"
    DISK_USAGE=$(du -sh "$TILES_DIR" 2>/dev/null | cut -f1 || echo "N/A")
    
    log "✅ Daily update pipeline completed at $(date)"
    
    # Send success email notification with comprehensive health status and validation report
    VALIDATION_CONTENT=$(cat "$VALIDATION_REPORT" 2>/dev/null || echo "No validation report")
    send_email_notification "success" "$DURATION '$TILES_DIR' '$DISK_USAGE' '$HEALTH_STATUS' '$VALIDATION_CONTENT'"
}

# Error handling
trap 'error "Script failed at line $LINENO"' ERR

# Check prerequisites
if ! command_exists python3; then
    error "Python3 is not installed"
fi

if ! command_exists curl; then
    error "curl is not installed"
fi

# Run main function
main "$@"
