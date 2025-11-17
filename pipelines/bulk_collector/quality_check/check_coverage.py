#!/usr/bin/env python3
"""
Compare GeoJSON parcel IDs vs. scraped JSONL records to measure coverage.

Defaults:
- GeoJSON dir: report_builder/geojsons/{county}/ownership_data_latest.geojson
- Scraped dir: report_builder/scraped_data_download/*.jsonl  (or use --scraped-dir to point to 'output/')
"""

import os
import json
import argparse
from typing import Dict, Set, List

COUNTIES = [
    "fremont_county_wy",
    "lincoln_county_wy",
    "sublette_county_wy",
    "teton_county_wy",
]

def load_geojson_parcels(geojson_path: str) -> Set[str]:
    if not os.path.exists(geojson_path):
        print(f"Missing GeoJSON: {geojson_path}")
        return set()
    with open(geojson_path, "r") as f:
        data = json.load(f)
    parcels = set()
    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        cid = props.get("county_parcel_id")
        if cid:
            parcels.add(str(cid).strip())
    return parcels

def load_geojson_parcels_with_geom(geojson_path: str) -> Dict[str, bool]:
    """Return mapping: county_parcel_id -> has_geometry (True if geometry is non-null)."""
    geom_index: Dict[str, bool] = {}
    if not os.path.exists(geojson_path):
        return geom_index
    with open(geojson_path, "r") as f:
        data = json.load(f)
    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        cid = props.get("county_parcel_id")
        if not cid:
            continue
        pid = str(cid).strip()
        has_geom = feat.get("geometry") is not None
        geom_index[pid] = has_geom
    return geom_index

def load_geojson_key_flags(geojson_path: str) -> Dict[str, Dict[str, bool]]:
    """
    Return mapping: county_parcel_id -> {
        'has_property_key': bool,
        'has_tax_key': bool,
        'has_clerk_key': bool,
        'missing_keys_count': int
    }
    """
    key_index: Dict[str, Dict[str, bool]] = {}
    if not os.path.exists(geojson_path):
        return key_index
    with open(geojson_path, "r") as f:
        data = json.load(f)
    for feat in data.get("features", []):
        props = feat.get("properties", {}) or {}
        cid = props.get("county_parcel_id")
        if not cid:
            continue
        pid = str(cid).strip()
        prop_key = props.get("property_details_key")
        tax_key = props.get("tax_details_key")
        clerk_key = props.get("clerk_records_key")
        has_property_key = bool(prop_key)
        has_tax_key = bool(tax_key)
        has_clerk_key = bool(clerk_key)
        missing = 3 - sum([has_property_key, has_tax_key, has_clerk_key])
        key_index[pid] = {
            "has_property_key": has_property_key,
            "has_tax_key": has_tax_key,
            "has_clerk_key": has_clerk_key,
            "missing_keys_count": missing,
        }
    return key_index

def load_scraped_ids(jsonl_path: str) -> Set[str]:
    ids = set()
    if not os.path.exists(jsonl_path):
        return ids
    with open(jsonl_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            # Skip header lines that only carry file_type/created_at
            if not isinstance(obj, dict):
                continue
            pid = obj.get("parcel_id")
            if pid:
                ids.add(str(pid).strip())
    return ids

def check_county(county: str, geojson_base: str, scraped_dir: str, sample_missing: int = 20) -> Dict:
    geojson_path = os.path.join(geojson_base, county, "ownership_data_latest.geojson")
    geo_parcels = load_geojson_parcels(geojson_path)
    geom_index = load_geojson_parcels_with_geom(geojson_path)
    key_index = load_geojson_key_flags(geojson_path)

    # JSONL files expected in scraped_dir (from GCS download or 'output/')
    tax_file = os.path.join(scraped_dir, f"{county}_tax_data.jsonl")
    prop_file = os.path.join(scraped_dir, f"{county}_property_data.jsonl")
    clerk_file = os.path.join(scraped_dir, f"{county}_clerk_data.jsonl")

    tax_ids = load_scraped_ids(tax_file)
    prop_ids = load_scraped_ids(prop_file)
    clerk_ids = load_scraped_ids(clerk_file)

    def coverage(src_ids: Set[str], label: str):
        missing = sorted(list(geo_parcels - src_ids))
        overlap = len(geo_parcels & src_ids)
        pct = (overlap / len(geo_parcels) * 100.0) if geo_parcels else 0.0

        # Classify missing by geometry
        missing_with_geom = [pid for pid in missing if geom_index.get(pid, False)]
        missing_without_geom = [pid for pid in missing if not geom_index.get(pid, False)]

        # Classify missing by how many keys are absent in GeoJSON
        mk0 = mk1 = mk2 = mk3 = 0
        for pid in missing:
            kc = key_index.get(pid, {"missing_keys_count": 3})
            c = kc.get("missing_keys_count", 3)
            if c == 0: mk0 += 1
            elif c == 1: mk1 += 1
            elif c == 2: mk2 += 1
            else: mk3 += 1

        return {
            "label": label,
            "total_geo_parcels": len(geo_parcels),
            "scraped_records": len(src_ids),
            "covered": overlap,
            "coverage_pct": round(pct, 2),
            "missing_count": len(missing),
            "missing_with_geometry": len(missing_with_geom),
            "missing_without_geometry": len(missing_without_geom),
            "missing_keys_0": mk0,
            "missing_keys_1": mk1,
            "missing_keys_2": mk2,
            "missing_keys_3": mk3,
            "missing_sample": missing[:sample_missing],
            "missing_with_geometry_sample": missing_with_geom[:sample_missing],
            "missing_without_geometry_sample": missing_without_geom[:sample_missing],
        }

    return {
        "county": county,
        "geojson_path": geojson_path,
        "tax": coverage(tax_ids, "tax"),
        "property": coverage(prop_ids, "property"),
        "clerk": coverage(clerk_ids, "clerk"),
    }

def main():
    parser = argparse.ArgumentParser(description="Quality check: GeoJSON vs scraped data coverage")
    parser.add_argument("--geojson-dir", default="report_builder/geojsons", help="Base dir containing {county}/ownership_data_latest.geojson")
    parser.add_argument("--scraped-dir", default="report_builder/scraped_data_download", help="Dir containing *_tax_data.jsonl, *_property_data.jsonl, *_clerk_data.jsonl")
    parser.add_argument("--counties", nargs="+", default=COUNTIES, help="Counties to check")
    parser.add_argument("--sample-missing", type=int, default=20, help="How many missing IDs to sample per type")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    results: List[Dict] = []
    for county in args.counties:
        res = check_county(county, args.geojson_dir, args.scraped_dir, args.sample_missing)
        results.append(res)

    if args.json:
        print(json.dumps({"results": results}, indent=2))
        return

        # Pretty print
    for r in results:
        print("\n" + "="*80)
        print(f"County: {r['county']}")
        print(f"GeoJSON: {r['geojson_path']}")
        for key in ["tax", "property", "clerk"]:
            sec = r[key]
            print(f"\n[{sec['label'].upper()}]")
            print(f"- total_geo_parcels:           {sec['total_geo_parcels']}")
            print(f"- scraped_records:             {sec['scraped_records']}")
            print(f"- covered:                     {sec['covered']}")
            print(f"- coverage_pct:                {sec['coverage_pct']}%")
            print(f"- missing_count:               {sec['missing_count']}")
            print(f"- missing_with_geometry:       {sec['missing_with_geometry']}")
            print(f"- missing_without_geometry:    {sec['missing_without_geometry']}")
            print(f"- missing_keys_0:              {sec['missing_keys_0']}  # has all three keys")
            print(f"- missing_keys_1:              {sec['missing_keys_1']}")
            print(f"- missing_keys_2:              {sec['missing_keys_2']}")
            print(f"- missing_keys_3:              {sec['missing_keys_3']}")
            if sec["missing_sample"]:
                print(f"- missing_sample:              {sec['missing_sample']}")
            if sec["missing_with_geometry_sample"]:
                print(f"- missing_with_geometry_sample:{sec['missing_with_geometry_sample']}")
            if sec["missing_without_geometry_sample"]:
                print(f"- missing_without_geometry_sample:{sec['missing_without_geometry_sample']}")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()