# ComunityView Backend Architecture

## Overview

Multi-VM architecture for property data collection and API services.

## System Architecture

```
┌─────────────────────────────────────┐
│  VM1 - API Services (9000-9002)    │
├─────────────────────────────────────┤
│  • Search API (9000)                │
│  • Property API (9001)              │
│  • Report API (9002)                │
│  • Martin Tile Server (9003)        │
└─────────────────────────────────────┘
           ↕
┌─────────────────────────────────────┐
│  Shared Database                    │
│  shared/database/storage/           │
│  property_data.db (545MB)           │
└─────────────────────────────────────┘
           ↕
┌─────────────────────────────────────┐
│  VM2 - Processing Pipelines        │
├─────────────────────────────────────┤
│  • Bulk Collector                   │
│  • PMTiles Generator                │
└─────────────────────────────────────┘
```

## Directory Structure

```
comunity_view_backend_v2/
├── services/                   # VM1 - API Services
│   ├── property_api/          # Port 9001 - Individual parcel data
│   ├── report_api/            # Port 9002 - Bulk cached data
│   └── search_api/            # Port 9000 - Property search
│
├── pipelines/                  # VM2 - Heavy Processing
│   ├── bulk_collector/        # Mass data collection
│   └── pmtiles/              # GeoJSON → PMTiles conversion
│
├── shared/
│   └── database/             # Shared SQLite database
│
├── scripts/
│   ├── vm1_services/         # API server scripts
│   └── vm2_pipelines/        # Processing server scripts
│
└── tiles/                    # Martin tile server output
```

## Port Allocation

**VM1 Services:**
- `9000` - Martin Tile Server (PMTiles/vector tiles)
- `9001` - Search API
- `9002` - Property API (single instance)
- `9003` - Report API
- `9011-9013` - Property API (load balanced - 3 instances)

**VM2 Pipelines:**
- No exposed ports (batch jobs only)

### Load Balancing
For high-traffic scenarios, use `start_property_multi.sh` to run 3 Property API instances on ports 9011, 9012, 9013. Then configure nginx/load balancer to distribute requests across them.

## Services

### Martin Tile Server (9000)
- **Purpose**: Serve vector tiles (PMTiles)
- **Usage**: Map layer rendering
- **Data Source**: `tiles/` directory
- **Location**: `pipelines/pmtiles/`

### Search API (9001)
- **Purpose**: Full-text search across properties
- **Usage**: Property discovery
- **Data Source**: `search_index.json`

### Property API (9002)
- **Purpose**: Individual parcel details with scraping
- **Usage**: Map detail views (click on parcel)
- **Flow**: Cache → Scrape → Save → Return

### Report API (9003)
- **Purpose**: Bulk cached data retrieval
- **Usage**: Report generation from polygon selection
- **Flow**: Cache only (fast)

## Data Flow

1. **Collection**: VM2 bulk collector → shared database
2. **API Access**: VM1 reads from shared database
3. **Updates**: VM2 runs nightly updates
4. **Search Index**: Generated from database periodically

## Deployment

See `DEPLOYMENT_VM1.md` and `DEPLOYMENT_VM2.md` for detailed deployment instructions.

