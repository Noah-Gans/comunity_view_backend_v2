# Report Database

This directory contains the shared database used by multiple backend services.

## Structure

```
report_db/
├── storage/
│   ├── db.py                  # Database access functions
│   └── property_data.db       # SQLite database (shared by all services)
└── README.md
```

## Database

**Location**: `report_db/storage/property_data.db`

**Used by**:
- `property_info_api` - Writes scraped data
- `report_builder_api` - Reads cached data for reports
- `report_builder` - Bulk collection scripts

**Schema**: See `db.py` for table definitions

## Functions

### `init_db()`
Initialize the database and create tables if they don't exist.

### `get_latest_raw(county: str, county_parcel_id: str)`
Get the latest cached data for a parcel.

### `save_raw(county: str, county_parcel_id: str, bundle: dict)`
Save scraped data to the database.

## Usage

```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from report_db.storage.db import init_db, get_latest_raw, save_raw

# Initialize
init_db()

# Get data
data = get_latest_raw("teton_county_wy", "R0012345")

# Save data
save_raw("teton_county_wy", "R0012345", {
    "tax_raw_data": {...},
    "property_raw_data": {...},
    "clerk_raw_data": {...}
})
```

