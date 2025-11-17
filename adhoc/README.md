# Ad-hoc Scripts

This folder contains one-off scripts for special data processing tasks.

## backfill_teton_zoning_and_links.py

Backfills Teton County WY parcels with:
1. **Zoning data** - Fetched from ArcGIS REST API using account numbers
2. **County links** - Extracted from the geojson file (clerk_rec, property_det, tax_info, map_no, deed_no, smart_gov)

### Usage

```bash
python3 adhoc/backfill_teton_zoning_and_links.py
```

### What it does

1. **Loads geojson lookup**: Reads `teton_county_wy_ownership_complete.geojson` and creates a lookup by `pidn` (county_parcel_id) to get:
   - Account numbers
   - Zoning (if already in geojson)
   - All county links

2. **Fetches all Teton County WY parcels** from the database

3. **For each parcel**:
   - Matches with geojson data by `pidn` (county_parcel_id)
   - Gets account number from geojson (or from existing property_raw_data)
   - Fetches zoning from ArcGIS API if not already in geojson
   - Updates `property_raw_data.property_data.zoning` with the zoning code
   - Updates `county_links` with all links from geojson

4. **Reports progress** every 100 parcels and provides a final summary

### Requirements

- Database must be initialized (`shared/database/storage/property_data.db`)
- Geojson file must exist at: `pipelines/pmtiles/intermediate_data/teton_county_wy_data_files/teton_county_wy_ownership_complete.geojson`
- Internet connection for ArcGIS API calls
- Python packages: `requests`, `sqlite3` (standard library)

### Notes

- The script includes a 0.1 second delay between API calls to avoid rate limiting
- If a parcel doesn't have geojson data, it's skipped
- If a parcel doesn't have an account number, zoning fetching is skipped but links are still added
- The script updates existing records in the database, preserving all other data


