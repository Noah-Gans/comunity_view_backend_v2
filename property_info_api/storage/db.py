import os
import json
import sqlite3
from typing import Optional, Dict, Any
from pathlib import Path

def _get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "property_info_api/storage/property_data.db")

def init_db() -> None:
    # Create table if it doesn't exist
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS property_raw (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          county TEXT NOT NULL,
          county_parcel_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          tax_raw_data TEXT,
          property_raw_data TEXT,
          clerk_raw_data TEXT,
          county_links TEXT,
          source TEXT,
          collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (county, county_parcel_id, version)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_property_raw_lookup
          ON property_raw (county, county_parcel_id, version)
        """)
    print("Database initialized successfully")

def close_db() -> None:
    pass

def _next_version(county: str, parcel_id: str) -> int:
    with sqlite3.connect(_get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM property_raw WHERE county=? AND county_parcel_id=?",
            (county, parcel_id),
        )
        row = cursor.fetchone()
        return int(row[0]) + 1

def save_raw(county: str, county_parcel_id: str, bundle: Dict[str, Any], version: Optional[int] = None) -> int:
    v = version if version is not None else _next_version(county, county_parcel_id)

    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO property_raw (
              county, county_parcel_id, version,
              tax_raw_data, property_raw_data, clerk_raw_data, county_links, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                county,
                county_parcel_id,
                v,
                json.dumps(bundle.get("tax_raw_data")) if bundle.get("tax_raw_data") is not None else None,
                json.dumps(bundle.get("property_raw_data")) if bundle.get("property_raw_data") is not None else None,
                json.dumps(bundle.get("clerk_raw_data")) if bundle.get("clerk_raw_data") is not None else None,
                json.dumps(bundle.get("county_links")) if bundle.get("county_links") is not None else None,
                bundle.get("source"),
            ),
        )
    return v

def get_latest_raw(county: str, county_parcel_id: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT county, county_parcel_id, version,
                   tax_raw_data, property_raw_data, clerk_raw_data, county_links,
                   source, collected_at
            FROM property_raw
            WHERE county=? AND county_parcel_id=?
            ORDER BY version DESC
            LIMIT 1  -- Only get the latest record!
            """,
            (county, county_parcel_id),
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Use only the latest record, don't merge
        return {
            "county": row["county"],
            "county_parcel_id": row["county_parcel_id"],
            "version": row["version"],
            "tax_raw_data": json.loads(row["tax_raw_data"]) if row["tax_raw_data"] else None,
            "property_raw_data": json.loads(row["property_raw_data"]) if row["property_raw_data"] else None,
            "clerk_raw_data": json.loads(row["clerk_raw_data"]) if row["clerk_raw_data"] else None,
            "county_links": json.loads(row["county_links"]) if row["county_links"] else None,
            "source": row["source"],
            "collected_at": row["collected_at"]
        }

def debug_database_contents():
    """Print all unique counties and sample data in the database"""
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get unique counties
        cursor = conn.execute("SELECT DISTINCT county FROM property_raw ORDER BY county")
        counties = [row[0] for row in cursor.fetchall()]
        print(f"[DB DEBUG] Unique counties: {counties}")
        
        # Get count per county
        cursor = conn.execute("SELECT county, COUNT(*) as count FROM property_raw GROUP BY county ORDER BY county")
        for row in cursor.fetchall():
            print(f"[DB DEBUG] {row['county']}: {row['count']} records")
        
        # Get sample records (first 3 from each county)
        for county in counties:
            cursor = conn.execute(
                "SELECT county_parcel_id, version, source, collected_at FROM property_raw WHERE county = ? ORDER BY collected_at DESC LIMIT 3",
                (county,)
            )
            print(f"[DB DEBUG] Sample records for {county}:")
            for row in cursor.fetchall():
                print(f"  - parcel_id: {row['county_parcel_id']}, version: {row['version']}, source: {row['source']}, collected: {row['collected_at']}")

def import_scraped_data():
    """Import all scraped data files into the database"""
    
    # Initialize database
    init_db()
    
    # Path to scraped data
    project_root = Path(__file__).parent.parent.parent
    scraped_dir = project_root / "report_builder" / "scraped_data_download"
    
    if not scraped_dir.exists():
        print(f"Scraped data directory not found: {scraped_dir}")
        return
    
    # Group data by parcel_id first
    parcel_data = {}
    
    # Process all .jsonl files
    for jsonl_file in scraped_dir.glob("*.jsonl"):
        print(f"Processing {jsonl_file.name}...")
        
        with open(jsonl_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    
                    # Extract county from filename
                    filename = jsonl_file.stem
                    county = filename.split('_')[0] + '_' + filename.split('_')[1] + '_' + filename.split('_')[2]
                    
                    parcel_id = data.get('parcel_id')
                    if not parcel_id:
                        print(f"  Skipping line {line_num}: No parcel_id found")
                        continue
                    
                    # Initialize parcel if not exists
                    if parcel_id not in parcel_data:
                        parcel_data[parcel_id] = {
                            'county': county,
                            'parcel_id': parcel_id,
                            'source': 'scraped_import'
                        }
                    
                    # Add data type to parcel
                    if 'tax_data' in filename:
                        parcel_data[parcel_id]['tax_raw_data'] = data
                    elif 'property_data' in filename:
                        parcel_data[parcel_id]['property_raw_data'] = data
                    elif 'clerk_data' in filename:
                        parcel_data[parcel_id]['clerk_raw_data'] = data
                        
                except json.JSONDecodeError as e:
                    print(f"  Error parsing line {line_num}: {e}")
                except Exception as e:
                    print(f"  Error processing line {line_num}: {e}")
    
    # Now save each parcel as a single record
    imported_count = 0
    for parcel_id, bundle in parcel_data.items():
        version = save_raw(bundle['county'], parcel_id, bundle)
        imported_count += 1
        
        if imported_count % 100 == 0:
            print(f"  Imported {imported_count} records...")
    
    print(f"Import complete! Imported {imported_count} records total.")

if __name__ == "__main__":
    import_scraped_data()