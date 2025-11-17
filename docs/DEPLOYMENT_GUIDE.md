# VM Deployment Guide for Report Builder

## Overview
This guide covers deploying the report builder to a VM using Google Cloud Storage (GCS) for GeoJSON file transfer, avoiding the need to install GDAL on the VM.

## Strategy
1. **Local Machine**: Generate GeoJSONs using PMTiles_Cycle (with GDAL)
2. **Upload to GCS**: Transfer GeoJSONs to Google Cloud Storage
3. **VM**: Download GeoJSONs from GCS and run report builder

## Prerequisites

### Local Machine Setup
```bash
# Install required packages
cd PMTiles_Cycle
python3 -m pip install -r requirements.txt

# Test the PMTiles_Cycle
python3 main.py --help
```

### VM Setup
```bash
# Install Python and pip
sudo apt update
sudo apt install python3 python3-pip

# Install Google Cloud SDK (for authentication)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud auth application-default login

# Install Python dependencies
pip3 install google-cloud-storage asyncio aiohttp beautifulsoup4 requests
```

## Step-by-Step Deployment

### Step 1: Generate GeoJSONs Locally
```bash
cd PMTiles_Cycle

# Generate all GeoJSONs (this requires GDAL)
python3 main.py --ownership

# Or generate specific counties
python3 main.py --counties fremont_county_wy lincoln_county_wy sublette_county_wy teton_county_wy
```

### Step 2: Upload GeoJSONs to GCS
```bash
cd PMTiles_Cycle

# Edit the bucket name in upload_geojsons_to_gcs.py first!
# Replace "your-bucket-name" with your actual GCS bucket

python3 upload_geojsons_to_gcs.py upload --bucket your-actual-bucket-name
```

### Step 3: Deploy to VM
```bash
# Copy the report_builder directory to your VM
scp -r report_builder/ user@vm-ip:/path/to/deployment/

# SSH into VM
ssh user@vm-ip
```

### Step 4: Download GeoJSONs on VM
```bash
cd /path/to/deployment/report_builder

# Download GeoJSONs from GCS
python3 download_geojsons.py --bucket your-actual-bucket-name
```

### Step 5: Run Report Builder on VM
```bash
cd report_builder

# Test with small dataset
python3 main.py --max-parcels 10

# Run full collection
python3 main.py

# Run specific counties
python3 main.py --counties fremont_county_wy lincoln_county_wy --max-parcels 100
```

## Production Workflow

### Automated Pipeline (Recommended)
1. **PMTiles VM**: Runs `python3 main.py --ownership` and uploads to GCS
2. **Report Builder VM**: Downloads from GCS and runs collection
3. **Scheduled**: Use cron jobs for regular updates

### Cron Job Example
```bash
# On PMTiles VM (daily at 2 AM)
0 2 * * * cd /path/to/PMTiles_Cycle && python3 main.py --ownership && python3 upload_geojsons_to_gcs.py upload --bucket your-bucket

# On Report Builder VM (daily at 3 AM)
0 3 * * * cd /path/to/report_builder && python3 download_geojsons.py --bucket your-bucket && python3 main.py
```

## File Structure After Deployment
```
report_builder/
├── main.py
├── download_geojsons.py
├── collectors/
├── config/
├── storage/
├── monitoring/
└── output/
    ├── fremont_county_wy_tax_data.jsonl
    ├── fremont_county_wy_property_data.jsonl
    ├── fremont_county_wy_clerk_data.jsonl
    └── ... (other counties)

../PMTiles_Cycle/geojsons_for_db_upload/
├── fremont_county_wy_data_files/
│   └── fremont_county_wy_final_ownership.geojson
├── lincoln_county_wy_data_files/
│   └── lincoln_county_wy_final_ownership.geojson
├── sublette_county_wy_data_files/
│   └── sublette_county_wy_final_ownership.geojson
└── teton_county_wy_data_files/
    └── teton_county_wy_final_ownership.geojson
```

## Troubleshooting

### Common Issues
1. **Authentication Error**: Run `gcloud auth application-default login` on VM
2. **Permission Denied**: Ensure GCS bucket has proper permissions
3. **Missing Files**: Check that GeoJSONs were uploaded successfully

### Verification Commands
```bash
# Check GeoJSON files exist
ls -la ../PMTiles_Cycle/geojsons_for_db_upload/*/final_ownership.geojson

# Test report builder with 1 parcel
python3 main.py --counties fremont_county_wy --max-parcels 1

# Check output files
ls -la output/
```

## Performance Expectations
- **GeoJSON Generation**: ~30 minutes for all counties
- **GCS Upload**: ~5 minutes for all files
- **GCS Download**: ~2 minutes for all files
- **Data Collection**: ~3 days for all parcels (77,548 total)

## Cost Optimization
- Use GCS Nearline storage for GeoJSONs (cheaper for infrequent access)
- Run collection during off-peak hours
- Consider regional storage classes based on VM location
