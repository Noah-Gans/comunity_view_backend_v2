#!/bin/bash

# Deployment script for Teton County Idaho Property Info API
# Usage: ./deploy_to_vm.sh user@your-vm-ip

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 user@your-vm-ip"
    echo "Example: $0 ubuntu@192.168.1.100"
    exit 1
fi

VM_ADDRESS=$1
APP_NAME="teton_gis_api"

echo "🚀 Deploying Teton GIS API to VM: $VM_ADDRESS"

# Create production directory structure on VM
echo "📁 Creating directory structure..."
ssh $VM_ADDRESS "sudo mkdir -p /opt/$APP_NAME/{data,processed,logs}"
ssh $VM_ADDRESS "sudo chown -R \$USER:\$USER /opt/$APP_NAME"

# Copy application files
echo "📦 Copying application files..."
scp -r . $VM_ADDRESS:/opt/$APP_NAME/

# Copy database (if it exists)
if [ -f "teton_county_id_download/processed/teton_county_id.db" ]; then
    echo "🗄️ Copying database..."
    scp teton_county_id_download/processed/teton_county_id.db $VM_ADDRESS:/opt/$APP_NAME/
else
    echo "⚠️ Database not found locally, will be downloaded on VM"
fi

# Set up environment
echo "🔧 Setting up production environment..."
ssh $VM_ADDRESS "cd /opt/$APP_NAME && export ENVIRONMENT=production"

# Install dependencies
echo "📦 Installing Python dependencies..."
ssh $VM_ADDRESS "cd /opt/$APP_NAME && python3 -m pip install -r requirements.txt"

# Set up systemd service
echo "⚙️ Setting up systemd service..."
cat > teton_gis_api.service << EOF
[Unit]
Description=Teton GIS Property Info API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/$APP_NAME
Environment=ENVIRONMENT=production
Environment=API_HOST=0.0.0.0
Environment=API_PORT=8000
ExecStart=/opt/$APP_NAME/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

scp teton_gis_api.service $VM_ADDRESS:/tmp/
ssh $VM_ADDRESS "sudo mv /tmp/teton_gis_api.service /etc/systemd/system/"
ssh $VM_ADDRESS "sudo systemctl daemon-reload"
ssh $VM_ADDRESS "sudo systemctl enable teton_gis_api"

# Set up cron job for nightly data updates
echo "⏰ Setting up cron job for nightly updates..."
cat > teton_gis_cron << EOF
# Teton GIS Data Download - Run nightly at 2 AM
0 2 * * * cd /opt/$APP_NAME && export ENVIRONMENT=production && python3 teton_county_id_download/download_and_process.py >> /opt/$APP_NAME/logs/cron.log 2>&1
EOF

scp teton_gis_cron $VM_ADDRESS:/tmp/
ssh $VM_ADDRESS "sudo mv /tmp/teton_gis_cron /etc/cron.d/teton_gis"
ssh $VM_ADDRESS "sudo chmod 644 /etc/cron.d/teton_gis"

# Create log rotation
echo "📝 Setting up log rotation..."
cat > teton_gis_logrotate << EOF
/opt/$APP_NAME/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 644 $USER $USER
}
EOF

scp teton_gis_logrotate $VM_ADDRESS:/tmp/
ssh $VM_ADDRESS "sudo mv /tmp/teton_gis_logrotate /etc/logrotate.d/teton_gis"

# Start the service
echo "🚀 Starting the API service..."
ssh $VM_ADDRESS "sudo systemctl start teton_gis_api"
ssh $VM_ADDRESS "sudo systemctl status teton_gis_api"

# Test the API
echo "🧪 Testing the API..."
sleep 5
curl -X POST "http://$VM_ADDRESS:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"county": "teton_idaho", "links": {"property_details": "https://example.com?parcelid=LR00196012BU09"}}'

echo "✅ Deployment complete!"
echo "📊 API Status:"
ssh $VM_ADDRESS "sudo systemctl status teton_gis_api"
echo "📁 Files:"
ssh $VM_ADDRESS "ls -la /opt/$APP_NAME/"
echo "🗄️ Database:"
ssh $VM_ADDRESS "ls -la /opt/$APP_NAME/teton_county_id.db"

# Clean up local files
rm -f teton_gis_api.service teton_gis_cron teton_gis_logrotate

echo "🎉 Deployment successful! Your API is now running on the VM."
echo "🌐 Access it at: http://$VM_ADDRESS:8000" 