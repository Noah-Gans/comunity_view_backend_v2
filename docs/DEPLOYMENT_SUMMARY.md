# 🚀 Martin Server Backend - Deployment Summary

## What We've Built

You now have a **complete, automated backend system** that handles:
- **PMTiles generation** from county data sources
- **Martin tile server** management with automatic updates
- **Search API** with automatic index regeneration
- **Daily automated updates** at 2:00 AM

## 🏗️ System Architecture

```
Daily Update Pipeline (2:00 AM)
           ↓
    PMTiles_Cycle/
    ├── Downloads county data
    ├── Generates GeoJSON
    ├── Creates MBTiles
    └── Converts to PMTiles
           ↓
    Martin Server
    ├── Serves updated tiles
    ├── Auto-reloads config
    └── Zero downtime updates
           ↓
    Search API
    ├── Regenerates index
    ├── Reloads fresh data
    └── Serves property searches
```

## 📁 Files Created

### **Core Scripts:**
- **`daily_update_pipeline.sh`** - Main automation script
- **`setup_cron.sh`** - Sets up daily cron job
- **`test_pipeline.sh`** - Tests system components

### **Documentation:**
- **`DAILY_UPDATE_README.md`** - Comprehensive system guide
- **`DEPLOYMENT_SUMMARY.md`** - This deployment guide

## 🔧 How It Solves Your PMTiles Path Problem

### **Before (Problem):**
- PMTiles accumulated in same directory
- Same filenames caused confusion
- Martin server needed restart to see new tiles
- No versioning or rollback capability

### **After (Solution):**
- **Timestamped directories**: `~/tiles/runs/20250812_020000/`
- **Symlink management**: `~/tiles/latest` always points to current tiles
- **Automatic config updates**: Martin config updates to point to latest
- **Server reload**: Martin reloads without restart (SIGHUP)
- **Rollback capability**: Keep last 5 runs for emergency recovery

## 🚀 Deployment to VM

### **Step 1: Copy Files**
```bash
# On your local machine, copy the entire directory
scp -r comunity_view_backend_v2/ user@your-vm:/path/to/destination/
```

### **Step 2: Install Dependencies**
```bash
# SSH to your VM
ssh user@your-vm

# Navigate to the directory
cd /path/to/destination/comunity_view_backend_v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PMTiles dependencies
pip install -r PMTiles_Cycle/requirements.txt

# Install search API dependencies
pip install -r search_api/requirements.txt
```

### **Step 3: Test the System**
```bash
# Test all components work
./test_pipeline.sh

# Test the full pipeline manually (this will take 30-60 minutes)
./daily_update_pipeline.sh
```

### **Step 4: Set Up Automation**
```bash
# Set up daily cron job at 2:00 AM
./setup_cron.sh

# Verify cron job was created
crontab -l
```

### **Step 5: Start Services**
```bash
# Start Martin server (adjust path as needed)
martin --config PMTiles_Cycle/martin_config.yaml &

# Start search API
cd search_api
python start_api.py &
```

## 📊 Daily Update Process (2:00 AM)

### **What Happens Automatically:**
1. **Data Download** - Fresh county data downloaded
2. **Tile Generation** - MBTiles created from GeoJSON
3. **PMTiles Conversion** - MBTiles converted to PMTiles
4. **File Organization** - New tiles moved to timestamped directory
5. **Symlink Update** - `~/tiles/latest` points to new tiles
6. **Martin Config Update** - Config points to latest tiles
7. **Server Reload** - Martin server reloads (no restart)
8. **Search Index Regeneration** - New search index created
9. **API Reload** - Search API loads fresh data
10. **Cleanup** - Old runs removed (keeps last 5)

### **Timing:**
- **Total process**: 30-60 minutes
- **Downtime**: Minimal (services stay running)
- **Martin reload**: 2-5 seconds
- **Search update**: 5-10 minutes

## 🔍 Monitoring & Maintenance

### **Check Status:**
```bash
# View current tile structure
ls -la ~/tiles/
ls -la ~/tiles/latest/

# Check Martin server
pgrep -f martin

# Check search API
curl http://localhost:8000/health

# View pipeline logs
tail -f daily_update.log

# View cron logs
tail -f cron.log
```

### **Manual Operations:**
```bash
# Run pipeline manually
./daily_update_pipeline.sh

# Regenerate search index only
cd search_api && python search_file_generator.py

# Reload Martin server
pkill -HUP -f martin

# Reload search API
curl -X POST http://localhost:8000/reload
```

## 🚨 Emergency Procedures

### **If Pipeline Fails:**
```bash
# Check logs for errors
tail -f daily_update.log

# Run manually to see errors
./daily_update_pipeline.sh

# Check disk space
du -sh ~/tiles/
```

### **If Martin Server Issues:**
```bash
# Check if running
pgrep -f martin

# Restart if needed
pkill -f martin
martin --config PMTiles_Cycle/martin_config.yaml &
```

### **If Search API Issues:**
```bash
# Check if running
pgrep -f start_api.py

# Restart if needed
pkill -f start_api.py
cd search_api && python start_api.py &
```

### **Complete Reset:**
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

## 📈 Performance & Scaling

### **Current Capacity:**
- **Teton County**: 16,340 properties (working)
- **Other counties**: Ready to add when data available
- **Storage**: ~5-10GB per run (keeps last 5 runs)
- **Memory**: Peak during tile generation

### **Future Enhancements:**
- **Parallel processing** for multiple counties
- **Incremental updates** for changed data only
- **CDN integration** for tile serving
- **Database backend** for search (instead of JSON files)

## ✅ What's Working Now

1. **PMTiles Pipeline** ✅ - Tested and working
2. **Search API** ✅ - Tested and working  
3. **File Organization** ✅ - Tested and working
4. **Symlink Management** ✅ - Tested and working
5. **Config Updates** ✅ - Tested and working
6. **Automation Scripts** ✅ - Tested and working

## 🎯 Next Steps

1. **Deploy to VM** - Copy files and install dependencies
2. **Test locally** - Run test script and manual pipeline
3. **Set up cron** - Automate daily updates
4. **Start services** - Martin server and search API
5. **Monitor first run** - Watch logs during first automated update
6. **Scale up** - Add more counties as data becomes available

## 🆘 Support

If you encounter issues:
1. **Check logs first**: `tail -f daily_update.log`
2. **Run test script**: `./test_pipeline.sh`
3. **Check system status**: Use monitoring commands above
4. **Review documentation**: `DAILY_UPDATE_README.md`

---

**🎉 Congratulations! You now have a production-ready, automated backend system that will keep your Martin server and search API updated daily with zero manual intervention.**
