# ComunityView Backend v2

Multi-VM backend architecture for property data collection and API services.

## 🏗️ Architecture

- **VM1**: API Services (ports 9000-9002)
- **VM2**: Heavy Processing Pipelines

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detailed architecture.

## 🚀 Quick Start

### VM1 - API Services

Start all services:
```bash
./scripts/vm1_services/start_all.sh
```

Stop all services:
```bash
./scripts/vm1_services/stop_all.sh
```

Individual services:
```bash
# Martin tile server runs on port 9000 (see pipelines/pmtiles/martin_config.yaml)
cd services/search_api && python3 start_api.py      # Port 9001
cd services/property_api && ./start_api.sh          # Port 9002
cd services/report_api && ./start_api.sh            # Port 9003
```

Load balanced Property API (3 instances):
```bash
./scripts/vm1_services/start_property_multi.sh      # Ports 9011-9013
```

### VM2 - Processing Pipelines

Bulk data collection:
```bash
./scripts/vm2_pipelines/start_bulk_collector.sh
```

## 📁 Directory Structure

```
comunity_view_backend_v2/
├── services/           # VM1 - API Services (9000-9002)
│   ├── property_api/   # Individual parcel data
│   ├── report_api/     # Bulk cached data retrieval
│   └── search_api/     # Property search
│
├── pipelines/          # VM2 - Heavy Processing
│   ├── bulk_collector/ # Mass data collection
│   └── pmtiles/       # GeoJSON → PMTiles conversion
│
├── shared/
│   └── database/      # Shared SQLite database (545MB)
│
├── scripts/
│   ├── vm1_services/  # API server scripts
│   └── vm2_pipelines/ # Processing scripts
│
└── docs/              # Documentation
```

## 🌐 API Endpoints

| Service | Port | Purpose |
|---------|------|---------|
| **Martin Tile Server** | 9000 | Vector tiles (PMTiles) |
| **Search API** | 9001 | Property search |
| **Property API** | 9002 | Individual parcel details |
| **Report API** | 9003 | Bulk cached data for reports |
| **Property API (Multi)** | 9011-9013 | Load balanced instances (optional) |

## 📊 Database

**Location**: `shared/database/storage/property_data.db`

**Size**: 545MB

**Shared by**: All API services

## 🧪 Testing

Test Report API:
```bash
curl http://localhost:9003/health
curl -X POST http://localhost:9003/batch-retrieve \
  -H "Content-Type: application/json" \
  -d '{"parcels":[{"county":"teton_county_wy","county_parcel_id":"22-41-17-22-1-01-020"}]}'
```

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Documentation](http://localhost:9001/docs) (when running)

## 🔄 Data Flow

1. VM2 bulk collector → shared database
2. VM1 APIs read from shared database
3. Frontend → VM1 APIs → Response

## 🛠️ Development

Each service has its own virtual environment:
- `services/property_api/venv/`
- Root `venv/` for other scripts

## 📝 Notes

- Port 9000+ used to avoid conflicts between local and VM
- Bulk collector runs on separate VM due to resource requirements
- Martin tile server output goes to `tiles/` directory

