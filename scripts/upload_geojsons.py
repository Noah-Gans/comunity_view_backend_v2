#!/usr/bin/env python3
"""
Upload GeoJSON files to Google Cloud Storage for VM deployment
"""

import os
import sys
from pathlib import Path
from google.cloud import storage

def upload_geojsons_to_gcs(bucket_name="your-bucket-name", local_dir="geojsons_for_db_upload"):
    """Upload all GeoJSON files to GCS"""
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Find all GeoJSON files
    geojson_files = []
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            if file.endswith('.geojson'):
                full_path = os.path.join(root, file)
                geojson_files.append(full_path)
    
    print(f"Found {len(geojson_files)} GeoJSON files to upload:")
    
    for file_path in geojson_files:
        # Create blob name (maintain directory structure)
        blob_name = file_path.replace(f"{local_dir}/", "")
        
        print(f"Uploading {file_path} -> gs://{bucket_name}/{blob_name}")
        
        # Upload file
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        
        print(f"✅ Uploaded {file_path}")
    
    print(f"\n🎉 Successfully uploaded {len(geojson_files)} files to gs://{bucket_name}/")

def download_geojsons_from_gcs(bucket_name="your-bucket-name", local_dir="geojsons_for_db_upload"):
    """Download all GeoJSON files from GCS (for VM)"""
    
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
        # Create local file path
        local_path = os.path.join(local_dir, blob.name)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        print(f"Downloading gs://{bucket_name}/{blob.name} -> {local_path}")
        
        # Download file
        blob.download_to_filename(local_path)
        
        print(f"✅ Downloaded {blob.name}")
    
    print(f"\n🎉 Successfully downloaded {len(geojson_blobs)} files to {local_dir}/")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload/Download GeoJSON files to/from GCS")
    parser.add_argument("action", choices=["upload", "download"], help="Action to perform")
    parser.add_argument("--bucket", default="your-bucket-name", help="GCS bucket name")
    parser.add_argument("--dir", default="geojsons_for_db_upload", help="Local directory")
    
    args = parser.parse_args()
    
    if args.action == "upload":
        upload_geojsons_to_gcs(args.bucket, args.dir)
    elif args.action == "download":
        download_geojsons_from_gcs(args.bucket, args.dir)
