# Report API - VM Deployment Notes

## ✅ What's Been Set Up

The Report API is now integrated with data standardization and ready for VM deployment.

### **Key Features:**
- ✅ **Data Standardization**: All responses use county-specific configs
- ✅ **Standalone Setup**: Creates its own venv on first run
- ✅ **Auto-dependencies**: Installs required packages automatically
- ✅ **Error Handling**: Checks port availability and validates setup
- ✅ **Testing**: Test script updated with real parcel IDs

### **Files Added/Modified:**
1. `data_standardizer.py` - Copied from property_api
2. `configs/` - All 5 county config files copied
3. `start_api.sh` - Enhanced with proper VM setup
4. `requirements.txt` - Updated to compatible versions
5. `test_api.sh` - Updated with real parcel IDs
6. `README.md` - Updated documentation

## 🚀 Deployment on VM

### **Option 1: Quick Start**
```bash
cd services/report_api
chmod +x start_api.sh
./start_api.sh
```

The script will:
- Create venv if it doesn't exist
- Install all dependencies
- Check if port 9003 is free
- Start the API

### **Option 2: Use start_all.sh**
```bash
cd scripts/vm1_services
./start_all.sh
```

This starts all APIs including Report API (port 9003).

## 📊 What It Returns

For each parcel, the API returns standardized data with:

1. **Tax Data**: Current year taxes, payment history, due dates
2. **Property Data**: Values, acreage, buildings/developments
3. **Clerk Data**: Deeds, mortgages, liens, easements

All data is standardized using county-specific configs for consistent format.

## 🗄️ Database

- Shares database with property_api: `shared/database/storage/property_data.db`
- Uses relative path that works on VM
- Data is populated by property_api and bulk collectors

## 🧪 Testing

```bash
# Health check
curl http://localhost:9003/health

# Test single parcel
curl -X POST http://localhost:9003/batch-retrieve \
  -H "Content-Type: application/json" \
  -d '{"parcels": [{"county": "teton_county_wy", "county_parcel_id": "22-41-17-22-1-01-020"}]}'

# Run full test suite
cd services/report_api
./test_api.sh
```

## 📝 Example Response

```json
{
  "total_requested": 1,
  "total_found": 1,
  "total_missing": 0,
  "processing_time_ms": 9.48,
  "parcels": [{
    "county": "teton_county_wy",
    "county_parcel_id": "22-41-17-22-1-01-020",
    "found": true,
    "tax_data": {
      "status": "success",
      "data": { /* standardized tax data */ }
    },
    "property_data": {
      "status": "success",
      "data": { /* standardized property data */ }
    },
    "clerk_data": {
      "status": "success",
      "data": { /* standardized clerk data */ }
    }
  }]
}
```

## 🔧 Configuration

County-specific configs in `configs/`:
- `teton_county_wy.json`
- `lincoln_county_wy.json`
- `sublette_county_wy.json`
- `fremont_county_wy.json`
- `teton_county_id.json`

## ✅ Ready to Deploy

The Report API is fully functional and ready for VM deployment. No additional setup needed beyond running `./start_api.sh` on your VM.








