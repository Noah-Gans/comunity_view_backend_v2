# PMTiles Pipeline Workflow

Safe 3-step workflow with validation between data generation and deployment.

## 🔄 New Workflow (Recommended)

### Step 1: Generate New GeoJSONs
```bash
cd pipelines/pmtiles
python3 main.py --counties teton_county_wy lincoln_county_wy

# What happens:
# ✅ Archives ALL of final_parcels/ → final_parcels_previous/
#    (Overwrites old archive - only keeps most recent)
# ✅ Clears ALL intermediate_data/
# ✅ Clears ALL final_parcels/
# ✅ Downloads & processes new data (clean directories)
# ✅ Generates new GeoJSONs → final_parcels/
# ⏹️ STOPS - Does NOT upload or generate tiles
```

### Step 2: Validate New Data
```bash
# Compare new vs previous
ls -lh final_parcels/*/
ls -lh final_parcels_previous/*/

# Check feature counts
echo "NEW:"
python3 -c "
import json
with open('final_parcels/teton_county_wy_data_files/teton_county_wy_final_ownership.geojson') as f:
    data = json.load(f)
    print(f'  Features: {len(data[\"features\"])}')
"

echo "PREVIOUS:"
python3 -c "
import json
with open('final_parcels_previous/teton_county_wy_data_files/teton_county_wy_final_ownership.geojson') as f:
    data = json.load(f)
    print(f'  Features: {len(data[\"features\"])}')
"

# Spot check parcels, verify bboxes, etc.
```

### Step 3a: Upload to GCS (After Validation)
```bash
# Only if validation passed!
python3 main.py --upload-only --counties teton_county_wy lincoln_county_wy
```

### Step 3b: Generate Tiles (After Validation)
```bash
# Only if validation passed!
python3 main.py --pmtiles-only --counties teton_county_wy lincoln_county_wy
```

## 📋 Complete Example

```bash
# Day 1: Generate new data
python3 main.py --counties teton_county_wy

# Check the output
ls -lh final_parcels/teton_county_wy_data_files/
# → teton_county_wy_final_ownership.geojson (149MB)

# Compare with old version
ls -lh final_parcels_archive_teton_county_wy_20251019_143022/
# → Compare feature counts, spot check parcels

# Day 2: After validation passes
python3 main.py --upload-only --counties teton_county_wy
python3 main.py --pmtiles-only --counties teton_county_wy

# Done! Safe deployment.
```

## 🚨 Rollback (If Validation Fails)

If the new data has issues:

```bash
# Simple rollback - restore previous version
rm -rf final_parcels/
mv final_parcels_previous/ final_parcels/

# Now you're back to the previous working version
# Fix issues and re-run pipeline
python3 main.py --counties teton_county_wy
```

## 🗂️ Directory Structure During Workflow

```
pipelines/pmtiles/
├── intermediate_data/                   # Working files (cleared each run)
│   └── {county}_data_files/            # Temp files during processing
│
├── final_parcels/                       # NEW data from current run
│   └── {county}_data_files/
│       └── {county}_final_ownership.geojson
│
└── final_parcels_previous/              # OLD data from last run
    └── {county}_data_files/            # For comparison
        └── {county}_final_ownership.geojson
    (Only keeps ONE previous version - overwritten each run)
```

## 🎯 Benefits

1. ✅ **Safe**: Old data archived before deletion
2. ✅ **Validation**: Manual check before upload/tiles
3. ✅ **Rollback**: Can restore from archive if issues
4. ✅ **Flexible**: Upload and tiles are separate steps
5. ✅ **Clear**: Each step has a single purpose

## 📌 Key Changes from Old Flow

**Old Flow (Risky)**:
```
Process → Upload → Tiles (all automatic, no validation)
```

**New Flow (Safe)**:
```
Process → Validate → Upload → Tiles (manual validation gate)
         (You check)
```

## 🔧 All Available Flags

```bash
# Processing
--counties teton_county_wy           # Process specific counties
--county teton_county_wy             # Process single county
--ownership                          # Process all counties

# Workflow (new)
--upload-only                        # Upload validated GeoJSONs to GCS
--pmtiles-only                       # Generate tiles from validated data

# Utilities
--skip-data                          # Use existing intermediate files
```

## ⚡ Quick Reference

```bash
# Generate new data
python3 main.py --counties <county>

# Upload after validation
python3 main.py --upload-only --counties <county>

# Generate tiles after validation  
python3 main.py --pmtiles-only --counties <county>
```

