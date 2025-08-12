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
            self.data_dir = self.base_dir / "data"
            self.processed_dir = self.base_dir / "processed"
        self.database_path = self.processed_dir / "teton_county_id.db"
        
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
        """Process all DBF files and convert to SQLite database."""
        logger.info("Processing DBF files...")
        
        # Initialize SQLite database
        self._init_database()
        
        # Process each file type
        self._process_parcel_master()
        self._process_improvements()
        self._process_legal_descriptions()
        self._process_land_records()
        self._process_parcel_names()
        self._process_sales()
        self._process_permits()
        self._process_appeals()
        
        logger.info("DBF processing completed")
    
    def _init_database(self):
        """Initialize the SQLite database with proper schema."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create main tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parcels (
                county_parcel_id TEXT PRIMARY KEY,
                parcel_status TEXT,
                owner_name TEXT,
                mailing_address_line1 TEXT,
                mailing_address_line2 TEXT,
                mailing_city TEXT,
                mailing_state TEXT,
                mailing_zip TEXT,
                physical_address TEXT,
                property_zip TEXT,
                deed_reference1 TEXT,
                deed_reference2 TEXT,
                deed_reference3 TEXT,
                deed_reference4 TEXT,
                deed_reference5 TEXT,
                total_value REAL,
                improvement_value REAL,
                land_value REAL,
                total_acres REAL,
                zoning TEXT,
                tax_district TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_parcel_id TEXT,
                improvement_number TEXT,
                dwelling_type TEXT,
                property_address TEXT,
                year_built INTEGER,
                stories INTEGER,
                bedrooms INTEGER,
                bathrooms REAL,
                fireplaces INTEGER,
                first_floor_sqft REAL,
                second_floor_sqft REAL,
                basement_sqft REAL,
                attic_sqft REAL,
                total_sqft REAL,
                siding TEXT,
                roofing TEXT,
                heating_system1 TEXT,
                heating_system2 TEXT,
                heating_system3 TEXT,
                improvement_value REAL,
                garage1_sqft REAL,
                garage2_sqft REAL,
                FOREIGN KEY (county_parcel_id) REFERENCES parcels (county_parcel_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS legal_descriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_parcel_id TEXT,
                legal_line1 TEXT,
                legal_line2 TEXT,
                legal_line3 TEXT,
                legal_line4 TEXT,
                legal_line5 TEXT,
                legal_line6 TEXT,
                FOREIGN KEY (county_parcel_id) REFERENCES parcels (county_parcel_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS land_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_parcel_id TEXT,
                land_category INTEGER,
                land_location TEXT,
                land_class INTEGER,
                land_type INTEGER,
                land_quantity REAL,
                land_unit TEXT,
                land_value REAL,
                FOREIGN KEY (county_parcel_id) REFERENCES parcels (county_parcel_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_parcel_id TEXT,
                sale_date TEXT,
                sale_price REAL,
                valid_sale TEXT,
                personal_property_included TEXT,
                FOREIGN KEY (county_parcel_id) REFERENCES parcels (county_parcel_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                county_parcel_id TEXT,
                permit_ref_number TEXT,
                permit_filing_date TEXT,
                permit_description TEXT,
                permit_type TEXT,
                FOREIGN KEY (county_parcel_id) REFERENCES parcels (county_parcel_id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parcels_id ON parcels (county_parcel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_improvements_parcel ON improvements (county_parcel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_legal_parcel ON legal_descriptions (county_parcel_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_land_parcel ON land_records (county_parcel_id)')
        
        conn.commit()
        conn.close()
    
    def _process_parcel_master(self):
        """Process the main parcel master file (PCPARC00.DBF)."""
        dbf_path = self.data_dir / "pcparc00.dbf"
        if not dbf_path.exists():
            logger.warning("Parcel master file not found")
            return
        
        logger.info("Processing parcel master file...")
        
        try:
            # Read DBF file using dbf library
            table = dbf.Table(str(dbf_path))
            table.open()
            logger.info(f"Loaded {len(table)} records from parcel master")
            
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Clear existing data
            cursor.execute('DELETE FROM parcels')
            
            # Process each record
            for record in table:
                parcel_data = {
                    'county_parcel_id': str(record.PM_PAR_14).strip(),
                    'parcel_status': str(record.PM_PAR_15).strip(),
                    'owner_name': str(record.PM_MAIL_NM).strip(),
                    'mailing_address_line1': str(record.PM_MAIL_A1).strip(),
                    'mailing_address_line2': str(record.PM_MAIL_A2).strip(),
                    'mailing_city': str(record.PM_MAIL_CT).strip(),
                    'mailing_state': str(record.PM_MAIL_ST).strip(),
                    'mailing_zip': str(record.PM_MAIL_ZP).strip(),
                    'physical_address': str(record.PM_PROP_AD).strip(),
                    'property_zip': str(record.PM_PROP_ZP).strip(),
                    'deed_reference1': str(record.PM_DEEDRF1).strip(),
                    'deed_reference2': str(record.PM_DEEDRF2).strip(),
                    'deed_reference3': str(record.PM_DEEDRF3).strip(),
                    'deed_reference4': str(record.PM_DEEDRF4).strip(),
                    'deed_reference5': str(record.PM_DEEDRF5).strip(),
                    'total_value': self._parse_numeric(record.PM_TOT_VAL),
                    'improvement_value': self._parse_numeric(record.PM_IMP_VAL),
                    'land_value': self._parse_numeric(record.PM_LND_VAL),
                    'total_acres': self._parse_numeric(record.PM_PV_ACRE),
                    'zoning': str(record.PM_ZONING).strip(),
                    'tax_district': str(record.PM_TAXAREA).strip()
                }
                
                # Insert into database
                cursor.execute('''
                    INSERT INTO parcels (
                        county_parcel_id, parcel_status, owner_name,
                        mailing_address_line1, mailing_address_line2,
                        mailing_city, mailing_state, mailing_zip,
                        physical_address, property_zip,
                        deed_reference1, deed_reference2, deed_reference3,
                        deed_reference4, deed_reference5,
                        total_value, improvement_value, land_value,
                        total_acres, zoning, tax_district
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    parcel_data['county_parcel_id'],
                    parcel_data['parcel_status'],
                    parcel_data['owner_name'],
                    parcel_data['mailing_address_line1'],
                    parcel_data['mailing_address_line2'],
                    parcel_data['mailing_city'],
                    parcel_data['mailing_state'],
                    parcel_data['mailing_zip'],
                    parcel_data['physical_address'],
                    parcel_data['property_zip'],
                    parcel_data['deed_reference1'],
                    parcel_data['deed_reference2'],
                    parcel_data['deed_reference3'],
                    parcel_data['deed_reference4'],
                    parcel_data['deed_reference5'],
                    parcel_data['total_value'],
                    parcel_data['improvement_value'],
                    parcel_data['land_value'],
                    parcel_data['total_acres'],
                    parcel_data['zoning'],
                    parcel_data['tax_district']
                ))
            
            conn.commit()
            conn.close()
            table.close()
            
            logger.info(f"Processed {len(table)} parcel records")
            
        except Exception as e:
            logger.error(f"Error processing parcel master: {e}")
    
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
    
    def create_api_index(self):
        """Create a JSON index file for the API to quickly look up parcels."""
        logger.info("Creating API index...")
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Get all parcels with basic info
        cursor.execute('''
            SELECT 
                county_parcel_id,
                owner_name,
                physical_address,
                total_value,
                total_acres,
                last_updated
            FROM parcels
            ORDER BY county_parcel_id
        ''')
        
        parcels = []
        for row in cursor.fetchall():
            parcels.append({
                'county_parcel_id': row[0],
                'owner_name': row[1],
                'physical_address': row[2],
                'total_value': row[3],
                'total_acres': row[4],
                'last_updated': row[5]
            })
        
        # Save to JSON file
        index_path = self.processed_dir / "parcel_index.json"
        with open(index_path, 'w') as f:
            json.dump({
                'metadata': {
                    'county': 'Teton County Idaho',
                    'total_parcels': len(parcels),
                    'last_updated': datetime.now().isoformat(),
                    'source': 'Teton County Idaho GIS Database'
                },
                'parcels': parcels
            }, f, indent=2)
        
        conn.close()
        logger.info(f"Created API index with {len(parcels)} parcels")
    
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
        self.create_api_index()
        
        logger.info("Pipeline completed successfully!")
        return True

def main():
    """Main entry point for the script."""
    processor = TetonCountyDataProcessor()
    
    # Check if we're running in manual mode (files already downloaded)
    if any((processor.data_dir / f).exists() for f in processor.expected_files):
        logger.info("Found existing DBF files, processing only...")
        processor.process_dbf_files()
        processor.create_api_index()
    else:
        # Run full pipeline
        processor.run_full_process()

if __name__ == "__main__":
    main() 