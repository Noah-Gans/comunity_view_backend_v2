# Report Builder API

Fast batch retrieval of cached property data for report generation.

## Overview

This API provides bulk access to cached property data stored in the shared database. Unlike `property_info_api` which scrapes individual parcels, this service is optimized for retrieving multiple parcels at once for report generation.

## Features

- ✅ **Fast Bulk Retrieval**: Query multiple parcels in a single request
- ✅ **Cache-Only**: No scraping, only returns already-collected data
- ✅ **Shared Database**: Uses same database as `property_info_api`
- ✅ **Detailed Data**: Returns tax, property, and clerk data for each parcel
- ✅ **Data Standardization**: All responses are standardized using config-driven mapping
- ✅ **County-Specific Mapping**: Config files define how raw data is transformed per county

## API Endpoints

### `GET /` 
API information and available endpoints

### `GET /health`
Health check endpoint

### `GET /stats`
Database statistics (total records, parcels by county, etc.)

### `POST /batch-retrieve`
Retrieve cached data for multiple parcels. **Processes parcels concurrently** for optimal performance.

**Features:**
- ✅ **Concurrent Processing**: Up to 50 parallel database queries
- ✅ **Batch Size Limits**: Maximum 1000 parcels per request (configurable)
- ✅ **Automatic Throttling**: Semaphore prevents database overload
- ✅ **Fast**: ~10ms per parcel for typical requests

**Request Body:**
```json
{
  "parcels": [
    {
      "county": "teton_county_wy",
      "county_parcel_id": "22-41-17-22-1-01-020"
    },
    {
      "county": "teton_county_wy",
      "county_parcel_id": "22-42-16-10-2-07-003"
    }
  ]
}
```

**Configuration** (via environment variables):
- `MAX_BATCH_SIZE` - Maximum parcels per request (default: 1000)
- `MAX_CONCURRENT_DB_QUERIES` - Parallel database queries (default: 50)

**Response:**
```json
{
  "total_requested": 2,
  "total_found": 1,
  "total_missing": 1,
  "processing_time_ms": 12.45,
  "parcels": [
    {
      "county": "teton_county_wy",
      "county_parcel_id": "R0012345",
      "found": true,
      "tax_data": { /* ... */ },
      "property_data": { /* ... */ },
      "clerk_data": { /* ... */ },
      "collected_at": "2025-10-17 10:30:45"
    },
    {
      "county": "lincoln_county_wy",
      "county_parcel_id": "L0009876",
      "found": false,
      "tax_data": null,
      "property_data": null,
      "clerk_data": null,
      "collected_at": null
    }
  ]
}
```

## Installation

```bash
cd report_builder_api
pip install -r requirements.txt
```

## Running the API

```bash
./start_api.sh
```

The API will start on `http://localhost:9003`

## Testing

See `test_api.sh` for example curl commands.

## Architecture

```
Frontend (draws polygon)
    ↓
Gets list of parcels from map
    ↓
POST /batch-retrieve → Report Builder API (port 9003)
    ↓
Queries shared database
    ↓
Data Standardizer applies county-specific configs
    ↓
Returns standardized data for all parcels
```

## Related Services

- **property_info_api** (port 8001): Individual parcel scraping with caching
- **search_api** (port 8000): Property search functionality
- **report_builder_api** (port 9003): Bulk cached data retrieval with standardization (this service)

## Database

Shares the same SQLite database with `property_info_api`:
- Location: `../shared/database/storage/property_data.db`
- Read-only access for this service
- Data populated by `property_info_api` and bulk collection scripts

## Data Standardization

All responses are standardized using the same `DataStandardizer` used by `property_info_api`. 
County-specific config files in `configs/` define how raw data from different sources is mapped 
to a consistent format.

### Configuration Files

- `configs/teton_county_wy.json` - Teton County, WY mappings
- `configs/lincoln_county_wy.json` - Lincoln County, WY mappings
- `configs/sublette_county_wy.json` - Sublette County, WY mappings
- `configs/fremont_county_wy.json` - Fremont County, WY mappings
- `configs/teton_county_id.json` - Teton County, ID mappings

Each config file defines:
- Field mappings with priority ordering
- Data transformations (formatting, calculations, etc.)
- Historical data standardization rules
- Development data processing rules

