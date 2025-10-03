#!/usr/bin/env python3
"""
Download scraped data files from Google Cloud Storage for property_info_api
"""

import os
import sys
from pathlib import Path
from google.cloud import storage

def download_scraped_data_from_gcs(bucket_name="teton-county-gis-bucket", local_dir="report_builder/scraped_data_download"):
    """Download all scraped data .jsonl files from GCS"""
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    print(f"🔄 Downloading scraped data from gs://{bucket_name}")
    
    # Create local directory
    os.makedirs(local_dir, exist_ok=True)
    
    # List all blobs with .jsonl extension
    blobs = bucket.list_blobs(prefix="")
    jsonl_blobs = [blob for blob in blobs if blob.name.endswith('.jsonl')]
    
    print(f"Found {len(jsonl_blobs)} .jsonl files to download:")
    
    downloaded_count = 0
    for blob in jsonl_blobs:
        # Skip if it's not scraped data (filter for data files)
        if not any(data_type in blob.name for data_type in ['_tax_data.jsonl', '_property_data.jsonl', '_clerk_data.jsonl']):
            continue
            
        # Extract just the filename from the blob path
        filename = os.path.basename(blob.name)
        
        # Create local file path (just the filename, no directory structure)
        local_path = os.path.join(local_dir, filename)
        
        print(f"Downloading gs://{bucket_name}/{blob.name} -> {local_path}")
        
        # Download file
        blob.download_to_filename(local_path)
        downloaded_count += 1
        
        print(f"✅ Downloaded {filename}")
    
    print(f"\n🎉 Successfully downloaded {downloaded_count} scraped data files to {local_dir}/")
    
    # Show what was downloaded
    if os.path.exists(local_dir):
        print(f"📁 Downloaded files:")
        for file in os.listdir(local_dir):
            if file.endswith('.jsonl'):
                print(f"   {file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download scraped data from GCS")
    parser.add_argument("--bucket", default="teton-county-gis-bucket", help="GCS bucket name")
    parser.add_argument("--dir", default="report_builder/scraped_data_download", help="Local directory to save files")
    
    args = parser.parse_args()
    
    download_scraped_data_from_gcs(args.bucket, args.dir)
