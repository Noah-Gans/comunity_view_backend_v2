#!/usr/bin/env python3
"""
Download GeoJSON files from Google Cloud Storage for report builder
"""

import os
import sys
from pathlib import Path
from google.cloud import storage

def download_geojsons_from_gcs(bucket_name="your-bucket-name", local_dir="../pmtiles/final_parcels"):
    """Download all GeoJSON files from GCS to the correct directory structure"""
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # List all blobs with .geojson extension
    blobs = bucket.list_blobs(prefix="")
    geojson_blobs = [blob for blob in blobs if blob.name.endswith('.geojson')]
    
    print(f"Found {len(geojson_blobs)} GeoJSON files to download:")
    
    # Create local directory structure
    os.makedirs(local_dir, exist_ok=True)
    
    for blob in geojson_blobs:
        # Create local file path maintaining directory structure
        local_path = os.path.join(local_dir, blob.name)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        print(f"Downloading gs://{bucket_name}/{blob.name} -> {local_path}")
        
        # Download file
        blob.download_to_filename(local_path)
        
        print(f"✅ Downloaded {blob.name}")
    
    print(f"\n🎉 Successfully downloaded {len(geojson_blobs)} files to {local_dir}/")
    print(f"📁 Directory structure:")
    for root, dirs, files in os.walk(local_dir):
        level = root.replace(local_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download GeoJSON files from GCS for report builder")
    parser.add_argument("--bucket", default="your-bucket-name", help="GCS bucket name")
    parser.add_argument("--dir", default="../pmtiles/final_parcels", help="Local directory")
    
    args = parser.parse_args()
    
    download_geojsons_from_gcs(args.bucket, args.dir)
