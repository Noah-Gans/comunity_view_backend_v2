#!/bin/bash

# Daily Update Pipeline for Martin Server Backend
# This script runs the complete daily update process:
# 1. Run PMTiles pipeline to download data and generate tiles
# 2. Update Martin server with new PMTiles
# 3. Regenerate search index and reload search API
# 4. Clean up old files

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PMTILES_DIR="$SCRIPT_DIR/PMTiles_Cycle"
SEARCH_API_DIR="$SCRIPT_DIR/search_api"
TILES_BASE_DIR="$HOME/tiles"
MARTIN_CONFIG="$PMTILES_DIR/martin_config.yaml"
LOG_FILE="$SCRIPT_DIR/daily_update.log"

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

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
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
reload_martin_server() {
    if check_martin_server; then
        log "🔄 Reloading Martin server..."
        # Send SIGHUP to reload configuration
        pkill -HUP -f "martin" || warning "Could not send SIGHUP to Martin server"
        sleep 2
        
        if check_martin_server; then
            log "✅ Martin server reloaded successfully"
        else
            warning "Martin server may not have reloaded properly"
        fi
    else
        warning "Martin server is not running - new tiles will be available on next restart"
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

# Main execution
main() {
    log "🚀 Starting daily update pipeline at $TIMESTAMP"
    
    # Create necessary directories
    mkdir -p "$TILES_RUN_DIR"
    mkdir -p "$TILES_BASE_DIR/runs"
    
    # Change to PMTiles directory
    cd "$PMTILES_DIR" || error "Could not change to PMTiles directory"
    
    # Step 1: Run PMTiles pipeline
    log "📥 Step 1: Running PMTiles pipeline..."
    
    # Activate virtual environment
    source "$SCRIPT_DIR/venv/bin/activate" || error "Could not activate virtual environment"
    
    # Run the ownership pipeline for all counties
    log "🔄 Running ownership pipeline for all counties..."
    if python main.py --ownership --generate-pmtiles; then
        log "✅ PMTiles pipeline completed successfully"
    else
        error "PMTiles pipeline failed"
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
    log "🔄 Step 4: Reloading Martin server..."
    reload_martin_server
    
    # Step 5: Regenerate search index
    log "🔍 Step 5: Regenerating search index..."
    
    cd "$SEARCH_API_DIR" || error "Could not change to search API directory"
    
    # Activate virtual environment again
    source "$SCRIPT_DIR/venv/bin/activate" || error "Could not activate virtual environment"
    
    # Generate new search index
    if python search_file_generator.py; then
        log "✅ Search index regenerated successfully"
    else
        error "Search index generation failed"
    fi
    
    # Step 6: Reload search API
    log "🔄 Step 6: Reloading search API..."
    reload_search_api
    
    # Step 7: Cleanup old runs
    cleanup_old_runs
    
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
    du -sh "$TILES_BASE_DIR" | tee -a "$LOG_FILE"
    
    log "✅ Daily update pipeline completed at $(date)"
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
