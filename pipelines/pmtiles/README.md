# PMTiles Pipeline

GeoJSON processing and PMTiles generation pipeline for property ownership data.

## Directory Structure

```
pipelines/pmtiles/
├── main.py                              # Pipeline entry point
├── ownership_pipeline.py                # Core ownership processing
├── download_and_file_config.json        # County download configurations
│
├── counties/                            # County-specific logic
│   ├── base_county.py
│   └── counties.py
│
├── downloading_and_geojson_processing/  # Processing modules
│   ├── base_downloader.py
│   ├── data_standardizer.py
│   ├── data_merger.py
│   ├── cloud_gcs_uploader.py
│   └── lincoln_county_scraper.py
│
├── intermediate_data/                   # Temporary processing files
│   ├── fremont_county_wy_data_files/
│   ├── lincoln_county_wy_data_files/
│   ├── sublette_county_wy_data_files/
│   ├── teton_county_id_data_files/
│   └── teton_county_wy_data_files/
│   └── (Auto-generated during processing, can be deleted after)
│
└── final_parcels/                       # Final processed GeoJSONs
    ├── fremont_county_wy_data_files/
    ├── lincoln_county_wy_data_files/
    ├── sublette_county_wy_data_files/
    ├── teton_county_id_data_files/
    └── teton_county_wy_data_files/
    └── (Used by Search API and Martin tile server)
```

## Data Flow

1. **Download** → `intermediate_data/` - Raw county data
2. **Process** → Standardize, merge, calculate bboxes
3. **Output** → `final_parcels/` - Standardized GeoJSONs
4. **Upload** → GCS (optional) via `scripts/upload_geojsons.py`
5. **Consume** → Search API reads from `final_parcels/`

## Usage

```bash
# Run ownership pipeline
python3 main.py

# Or use the ownership pipeline directly
python3 ownership_pipeline.py
```

## Configuration

County-specific settings in `download_and_file_config.json`:
- Download URLs
- Field mappings
- Standardization rules
- Link templates

## Output

**Final GeoJSONs** (`final_parcels/`):
- Used by Search API for search index generation
- Used by Martin tile server for map rendering
- Standardized format across all counties

**Intermediate Data** (`intermediate_data/`):
- Temporary processing files
- Can be deleted after successful run
- Will be regenerated on next pipeline run

## Dependencies

See `docs/requirements_pmtiles.txt`

## Related

- Martin config: `martin_config.yaml` (root level)
- Upload script: `scripts/upload_geojsons.py`









