#!/usr/bin/env python3
"""
Database Management Script for Property Data

This script provides a comprehensive interface for managing the property database:
- Download data from Google Cloud Storage
- Import downloaded data into the database
- View database statistics
- Query specific parcels
- Handle Teton County Idaho separately (uses DBF files, not JSONL)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Add parent directories to path
sys.path.append(str(Path(__file__).parent))
from storage.db import (
    init_db, 
    save_raw, 
    get_latest_raw, 
    debug_database_contents,
    _get_db_path
)

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("⚠️  google-cloud-storage not installed. GCS download will not work.")

def download_from_gcs(
    bucket_name: str = "teton-county-gis-bucket",
    local_dir: str = None,
    data_types: List[str] = None
) -> str:
    """
    Download scraped data files from Google Cloud Storage
    
    Args:
        bucket_name: GCS bucket name
        local_dir: Local directory to save files (default: pipelines/bulk_collector/scraped_data_download)
        data_types: List of data types to download (['tax', 'property', 'clerk'] or None for all)
    
    Returns:
        Path to downloaded directory
    """
    if not GCS_AVAILABLE:
        raise ImportError("google-cloud-storage not installed. Install with: pip install google-cloud-storage")
    
    if local_dir is None:
        # Default to bulk_collector scraped_data_download directory
        project_root = Path(__file__).parent.parent.parent
        local_dir = project_root / "pipelines" / "bulk_collector" / "scraped_data_download"
    else:
        local_dir = Path(local_dir)
    
    local_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Downloading scraped data from gs://{bucket_name}")
    
    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # List all blobs with .jsonl extension
    blobs = bucket.list_blobs(prefix="")
    jsonl_blobs = [blob for blob in blobs if blob.name.endswith('.jsonl')]
    
    print(f"Found {len(jsonl_blobs)} .jsonl files in bucket")
    
    # Filter by data type if specified
    if data_types:
        data_type_patterns = [f"_{dt}_data.jsonl" for dt in data_types]
        jsonl_blobs = [
            blob for blob in jsonl_blobs 
            if any(pattern in blob.name for pattern in data_type_patterns)
        ]
    
    # Filter for scraped data files
    jsonl_blobs = [
        blob for blob in jsonl_blobs 
        if any(data_type in blob.name for data_type in ['_tax_data.jsonl', '_property_data.jsonl', '_clerk_data.jsonl'])
    ]
    
    print(f"Filtered to {len(jsonl_blobs)} scraped data files")
    
    downloaded_count = 0
    for blob in jsonl_blobs:
        filename = os.path.basename(blob.name)
        local_path = local_dir / filename
        
        print(f"  Downloading {filename}...", end=" ")
        blob.download_to_filename(str(local_path))
        downloaded_count += 1
        print(f"✅")
    
    print(f"\n🎉 Successfully downloaded {downloaded_count} files to {local_dir}/")
    return str(local_dir)


def import_jsonl_files(
    scraped_dir: str,
    county_filter: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Import all scraped data JSONL files into the database
    
    Args:
        scraped_dir: Directory containing JSONL files
        county_filter: Only import data for specific county (e.g., 'teton_county_wy')
        dry_run: If True, don't actually import, just report what would be imported
    
    Returns:
        Dictionary with import statistics
    """
    scraped_dir = Path(scraped_dir)
    
    if not scraped_dir.exists():
        raise FileNotFoundError(f"Scraped data directory not found: {scraped_dir}")
    
    # Initialize database
    init_db()
    
    # Group data by parcel_id first
    parcel_data = defaultdict(lambda: {
        'tax_raw_data': None,
        'property_raw_data': None,
        'clerk_raw_data': None,
        'county': None,
        'county_parcel_id': None,
        'source': 'scraped_import'
    })
    
    print(f"📂 Processing JSONL files from {scraped_dir}...")
    
    # Process all .jsonl files
    jsonl_files = list(scraped_dir.glob("*.jsonl"))
    print(f"Found {len(jsonl_files)} JSONL files")
    
    for jsonl_file in jsonl_files:
        print(f"  Processing {jsonl_file.name}...")
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            line_count = 0
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Extract county from filename
                    # Format: county_data_type.jsonl (e.g., teton_county_wy_property_data.jsonl)
                    filename = jsonl_file.stem
                    parts = filename.split('_')
                    
                    # Find county (first 3 parts: county_state_state)
                    if len(parts) >= 3:
                        county = '_'.join(parts[:3])
                    else:
                        print(f"    ⚠️  Warning: Could not parse county from {filename}, skipping")
                        continue
                    
                    # Filter by county if specified
                    if county_filter and county != county_filter:
                        continue
                    
                    # Get parcel_id - check multiple possible field names
                    parcel_id = (
                        data.get('parcel_id') or 
                        data.get('county_parcel_id') or 
                        data.get('pidn') or
                        data.get('accountno')
                    )
                    
                    if not parcel_id:
                        if line_num <= 5:  # Only show first few warnings
                            print(f"    ⚠️  Skipping line {line_num}: No parcel_id found")
                        continue
                    
                    # Initialize parcel if not exists
                    if parcel_id not in parcel_data:
                        parcel_data[parcel_id]['county'] = county
                        parcel_data[parcel_id]['county_parcel_id'] = parcel_id
                    
                    # Add data type to parcel based on filename
                    if 'tax_data' in filename:
                        parcel_data[parcel_id]['tax_raw_data'] = data
                    elif 'property_data' in filename:
                        parcel_data[parcel_id]['property_raw_data'] = data
                    elif 'clerk_data' in filename:
                        parcel_data[parcel_id]['clerk_raw_data'] = data
                    
                    line_count += 1
                    
                except json.JSONDecodeError as e:
                    if line_num <= 5:
                        print(f"    ⚠️  Error parsing line {line_num}: {e}")
                except Exception as e:
                    if line_num <= 5:
                        print(f"    ⚠️  Error processing line {line_num}: {e}")
            
            print(f"    ✅ Processed {line_count} lines from {jsonl_file.name}")
    
    # Statistics
    stats = {
        'total_parcels': len(parcel_data),
        'by_county': defaultdict(int),
        'with_tax': 0,
        'with_property': 0,
        'with_clerk': 0,
        'complete': 0
    }
    
    for parcel_id, bundle in parcel_data.items():
        county = bundle['county']
        stats['by_county'][county] += 1
        
        if bundle['tax_raw_data']:
            stats['with_tax'] += 1
        if bundle['property_raw_data']:
            stats['with_property'] += 1
        if bundle['clerk_raw_data']:
            stats['with_clerk'] += 1
        
        if bundle['tax_raw_data'] and bundle['property_raw_data']:
            stats['complete'] += 1
    
    print(f"\n📊 Import Statistics:")
    print(f"  Total parcels: {stats['total_parcels']}")
    print(f"  By county: {dict(stats['by_county'])}")
    print(f"  With tax data: {stats['with_tax']}")
    print(f"  With property data: {stats['with_property']}")
    print(f"  With clerk data: {stats['with_clerk']}")
    print(f"  Complete (tax + property): {stats['complete']}")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - No data imported")
        return stats
    
    # Now save each parcel as a single record
    print(f"\n💾 Saving to database...")
    imported_count = 0
    skipped_count = 0
    
    for parcel_id, bundle in parcel_data.items():
        try:
            # Skip Teton County Idaho - it uses DBF files, not JSONL
            if bundle['county'] == 'teton_county_id':
                skipped_count += 1
                continue
            
            version = save_raw(
                bundle['county'], 
                bundle['county_parcel_id'], 
                bundle
            )
            imported_count += 1
            
            if imported_count % 100 == 0:
                print(f"  Imported {imported_count} records...")
                
        except Exception as e:
            print(f"  ⚠️  Error importing {parcel_id}: {e}")
            skipped_count += 1
    
    if skipped_count > 0:
        print(f"\n⚠️  Skipped {skipped_count} parcels (likely Teton County Idaho - use DBF import)")
    
    print(f"\n✅ Import complete! Imported {imported_count} records total.")
    return stats


def show_database_stats():
    """Show comprehensive database statistics"""
    import sqlite3
    
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    
    # Overall stats
    cursor = conn.execute("SELECT COUNT(*) as total FROM property_raw")
    total = cursor.fetchone()['total']
    print(f"\n📊 Total Records: {total:,}")
    
    if total == 0:
        print("\n⚠️  Database is empty!")
        conn.close()
        return
    
    # By county
    cursor = conn.execute("""
        SELECT 
            county,
            COUNT(*) as record_count,
            COUNT(DISTINCT county_parcel_id) as unique_parcels,
            MAX(version) as max_version
        FROM property_raw
        GROUP BY county
        ORDER BY record_count DESC
    """)
    
    print("\n📈 By County:")
    for row in cursor.fetchall():
        print(f"  {row['county']:25s}: {row['record_count']:6,} records, {row['unique_parcels']:6,} parcels, max version {row['max_version']}")
    
    # Data completeness
    print("\n📋 Data Completeness:")
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN tax_raw_data IS NOT NULL THEN 1 ELSE 0 END) as with_tax,
            SUM(CASE WHEN property_raw_data IS NOT NULL THEN 1 ELSE 0 END) as with_property,
            SUM(CASE WHEN clerk_raw_data IS NOT NULL THEN 1 ELSE 0 END) as with_clerk,
            SUM(CASE WHEN county_links IS NOT NULL THEN 1 ELSE 0 END) as with_links
        FROM property_raw
        WHERE version = (
            SELECT MAX(version) 
            FROM property_raw pr2 
            WHERE pr2.county = property_raw.county 
            AND pr2.county_parcel_id = property_raw.county_parcel_id
        )
    """)
    
    row = cursor.fetchone()
    if row and row['total'] > 0:
        print(f"  Total latest records: {row['total']:,}")
        print(f"  With tax data: {row['with_tax']:,} ({row['with_tax']/row['total']*100:.1f}%)")
        print(f"  With property data: {row['with_property']:,} ({row['with_property']/row['total']*100:.1f}%)")
        print(f"  With clerk data: {row['with_clerk']:,} ({row['with_clerk']/row['total']*100:.1f}%)")
        print(f"  With county links: {row['with_links']:,} ({row['with_links']/row['total']*100:.1f}%)")
    
    # Check for zoning in Teton County WY
    print("\n🏘️  Teton County WY Zoning Check:")
    cursor = conn.execute("""
        SELECT COUNT(DISTINCT county_parcel_id) as total_parcels
        FROM property_raw
        WHERE county = 'teton_county_wy'
    """)
    total_teton = cursor.fetchone()['total_parcels']
    
    if total_teton > 0:
        cursor = conn.execute("""
            SELECT property_raw_data
            FROM property_raw
            WHERE county = 'teton_county_wy'
            ORDER BY version DESC
            LIMIT 1000
        """)
        
        with_zoning = 0
        without_zoning = 0
        
        for row in cursor.fetchall():
            if row['property_raw_data']:
                try:
                    data = json.loads(row['property_raw_data'])
                    pd = data.get('property_data', data)
                    if isinstance(pd, dict) and pd.get('zoning'):
                        with_zoning += 1
                    else:
                        without_zoning += 1
                except:
                    without_zoning += 1
        
        print(f"  Total parcels: {total_teton:,}")
        if total_teton <= 1000:
            print(f"  With zoning: {with_zoning:,} ({with_zoning/(with_zoning+without_zoning)*100:.1f}%)")
            print(f"  Without zoning: {without_zoning:,}")
        else:
            print(f"  Sample (first 1000): {with_zoning} with zoning, {without_zoning} without")
    
    # Recent records
    print("\n🕐 Most Recent Records:")
    cursor = conn.execute("""
        SELECT county, county_parcel_id, source, collected_at, version
        FROM property_raw
        ORDER BY collected_at DESC
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"  {row['county']:25s} | {row['county_parcel_id']:20s} | {row['source']:20s} | {row['collected_at']}")
    
    conn.close()
    print("\n" + "=" * 80)


def query_parcel(county: str, parcel_id: str, show_raw: bool = False):
    """Query a specific parcel from the database"""
    data = get_latest_raw(county, parcel_id)
    
    if not data:
        print(f"❌ Parcel not found: {county}/{parcel_id}")
        return
    
    print("=" * 80)
    print(f"PARCEL: {county}/{parcel_id}")
    print("=" * 80)
    print(f"Version: {data['version']}")
    print(f"Source: {data['source']}")
    print(f"Collected: {data['collected_at']}")
    
    if show_raw:
        print("\n📄 Raw Data:")
        print(f"Tax Data: {'✅' if data.get('tax_raw_data') else '❌'}")
        print(f"Property Data: {'✅' if data.get('property_raw_data') else '❌'}")
        print(f"Clerk Data: {'✅' if data.get('clerk_raw_data') else '❌'}")
        print(f"County Links: {'✅' if data.get('county_links') else '❌'}")
        
        if data.get('property_raw_data'):
            print("\nProperty Data Preview:")
            prop = data['property_raw_data']
            if isinstance(prop, dict):
                pd = prop.get('property_data', prop)
                if isinstance(pd, dict):
                    print(f"  Zoning: {pd.get('zoning', 'N/A')}")
                    print(f"  Keys: {list(pd.keys())[:10]}...")
    else:
        print("\n💡 Use --show-raw to see full data structure")


def main():
    parser = argparse.ArgumentParser(
        description="Database Management Tool for Property Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download data from GCS
  python db_manager.py download
  
  # Import downloaded data
  python db_manager.py import --dir pipelines/bulk_collector/scraped_data_download
  
  # Import specific county
  python db_manager.py import --dir scraped_data --county teton_county_wy
  
  # Show database statistics
  python db_manager.py stats
  
  # Query a specific parcel
  python db_manager.py query teton_county_wy 22-40-16-18-1-05-320
  
  # Dry run (see what would be imported)
  python db_manager.py import --dir scraped_data --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download data from Google Cloud Storage')
    download_parser.add_argument('--bucket', default='teton-county-gis-bucket', help='GCS bucket name')
    download_parser.add_argument('--dir', help='Local directory to save files')
    download_parser.add_argument('--types', nargs='+', choices=['tax', 'property', 'clerk'], 
                                help='Data types to download')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import JSONL files into database')
    import_parser.add_argument('--dir', required=True, help='Directory containing JSONL files')
    import_parser.add_argument('--county', help='Only import data for specific county')
    import_parser.add_argument('--dry-run', action='store_true', help='Dry run (don\'t actually import)')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show database statistics')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query a specific parcel')
    query_parser.add_argument('county', help='County name')
    query_parser.add_argument('parcel_id', help='Parcel ID')
    query_parser.add_argument('--show-raw', action='store_true', help='Show raw data structure')
    
    # Debug command
    debug_parser = subparsers.add_parser('debug', help='Show debug database contents')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'download':
            download_from_gcs(
                bucket_name=args.bucket,
                local_dir=args.dir,
                data_types=args.types
            )
        
        elif args.command == 'import':
            import_jsonl_files(
                scraped_dir=args.dir,
                county_filter=args.county,
                dry_run=args.dry_run
            )
        
        elif args.command == 'stats':
            show_database_stats()
        
        elif args.command == 'query':
            query_parcel(args.county, args.parcel_id, args.show_raw)
        
        elif args.command == 'debug':
            debug_database_contents()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()







