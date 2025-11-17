#!/usr/bin/env python3
"""
Ad-hoc script to backfill Teton County WY parcels with:
1. Zoning data from ArcGIS API
2. County links from the geojson file

This script:
- Reads all teton_county_wy parcels from the database
- Loads the geojson file to create a lookup of pidn -> accountno and links
- For each parcel, fetches zoning from ArcGIS API if accountno is available
- Updates property_raw_data with zoning
- Updates county_links with links from geojson
"""

import sys
import os
import json
import sqlite3
import requests
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add paths to import database functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared', 'database', 'storage'))
from db import init_db, save_raw, get_latest_raw, _get_db_path

# ArcGIS API base URL
ARCGIS_BASE_URL = "https://gis.tetoncountywy.gov/server/rest/services/Public_Services/Parcels/FeatureServer"

def load_geojson_lookup(geojson_path: str) -> Dict[str, Dict]:
    """
    Load the geojson file and create a lookup dictionary by pidn (county_parcel_id).
    Returns: {pidn: {accountno, clerk_rec, property_det, tax_info, map_no, deed_no, smart_gov, zoning}}
    """
    print(f"Loading geojson file: {geojson_path}")
    lookup = {}
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"Found {len(features)} features in geojson")
    
    for feature in features:
        props = feature.get('properties', {})
        pidn = props.get('pidn')
        if not pidn:
            continue
        
        lookup[pidn] = {
            'accountno': props.get('accountno', ''),
            'clerk_rec': props.get('clerk_rec', ''),
            'property_det': props.get('property_det', ''),
            'tax_info': props.get('tax_info', ''),
            'map_no': props.get('map_no', ''),
            'deed_no': props.get('deed_no', ''),
            'smart_gov': props.get('smart_gov', ''),
            'zoning': props.get('zoning', '')  # Some geojson records might already have zoning
        }
    
    print(f"Created lookup for {len(lookup)} parcels")
    return lookup

def fetch_links_from_arcgis(accountno: str, pidn: str) -> Dict[str, str]:
    """
    Fetch links from ArcGIS API using account number and parcel ID.
    Returns a dictionary with all available links.
    """
    links = {}
    
    if not accountno and not pidn:
        return links
    
    url = f"{ARCGIS_BASE_URL}/0/query"
    params = {
        'f': 'json',
        'outFields': 'clerk_rec,property_det,tax_info,map_no,deed_no,smart_gov',
        'where': f"accountno='{accountno}'" if accountno else f"pidn='{pidn}'"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        features = data.get('features', [])
        if features and len(features) > 0:
            attrs = features[0].get('attributes', {})
            links = {
                'clerk_rec': attrs.get('clerk_rec', ''),
                'property_det': attrs.get('property_det', ''),
                'tax_info': attrs.get('tax_info', ''),
                'map_no': attrs.get('map_no', ''),
                'deed_no': attrs.get('deed_no', ''),
                'smart_gov': attrs.get('smart_gov', '')
            }
    except Exception as e:
        print(f"  Error fetching links for accountno {accountno}: {e}")
    
    return links

def fetch_zoning_from_arcgis(accountno: str, max_retries: int = 3) -> Optional[str]:
    """
    Fetch zoning data from ArcGIS API using account number.
    Returns zoning code or None if not found.
    """
    if not accountno:
        return None
    
    url = f"{ARCGIS_BASE_URL}/0/query"
    params = {
        'f': 'json',
        'outFields': 'zoning',
        'where': f"accountno='{accountno}'"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)  # Increased from 10 to 30
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if features and len(features) > 0:
                zoning = features[0].get('attributes', {}).get('zoning')
                return zoning if zoning else None
            return None
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                print(f"  Timeout for {accountno}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"  Error fetching zoning for accountno {accountno}: Timeout after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Error fetching zoning for accountno {accountno}: {e}, retrying...")
                time.sleep(2)
            else:
                print(f"  Error fetching zoning for accountno {accountno}: {e}")
                return None
    
    return None

def update_parcel_zoning_and_links(
    county: str,
    county_parcel_id: str,
    geojson_data: Dict,
    zoning: Optional[str] = None
) -> bool:
    """
    Update a parcel's property_raw_data with zoning and county_links with links.
    Returns True if successful, False otherwise.
    """
    # Get current data
    current_data = get_latest_raw(county, county_parcel_id)
    if not current_data:
        print(f"  Warning: No existing data found for {county_parcel_id}")
        return False
    
    # Prepare updated bundle
    bundle = {
        'tax_raw_data': current_data.get('tax_raw_data'),
        'property_raw_data': current_data.get('property_raw_data'),
        'clerk_raw_data': current_data.get('clerk_raw_data'),
        'county_links': current_data.get('county_links') or {},
        'source': current_data.get('source', 'backfill_script')
    }
    
    # Update zoning in property_raw_data
    if zoning:
        if bundle['property_raw_data']:
            # Handle nested structure: property_raw_data -> property_data -> zoning
            if isinstance(bundle['property_raw_data'], dict):
                if 'property_data' in bundle['property_raw_data']:
                    # Standard structure
                    bundle['property_raw_data']['property_data']['zoning'] = zoning
                elif 'zoning' not in bundle['property_raw_data']:
                    # Direct structure (less common)
                    bundle['property_raw_data']['zoning'] = zoning
        else:
            # Create minimal structure if property_raw_data doesn't exist
            bundle['property_raw_data'] = {
                'parcel_id': county_parcel_id,
                'property_data': {
                    'county_parcel_id': county_parcel_id,
                    'zoning': zoning
                }
            }
    
    # Update county_links
    links = {
        'tax_field': geojson_data.get('tax_info', ''),
        'property_details_field': geojson_data.get('property_det', ''),
        'clerk_field': geojson_data.get('clerk_rec', ''),
        'map_no': geojson_data.get('map_no', ''),
        'deed_no': geojson_data.get('deed_no', ''),
        'smart_gov': geojson_data.get('smart_gov', '')
    }
    
    # Merge with existing links
    if bundle['county_links']:
        bundle['county_links'].update(links)
    else:
        bundle['county_links'] = links
    
    # Save updated data
    try:
        save_raw(county, county_parcel_id, bundle)
        return True
    except Exception as e:
        print(f"  Error saving data for {county_parcel_id}: {e}")
        return False

def main():
    """Main function to backfill zoning and links for all Teton County WY parcels."""
    
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Try multiple possible paths for the geojson file
    # Priority: intermediate_data files have the raw links, final_parcels are processed
    intermediate_dir = Path(__file__).parent.parent / "pipelines" / "pmtiles" / "intermediate_data" / "teton_county_wy_data_files"
    possible_paths = []
    
    # First, check intermediate_data directory for any geojson files
    if intermediate_dir.exists():
        for geojson_file in intermediate_dir.glob("*.geojson"):
            possible_paths.append(geojson_file)
    
    # Then check for specific filename variations
    possible_paths.extend([
        Path(__file__).parent.parent / "pipelines" / "pmtiles" / "intermediate_data" / "teton_county_wy_data_files" / "teton_county_wy_ownership_complete.geojson",
        Path(__file__).parent.parent / "pipelines" / "pmtiles" / "intermediate_data" / "teton_county_wy_data_files" / "teton_county_wy_complete.geojson",
        Path(__file__).parent.parent / "pipelines" / "pmtiles" / "intermediate_data" / "teton_county_wy_data_files" / "ownership_complete.geojson",
    ])
    
    # Only fallback to final_parcels if no intermediate files found (but note: they won't have links)
    if not any(p.exists() for p in possible_paths):
        possible_paths.append(
            Path(__file__).parent.parent / "pipelines" / "pmtiles" / "final_parcels" / "teton_county_wy_data_files" / "teton_county_wy_final_ownership.geojson"
        )
    
    geojson_path = None
    for path in possible_paths:
        if path.exists():
            geojson_path = path
            break
    
    if not geojson_path:
        print(f"Error: Geojson file not found in any of these locations:")
        for path in possible_paths:
            print(f"  - {path}")
        print("\nNote: The intermediate_data file contains the raw links (clerk_rec, property_det, etc.)")
        print("If the file doesn't exist, you may need to run the pipeline to generate it.")
        print("\nPlease check if the file exists or download it from GCS.")
        return
    
    print(f"Using geojson file: {geojson_path}")
    print(f"Note: This file should contain raw links (clerk_rec, property_det, tax_info, etc.)")
    
    # Load geojson lookup
    geojson_lookup = load_geojson_lookup(str(geojson_path))
    
    # Get all teton_county_wy parcels from database
    print("\nFetching all Teton County WY parcels from database...")
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT DISTINCT county_parcel_id 
        FROM property_raw 
        WHERE county = 'teton_county_wy'
        ORDER BY county_parcel_id
    """)
    parcels = [row['county_parcel_id'] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(parcels)} parcels in database")
    
    # Process each parcel
    updated_zoning = 0
    updated_links = 0
    skipped_no_geojson = 0
    skipped_no_accountno = 0
    errors = 0
    
    for i, parcel_id in enumerate(parcels, 1):
        if i % 100 == 0:
            print(f"\nProgress: {i}/{len(parcels)} parcels processed")
            print(f"  Updated zoning: {updated_zoning}")
            print(f"  Updated links: {updated_links}")
            print(f"  Skipped (no geojson): {skipped_no_geojson}")
            print(f"  Skipped (no accountno): {skipped_no_accountno}")
            print(f"  Errors: {errors}")
        
        # Get geojson data for this parcel
        geojson_data = geojson_lookup.get(parcel_id)
        
        # Get accountno from geojson or try from existing property_raw_data
        accountno = ''
        if geojson_data:
            accountno = geojson_data.get('accountno', '')
        
        if not accountno:
            # Try to get accountno from existing property_raw_data
            current_data = get_latest_raw('teton_county_wy', parcel_id)
            if current_data and current_data.get('property_raw_data'):
                prop_data = current_data['property_raw_data']
                if isinstance(prop_data, dict):
                    accountno = prop_data.get('property_details_key', '')
        
        # If no geojson data, try to fetch links from API
        if not geojson_data:
            if accountno or parcel_id:
                geojson_data = fetch_links_from_arcgis(accountno, parcel_id)
                time.sleep(0.1)  # Rate limiting
            else:
                skipped_no_geojson += 1
                continue
        
        # Try to get zoning - first from geojson, then from API
        zoning = geojson_data.get('zoning') if isinstance(geojson_data, dict) else None
        if not zoning and accountno:
            # Fetch from API
            print(f"  Fetching zoning for parcel {parcel_id} (accountno: {accountno})...")
            zoning = fetch_zoning_from_arcgis(accountno)
            if zoning:
                print(f"  ✅ Found zoning: {zoning} for parcel {parcel_id}")
            else:
                print(f"  ⚠️ No zoning found for parcel {parcel_id}")
            # Increased delay to avoid rate limiting
            time.sleep(0.5)
        
        # Update parcel with zoning and links
        print(f"  Updating parcel {parcel_id} with links...")
        success = update_parcel_zoning_and_links(
            'teton_county_wy',
            parcel_id,
            geojson_data if isinstance(geojson_data, dict) else {},
            zoning
        )
        
        if success:
            if zoning:
                updated_zoning += 1
                print(f"  ✅ Updated parcel {parcel_id} with zoning and links")
            else:
                print(f"  ✅ Updated parcel {parcel_id} with links (no zoning)")
            updated_links += 1
        else:
            errors += 1
            print(f"  ❌ Failed to update parcel {parcel_id}")
        
        if not accountno:
            skipped_no_accountno += 1
    
    # Final summary
    print("\n" + "="*60)
    print("BACKFILL SUMMARY")
    print("="*60)
    print(f"Total parcels processed: {len(parcels)}")
    print(f"Parcels updated with zoning: {updated_zoning}")
    print(f"Parcels updated with links: {updated_links}")
    print(f"Parcels skipped (no geojson match): {skipped_no_geojson}")
    print(f"Parcels skipped (no accountno): {skipped_no_accountno}")
    print(f"Errors: {errors}")
    print("="*60)

if __name__ == "__main__":
    main()

