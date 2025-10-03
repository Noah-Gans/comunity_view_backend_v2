"""Teton County Wyoming tax scraper using direct API calls."""
import requests
from bs4 import BeautifulSoup
from typing import Dict
import time
import os
import re
import json
from datetime import datetime
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_tax(url: str) -> Dict:
    """Scrape tax information from Teton County Wyoming using direct API calls."""
    try:
        logger.info(f"(Teton County WY Tax) Starting Teton County WY tax scrape")
        start_time = time.time()
        
        # Extract tax_id from the URL
        tax_id = extract_tax_id_from_url(url)
        if not tax_id:
            logger.error("Could not extract tax_id from URL")
            return {"error": "Could not extract tax_id from URL"}
        
        logger.debug(f"Extracted tax_id: {tax_id}")
        
        # Get general tax data (Layer 0) - account, district, mill levy, etc.
        general_tax_data = get_general_tax_data_from_api(tax_id)
        
        # Get detailed current year tax data (Layer 4) - this has the real current year info
        current_tax_data = get_detailed_current_tax_data_from_api(tax_id)
        
        # Get historical tax data (Layer 1)
        historical_tax_data = get_historical_tax_data_from_api(tax_id)
        
        # Process and combine the data
        result = process_combined_tax_data(current_tax_data, historical_tax_data, tax_id, general_tax_data)
        
        total_time = time.time() - start_time
        logger.info(f"(Teton County WY Tax) Teton County WY tax scrape completed in {total_time:.2f} seconds")
        
        return result
        
    except Exception as e:
        logger.error(f"Teton County WY tax scrape error: {e}")
        return {"error": str(e), "source": "teton_county_wy_tax"}

def extract_tax_id_from_url(url: str) -> str:
    """Extract tax_id from the dashboard URL."""
    match = re.search(r'#ParcelInfo=([^&]+)', url)
    if match:
        return match.group(1)
    return None

def get_general_tax_data_from_api(tax_id: str) -> Dict:
    """Get general tax data from Layer 0."""
    try:
        api_url = "https://gis.tetoncountywy.gov/server/rest/services/Property_Tax_Search/Property_tax_search/FeatureServer/0/query"
        
        params = {
            'f': 'json',
            'where': f"localno='{tax_id}'",  # Changed from parcel to localno
            'outFields': '*'
        }
        
        logger.debug(f"Fetching general tax data from Layer 0 for tax_id: {tax_id}")
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Retrieved {len(data.get('features', []))} general tax records")
        
        return data
        
    except Exception as e:
        logger.warning(f"General tax API error: {e}")
        return {"features": []}

def get_detailed_current_tax_data_from_api(tax_id: str) -> Dict:
    """Get detailed current year tax data from Layer 4."""
    try:
        api_url = "https://gis.tetoncountywy.gov/server/rest/services/Property_Tax_Search/Property_tax_search/FeatureServer/4/query"
        
        params = {
            'f': 'json',
            'where': f"parcel='{tax_id}'",
            'outFields': '*'
        }
        
        logger.debug(f"Fetching detailed current tax data from Layer 4 for tax_id: {tax_id}")
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Retrieved {len(data.get('features', []))} detailed current tax records")
        
        return data
        
    except Exception as e:
        logger.warning(f"Detailed current tax API error: {e}")
        return {"features": []}

def get_historical_tax_data_from_api(tax_id: str) -> Dict:
    """Get historical tax data from Layer 1."""
    try:
        api_url = "https://gis.tetoncountywy.gov/server/rest/services/Property_Tax_Search/Property_tax_search/FeatureServer/1/query"
        
        params = {
            'f': 'json',
            'where': f"tax_id='{tax_id}'",
            'outFields': '*',
            'resultRecordCount': 1000,
            'orderByFields': 'taxyear DESC'
        }
        
        logger.debug(f"Fetching historical tax data from Layer 1 for tax_id: {tax_id}")
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Retrieved {len(data.get('features', []))} historical tax records")
        
        return data
        
    except Exception as e:
        logger.warning(f"Historical tax API error: {e}")
        return {"features": []}

def process_combined_tax_data(current_data: Dict, historical_data: Dict, tax_id: str, general_data: Dict = None) -> Dict:
    """Process both current and historical tax data."""
    try:
        logger.debug(f"Processing combined tax data for tax_id: {tax_id}")
        
        # Process current year data (Layer 4 - detailed current year info)
        current_tax = process_current_tax_data(current_data)  # Keep original function name
        
        # Process historical data (Layer 1)
        historical_taxes = process_historical_tax_data(historical_data)
        
        # Process general data (Layer 0)
        general_info = process_general_tax_data(general_data)
        
        result = {
            "tax_id": tax_id,
            "current_tax": current_tax,
            "historical_taxes": historical_taxes,
            "general_info": general_info,
            "total_years": len(historical_taxes) + (1 if current_tax else 0),
            "source": "teton_county_wy_tax_api_combined",
            "scraped": True
        }
        
        # Print summary
        print_tax_summary(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return {"error": str(e)}

def process_current_tax_data(current_data: Dict) -> Dict:
    """Process current year tax data from Layer 4."""
    features = current_data.get('features', [])
    if not features:
        logger.debug("No current tax data features found")
        return None
    
    attrs = features[0].get('attributes', {})
    logger.debug(f"Processing current tax data: tax_year={attrs.get('taxyear')}")
    logger.debug(f"Processing current tax data: {features}")
    # Safely handle None values
    total_levied = attrs.get('totallevied', 0) or 0
    total_received = attrs.get('totalreceived', 0) or 0
    amount_due = total_levied - total_received
    
    return {
        "tax_year": attrs.get('taxyear'),
        "owner_name": attrs.get('ownername'),
        "total_tax_levied": total_levied,
        "tax_received": total_received,
        "amount_due": amount_due,
        "first_half": {
            "levied": attrs.get('firsthalftotallevied', 0) or 0,
            "paid": attrs.get('firsthalfreceived', 0) or 0,
            "balance": attrs.get('firsthalfdue_final', 0) or 0,
            "days_delinquent": attrs.get('firsthalfdays', 0) or 0
        },
        "second_half": {
            "levied": attrs.get('secondhalftotallevied', 0) or 0,
            "paid": attrs.get('secondhalfreceived', 0) or 0,
            "balance": attrs.get('secondhalfdue_final', 0) or 0,
            "days_delinquent": attrs.get('secondhalfdays', 0) or 0
        },
        "parcel": attrs.get('parcel', ''),
        "status": "paid" if total_received > 0 else "unpaid"
    }

def process_historical_tax_data(historical_data: Dict) -> list:
    """Process historical tax data from Layer 1."""
    features = historical_data.get('features', [])
    logger.debug(f"Processing {len(features)} historical tax features")
    
    # Group by year to handle multiple payments per year
    year_data = {}
    
    for feature in features:
        attrs = feature.get('attributes', {})
        year = attrs.get('taxyear')
        
        if year and year < 2025:  # Exclude current year
            if year not in year_data:
                year_data[year] = {
                    "tax_year": year,
                    "total_tax_levied": attrs.get('totaltaxlevied', 0),
                    "first_half_payment": 0,
                    "second_half_payment": 0,
                    "transaction_dates": [],
                    "tax_types": attrs.get('tax_types', ''),
                    "notes": attrs.get('notes', ''),
                    "status": "unpaid"
                }
            
            # Add payment amounts
            first_half = attrs.get('firsthalfpayment', 0) or 0
            second_half = attrs.get('secondhalfpayment', 0) or 0
            
            year_data[year]["first_half_payment"] += first_half
            year_data[year]["second_half_payment"] += second_half
            
            # Track transaction dates
            transaction_date = convert_timestamp(attrs.get('transactiondate'))
            if transaction_date:
                year_data[year]["transaction_dates"].append(transaction_date)
            
            # Update status if any payment was made
            if first_half > 0 or second_half > 0:
                year_data[year]["status"] = "paid"
    
    # Convert to list and sort by year
    historical_taxes = []
    for year, data in year_data.items():
        # Calculate total tax paid
        total_paid = data["first_half_payment"] + data["second_half_payment"]
        
        # Use the earliest transaction date as the main date_paid
        data["transaction_date"] = min(data["transaction_dates"]) if data["transaction_dates"] else None
        del data["transaction_dates"]  # Remove the list, keep only the main date
        
        # Add the missing tax_paid field
        data["tax_paid"] = total_paid
        
        historical_taxes.append(data)
    
    # Sort by year (newest first)
    historical_taxes.sort(key=lambda x: x['tax_year'], reverse=True)
    logger.debug(f"Processed {len(historical_taxes)} historical tax years")
    return historical_taxes

def process_general_tax_data(general_data: Dict) -> Dict:
    """Process general tax data from Layer 0."""
    features = general_data.get('features', [])
    logger.debug(f"Processing {general_data} ")
    if not features:
        logger.debug("No general tax data features found")
        return {}
    
    attrs = features[0].get('attributes', {})
    logger.debug(f"Processing general tax data: parcel={attrs.get('parcel')}")
    
    # Debug: Print all available attributes
    logger.debug("Available attributes from general tax data:")
    for key, value in attrs.items():
        logger.debug(f"  {key}: {value}")
    
    return {
        "account": attrs.get('accountno'),  # Changed from accountnumber to accountno
        "district": attrs.get('defaulttaxdistrict'),  # Changed from district to defaulttaxdistrict
        "mill_levy": attrs.get('totalmilllevy'),  # Changed from milllevy to totalmilllevy
        "street_address": attrs.get('st_address'),  # Added street address
        "legal_description": attrs.get('legal'),  # Added legal description
        "owner_name": attrs.get('name1'),  # Added owner name
        "mailing_address": attrs.get('mailaddress1'),  # Added mailing address
        "mailing_city": attrs.get('mailcity'),  # Added mailing city
        "mailing_state": attrs.get('mailstate'),  # Added mailing state
        "mailing_zip": attrs.get('mailzipcode'),  # Added mailing zip
        "parcel": attrs.get('parcel')
    }

def convert_timestamp(timestamp):
    """Convert Unix timestamp to readable date."""
    if timestamp:
        return datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
    return None

def print_tax_summary(tax_data: Dict) -> None:
    """Print a summary of the tax data."""
    logger.debug("="*80)
    logger.debug("️ TETON COUNTY WYOMING TAX SUMMARY")
    logger.debug("="*80)
    
    # Current year summary
    current_year = tax_data.get('current_tax')
    if current_year:
        logger.debug(f"📅 CURRENT YEAR ({current_year.get('tax_year', 'N/A')}):")
        logger.debug(f"   👤 Owner: {current_year.get('owner_name', 'N/A')}")
        logger.debug(f"   💰 Total Tax Levied: ${current_year.get('total_tax_levied', 0):,.2f}")
        logger.debug(f"   💸 Amount Due: ${current_year.get('amount_due', 0):,.2f}")
        logger.debug(f"   Status: {current_year.get('status', 'UNKNOWN').upper()}")
    
    # Historical summary
    historical = tax_data.get('historical_taxes', [])
    if historical:
        logger.debug(f"\n HISTORICAL DATA ({len(historical)} years):")
        for record in historical[:5]:  # Show first 5 years
            year = record.get('tax_year', 'N/A')
            total = record.get('total_tax_levied', 0)
            paid = record.get('tax_paid', 0)
            status = "PAID" if paid > 0 else "UNPAID"
            logger.debug(f"   {year}: ${total:,.2f} - {status}")
        if len(historical) > 5:
            logger.debug(f"   ... and {len(historical) - 5} more years")
    
    logger.debug("="*80)
