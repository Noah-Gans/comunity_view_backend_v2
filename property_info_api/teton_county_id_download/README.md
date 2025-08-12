# Teton County Idaho Data Download and Processing

This directory contains scripts to download and process Teton County Idaho's GIS database files for use with our property details API.

## Overview

Teton County Idaho publishes their GIS data as a set of DBF files that are updated nightly. This system:

1. **Downloads** the latest DBF files from their ArcGIS portal
2. **Processes** the files into a structured SQLite database
3. **Creates** a JSON index for quick API lookups
4. **Automates** the process to run nightly

## File Structure

```
teton_county_id_download/
├── download_and_process.py    # Main processing script
├── requirements.txt           # Python dependencies
├── setup_cron.sh             # Cron job setup script
├── README.md                 # This file
├── data/                     # Downloaded DBF files (created automatically)
├── processed/                # Processed database and index files
│   ├── teton_county_id.db   # SQLite database
│   └── parcel_index.json    # API lookup index
└── teton_download.log        # Processing logs
```

## DBF Files Processed

Based on the Teton County documentation, we process these files:

| File | Description | Record Length |
|------|-------------|---------------|
| PCXPAR00.DBF | Related Parcels | 88 |
| PCPARC00.DBF | Parcel Master | 399 |
| PCPARSUM.DBF | Parcel Summary | 567 |
| PCAPPL00.DBF | Appeals | 284 |
| PCLEGL00.DBF | Legal Descriptions | 169 |
| PCNAME00.DBF | Parcel Names | 78 |
| PCCATG00.DBF | Parcel Categories | 84 |
| PCPERM00.DBF | Permits | 191 |
| PCSALE00.DBF | Sales | 65 |
| PCSPEC00.DBF | Special Charges | 54 |
| PCIMPC00.DBF | Improvements | 288 |
| PCICAT00.DBF | Improvement Categories | 64 |
| PCIMAGE0.DBF | Improvement Images | 202 |
| PCLAND00.DBF | Land Records | 91 |
| PCLNDC00.DBF | Land Characteristics | 91 |
| PCOTHI00.DBF | Other Improvements | 84 |

## Database Schema

The processed data is stored in a SQLite database with these tables:

### parcels
- `county_parcel_id` (TEXT, PRIMARY KEY)
- `parcel_status` (TEXT)
- `owner_name` (TEXT)
- `mailing_address_line1` (TEXT)
- `mailing_address_line2` (TEXT)
- `mailing_city` (TEXT)
- `mailing_state` (TEXT)
- `mailing_zip` (TEXT)
- `physical_address` (TEXT)
- `property_zip` (TEXT)
- `deed_reference1-5` (TEXT)
- `total_value` (REAL)
- `improvement_value` (REAL)
- `land_value` (REAL)
- `total_acres` (REAL)
- `zoning` (TEXT)
- `tax_district` (TEXT)
- `last_updated` (TIMESTAMP)

### improvements
- `id` (INTEGER, PRIMARY KEY)
- `county_parcel_id` (TEXT, FOREIGN KEY)
- `improvement_number` (TEXT)
- `dwelling_type` (TEXT)
- `property_address` (TEXT)
- `year_built` (INTEGER)
- `stories` (INTEGER)
- `bedrooms` (INTEGER)
- `bathrooms` (REAL)
- `fireplaces` (INTEGER)
- `first_floor_sqft` (REAL)
- `second_floor_sqft` (REAL)
- `basement_sqft` (REAL)
- `attic_sqft` (REAL)
- `total_sqft` (REAL)
- `siding` (TEXT)
- `roofing` (TEXT)
- `heating_system1-3` (TEXT)
- `improvement_value` (REAL)
- `garage1_sqft` (REAL)
- `garage2_sqft` (REAL)

### legal_descriptions
- `id` (INTEGER, PRIMARY KEY)
- `county_parcel_id` (TEXT, FOREIGN KEY)
- `legal_line1-6` (TEXT)

### land_records
- `id` (INTEGER, PRIMARY KEY)
- `county_parcel_id` (TEXT, FOREIGN KEY)
- `land_category` (INTEGER)
- `land_location` (TEXT)
- `land_class` (INTEGER)
- `land_type` (INTEGER)
- `land_quantity` (REAL)
- `land_unit` (TEXT)
- `land_value` (REAL)

### sales
- `id` (INTEGER, PRIMARY KEY)
- `county_parcel_id` (TEXT, FOREIGN KEY)
- `sale_date` (TEXT)
- `sale_price` (REAL)
- `valid_sale` (TEXT)
- `personal_property_included` (TEXT)

### permits
- `id` (INTEGER, PRIMARY KEY)
- `county_parcel_id` (TEXT, FOREIGN KEY)
- `permit_ref_number` (TEXT)
- `permit_filing_date` (TEXT)
- `permit_description` (TEXT)
- `permit_type` (TEXT)

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up automated nightly runs:**
   ```bash
   chmod +x setup_cron.sh
   ./setup_cron.sh
   ```

## Usage

### Manual Run
```bash
cd teton_county_id_download
python3 download_and_process.py
```

### Check Status
```bash
# View cron jobs
crontab -l

# Check logs
tail -f teton_download.log

# Check processed data
ls -la processed/
```

### API Integration

The processed data can be accessed by your API through:

1. **SQLite Database:** `processed/teton_county_id.db`
2. **JSON Index:** `processed/parcel_index.json`

Example API query:
```python
import sqlite3

conn = sqlite3.connect('teton_county_id_download/processed/teton_county_id.db')
cursor = conn.cursor()

# Get parcel details
cursor.execute('''
    SELECT p.*, i.* 
    FROM parcels p 
    LEFT JOIN improvements i ON p.county_parcel_id = i.county_parcel_id 
    WHERE p.county_parcel_id = ?
''', ('PAR_14_VALUE',))

parcel_data = cursor.fetchall()
```

## Troubleshooting

### Download Issues
- The script requires manual download URL setup initially
- Check `teton_download.log` for specific errors
- Verify network connectivity to ArcGIS portal

### Processing Issues
- Ensure all DBF files are present in `data/` directory
- Check file permissions and disk space
- Verify Python dependencies are installed

### Cron Job Issues
- Check cron logs: `tail -f /var/log/cron`
- Verify script permissions: `chmod +x download_and_process.py`
- Test manual run first

## Data Source

- **Portal:** [Teton County Idaho ArcGIS Portal](https://tetonidaho.maps.arcgis.com/home/item.html?id=67907b10787449bcb1aaa4bdb23ca77c)
- **Update Frequency:** Nightly
- **Format:** DBF files (dBase format)
- **Total Files:** 16+ DBF files

## Field Mapping

The script maps DBF fields to our canonical structure:

| DBF Field | Canonical Field | Description |
|-----------|-----------------|-------------|
| PM_PAR_14 | county_parcel_id | Parcel identifier |
| PM_MAIL_NM | owner_name | Property owner |
| PM_PROP_AD | physical_address | Street address |
| PM_TOT_VAL | total_value | Total property value |
| PM_IMP_VAL | improvement_value | Building value |
| PM_LND_VAL | land_value | Land value |
| PM_PV_ACRE | total_acres | Total acreage |

## Performance

- **Processing Time:** ~5-10 minutes for full dataset
- **Database Size:** ~50-100MB depending on data volume
- **Memory Usage:** ~200MB during processing
- **Storage:** ~500MB total (raw + processed)

## Maintenance

- **Log Rotation:** Logs are appended, consider rotation for long-term use
- **Database Backup:** Consider backing up `teton_county_id.db` regularly
- **Disk Space:** Monitor `data/` and `processed/` directories
- **Updates:** Check for changes in DBF file structure or field definitions 