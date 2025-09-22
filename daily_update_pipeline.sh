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
PMTILES_DIR="$SCRIPT_DIR/PMTiles_Cycle"
SEARCH_API_DIR="$SCRIPT_DIR/search_api"
TILES_BASE_DIR="$HOME/tiles"
MARTIN_CONFIG="$PMTILES_DIR/martin_config.yaml"
LOG_FILE="$SCRIPT_DIR/daily_update.log"

# Email configuration - UPDATE THESE VALUES
EMAIL_TO="your-personal-gmail@gmail.com"      # Change this to your Gmail
EMAIL_FROM="your-personal-gmail@gmail.com"    # Change this to your Gmail  
SMTP_USER="your-personal-gmail@gmail.com"     # Your Gmail for authentication
SMTP_PASS="your-weird-password-thing"        # Your Gmail app password

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TILES_RUN_DIR="$TILES_BASE_DIR/runs/$TIMESTAMP"
LATEST_SYMLINK="$TILES_BASE_DIR/latest"

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
    source "$SCRIPT_DIR/venv/bin/activate" || {
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
    
    # Start new Martin server with updated tiles
    cd "$TILES_BASE_DIR"
    nohup martin combined_ownership.pmtiles --listen-addresses 0.0.0.0:3000 --webui enable-for-all > "$SCRIPT_DIR/martin.log" 2>&1 &
    
    # Wait for server to start
    sleep 5
    
    # Verify server is running
    if pgrep -f "martin" > /dev/null; then
        log "✅ Martin server restarted successfully with new tiles"
    else
        error "Failed to restart Martin server"
    fi
}

# Function to reload search API
reload_search_api() {
    log "🔄 Reloading search API..."
    
    # Check if search API is running
    if pgrep -f "start_api.py" > /dev/null; then
        # Send reload request to the API
        if curl -s -X POST "http://localhost:8000/reload" > /dev/null; then
            log "✅ Search API reloaded successfully"
        else
            warning "Could not reload search API via HTTP - may need manual restart"
        fi
    else
        warning "Search API is not running - will need manual restart to load new index"
    fi
}

# Function to clean up old runs
cleanup_old_runs() {
    log "🧹 Cleaning up old tile runs..."
    
    # Keep only the last 5 runs
    cd "$TILES_BASE_DIR/runs" || return
    
    # List all runs sorted by modification time, keep only the 5 most recent
    ls -1t | tail -n +6 | while read -r old_run; do
        if [ -n "$old_run" ]; then
            log "🗑️  Removing old run: $old_run"
            rm -rf "$old_run"
        fi
    done
    
    log "✅ Cleanup completed"
}

# Function to check Martin server health
check_martin_health() {
    local max_retries=5
    local retry_count=0
    
    log "🔍 Checking Martin server health..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "http://localhost:3000/health" > /dev/null 2>&1; then
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
    
    log " Checking Search API health..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
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

# Function to get detailed health status
get_health_status() {
    local health_output=""
    
    # Check Martin server
    log "📊 Gathering Martin server status..."
    if curl -s -f "http://localhost:3000/health" > /dev/null 2>&1; then
        health_output+="\n✅ Martin Server (Tiles):\n"
        health_output+="$(curl -s "http://localhost:3000/health" 2>/dev/null || echo "Health endpoint not available")\n"
    else
        health_output+="\n❌ Martin Server (Tiles): Not responding\n"
    fi
    
    # Check Search API
    log "📊 Gathering Search API status..."
    if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
        health_output+="\n✅ Search API:\n"
        health_output+="$(curl -s "http://localhost:8000/health" 2>/dev/null || echo "Health endpoint not available")\n"
        
        # Also get stats if available
        if curl -s -f "http://localhost:8000/stats" > /dev/null 2>&1; then
            health_output+="\n�� Search API Stats:\n"
            health_output+="$(curl -s "http://localhost:8000/stats" 2>/dev/null || echo "Stats endpoint not available")\n"
        fi
    else
        health_output+="\n❌ Search API: Not responding\n"
    fi
    
    echo -e "$health_output"
}

# Main execution
main() {
    START_TIME=$(date +%s)  # Record start time for duration calculation
    local pipeline_status="success"
    local error_message=""
    
    log "🚀 Starting daily update pipeline at $TIMESTAMP"
    
    # Create necessary directories
    mkdir -p "$TILES_RUN_DIR"
    mkdir -p "$TILES_BASE_DIR/runs"
    
    # Change to PMTiles directory
    cd "$PMTILES_DIR" || {
        pipeline_status="error"
        error_message="Could not change to PMTiles directory"
        error "$error_message"
    }
    
    # Step 1: Run PMTiles pipeline
    log "📥 Step 1: Running PMTiles pipeline..."
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate" || {
        pipeline_status="error"
        error_message="Could not activate virtual environment"
        error "$error_message"
    }
    
    # Run the ownership pipeline for all counties
    log "🔄 Running ownership pipeline for all counties..."
    if python main.py --ownership --skip-data; then
        log "✅ PMTiles pipeline completed successfully"
    else
        pipeline_status="error"
        error_message="PMTiles pipeline failed"
        error "$error_message"
    fi
    
    # Step 2: Organize new tiles
    log "📁 Step 2: Organizing new tiles..."
    
    # Move new tiles to timestamped directory
    if [ -f "$TILES_BASE_DIR/combined_ownership.pmtiles" ]; then
        cp "$TILES_BASE_DIR/combined_ownership.pmtiles" "$TILES_RUN_DIR/"
        log "✅ Copied combined_ownership.pmtiles to $TILES_RUN_DIR"
    fi
    
    # Copy individual county tiles if they exist
    for county_file in "$TILES_BASE_DIR"/*_ownership.pmtiles; do
        if [ -f "$county_file" ] && [ "$(basename "$county_file")" != "combined_ownership.pmtiles" ]; then
            cp "$county_file" "$TILES_RUN_DIR/"
            log "✅ Copied $(basename "$county_file") to $TILES_RUN_DIR"
        fi
    done
    
    # Update symlink to point to latest
    if [ -L "$LATEST_SYMLINK" ]; then
        rm "$LATEST_SYMLINK"
    fi
    ln -sf "$TILES_RUN_DIR" "$LATEST_SYMLINK"
    log "✅ Updated symlink: $LATEST_SYMLINK -> $TILES_RUN_DIR"
    
    # Step 3: Update Martin config
    log "⚙️  Step 3: Updating Martin configuration..."
    
    # Backup current config
    cp "$MARTIN_CONFIG" "$MARTIN_CONFIG.backup.$TIMESTAMP"
    
    # Update config to point to latest tiles
    cat > "$MARTIN_CONFIG" << EOF
pmtiles:
  sources:
    combined_ownership: $LATEST_SYMLINK/combined_ownership.pmtiles
EOF
    
    log "✅ Martin config updated to point to latest tiles"
    
    # Step 4: Reload Martin server
    log "⚙️ Step 4: Restarting Martin server..."
    restart_martin_server
    
    # Health check Martin server
    if check_martin_health; then
        log "✅ Martin server is healthy"
    else
        warning "⚠️ Martin server health check failed"
    fi
    
    # Step 5: Regenerate search index
    log "🔍 Step 5: Regenerating search index..."
    
    cd "$SEARCH_API_DIR" || {
        pipeline_status="error"
        error_message="Could not change to search API directory"
        error "$error_message"
    }
    
    # Activate virtual environment again
    source "$SCRIPT_DIR/venv/bin/activate" || {
        pipeline_status="error"
        error_message="Could not activate virtual environment"
        error "$error_message"
    }
    
    # Generate new search index
    if python search_file_generator.py; then
        log "✅ Search index regenerated successfully"
    else
        pipeline_status="error"
        error_message="Search index generation failed"
        error "$error_message"
    fi
    
    # Step 6: Reload search API
    log " Step 6: Reloading search API..."
    reload_search_api
    
    # Health check Search API
    if check_search_api_health; then
        log "✅ Search API is healthy"
    else
        warning "⚠️ Search API health check failed"
    fi
    
    # Step 7: Cleanup old runs
    cleanup_old_runs
    
    # Calculate duration
    DURATION=$(($(date +%s) - START_TIME))
    
    # Gather health status for email
    log "📊 Gathering final health status..."
    HEALTH_STATUS=$(get_health_status)
    
    # Final status
    log "🎉 Daily update pipeline completed successfully!"
    log "📊 Summary:"
    log "   - New tiles generated in: $TILES_RUN_DIR"
    log "   - Latest symlink: $LATEST_SYMLINK"
    log "   - Martin config updated"
    log "   - Search index regenerated"
    log "   - Old runs cleaned up"
    
    # Show disk usage
    log "💾 Disk usage for tiles:"
    DISK_USAGE=$(du -sh "$TILES_BASE_DIR" | cut -f1)
    du -sh "$TILES_BASE_DIR" | tee -a "$LOG_FILE"
    
    log "✅ Daily update pipeline completed at $(date)"
    
    # Send success email notification with health status
    send_email_notification "success" "$DURATION '$TILES_RUN_DIR' '$LATEST_SYMLINK' '$DISK_USAGE' '$HEALTH_STATUS'"
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
