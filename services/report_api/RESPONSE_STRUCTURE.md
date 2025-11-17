# Report API Response Structure

## For Frontend Integration

### API Endpoint
```
POST http://localhost:9003/batch-retrieve
```

### Request Format
```json
{
  "parcels": [
    {"county": "teton_county_wy", "county_parcel_id": "22-41-17-22-1-01-020"}
  ]
}
```

### Response Structure

```json
{
  "total_requested": 1,
  "total_found": 1,
  "total_missing": 0,
  "processing_time_ms": 7.03,
  "parcels": [
    {
      "county": "teton_county_wy",
      "county_parcel_id": "22-41-17-22-1-01-020",
      "found": true,
      "collected_at": "2025-10-18 19:06:28",
      
      // ┌─────────────────────────────────────────────────────────────┐
      // │ 1. GENERAL INFO                                              │
      // └─────────────────────────────────────────────────────────────┘
      "general_info": {
        "county_state": null,
        "owner_name": "CARLMAN, LEONARD R. & ANN LADD ",
        "physical_address": "4980 H-H-R RANCH ROAD",
        "mailing_address": "PO BOX 1230, WILSON, WY, 830141230",
        "county_parcel_id": "22-41-17-22-1-01-020",
        "tax_id": "04-002797",
        "account_number": "R0008450",
        "acres": "5.45",
        "county_links": {
          "tax_records": "https://gis.tetoncountywy.gov/portal/...",
          "property_details": "https://gis.tetoncountywy.gov/portal/...",
          "clerk_records": "https://gis.tetoncountywy.gov/portal/..."
        }
      },

      // ┌─────────────────────────────────────────────────────────────┐
      // │ 2. TAX DATA                                                  │
      // └─────────────────────────────────────────────────────────────┘
      "tax_data": {
        "status": "success",
        "message": "Tax data retrieved successfully",
        "data": {
          "county": "Teton County Wy",
          "tax_id": "04-002797",
          "tax_year": 2025,
          "assessed_value": null,
          "taxable_value": null,
          "tax_amount": 18350.73,
          "first_half_due_date": "09/01/2025",
          "second_half_due_date": "03/01/2025",
          "status": "unpaid",
          "tax_district": "0121",
          "mill_levy": 56.799,
          "account_number": "R0008450",
          "owner_name": "CARLMAN, LEONARD R. & ANN LADD ",
          "property_address": "4980 H-H-R RANCH ROAD",
          "total_tax_levied": 18350.73,
          "tax_received": 0,
          "amount_due": 18350.73,
          "first_half_levied": 9175.37,
          "first_half_paid": 0,
          "second_half_levied": 9175.36,
          "second_half_paid": 0,
          "historical_data": [
            {
              "year": 2024,
              "tax_levied": 18541.82,
              "tax_paid": 18541.82,
              "date_paid": "2024-11-05",
              "amount_due": 18541.82,
              "first_half": {
                "tax_levied": 9270.91,
                "tax_paid": 9270.91,
                "date_paid": "2024-11-05",
                "amount_due": 18541.82
              },
              "second_half": {
                "tax_levied": 9270.91,
                "tax_paid": 9270.91,
                "date_paid": "2024-11-05",
                "amount_due": 18541.82
              }
            }
            // ... more historical years
          ]
        },
        "source": "teton_county_wy_tax_api_combined",
        "timestamp": "2025-11-02T09:51:33.290344"
      },

      // ┌─────────────────────────────────────────────────────────────┐
      // │ 3. PROPERTY DETAILS                                          │
      // └─────────────────────────────────────────────────────────────┘
      "property_data": {
        "status": "success",
        "message": "Property data retrieved successfully",
        "data": {
          "county": "Teton County Wy",
          "county_parcel_id": "22-41-17-22-1-01-020",
          "tax_id": "04-002797",
          "physical_address": "4980 H-H-R RANCH ROAD",
          "mailing_address": "PO BOX 1230, WILSON, WY, 830141230",
          "owner_name": "CARLMAN, LEONARD R. & ANN LADD ",
          "legal_description": "LOT 12, H-H-R RANCHES",
          "total_property_value": "5670607",
          "land_value": "4219087",
          "developments_value": "1451520",
          "total_acreage": "5.45",
          "acreage_breakdown": {
            "residential": 5.45,
            "agricultural": 0.0,
            "commercial": 0.0,
            "industrial": 0.0,
            "other": 0.0
          },
          "num_developments": 1,
          "developments": [
            {
              "id": 1.0,
              "description": "2 Story",
              "stories": 2.0,
              "sq_ft": "3946",
              "exterior": "Frame Siding",
              "roof_cover": "Wood Shake",
              "bedrooms": 3.0,
              "year_built": 1999
            }
          ]
        },
        "source": "property_scraper_teton_county_wy",
        "timestamp": "2025-11-02T09:51:33.290478"
      },

      // ┌─────────────────────────────────────────────────────────────┐
      // │ 4. CLERK RECORDS                                             │
      // └─────────────────────────────────────────────────────────────┘
      "clerk_data": {
        "status": "success",
        "message": "Clerk data retrieved successfully",
        "data": {
          "records_count": 34,
          "records": [
            {
              "entrynumber": "1043711",
              "dateofinstrument": "2022-08-02",
              "datetimeoffiling": "2022-08-02",
              "statepin": "22-41-17-22-1-01-020",
              "description": "COVENANTS",
              "beginningpage": null,
              "endingpage": null,
              "subdivision": "H H R RANCHES",
              "township": "",
              "range": "",
              "section": null,
              "record_url": "https://s3.us-west-2.amazonaws.com/tetoncountywy/clerk/pdf/1043711.pdf",
              "book": "358",
              "legal": "LOT 12, H-H-R RANCHES",
              "grantor": "HHR RANCHES HOMEOWNERS ASSOCIATION",
              "grantee": "THE PUBLIC"
            }
            // ... more records
          ],
          "source": "teton_county_wy_clerk_api",
          "scraped": true,
          "timestamp": "2025-10-18T13:06:28.347489"
        },
        "source": "teton_county_wy_clerk_api",
        "timestamp": "2025-11-02T09:51:33.290547"
      }
    }
  ]
}
```

## Key Sections

### Top-Level Fields
- `county` - County code
- `county_parcel_id` - Parcel identifier
- `found` - Whether parcel exists in database
- `collected_at` - When data was collected

### 1. **General Info** (`general_info`)
- Owner name and addresses
- Basic identifiers (tax_id, account_number)
- Acreage
- **county_links** - Direct links to county websites for tax, property, and clerk records

### 2. **Tax Data** (`tax_data.data`)
**Current Year:**
- `tax_year`, `tax_amount`, `status`
- `first_half_due_date`, `second_half_due_date`
- `total_tax_levied`, `tax_received`, `amount_due`
- Payment breakdown for each half

**Historical:**
- Array of years with full payment history
- Up to 28 years of data available

### 3. **Property Details** (`property_data.data`)
- Owner, addresses (physical & mailing)
- Property values: `total_property_value`, `land_value`, `developments_value`
- `total_acreage` with breakdown by type
- `developments` array with building details (sq_ft, bedrooms, year_built, etc.)

### 4. **Clerk Records** (`clerk_data.data`)
- `records_count` - Number of records
- `records` - Array of deeds, mortgages, liens, etc.
- Each record has: date, description, grantor, grantee, PDF URL

## Status Handling

Each section has a `status` field:
- `"success"` - Data available
- `"error"` - Data unavailable (e.g., no clerk data for some counties)

When `status` is `"error"`, `data` will be `null`.

## Notes

- Structure is **IDENTICAL** for all counties
- All data is **standardized** using county-specific configs
- Missing fields return `null`
- Historical data availability varies by county
- **General Info** section consolidates common fields from all data sources

