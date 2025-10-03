#!/usr/bin/env python3
"""
Teton County Idaho Data Download and Processing Script

This script downloads the nightly updated DBF files from Teton County Idaho's GIS portal,
processes them, and organizes the data for our property details API.

Files to download and process:
- PCXPAR00.DBF (Related Parcels)
- PCPARC00.DBF (Parcel Master)
- PCPARSUM.DBF (Parcel Summary)
- PCAPPL00.DBF (Appeals)
- PCLEGL00.DBF (Legal Descriptions)
- PCNAME00.DBF (Parcel Names)
- PCCATG00.DBF (Parcel Categories)
- PCPERM00.DBF (Permits)
- PCSALE00.DBF (Sales)
- PCSPEC00.DBF (Special Charges)
- PCIMPC00.DBF (Improvements)
- PCICAT00.DBF (Improvement Categories)
- PCIMAGE0.DBF (Improvement Images)
- PCLAND00.DBF (Land Records)
- PCLNDC00.DBF (Land Characteristics)
- PCOTHI00.DBF (Other Improvements)
"""

import os
import sys
import requests
import zipfile
import shutil
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import dbf
import logging

# Add this import
sys.path.append(str(Path(__file__).parent.parent))
from storage.db import save_raw

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
try:
    from config import TETON_IDAHO_DATA_DIR, TETON_IDAHO_PROCESSED_DIR
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teton_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TetonCountyDataProcessor:
    """Downloads and processes Teton County Idaho GIS data."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        if USE_CONFIG:
            self.data_dir = Path(TETON_IDAHO_DATA_DIR)
            self.processed_dir = Path(TETON_IDAHO_PROCESSED_DIR)
        else:
            # When running from main project directory
            self.data_dir = Path("property_info_api/teton_county_id_download/data")
            self.processed_dir = Path("property_info_api/teton_county_id_download/processed")
        # self.database_path = self.processed_dir / "teton_county_id.db" # Removed
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
        # ArcGIS portal URL
        self.portal_url = "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c/data"
        
        # Expected DBF files based on actual downloaded files (lowercase)
        self.expected_files = [
            "pcxpar00.dbf",  # Related Parcels
            "pcparc00.dbf",  # Parcel Master
            "pcparsum.dbf",  # Parcel Summary
            "pcappl00.dbf",  # Appeals
            "pclegl00.dbf",  # Legal Descriptions
            "pcname00.dbf",  # Parcel Names
            "pccatg00.dbf",  # Parcel Categories
            "pcperm00.dbf",  # Permits
            "pcsale00.dbf",  # Sales
            "pcspec00.dbf",  # Special Charges
            "pcimpc00.dbf",  # Improvements
            "pcicat00.dbf",  # Improvement Categories
            "pcimag00.dbf",  # Improvement Images (note: was PCIMAGE0.DBF)
            "pcland00.dbf",  # Land Records
            "pclndc00.dbf",  # Land Characteristics
            "pcothi00.dbf"   # Other Improvements
        ]
        
        # Field mappings for our canonical structure
        self.field_mappings = {
            'parcel_master': {
                'PM_PAR_14': 'county_parcel_id',
                'PM_PAR_15': 'parcel_status',
                'PM_MAIL_NM': 'owner_name',
                'PM_MAIL_A1': 'mailing_address_line1',
                'PM_MAIL_A2': 'mailing_address_line2',
                'PM_MAIL_CT': 'mailing_city',
                'PM_MAIL_ST': 'mailing_state',
                'PM_MAIL_ZP': 'mailing_zip',
                'PM_PROP_AD': 'physical_address',
                'PM_PROP_ZP': 'property_zip',
                'PM_DEEDRF1': 'deed_reference1',
                'PM_DEEDRF2': 'deed_reference2',
                'PM_DEEDRF3': 'deed_reference3',
                'PM_DEEDRF4': 'deed_reference4',
                'PM_DEEDRF5': 'deed_reference5',
                'PM_TOT_VAL': 'total_value',
                'PM_IMP_VAL': 'improvement_value',
                'PM_LND_VAL': 'land_value',
                'PM_PV_ACRE': 'total_acres',
                'PM_ZONING': 'zoning',
                'PM_TAXAREA': 'tax_district'
            },
            'improvements': {
                'IM_PAR_14': 'county_parcel_id',
                'IM_NUMBER': 'improvement_number',
                'IM_DWELL_N': 'dwelling_type',
                'IM_PROP_AD': 'property_address',
                'IM_YR_BLT': 'year_built',
                'IM_STORIES': 'stories',
                'IM_BEDROOM': 'bedrooms',
                'IM_BATHRM': 'bathrooms',
                'IM_FIREPLC': 'fireplaces',
                'IM_1ST_SQF': 'first_floor_sqft',
                'IM_2ND_SQF': 'second_floor_sqft',
                'IM_BAS_SQF': 'basement_sqft',
                'IM_ATT_SQF': 'attic_sqft',
                'IM_TOT_SQF': 'total_sqft',
                'IM_SIDING': 'siding',
                'IM_ROOFING': 'roofing',
                'IM_HEAT_1': 'heating_system1',
                'IM_HEAT_2': 'heating_system2',
                'IM_HEAT_3': 'heating_system3',
                'IM_EXT_VAL': 'improvement_value',
                'IM_GAR1_SF': 'garage1_sqft',
                'IM_GAR2_SF': 'garage2_sqft'
            },
            'legal': {
                'LG_PAR_14': 'county_parcel_id',
                'LG_LINE_1': 'legal_line1',
                'LG_LINE_2': 'legal_line2',
                'LG_LINE_3': 'legal_line3',
                'LG_LINE_4': 'legal_line4',
                'LG_LINE_5': 'legal_line5',
                'LG_LINE_6': 'legal_line6'
            },
            'land': {
                'LD_PAR_14': 'county_parcel_id',
                'LD_CAT_NUM': 'land_category',
                'LD_LOC_NUM': 'land_location',
                'LD_CLS_NUM': 'land_class',
                'LD_TYP_NUM': 'land_type',
                'LD_QNTY': 'land_quantity',
                'LD_UNIT': 'land_unit',
                'LD_VALUE': 'land_value'
            }
        }
    
    def download_data(self):
        """Download the latest data from Teton County's ArcGIS portal."""
        logger.info("Starting download from Teton County Idaho GIS portal...")
        
        try:
            # First, we need to get the actual download URL from the portal
            # This might require authentication or finding the direct download link
            # For now, we'll simulate the download process
            
            # Check if we have a cached download URL or need to find it
            download_url = self._get_download_url()
            
            if not download_url:
                logger.error("Could not find download URL. Manual intervention required.")
                return False
            
            # Download the file (could be zip or individual files)
            download_path = self.data_dir / "teton_county_data"
            logger.info(f"Downloading to {download_path}")
            
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Check if it's a zip file by content type or filename
            content_type = response.headers.get('content-type', '')
            is_zip = 'zip' in content_type or download_url.lower().endswith('.zip')
            
            if is_zip:
                # Download as zip file
                zip_path = self.data_dir / "teton_county_data.zip"
                logger.info(f"Downloading zip file to {zip_path}")
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Extract the zip file
                logger.info("Extracting downloaded zip file...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.data_dir)
                
                # Clean up zip file
                zip_path.unlink()
                logger.info("Zip file extracted and cleaned up")
            else:
                # Download as individual file
                logger.info(f"Downloading individual file to {download_path}")
                with open(download_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Check if the downloaded file is actually a zip
                try:
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        logger.info("Downloaded file is a zip, extracting...")
                        zip_ref.extractall(self.data_dir)
                    # Clean up the downloaded file
                    download_path.unlink()
                    logger.info("File extracted and cleaned up")
                except zipfile.BadZipFile:
                    logger.info("Downloaded file is not a zip, using as-is")
            
            # Verify we have the expected files
            missing_files = []
            for expected_file in self.expected_files:
                file_path = self.data_dir / expected_file
                if not file_path.exists():
                    missing_files.append(expected_file)
                    logger.warning(f"Missing expected file: {expected_file}")
            
            if missing_files:
                logger.warning(f"Missing {len(missing_files)} expected files: {missing_files}")
            
            logger.info("Download completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            logger.info("Checking if files already exist in data directory...")
            
            # Check if we have any of the expected files already
            existing_files = [f for f in self.expected_files if (self.data_dir / f).exists()]
            if existing_files:
                logger.info(f"Found {len(existing_files)} existing files: {existing_files}")
                logger.info("Proceeding with processing existing files...")
                return True
            else:
                logger.error("No existing files found. Manual download required.")
                return False
    
    def _get_download_url(self):
        """Get the actual download URL from the ArcGIS portal."""
        try:
            # Try to access the ArcGIS REST API endpoint
            logger.info(f"Attempting to access: {self.portal_url}")
            
            response = requests.get(self.portal_url, timeout=30)
            response.raise_for_status()
            
            # Log response details for debugging
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response content (first 500 chars): {response.text[:500]}")
            
            # Check if response is JSON
            content_type = response.headers.get('content-type', '')
            if 'json' not in content_type.lower():
                # Check if it's actually a zip file (which is what we want!)
                if 'zip' in content_type.lower() or 'application/zip' in content_type.lower():
                    logger.info(f"✓ Found zip file! Content-Type: {content_type}")
                    logger.info(f"✓ File size: {response.headers.get('content-length', 'unknown')} bytes")
                    logger.info(f"✓ Filename: {response.headers.get('content-disposition', 'unknown')}")
                    
                    # This is the actual download URL that returns the zip file
                    return self.portal_url
                else:
                    logger.warning(f"Response is not JSON. Content-Type: {content_type}")
                    logger.info("Trying alternative ArcGIS REST API endpoints...")
                
                # Try alternative endpoints
                alternative_urls = [
                    "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c",
                    "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c?f=json",
                    "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c/data?f=json"
                ]
                
                for alt_url in alternative_urls:
                    try:
                        logger.info(f"Trying alternative URL: {alt_url}")
                        alt_response = requests.get(alt_url, timeout=30)
                        alt_response.raise_for_status()
                        
                        if 'json' in alt_response.headers.get('content-type', '').lower():
                            data = alt_response.json()
                            logger.info(f"Alternative URL worked! Response: {data}")
                            
                            # Look for download URL in the response
                            if 'url' in data:
                                download_url = data['url']
                                logger.info(f"Found download URL: {download_url}")
                                return download_url
                            elif 'data' in data and 'url' in data['data']:
                                download_url = data['data']['url']
                                logger.info(f"Found download URL in data: {download_url}")
                                return download_url
                            else:
                                logger.warning(f"No download URL found in alternative response. Keys: {list(data.keys())}")
                    except Exception as e:
                        logger.warning(f"Alternative URL failed: {e}")
                        continue
                
                logger.error("All ArcGIS REST API attempts failed.")
                
                # Try the direct download URL that we know works
                logger.info("Trying direct download URL...")
                direct_download_url = "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c/data"
                
                try:
                    test_response = requests.head(direct_download_url, timeout=10)
                    if test_response.status_code == 200:
                        logger.info("✓ Direct download URL is accessible!")
                        return direct_download_url
                    else:
                        logger.warning(f"✗ Direct download URL returned status: {test_response.status_code}")
                except Exception as e:
                    logger.error(f"✗ Error testing direct download URL: {e}")
                
                logger.error("Manual download required.")
                return None
            
            # Parse the response to find the actual download URL
            data = response.json()
            logger.info(f"Portal response: {data}")
            
            # Look for download URL in the response
            logger.info(f"Full response data: {data}")
            
            # Check various possible locations for the download URL
            possible_url_keys = ['url', 'downloadUrl', 'dataUrl', 'fileUrl', 'href']
            possible_data_keys = ['data', 'attributes', 'properties']
            
            # First, check direct URL keys
            for key in possible_url_keys:
                if key in data and data[key]:
                    download_url = data[key]
                    logger.info(f"Found download URL in '{key}': {download_url}")
                    return download_url
            
            # Then check nested data structures
            for data_key in possible_data_keys:
                if data_key in data and isinstance(data[data_key], dict):
                    for url_key in possible_url_keys:
                        if url_key in data[data_key] and data[data_key][url_key]:
                            download_url = data[data_key][url_key]
                            logger.info(f"Found download URL in '{data_key}.{url_key}': {download_url}")
                            return download_url
            
            # Check if there's a direct download URL in the item info
            if 'id' in data:
                # Try to construct a direct download URL
                item_id = data['id']
                direct_url = f"https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/{item_id}/data"
                logger.info(f"Trying constructed direct URL: {direct_url}")
                return direct_url
            
            logger.warning(f"No download URL found in response. Response keys: {list(data.keys())}")
            return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing portal: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing portal response: {e}")
            logger.info("Response might be HTML or require authentication")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def process_dbf_files(self):
        """Process all DBF files and save to main property_data.db."""
        logger.info("Processing DBF files and saving to main database...")
        
        # Process each file type and save to main database
        self._process_parcel_master()
        # You can also process improvements, legal descriptions, etc. if needed
        # self._process_improvements() 
        # self._process_legal_descriptions()
        
        logger.info("DBF processing completed - all data saved to main database")
    
    def _process_parcel_master(self):
        """Process the main parcel master file (PCPARC00.DBF)."""
        dbf_path = self.data_dir / "pcparc00.dbf"
        if not dbf_path.exists():
            logger.warning("Parcel master file not found")
            return
        
        logger.info("Processing parcel master file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            logger.info(f"Loaded {len(table)} records from parcel master")
            
            # Load all improvements data once into a lookup dictionary
                        # Load all improvements data once into a lookup dictionary
            logger.info("Loading improvements data...")
            improvements_lookup = self._load_improvements_lookup()
            logger.info(f"Loaded improvements for {len(improvements_lookup)} parcels")
            
            # Load all other improvements once
            logger.info("Loading other improvements data...")
            other_improvements_lookup = self._load_other_improvements_lookup()
            logger.info(f"Loaded other improvements for {len(other_improvements_lookup)} parcels")
            
            # Load legal descriptions once
            logger.info("Loading legal descriptions...")
            legal_lookup = self._load_legal_lookup()
            logger.info(f"Loaded legal descriptions for {len(legal_lookup)} parcels")
            
            # Process each record and save to main database
            for record in table:
                parcel_id = str(record.PM_PAR_14).strip()
                
                # Get improvements for this parcel from lookups (fast!)
                improvements = improvements_lookup.get(parcel_id, [])
                other_improvements = other_improvements_lookup.get(parcel_id, [])
                developments = improvements + other_improvements
                
                # Get legal description for this parcel
                legal_location = legal_lookup.get(parcel_id, "")
                
                parcel_data = {
                    "tax_raw_data": {
                        "tax_data": {
                            "tax_id": str(record.PM_DEEDRF1).strip(),
                            "latest_tax_amount": (amt := self._parse_numeric(getattr(record, 'PM_TAX_AMT', ''))),
                            "latest_tax_year": (yr := int(self._parse_numeric(getattr(record, 'PM_TAXYEAR', '')) or 0) or None),
                            "tax_district": str(record.PM_TAXAREA).strip(),
                            "owner_name": str(record.PM_MAIL_NM).strip(),
                            "property_address": str(record.PM_PROP_AD).strip(),
                            "paid_flag": (paid_flag := str(getattr(record, 'PM_PAIDFLG', '')).strip() or None),
                            "current_tax": (lambda a, y, pf: {
                                "tax_year": y,
                                "total_tax_levied": a,
                                "tax_received": a if (pf == "Y") else 0,
                                "amount_due": 0 if (pf == "Y") else a,
                                "status": "PAID" if (pf == "Y") else "DUE",
                                "first_half": {
                                    "levied": (a / 2 if a is not None else None),
                                    "paid": (a / 2 if (pf == "Y" and a is not None) else 0),
                                    "balance": 0 if (pf == "Y") else (a / 2 if a is not None else None)
                                },
                                "second_half": {
                                    "levied": (a / 2 if a is not None else None),
                                    "paid": (a / 2 if (pf == "Y" and a is not None) else 0),
                                    "balance": 0 if (pf == "Y") else (a / 2 if a is not None else None)
                                }
                            })(amt, yr, paid_flag)
                        }
                    },
                    "property_raw_data": {
                        "property_data": {
                            "county_parcel_id": parcel_id,
                            "tax_id": str(record.PM_DEEDRF1).strip(),
                            "owner_name": str(record.PM_MAIL_NM).strip(),
                            "physical_address": str(record.PM_PROP_AD).strip(),
                            "mailing_address": f"{str(record.PM_MAIL_A1).strip()}, {str(record.PM_MAIL_CT).strip()}, {str(record.PM_MAIL_ST).strip()} {str(record.PM_MAIL_ZP).strip()}",
                            "total_acres": str(self._parse_numeric(record.PM_PV_ACRE) or ''),
                            "value_summary": (lambda tv, iv: {
                                "total_value": str(tv),
                                "land": str(max(tv - iv, 0)),
                                "developments": str(iv)
                            })(
                                (self._parse_numeric(record.PM_TOT_VAL) or 0),
                                (self._parse_numeric(record.PM_IMP_VAL) or 0)
                            ),
                            "tax_district": str(record.PM_TAXAREA).strip(),
                                                        "tax_district": str(record.PM_TAXAREA).strip(),
                            "deed": f"{str(record.PM_DEEDRF1).strip()}; {str(record.PM_DEEDRF2).strip()}; {str(record.PM_DEEDRF3).strip()}",
                            # Build deed_url from the numeric part of PM_DEEDRF1
                            "deed_url": (lambda docnum: (
                                f"https://tetoncountyid-web.tylerhost.net/web/web/integration/document?DocumentNumberId={docnum}"
                            ) if docnum else None)(
                                ''.join(ch for ch in str(record.PM_DEEDRF1).strip() if ch.isdigit())
                            ),
                            "developments": developments,
                            "legal": {
                                "location": legal_location
                            }
                        }
                    },
                    "clerk_raw_data": {
                        "clerk_data": {}
                    },
                    "county_links": {
                        "tax_field": None,
                        "property_details_field": None,
                        "clerk_field": "https://tetoncountyid-web.tylerhost.net/web/"
                    },
                    "source": "teton_county_id_dbf_import",
                    "collected_at": datetime.now().isoformat()
                }
                
                # Save to main property_data.db
                save_raw("teton_county_id", parcel_id, parcel_data)
                
            table.close()
            logger.info(f"Processed and saved {len(table)} parcels to main database")
            
        except Exception as e:
            logger.error(f"Error processing parcel master: {e}")

    def _load_legal_lookup(self):
        """Load legal descriptions from PCLEGL00.DBF keyed by LG_PAR_14 → LG_LINE_2."""
        lookup = {}
        dbf_path = self.data_dir / "pclegl00.dbf"
        if not dbf_path.exists():
            logger.warning("Legal descriptions file not found")
            return lookup
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            for record in table:
                try:
                    parcel_id = str(record.LG_PAR_14).strip()
                    # Use LG_LINE_2 per requirement (e.g., 'SEC 11 T5N R45E')
                    line2 = str(getattr(record, "LG_LINE_2", "")).strip()
                    if line2 and parcel_id and parcel_id not in lookup:
                        lookup[parcel_id] = line2
                except Exception:
                    continue
            table.close()
        except Exception as e:
            logger.error(f"Error loading legal descriptions: {e}")
        return lookup

    def _load_other_improvements_lookup(self):
        """Load all 'other improvements' from PCOTHI00.DBF into a lookup dictionary keyed by parcel_id."""
        lookup = {}
        dbf_path = self.data_dir / "pcothi00.dbf"
        if not dbf_path.exists():
            logger.warning("Other Improvements file not found")
            return lookup
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            for record in table:
                parcel_id = str(record.OI_PAR_14).strip()
                
                # Map fields to development-style dict
                number = str(record.OI_NUMBER).strip()
                use_code = str(record.OI_USE_COD).strip()
                oi = {
                    "Building ID": number or "",                         # keeps consistent ID field
                    "Description": f"Other Improvement (Use {use_code})" if use_code else "Other Improvement",
                    "Total Sq Ft": str(self._parse_numeric(record.OI_TOT_SQF) or ''),
                    "Year Built": str(self._parse_numeric(record.OI_YR_BLT) or ''),
                    "Improvement Value": str(self._parse_numeric(record.OI_VALUE) or ''),
                    "Class": str(record.OI_CLASS).strip() if hasattr(record, "OI_CLASS") else "",
                    "Base Cost": str(self._parse_numeric(record.OI_BAS_CST) or ''),
                    "Use Code": use_code
                }
                
                # Drop empty values
                oi = {k: v for k, v in oi.items() if v not in (None, "", "None")}
                
                if parcel_id not in lookup:
                    lookup[parcel_id] = []
                lookup[parcel_id].append(oi)
            
            table.close()
        except Exception as e:
            logger.error(f"Error loading other improvements lookup: {e}")
        
        return lookup
        
    def _load_improvements_lookup(self):
        """Load all improvements data once into a lookup dictionary."""
        improvements_lookup = {}
        
        dbf_path = self.data_dir / "pcimpc00.dbf"
        if not dbf_path.exists():
            logger.warning("Improvements file not found")
            return improvements_lookup
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            for record in table:
                parcel_id = str(record.IM_PAR_14).strip()
                
                improvement = {
                    "Building ID": str(record.IM_NUMBER).strip(),
                    "Property Type": str(record.IM_DWELL_N).strip(),
                    "Property Address": str(record.IM_PROP_AD).strip(),
                    "Year Built": str(self._parse_numeric(record.IM_YR_BLT) or ''),
                    "Stories": str(self._parse_numeric(record.IM_STORIES) or ''),
                    "Bedrooms": str(self._parse_numeric(record.IM_BEDROOM) or ''),
                    "Bathrooms": str(self._parse_numeric(record.IM_BATHRM) or ''),
                    "Fireplaces": str(self._parse_numeric(record.IM_FIREPLC) or ''),
                    "First Floor Sq Ft": str(self._parse_numeric(record.IM_1ST_SQF) or ''),
                    "Second Floor Sq Ft": str(self._parse_numeric(record.IM_2ND_SQF) or ''),
                    "Basement Sq Ft": str(self._parse_numeric(record.IM_BAS_SQF) or ''),
                    "Attic Sq Ft": str(self._parse_numeric(record.IM_ATT_SQF) or ''),
                    "Total Sq Ft": str(self._parse_numeric(record.IM_TOT_SQF) or ''),
                    "Siding": str(record.IM_SIDING).strip(),
                    "Roofing": str(record.IM_ROOFING).strip(),
                    "Heating System 1": str(record.IM_HEAT_1).strip(),
                    "Heating System 2": str(record.IM_HEAT_2).strip(),
                    "Heating System 3": str(record.IM_HEAT_3).strip(),
                    "Improvement Value": str(self._parse_numeric(record.IM_EXT_VAL) or ''),
                    "Garage 1 Sq Ft": str(self._parse_numeric(record.IM_GAR1_SF) or ''),
                    "Garage 2 Sq Ft": str(self._parse_numeric(record.IM_GAR2_SF) or '')
                }

                # Add description from IM_DWELL_N
                desc_map = {"D": "Residential dwelling", "C": "Commercial", "M": "Manufactured housing"}
                dwell_code = str(record.IM_DWELL_N).strip()
                improvement["Description"] = desc_map.get(dwell_code, dwell_code)
                
                # Remove empty values
                improvement = {k: v for k, v in improvement.items() if v and v.strip()}
                
                # Add to lookup dictionary
                if parcel_id not in improvements_lookup:
                    improvements_lookup[parcel_id] = []
                improvements_lookup[parcel_id].append(improvement)
            
            table.close()
            
        except Exception as e:
            logger.error(f"Error loading improvements lookup: {e}")
        
        return improvements_lookup
    
    def _process_improvements(self):
        """Process the improvements file (PCIMPC00.DBF)."""
        dbf_path = self.data_dir / "pcimpc00.dbf"
        if not dbf_path.exists():
            logger.warning("Improvements file not found")
            return
        
        logger.info("Processing improvements file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM improvements')
            
            for record in table:
                improvement_data = {
                    'county_parcel_id': str(record.IM_PAR_14).strip(),
                    'improvement_number': str(record.IM_NUMBER).strip(),
                    'dwelling_type': str(record.IM_DWELL_N).strip(),
                    'property_address': str(record.IM_PROP_AD).strip(),
                    'year_built': self._parse_numeric(record.IM_YR_BLT),
                    'stories': self._parse_numeric(record.IM_STORIES),
                    'bedrooms': self._parse_numeric(record.IM_BEDROOM),
                    'bathrooms': self._parse_numeric(record.IM_BATHRM),
                    'fireplaces': self._parse_numeric(record.IM_FIREPLC),
                    'first_floor_sqft': self._parse_numeric(record.IM_1ST_SQF),
                    'second_floor_sqft': self._parse_numeric(record.IM_2ND_SQF),
                    'basement_sqft': self._parse_numeric(record.IM_BAS_SQF),
                    'attic_sqft': self._parse_numeric(record.IM_ATT_SQF),
                    'total_sqft': self._parse_numeric(record.IM_TOT_SQF),
                    'siding': str(record.IM_SIDING).strip(),
                    'roofing': str(record.IM_ROOFING).strip(),
                    'heating_system1': str(record.IM_HEAT_1).strip(),
                    'heating_system2': str(record.IM_HEAT_2).strip(),
                    'heating_system3': str(record.IM_HEAT_3).strip(),
                    'improvement_value': self._parse_numeric(record.IM_EXT_VAL),
                    'garage1_sqft': self._parse_numeric(record.IM_GAR1_SF),
                    'garage2_sqft': self._parse_numeric(record.IM_GAR2_SF)
                }
                
                cursor.execute('''
                    INSERT INTO improvements (
                        county_parcel_id, improvement_number, dwelling_type,
                        property_address, year_built, stories, bedrooms,
                        bathrooms, fireplaces, first_floor_sqft,
                        second_floor_sqft, basement_sqft, attic_sqft,
                        total_sqft, siding, roofing, heating_system1,
                        heating_system2, heating_system3, improvement_value,
                        garage1_sqft, garage2_sqft
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    improvement_data['county_parcel_id'],
                    improvement_data['improvement_number'],
                    improvement_data['dwelling_type'],
                    improvement_data['property_address'],
                    improvement_data['year_built'],
                    improvement_data['stories'],
                    improvement_data['bedrooms'],
                    improvement_data['bathrooms'],
                    improvement_data['fireplaces'],
                    improvement_data['first_floor_sqft'],
                    improvement_data['second_floor_sqft'],
                    improvement_data['basement_sqft'],
                    improvement_data['attic_sqft'],
                    improvement_data['total_sqft'],
                    improvement_data['siding'],
                    improvement_data['roofing'],
                    improvement_data['heating_system1'],
                    improvement_data['heating_system2'],
                    improvement_data['heating_system3'],
                    improvement_data['improvement_value'],
                    improvement_data['garage1_sqft'],
                    improvement_data['garage2_sqft']
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} improvement records")
            
        except Exception as e:
            logger.error(f"Error processing improvements: {e}")
    
    def _process_legal_descriptions(self):
        """Process the legal descriptions file (PCLEGL00.DBF)."""
        dbf_path = self.data_dir / "pclegl00.dbf"
        if not dbf_path.exists():
            logger.warning("Legal descriptions file not found")
            return
        
        logger.info("Processing legal descriptions file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM legal_descriptions')
            
            for record in table:
                cursor.execute('''
                    INSERT INTO legal_descriptions (
                        county_parcel_id, legal_line1, legal_line2,
                        legal_line3, legal_line4, legal_line5, legal_line6
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(record.LG_PAR_14).strip(),
                    str(record.LG_LINE_1).strip(),
                    str(record.LG_LINE_2).strip(),
                    str(record.LG_LINE_3).strip(),
                    str(record.LG_LINE_4).strip(),
                    str(record.LG_LINE_5).strip(),
                    str(record.LG_LINE_6).strip()
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} legal description records")
            
        except Exception as e:
            logger.error(f"Error processing legal descriptions: {e}")
    
    def _process_land_records(self):
        """Process the land records file (PCLAND00.DBF)."""
        dbf_path = self.data_dir / "pcland00.dbf"
        if not dbf_path.exists():
            logger.warning("Land records file not found")
            return
        
        logger.info("Processing land records file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM land_records')
            
            for record in table:
                cursor.execute('''
                    INSERT INTO land_records (
                        county_parcel_id, land_category, land_location,
                        land_class, land_type, land_quantity, land_unit, land_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(record.LD_PAR_14).strip(),
                    self._parse_numeric(record.LD_CAT_NUM),
                    str(record.LD_LOC_NUM).strip(),
                    self._parse_numeric(record.LD_CLS_NUM),
                    self._parse_numeric(record.LD_TYP_NUM),
                    self._parse_numeric(record.LD_QNTY),
                    str(record.LD_UNIT).strip(),
                    self._parse_numeric(record.LD_VALUE)
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} land records")
            
        except Exception as e:
            logger.error(f"Error processing land records: {e}")
    
    def _process_parcel_names(self):
        """Process the parcel names file (PCNAME00.DBF)."""
        # This would update parcel owner names if needed
        pass
    
    def _process_sales(self):
        """Process the sales file (PCSALE00.DBF)."""
        dbf_path = self.data_dir / "pcsale00.dbf"
        if not dbf_path.exists():
            logger.warning("Sales file not found")
            return
        
        logger.info("Processing sales file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM sales')
            
            for record in table:
                cursor.execute('''
                    INSERT INTO sales (
                        county_parcel_id, sale_date, sale_price,
                        valid_sale, personal_property_included
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(record.SL_PAR_14).strip(),
                    str(record.SL_SALE_DT).strip(),
                    self._parse_numeric(record.SL_PRICE),
                    str(record.SL_VALID).strip(),
                    str(record.SL_PERS_PR).strip()
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} sales records")
            
        except Exception as e:
            logger.error(f"Error processing sales: {e}")
    
    def _process_permits(self):
        """Process the permits file (PCPERM00.DBF)."""
        dbf_path = self.data_dir / "pcperm00.dbf"
        if not dbf_path.exists():
            logger.warning("Permits file not found")
            return
        
        logger.info("Processing permits file...")
        
        try:
            table = dbf.Table(str(dbf_path))
            table.open()
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM permits')
            
            for record in table:
                cursor.execute('''
                    INSERT INTO permits (
                        county_parcel_id, permit_ref_number,
                        permit_filing_date, permit_description, permit_type
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(record.PE_PAR_14).strip(),
                    str(record.PE_REF_NUM).strip(),
                    str(record.PE_FIL_DAT).strip(),
                    str(record.PE_DESCRIP).strip(),
                    str(record.PE_TYPE).strip()
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} permit records")
            
        except Exception as e:
            logger.error(f"Error processing permits: {e}")
    
    def _process_appeals(self):
        """Process the appeals file (PCAPPL00.DBF)."""
        # This would track property value appeals
        pass
    
    def _parse_numeric(self, value):
        """Parse numeric values from DBF, handling empty strings and formatting."""
        if not value or value.strip() == '':
            return None
        
        try:
            # Remove any formatting and convert to float
            cleaned = str(value).strip().replace(',', '')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    # Removed _ensure_column
    
    def manual_download_instructions(self):
        """Print instructions for manual download."""
        logger.info("=" * 60)
        logger.info("MANUAL DOWNLOAD INSTRUCTIONS")
        logger.info("=" * 60)
        logger.info("1. Visit: https://tetonidaho.maps.arcgis.com/home/item.html?id=67907b10787449bcb1aaa4bdb23ca77c")
        logger.info("2. Look for a 'Download' or 'Export' button")
        logger.info("3. Download the DBF files (may be in a zip)")
        logger.info("4. Extract all files to: " + str(self.data_dir))
        logger.info("5. Ensure these files are present:")
        for file in self.expected_files[:5]:  # Show first 5
            logger.info(f"   - {file}")
        logger.info(f"   ... and {len(self.expected_files)-5} more files")
        logger.info("6. Run this script again")
        logger.info("=" * 60)
        
        # Also try to get more info about the portal
        self._check_portal_accessibility()
    
    def _check_portal_accessibility(self):
        """Check if we can access the portal and get more information."""
        logger.info("Checking portal accessibility...")
        
        try:
            # Try the main portal page
            main_url = "https://tetonidaho.maps.arcgis.com/home/item.html?id=67907b10787449bcb1aaa4bdb23ca77c"
            response = requests.get(main_url, timeout=30)
            
            if response.status_code == 200:
                logger.info("✓ Main portal page is accessible")
                
                # Look for download links in the HTML
                if 'download' in response.text.lower() or 'export' in response.text.lower():
                    logger.info("✓ Found download/export references in portal page")
                else:
                    logger.info("✗ No download/export references found in portal page")
            else:
                logger.warning(f"✗ Main portal page returned status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"✗ Error accessing portal: {e}")
        
        # Try to get item info
        try:
            item_url = "https://tetonidaho.maps.arcgis.com/sharing/rest/content/items/67907b10787449bcb1aaa4bdb23ca77c?f=json"
            response = requests.get(item_url, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info("✓ Item info accessible")
                    logger.info(f"Item title: {data.get('title', 'Unknown')}")
                    logger.info(f"Item type: {data.get('type', 'Unknown')}")
                    logger.info(f"Item size: {data.get('size', 'Unknown')}")
                    
                    # Check for download URLs
                    if 'url' in data:
                        logger.info(f"✓ Found URL: {data['url']}")
                    if 'data' in data and 'url' in data['data']:
                        logger.info(f"✓ Found data URL: {data['data']['url']}")
                        
                except json.JSONDecodeError:
                    logger.warning("✗ Item info is not JSON format")
            else:
                logger.warning(f"✗ Item info returned status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"✗ Error accessing item info: {e}")
    
    # Removed create_api_index
    
    def run_full_process(self):
        """Run the complete download and processing pipeline."""
        logger.info("Starting Teton County Idaho data processing pipeline...")
        
        # Step 1: Download data
        if not self.download_data():
            logger.error("Download failed.")
            self.manual_download_instructions()
            return False
        
        # Step 2: Process DBF files
        self.process_dbf_files()
        
        # Step 3: Create API index
        # self.create_api_index() # Removed
        
        logger.info("Pipeline completed successfully!")
        return True

def main():
    """Main entry point for the script."""
    processor = TetonCountyDataProcessor()
    
    # Check if we're running in manual mode (files already downloaded)
    if any((processor.data_dir / f).exists() for f in processor.expected_files):
        logger.info("Found existing DBF files, processing only...")
        processor.process_dbf_files()
        # processor.create_api_index() # Removed
    else:
        # Run full pipeline
        processor.run_full_process()

if __name__ == "__main__":
    main() 