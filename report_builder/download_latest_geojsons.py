#!/usr/bin/env python3
"""
Download latest GeoJSON files from GCS and clean up old ones
"""

import os
import sys
import json
import shutil
from pathlib import Path
from google.cloud import storage
from datetime import datetime

def download_latest_geojsons(bucket_name="teton-county-gis-bucket", local_dir="geojsons"):
    """Download the most recent GeoJSON files and clean up old ones"""
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    print(f"🔄 Downloading latest GeoJSON files from gs://{bucket_name}")
    
    # Clean up existing geojsons directory
    if os.path.exists(local_dir):
        print(f"🗑️  Removing old GeoJSON files from {local_dir}")
        shutil.rmtree(local_dir)
    
    # Create fresh directory
    os.makedirs(local_dir, exist_ok=True)
    
    # Find the most recent GeoJSON files for each county
    counties = ["fremont_county_wy", "lincoln_county_wy", "sublette_county_wy", "teton_county_wy"]
    
    for county in counties:
        print(f"\n�� Processing {county}...")
        
        # List all GeoJSON files for this county
        prefix = f"geojsons/{county}/"
        blobs = bucket.list_blobs(prefix=prefix)
        geojson_blobs = [blob for blob in blobs if blob.name.endswith('.geojson')]
        
        if not geojson_blobs:
            print(f"   ⚠️  No GeoJSON files found for {county}")
            continue
        
        # Find the most recent file (by modification time)
        latest_blob = max(geojson_blobs, key=lambda b: b.time_created)
        
        # Create county directory
        county_dir = os.path.join(local_dir, county)
        os.makedirs(county_dir, exist_ok=True)
        
        # Download the latest file
        local_path = os.path.join(county_dir, "ownership_data_latest.geojson")
        
        print(f"   📥 Downloading {latest_blob.name}")
        print(f"   📅 Created: {latest_blob.time_created}")
        print(f"   💾 Size: {latest_blob.size / 1024 / 1024:.1f} MB")
        
        latest_blob.download_to_filename(local_path)
        print(f"   ✅ Downloaded to {local_path}")
        
        # Show file info
        file_size = os.path.getsize(local_path)
        print(f"   📊 Local size: {file_size / 1024 / 1024:.1f} MB")
    
    print(f"\n�� Successfully downloaded latest GeoJSON files to {local_dir}/")
    
    # Show final directory structure
    print(f"\n📁 Directory structure:")
    for root, dirs, files in os.walk(local_dir):
        level = root.replace(local_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path) / 1024 / 1024
            print(f"{subindent}{file} ({file_size:.1f} MB)")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download latest GeoJSON files from GCS")
    parser.add_argument("--bucket", default="teton-county-gis-bucket", help="GCS bucket name")
    parser.add_argument("--dir", default="geojsons", help="Local directory")
    
    args = parser.parse_args()
    
    download_latest_geojsons(args.bucket, args.dir)
