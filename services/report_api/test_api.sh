#!/bin/bash

# Test script for Report Builder API
# Make sure the API is running on port 8002 before running these tests

API_URL="http://localhost:9003"

echo "════════════════════════════════════════════════════════════════"
echo "Report Builder API Test Suite"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
echo "─────────────────────────────────────────────────────────────────"
curl -s "$API_URL/health" | jq '.'
echo ""
echo ""

# Test 2: Root Info
echo "Test 2: Root Info"
echo "─────────────────────────────────────────────────────────────────"
curl -s "$API_URL/" | jq '.'
echo ""
echo ""

# Test 3: Database Stats
echo "Test 3: Database Stats"
echo "─────────────────────────────────────────────────────────────────"
curl -s "$API_URL/stats" | jq '.'
echo ""
echo ""

# Test 4: Batch Retrieve - Single Parcel
echo "Test 4: Batch Retrieve - Single Parcel"
echo "─────────────────────────────────────────────────────────────────"
curl -s -X POST "$API_URL/batch-retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "parcels": [
      {
        "county": "teton_county_wy",
        "county_parcel_id": "22-41-17-22-1-01-020"
      }
    ]
  }' | jq '{total_requested, total_found, total_missing, processing_time_ms, parcels: [.parcels[] | {county, county_parcel_id, found, collected_at}]}'
echo ""
echo ""

# Test 5: Batch Retrieve - Multiple Parcels
echo "Test 5: Batch Retrieve - Multiple Parcels"
echo "─────────────────────────────────────────────────────────────────"
curl -s -X POST "$API_URL/batch-retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "parcels": [
      {
        "county": "teton_county_wy",
        "county_parcel_id": "22-41-17-22-1-01-020"
      },
      {
        "county": "teton_county_wy",
        "county_parcel_id": "22-42-16-10-2-07-003"
      },
      {
        "county": "teton_county_wy",
        "county_parcel_id": "22-42-16-10-2-07-007"
      }
    ]
  }' | jq '{total_requested, total_found, total_missing, processing_time_ms}'
echo ""
echo ""

# Test 6: Empty Request (Should Fail)
echo "Test 6: Empty Request (Should Fail)"
echo "─────────────────────────────────────────────────────────────────"
curl -s -X POST "$API_URL/batch-retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "parcels": []
  }' | jq '.'
echo ""
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "Tests Complete!"
echo "════════════════════════════════════════════════════════════════"

