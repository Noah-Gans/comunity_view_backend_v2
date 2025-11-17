# Daily Update Pipeline for Martin Server Backend

## Overview

This system provides a complete automated daily update pipeline that:
1. **Downloads fresh data** from county sources
2. **Generates PMTiles** for the Martin tile server
3. **Updates Martin server** with new tiles
4. **Regenerates search index** with latest data
5. **Reloads search API** to serve fresh data

## How It Works

### Daily Schedule
- **Runs at 2:00 AM daily** via cron job
- **Complete pipeline** from data download to API reload
- **Automatic cleanup** of old tile files

### File Organization
```
~/tiles/
├── latest -> runs/20250812_020000/          # Symlink to current tiles
├── runs/                                    # Timestamped tile directories
│   ├── 20250812_020000/                     # Today's 2 AM run
│   │   ├── combined_ownership.pmtiles
│   │   └── teton_county_wy_ownership.pmtiles
│   ├── 20250811_020000/                     # Yesterday's run
│   └── 20250810_020000/                     # Day before
└── combined_ownership.pmtiles               # Working directory (gets copied)
```

## PMTiles Path Management

### The Problem
- **Old system**: PMTiles accumulated in same directory with same names
- **No versioning**: Couldn't track which tiles were current
- **Martin reload**: Server had to be restarted to see new tiles

### The Solution
1. **Timestamped directories**: Each run gets its own directory (`20250812_020000/`)
2. **Symlink management**: `~/tiles/latest` always points to current tiles
3. **Automatic config update**: Martin config updates to point to latest tiles
4. **Server reload**: Martin server reloads configuration (no restart needed)

### Martin Configuration
```yaml
# Before update
pmtiles:
  sources:
    combined_ownership: /Users/noahgans/tiles/combined_ownership.pmtiles

# After update (automatic)
pmtiles:
  sources:
    combined_ownership: /Users/noahgans/tiles/latest/combined_ownership.pmtiles
```

## Scripts

### 1. `daily_update_pipeline.sh` - Main Pipeline
**What it does:**
- Runs PMTiles pipeline (`main.py --ownership --generate-pmtiles`)
- Creates timestamped directory for new tiles
- Updates symlink to point to latest tiles
- Updates Martin configuration
- Reloads Martin server (SIGHUP)
- Regenerates search index
- Reloads search API
- Cleans up old runs (keeps last 5)

**Usage:**
```bash
./daily_update_pipeline.sh
```

### 2. `setup_cron.sh` - Cron Setup
**What it does:**
- Sets up cron job to run daily at 2:00 AM
- Removes any existing cron jobs for this script
- Shows current cron configuration

**Usage:**
```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

## Manual Operations

### Test the Pipeline
```bash
# Run the complete pipeline manually
./daily_update_pipeline.sh

# Check logs
tail -f daily_update.log
```

### Check Status
```bash
# View current tile structure
ls -la ~/tiles/
ls -la ~/tiles/latest/

# Check Martin server status
pgrep -f martin

# Check search API status
curl http://localhost:8000/health
```

### Emergency Operations
```bash
# Stop the pipeline if it's running
pkill -f "daily_update_pipeline.sh"

# Manually reload Martin server
pkill -HUP -f martin

# Manually reload search API
curl -X POST http://localhost:8000/reload

# Rollback to previous tiles
rm ~/tiles/latest
ln -sf ~/tiles/runs/PREVIOUS_TIMESTAMP ~/tiles/latest
```

## Logging

### Log Files
- **`daily_update.log`**: Main pipeline execution log
- **`cron.log`**: Cron job execution log (if errors occur)

### Log Monitoring
```bash
# Watch pipeline logs in real-time
tail -f daily_update.log

# Watch cron logs
tail -f cron.log

# Search for errors
grep "ERROR" daily_update.log
grep "WARNING" daily_update.log
```

## Troubleshooting

### Common Issues

#### 1. PMTiles Pipeline Fails
```bash
# Check PMTiles directory
cd PMTiles_Cycle
python main.py --ownership --generate-pmtiles

# Check for missing dependencies
pip install -r requirements.txt
```

#### 2. Martin Server Won't Reload
```bash
# Check if Martin is running
pgrep -f martin

# Check Martin config
cat PMTiles_Cycle/martin_config.yaml

# Manual reload
pkill -HUP -f martin
```

#### 3. Search API Issues
```bash
# Check if API is running
pgrep -f start_api.py

# Test API health
curl http://localhost:8000/health

# Regenerate search index manually
cd search_api
python search_file_generator.py
```

#### 4. Disk Space Issues
```bash
# Check disk usage
du -sh ~/tiles/

# Clean up old runs manually
rm -rf ~/tiles/runs/OLD_TIMESTAMP
```

### Recovery Procedures

#### Complete Reset
```bash
# Stop all services
pkill -f martin
pkill -f start_api.py

# Clean up tiles
rm -rf ~/tiles/runs/*
rm ~/tiles/latest

# Restart pipeline
./daily_update_pipeline.sh
```

## VM Deployment

### Prerequisites
1. **Python 3.9+** with virtual environment
2. **Martin server** installed and configured
3. **Cron** enabled
4. **Sufficient disk space** (at least 10GB for tiles)

### Setup Steps
1. **Copy files** to VM
2. **Install dependencies**:
   ```bash
   cd PMTiles_Cycle && pip install -r requirements.txt
   cd ../search_api && pip install -r requirements.txt
   ```
3. **Set up cron job**:
   ```bash
   chmod +x setup_cron.sh
   ./setup_cron.sh
   ```
4. **Test manually**:
   ```bash
   ./daily_update_pipeline.sh
   ```

### Monitoring
- **Check cron logs**: `tail -f cron.log`
- **Monitor disk usage**: `du -sh ~/tiles/`
- **Verify services**: Check Martin and search API are responding

## Performance Considerations

### Timing
- **Full pipeline**: 30-60 minutes (depending on data size)
- **Martin reload**: 2-5 seconds
- **Search index generation**: 5-10 minutes
- **Total downtime**: Minimal (services stay running)

### Resource Usage
- **Memory**: Peak usage during tile generation
- **Disk**: ~5-10GB per run (keeps last 5 runs)
- **CPU**: High during tile generation, low during serving

### Optimization
- **Parallel processing**: Counties processed sequentially (can be parallelized)
- **Incremental updates**: Only processes changed counties
- **Smart cleanup**: Keeps recent runs for rollback capability
