# 🚀 Teton GIS API Deployment Guide

## **📋 Overview**

This guide explains how to deploy the Teton County Idaho Property Info API from your local development environment to a production VM.

## **🏗️ Architecture**

### **Development (Local):**
```
Your MacBook
├── SQLite Database: teton_county_id_download/processed/teton_county_id.db
├── FastAPI Server: main.py
└── All scrapers and overrides
```

### **Production (VM):**
```
Your VM
├── SQLite Database: /opt/teton_gis_api/teton_county_id.db
├── FastAPI Server: /opt/teton_gis_api/main.py
├── Systemd Service: /etc/systemd/system/teton_gis_api.service
├── Cron Job: /etc/cron.d/teton_gis (nightly updates)
└── Log Rotation: /etc/logrotate.d/teton_gis
```

## **🚀 Quick Deployment**

### **1. Automated Deployment:**
```bash
# Make the script executable
chmod +x deploy_to_vm.sh

# Deploy to your VM
./deploy_to_vm.sh user@your-vm-ip
```

### **2. Manual Deployment:**
```bash
# Create directories on VM
ssh user@your-vm-ip "sudo mkdir -p /opt/teton_gis_api/{data,processed,logs}"
ssh user@your-vm-ip "sudo chown -R \$USER:\$USER /opt/teton_gis_api"

# Copy files
scp -r . user@your-vm-ip:/opt/teton_gis_api/
scp teton_county_id_download/processed/teton_county_id.db user@your-vm-ip:/opt/teton_gis_api/

# Set environment and install dependencies
ssh user@your-vm-ip "cd /opt/teton_gis_api && export ENVIRONMENT=production && pip install -r requirements.txt"
```

## **⚙️ Configuration**

### **Environment Variables:**
```bash
# Production environment
export ENVIRONMENT=production

# API settings
export API_HOST=0.0.0.0
export API_PORT=8000
export API_WORKERS=1

# Logging
export LOG_LEVEL=INFO
```

### **Database Paths:**
- **Development**: `./teton_county_id_download/processed/teton_county_id.db`
- **Production**: `/opt/teton_gis_api/teton_county_id.db`

## **🔧 Services Setup**

### **1. Systemd Service:**
```bash
# Create service file
sudo tee /etc/systemd/system/teton_gis_api.service << EOF
[Unit]
Description=Teton GIS Property Info API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/teton_gis_api
Environment=ENVIRONMENT=production
Environment=API_HOST=0.0.0.0
Environment=API_PORT=8000
ExecStart=/opt/teton_gis_api/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable teton_gis_api
sudo systemctl start teton_gis_api
```

### **2. Cron Job (Nightly Updates):**
```bash
# Create cron job
sudo tee /etc/cron.d/teton_gis << EOF
# Teton GIS Data Download - Run nightly at 2 AM
0 2 * * * cd /opt/teton_gis_api && export ENVIRONMENT=production && python3 teton_county_id_download/download_and_process.py >> /opt/teton_gis_api/logs/cron.log 2>&1
EOF

sudo chmod 644 /etc/cron.d/teton_gis
```

### **3. Log Rotation:**
```bash
# Create logrotate config
sudo tee /etc/logrotate.d/teton_gis << EOF
/opt/teton_gis_api/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 ubuntu ubuntu
}
EOF
```

## **📊 Monitoring**

### **Check Service Status:**
```bash
# Service status
sudo systemctl status teton_gis_api

# View logs
sudo journalctl -u teton_gis_api -f

# Check cron logs
tail -f /opt/teton_gis_api/logs/cron.log
```

### **Test API:**
```bash
# Test endpoint
curl -X POST "http://your-vm-ip:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"county": "teton_idaho", "links": {"property_details": "https://example.com?parcelid=LR00196012BU09"}}'
```

## **🔄 Data Updates**

### **Manual Update:**
```bash
cd /opt/teton_gis_api
export ENVIRONMENT=production
python3 teton_county_id_download/download_and_process.py
```

### **Automatic Updates:**
- **Frequency**: Nightly at 2 AM
- **Logs**: `/opt/teton_gis_api/logs/cron.log`
- **Database**: Automatically updated with latest county data

## **🔒 Security Considerations**

### **Firewall:**
```bash
# Allow API port
sudo ufw allow 8000

# Restrict to specific IPs if needed
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

### **SSL/TLS:**
```bash
# For production, consider using nginx as reverse proxy
sudo apt install nginx
# Configure nginx to proxy to localhost:8000
```

## **📈 Performance**

### **Expected Performance:**
- **Response Time**: ~50ms (local database)
- **Throughput**: 1000+ requests/minute
- **Database Size**: ~4MB (15,789 parcels)
- **Memory Usage**: ~50MB

### **Scaling:**
```bash
# Increase workers for higher load
export API_WORKERS=4
sudo systemctl restart teton_gis_api
```

## **🛠️ Troubleshooting**

### **Common Issues:**

**1. Database not found:**
```bash
# Check if database exists
ls -la /opt/teton_gis_api/teton_county_id.db

# Re-run download if missing
cd /opt/teton_gis_api
export ENVIRONMENT=production
python3 teton_county_id_download/download_and_process.py
```

**2. Service won't start:**
```bash
# Check logs
sudo journalctl -u teton_gis_api -n 50

# Check permissions
sudo chown -R ubuntu:ubuntu /opt/teton_gis_api
```

**3. API returns empty data:**
```bash
# Check if parcel exists in database
sqlite3 /opt/teton_gis_api/teton_county_id.db "SELECT COUNT(*) FROM parcels WHERE county_parcel_id = 'LR00196012BU09';"
```

## **🎯 Summary**

Your production deployment will have:
- ✅ **Automated deployment** with `deploy_to_vm.sh`
- ✅ **Systemd service** for reliable API hosting
- ✅ **Cron job** for nightly data updates
- ✅ **Log rotation** for disk space management
- ✅ **Environment-based configuration** for dev/prod
- ✅ **Rich property data** from local SQLite database

The API will be **fast, reliable, and always up-to-date** with the latest county data! 🚀 