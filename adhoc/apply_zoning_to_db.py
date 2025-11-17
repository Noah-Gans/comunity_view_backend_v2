#!/usr/bin/env python3
"""
Apply Zoning Data to Database from Mapping File

Reads the parcel_zoning_mapping.txt file and updates the database
with zoning information for all matching parcels.
"""

import sys
import json
from pathlib import Path
from tqdm import tqdm

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
from shared.database.storage.db import init_db, get_latest_raw, save_raw

MAPPING_FILE = Path(__file__).parent / "parcel_zoning_mapping.txt"
COUNTY = 'teton_county_wy'


def load_zoning_mapping():
    """Load zoning mapping from file"""
    print(f"📂 Loading zoning mapping from {MAPPING_FILE}...")
    
    if not MAPPING_FILE.exists():
        raise FileNotFoundError(f"Mapping file not found: {MAPPING_FILE}")
    
    zoning_mapping = {}
    
    with open(MAPPING_FILE, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                # Format: parcel_id|zoning
                parts = line.split('|')
                if len(parts) == 2:
                    parcel_id = parts[0].strip()
                    zoning = parts[1].strip()
                    if parcel_id and zoning:
                        zoning_mapping[parcel_id] = zoning
            except Exception as e:
                print(f"⚠️  Warning: Error parsing line {line_num}: {e}")
                continue
    
    print(f"✅ Loaded {len(zoning_mapping):,} parcel zoning mappings")
    return zoning_mapping


def update_database_with_zoning(zoning_mapping):
    """Update database with zoning data"""
    print(f"\n💾 Updating database with zoning data...")
    
    init_db()
    
    updated_count = 0
    not_found_count = 0
    error_count = 0
    
    for parcel_id, zoning in tqdm(zoning_mapping.items(), desc="Updating database"):
        try:
            # Get existing data
            raw_data = get_latest_raw(COUNTY, parcel_id)
            
            if not raw_data:
                not_found_count += 1
                continue
            
            # Get property_raw_data
            property_raw_data = raw_data.get('property_raw_data')
            
            # Handle different data structures
            if property_raw_data is None:
                property_raw_data = {}
            
            if not isinstance(property_raw_data, dict):
                # If it's a string (JSON), parse it
                if isinstance(property_raw_data, str):
                    try:
                        property_raw_data = json.loads(property_raw_data)
                    except:
                        property_raw_data = {}
                else:
                    property_raw_data = {}
            
            # Ensure nested structure: property_raw_data -> property_data -> zoning
            if 'property_data' not in property_raw_data:
                property_raw_data['property_data'] = {}
            
            if not isinstance(property_raw_data['property_data'], dict):
                property_raw_data['property_data'] = {}
            
            # Set zoning
            property_raw_data['property_data']['zoning'] = zoning
            
            # Prepare save bundle (preserve all existing data)
            save_bundle = {
                'tax_raw_data': raw_data.get('tax_raw_data'),
                'property_raw_data': property_raw_data,
                'clerk_raw_data': raw_data.get('clerk_raw_data'),
                'county_links': raw_data.get('county_links'),
                'source': raw_data.get('source', 'zoning_mapper')
            }
            
            # Save updated data (creates new version)
            save_raw(COUNTY, parcel_id, save_bundle)
            updated_count += 1
            
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Only show first 10 errors
                print(f"\n⚠️  Error updating {parcel_id}: {e}")
    
    print(f"\n📊 Update Summary:")
    print(f"  ✅ Updated: {updated_count:,} parcels")
    print(f"  ❌ Not found in database: {not_found_count:,} parcels")
    print(f"  ⚠️  Errors: {error_count:,} parcels")
    
    if not_found_count > 0:
        print(f"\n💡 Note: {not_found_count:,} parcels from mapping file were not found in database.")
        print(f"   These may need to be scraped first, or they may use different parcel IDs.")
    
    return updated_count, not_found_count, error_count


def main():
    """Main execution"""
    print("=" * 80)
    print("APPLY ZONING DATA TO DATABASE")
    print("=" * 80)
    
    try:
        # Load mapping
        zoning_mapping = load_zoning_mapping()
        
        # Show sample
        print("\n📋 Sample mappings:")
        for i, (pid, zoning) in enumerate(list(zoning_mapping.items())[:5]):
            print(f"  {pid} -> {zoning}")
        
        # Confirm (skip if running non-interactively)
        print(f"\n⚠️  This will update {len(zoning_mapping):,} parcels in the database.")
        try:
            confirm = input("Continue? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Cancelled")
                return
        except EOFError:
            # Non-interactive mode, auto-confirm
            print("   (Non-interactive mode, proceeding...)")
        
        # Update database
        updated, not_found, errors = update_database_with_zoning(zoning_mapping)
        
        print("\n" + "=" * 80)
        print("✅ COMPLETE!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

