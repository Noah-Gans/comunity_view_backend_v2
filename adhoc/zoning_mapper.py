#!/usr/bin/env python3
"""
Zoning Mapper for Teton County WY Parcels

This script:
1. Reads all parcels from the ownership geojson
2. Performs spatial joins with county_zoning.shp and toj_zoning.shp
3. Creates a mapping file (parcel_id -> zoning)
4. Updates the local database with zoning data
5. Generates a text file for VM upload

Priority: TOJ (Town of Jackson) zoning takes precedence over county zoning
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Optional
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from tqdm import tqdm

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
from shared.database.storage.db import init_db, get_latest_raw, save_raw

# Paths
ZONING_DIR = Path(__file__).parent / "zoning 5"
GEOJSON_PATH = Path(__file__).parent.parent / "pipelines" / "pmtiles" / "intermediate_data" / "teton_county_wy_data_files" / "teton_county_wy_ownership_complete.geojson"
OUTPUT_MAPPING_FILE = Path(__file__).parent / "parcel_zoning_mapping.txt"

def load_zoning_shapefiles():
    """Load county and TOJ zoning shapefiles"""
    print("📂 Loading zoning shapefiles...")
    
    county_zoning_path = ZONING_DIR / "county_zoning.shp"
    toj_zoning_path = ZONING_DIR / "toj_zoning.shp"
    
    if not county_zoning_path.exists():
        raise FileNotFoundError(f"County zoning file not found: {county_zoning_path}")
    if not toj_zoning_path.exists():
        raise FileNotFoundError(f"TOJ zoning file not found: {toj_zoning_path}")
    
    # Load shapefiles
    county_gdf = gpd.read_file(county_zoning_path)
    toj_gdf = gpd.read_file(toj_zoning_path)
    
    # Ensure CRS is set (should be same for spatial operations)
    if county_gdf.crs is None:
        print("⚠️  County zoning has no CRS, assuming same as TOJ")
    if toj_gdf.crs is None:
        print("⚠️  TOJ zoning has no CRS, assuming same as parcels")
    
    # Make sure both are in same CRS
    if county_gdf.crs != toj_gdf.crs:
        print(f"⚠️  CRS mismatch: county={county_gdf.crs}, toj={toj_gdf.crs}")
        print("   Converting TOJ to match county CRS...")
        toj_gdf = toj_gdf.to_crs(county_gdf.crs)
    
    print(f"✅ Loaded {len(county_gdf)} county zoning polygons")
    print(f"✅ Loaded {len(toj_gdf)} TOJ zoning polygons")
    
    # Check zoning column
    if 'zoning' not in county_gdf.columns:
        raise ValueError(f"County zoning missing 'zoning' column. Available: {list(county_gdf.columns)}")
    if 'zoning' not in toj_gdf.columns:
        raise ValueError(f"TOJ zoning missing 'zoning' column. Available: {list(toj_gdf.columns)}")
    
    return county_gdf, toj_gdf


def load_parcels_geojson():
    """Load parcels from geojson file"""
    print(f"📂 Loading parcels from {GEOJSON_PATH}...")
    
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {GEOJSON_PATH}")
    
    # Read geojson (might be FeatureCollection or JSONL)
    try:
        # Try as FeatureCollection first
        gdf = gpd.read_file(GEOJSON_PATH)
        print(f"✅ Loaded {len(gdf)} parcels from FeatureCollection")
    except:
        # Try as JSONL
        print("   Trying as JSONL format...")
        features = []
        with open(GEOJSON_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        feature = json.loads(line.strip())
                        if 'type' in feature and feature['type'] == 'Feature':
                            features.append(feature)
                    except:
                        pass
        
        if features:
            gdf = gpd.GeoDataFrame.from_features(features)
            print(f"✅ Loaded {len(gdf)} parcels from JSONL")
        else:
            raise ValueError("Could not parse GeoJSON file")
    
    # Find parcel ID column
    parcel_id_col = None
    for col in ['pidn', 'PIDN', 'parcel_id', 'PARCEL_ID', 'accountno', 'ACCOUNTNO']:
        if col in gdf.columns:
            parcel_id_col = col
            break
    
    if parcel_id_col is None:
        print(f"⚠️  Warning: Could not find parcel ID column. Available columns: {list(gdf.columns)[:20]}")
        # Try to infer from properties if it's nested
        if 'properties' in gdf.columns:
            print("   Checking properties column...")
        else:
            raise ValueError("Could not find parcel ID column")
    
    print(f"✅ Using '{parcel_id_col}' as parcel ID column")
    
    # Ensure geometry is valid
    print("   Cleaning geometries...")
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()
    
    # Ensure CRS matches zoning
    if gdf.crs is None:
        print("⚠️  Parcels have no CRS, assuming same as county zoning")
    else:
        print(f"   Parcels CRS: {gdf.crs}")
    
    return gdf, parcel_id_col


def perform_spatial_joins(parcels_gdf, parcel_id_col, county_gdf, toj_gdf):
    """
    Perform spatial joins to find zoning for each parcel.
    Priority: TOJ zoning takes precedence over county zoning.
    """
    print("\n🔍 Performing spatial joins...")
    
    # Ensure CRS matches
    if parcels_gdf.crs != county_gdf.crs:
        print(f"   Converting parcels CRS from {parcels_gdf.crs} to {county_gdf.crs}")
        parcels_gdf = parcels_gdf.to_crs(county_gdf.crs)
    
    # Use centroids for point-in-polygon (faster than within/intersects for large datasets)
    print("   Computing parcel centroids...")
    parcels_gdf['centroid'] = parcels_gdf.geometry.centroid
    parcels_centroids = gpd.GeoDataFrame(
        parcels_gdf[[parcel_id_col]],
        geometry=parcels_gdf['centroid'],
        crs=parcels_gdf.crs
    )
    
    # Join with TOJ zoning (higher priority)
    print("   Joining with TOJ zoning...")
    toj_joined = gpd.sjoin(
        parcels_centroids,
        toj_gdf[['zoning', 'geometry']].rename(columns={'zoning': 'toj_zoning'}),
        how='left',
        predicate='within'
    )
    
    # Join with county zoning
    print("   Joining with county zoning...")
    county_joined = gpd.sjoin(
        parcels_centroids,
        county_gdf[['zoning', 'geometry']].rename(columns={'zoning': 'county_zoning'}),
        how='left',
        predicate='within'
    )
    
    # Merge results: TOJ takes precedence
    print("   Merging results (TOJ takes precedence)...")
    merged = parcels_centroids.merge(
        toj_joined[[parcel_id_col, 'toj_zoning']].drop_duplicates(subset=[parcel_id_col], keep='first'),
        on=parcel_id_col,
        how='left'
    ).merge(
        county_joined[[parcel_id_col, 'county_zoning']].drop_duplicates(subset=[parcel_id_col], keep='first'),
        on=parcel_id_col,
        how='left'
    )
    
    # Build mapping: TOJ takes precedence
    zoning_mapping = {}
    for _, row in tqdm(merged.iterrows(), total=len(merged), desc="Building mapping"):
        parcel_id = row[parcel_id_col]
        if pd.isna(parcel_id):
            continue
        
        parcel_id = str(parcel_id).strip()
        
        # Check TOJ first
        if 'toj_zoning' in row and not pd.isna(row['toj_zoning']):
            zoning = str(row['toj_zoning']).strip()
            if zoning:
                zoning_mapping[parcel_id] = zoning
                continue
        
        # Check county
        if 'county_zoning' in row and not pd.isna(row['county_zoning']):
            zoning = str(row['county_zoning']).strip()
            if zoning:
                zoning_mapping[parcel_id] = zoning
    
    print(f"\n✅ Found zoning for {len(zoning_mapping):,} out of {len(parcels_gdf):,} parcels")
    if len(parcels_gdf) > 0:
        print(f"   Coverage: {len(zoning_mapping)/len(parcels_gdf)*100:.1f}%")
    
    return zoning_mapping


def save_mapping_file(zoning_mapping: Dict[str, str]):
    """Save mapping to text file for VM upload"""
    print(f"\n💾 Saving mapping file to {OUTPUT_MAPPING_FILE}...")
    
    with open(OUTPUT_MAPPING_FILE, 'w') as f:
        # Header
        f.write("# Parcel ID -> Zoning Mapping\n")
        f.write("# Format: parcel_id|zoning\n")
        f.write("# Generated for Teton County WY\n\n")
        
        # Write mapping (sorted for consistency)
        for parcel_id in sorted(zoning_mapping.keys()):
            zoning = zoning_mapping[parcel_id]
            f.write(f"{parcel_id}|{zoning}\n")
    
    print(f"✅ Saved {len(zoning_mapping):,} mappings to {OUTPUT_MAPPING_FILE}")


def update_database(zoning_mapping: Dict[str, str]):
    """Update local database with zoning data"""
    print("\n💾 Updating database...")
    
    init_db()
    
    county = 'teton_county_wy'
    updated_count = 0
    not_found_count = 0
    
    for parcel_id, zoning in tqdm(zoning_mapping.items(), desc="Updating database"):
        # Get existing data
        raw_data = get_latest_raw(county, parcel_id)
        
        if not raw_data:
            not_found_count += 1
            continue
        
        # Update property_raw_data with zoning
        property_raw_data = raw_data.get('property_raw_data') or {}
        
        if isinstance(property_raw_data, dict):
            # Ensure nested structure
            if 'property_data' in property_raw_data:
                property_raw_data['property_data']['zoning'] = zoning
            else:
                property_raw_data['property_data'] = {'zoning': zoning}
        else:
            property_raw_data = {'property_data': {'zoning': zoning}}
        
        # Prepare save bundle
        save_bundle = {
            'tax_raw_data': raw_data.get('tax_raw_data'),
            'property_raw_data': property_raw_data,
            'clerk_raw_data': raw_data.get('clerk_raw_data'),
            'county_links': raw_data.get('county_links'),
            'source': raw_data.get('source', 'zoning_mapper')
        }
        
        # Save updated data
        save_raw(county, parcel_id, save_bundle)
        updated_count += 1
        
        if updated_count % 100 == 0:
            print(f"   Updated {updated_count} parcels...")
    
    print(f"\n✅ Updated {updated_count:,} parcels in database")
    if not_found_count > 0:
        print(f"⚠️  {not_found_count:,} parcels not found in database (may need to be scraped first)")


def main():
    """Main execution"""
    print("=" * 80)
    print("TETON COUNTY WY ZONING MAPPER")
    print("=" * 80)
    
    try:
        # Load zoning shapefiles
        county_gdf, toj_gdf = load_zoning_shapefiles()
        
        # Load parcels
        parcels_gdf, parcel_id_col = load_parcels_geojson()
        
        # Perform spatial joins
        zoning_mapping = perform_spatial_joins(parcels_gdf, parcel_id_col, county_gdf, toj_gdf)
        
        # Show sample
        print("\n📋 Sample mappings:")
        for i, (pid, zoning) in enumerate(list(zoning_mapping.items())[:10]):
            print(f"  {pid} -> {zoning}")
        
        # Show zoning distribution
        print("\n📊 Zoning Distribution:")
        zoning_counts = {}
        for zoning in zoning_mapping.values():
            zoning_counts[zoning] = zoning_counts.get(zoning, 0) + 1
        
        for zoning, count in sorted(zoning_counts.items(), key=lambda x: -x[1])[:20]:
            print(f"  {zoning:20s}: {count:6,} parcels")
        
        # Save mapping file
        save_mapping_file(zoning_mapping)
        
        # Update database
        update_choice = input("\n🤔 Update local database with zoning data? (y/n): ").strip().lower()
        if update_choice == 'y':
            update_database(zoning_mapping)
        else:
            print("⏭️  Skipping database update")
        
        print("\n" + "=" * 80)
        print("✅ COMPLETE!")
        print(f"📄 Mapping file: {OUTPUT_MAPPING_FILE}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

