# Backend Reorganization Summary

**Date**: October 18, 2025  
**Status**: ✅ Complete

## What Changed

### 1. Directory Restructure

**Before**:
```
comunity_view_backend_v2/
├── property_info_api/
├── report_builder_api/
├── search_api/
├── report_builder/
├── PMTiles_Cycle/
└── report_db/
```

**After**:
```
comunity_view_backend_v2/
├── services/              # VM1 - All API services
│   ├── property_api/
│   ├── report_api/
│   └── search_api/
├── pipelines/            # VM2 - Heavy processing
│   ├── bulk_collector/
│   └── pmtiles/
├── shared/
│   └── database/        # Shared database
├── scripts/
│   ├── vm1_services/    # API startup scripts
│   └── vm2_pipelines/   # Pipeline scripts
└── tiles/               # Martin tile output
```

### 2. Port Changes (9000+)

| Service | Old Port | New Port |
|---------|----------|----------|
| Search API | 8000 | **9000** |
| Property API | 8001 | **9001** |
| Report API | 8010 | **9002** |

**Reason**: Eliminates conflicts between local and VM environments.

### 3. Name Changes

| Old Name | New Name | Reason |
|----------|----------|--------|
| `property_info_api` | `services/property_api` | Shorter, clearer |
| `report_builder_api` | `services/report_api` | Shorter, clearer |
| `report_builder` | `pipelines/bulk_collector` | Clearer purpose |
| `PMTiles_Cycle` | `pipelines/pmtiles` | Standard naming |
| `report_db` | `shared/database` | Clearer purpose |

### 4. Import Path Updates

**Before**:
```python
from report_db.storage.db import init_db
```

**After**:
```python
from shared.database.storage.db import init_db
```

## How to Use

### Start All Services (VM1)

```bash
# From project root
./scripts/vm1_services/start_all.sh
```

This starts:
- Search API on port 9000
- Property API on port 9001
- Report API on port 9002

### Start Individual Service

```bash
cd services/search_api && python3 start_api.py      # Port 9000
cd services/property_api && ./start_api.sh          # Port 9001  
cd services/report_api && ./start_api.sh            # Port 9002
```

### Stop All Services

```bash
./scripts/vm1_services/stop_all.sh
```

### Run Bulk Collector (VM2)

```bash
./scripts/vm2_pipelines/start_bulk_collector.sh
```

## Testing After Migration

### Test Report API (Port 9002)
```bash
# Health check
curl http://localhost:9002/health

# Batch retrieve
curl -X POST http://localhost:9002/batch-retrieve \
  -H "Content-Type: application/json" \
  -d '{"parcels":[{"county":"teton_county_wy","county_parcel_id":"22-41-17-22-1-01-020"}]}'
```

### Test Property API (Port 9001)
```bash
# Health check
curl http://localhost:9001/docs
```

### Test Search API (Port 9000)
```bash
# Health check
curl http://localhost:9000/health

# Search
curl "http://localhost:9000/search?q=carlman&limit=10"
```

## Files Cleaned Up

- ✅ Removed `start_all_apis.sh` from root
- ✅ Removed `start_report_builder_api.sh` from root
- ✅ Moved all startup scripts to `scripts/`
- ✅ Removed obsolete database location references

## What Still Needs Attention

### Optional Cleanup (Property API)

These files might be removable:
- `services/property_api/capture_raw_data.py` - Seems unused
- `services/property_api/report_builder/` - Duplicate data?
- `services/property_api/storage/` - Old database location (empty now)

### Documentation to Update

If you have deployment docs, update:
- Port references (8000→9000, 8001→9001, 8010→9002)
- Path references (old directory names)

## Database Location

**New location**: `shared/database/storage/property_data.db`

**Size**: 545MB

**Accessed by**:
- Property API (9001)
- Report API (9002)
- Bulk Collector pipeline

## VM Deployment

### VM1 (API Server)
Deploy these directories:
- `services/`
- `shared/database/`
- `scripts/vm1_services/`

### VM2 (Processing Server)
Deploy these directories:
- `pipelines/`
- `shared/database/` (or network access to VM1's database)
- `scripts/vm2_pipelines/`

## Benefits of New Structure

1. ✅ **Clear separation**: APIs vs pipelines
2. ✅ **Port consistency**: No conflicts between local/VM
3. ✅ **Better organization**: Services grouped logically
4. ✅ **VM-specific scripts**: Easy deployment per VM
5. ✅ **Scalable**: Easy to add new services/pipelines

## Rollback (If Needed)

If something breaks, you can reference old ports/paths temporarily:
- Old ports are commented in code
- Git history has all old directory names
- Database wasn't changed, just moved

## Next Steps

1. ✅ Test all APIs on new ports
2. ✅ Update frontend to use ports 9000-9002
3. ✅ Update any CI/CD pipelines
4. ✅ Update deployment documentation
5. ✅ Deploy to VMs with new structure

