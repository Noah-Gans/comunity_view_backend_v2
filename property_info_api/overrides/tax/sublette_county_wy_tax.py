"""Sublette County WY tax scraper for Terra GIS system."""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import time
import re
import json
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_tax(url: str, county: str = None) -> Dict:
    """Scrape tax information from Sublette County Terra GIS system."""
    try:
        logger.info(f"(Sublette County WY Tax) Starting Sublette County WY tax scrape for {county}")
        start_time = time.time()
        
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Fetch the tax page
        logger.debug(f"(Sublette County WY Tax) Fetching tax page")
        response = session.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        
        fetch_time = time.time() - start_time
        logger.debug(f"(Sublette County WY Tax) Fetch time: {fetch_time:.2f}s")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Write HTML file for debugging
        
        
        # Extract tax data
        tax_data = extract_sublette_tax_data(soup, county)
        
        total_time = time.time() - start_time
        logger.info(f"(Sublette County WY Tax) Sublette County WY tax scrape completed in {total_time:.2f}s for {county}")
        
        return tax_data
        
    except Exception as e:
        logger.error(f"(Sublette County WY Tax) Error: {e}")
        return {"error": str(e), "source": f"sublette_tax_{county}"}

def extract_sublette_tax_data(soup: BeautifulSoup, county: str) -> Dict:
    """Extract tax data from Sublette County Terra GIS HTML structure."""
    try:
        logger.debug(f"(Sublette County WY Tax) Extracting data for {county}")
        
        # Initialize tax data structure
        tax_data = {
            "county": county.replace("_", " ").title(),
            "tax_id": None,
            "account_number": None,
            "tax_types": None,
            "current_year": None,
            "district": None,
            "mill_levy": None,
            "owner_name": None,
            "mailing_address": None,
            "street_address": None,
            "legal_description": None,
            "current_taxes": {},
            "historical_taxes": [],
            "source": f"sublette_tax_{county}",
            "scraped": True
        }
        
        # Find the parcel information table
        parcel_table = soup.find('table', class_='parcelDetail')
        if not parcel_table:
            logger.debug(f"(Sublette County WY Tax) Parcel table not found")
            return tax_data
        
        logger.debug(f"(Sublette County WY Tax) Found parcel table")
        
        # Extract basic parcel information from the first row
        first_row = parcel_table.find('tr')
        if first_row:
            cells = first_row.find_all('td')
            if len(cells) >= 3:
                # First cell: Tax ID, Account, Tax Types
                first_cell_text = cells[0].get_text()
                
                # Extract Tax ID
                tax_id_match = re.search(r'Tax\s+ID:\s*([^\s]+)', first_cell_text)
                if tax_id_match:
                    tax_data["tax_id"] = tax_id_match.group(1)
                    logger.debug(f"(Sublette County WY Tax) Found tax ID: {tax_data['tax_id']}")
                
                # Extract Account Number
                account_match = re.search(r'Account:\s*([^\s]+)', first_cell_text)
                if account_match:
                    tax_data["account_number"] = account_match.group(1)
                    logger.debug(f"(Sublette County WY Tax) Found account: {tax_data['account_number']}")
                
                # Extract Tax Types
                tax_types_match = re.search(r'Tax Type\(s\).*?:\s*([A-Z,\s]+)', first_cell_text)
                if tax_types_match:
                    tax_data["tax_types"] = tax_types_match.group(1).strip()
                    logger.debug(f"(Sublette County WY Tax) Found tax types: {tax_data['tax_types']}")
                
                # Second cell: Current Year
                second_cell_text = cells[1].get_text()
                year_match = re.search(r'Current Year:\s*(\d{4})', second_cell_text)
                if year_match:
                    tax_data["current_year"] = year_match.group(1)
                    logger.debug(f"(Sublette County WY Tax) Found current year: {tax_data['current_year']}")
                
                # Third cell: District and Mill Levy
                third_cell_text = cells[2].get_text()
                district_match = re.search(r'District:\s*(\d+)', third_cell_text)
                if district_match:
                    district_num = district_match.group(1)
                    district_name_match = re.search(r'DISTRICT\s+\d+\s+([^\n]+)', third_cell_text)
                    if district_name_match:
                        district_name = district_name_match.group(1).strip()
                        tax_data["district"] = f"{district_num} {district_name}"
                    else:
                        tax_data["district"] = district_num
                    logger.debug(f"(Sublette County WY Tax) Found district: {tax_data['district']}")
                
                mill_levy_match = re.search(r'Mill Levy:\s*([\d.]+)', third_cell_text)
                if mill_levy_match:
                    tax_data["mill_levy"] = mill_levy_match.group(1)
                    logger.debug(f"(Sublette County WY Tax) Found mill levy: {tax_data['mill_levy']}")
        
        # Extract owner information from second row
        rows = parcel_table.find_all('tr')
        logger.debug(f"(Sublette County WY Tax) Found {len(rows)} rows in parcel table")
        
        if len(rows) > 1:
            owner_row = rows[1]
            owner_cells = owner_row.find_all('td')
            logger.debug(f"(Sublette County WY Tax) Owner row has {len(owner_cells)} cells")
            if len(owner_cells) >= 2:
                owner_text = owner_cells[1].get_text(strip=True)
                logger.debug(f"(Sublette County WY Tax) Owner cell text: '{owner_text}'")
                if owner_text and owner_text != "Current Owner(s):":
                    tax_data["owner_name"] = owner_text
                    logger.debug(f"(Sublette County WY Tax) Found owner: {tax_data['owner_name']}")
                else:
                    logger.debug(f"(Sublette County WY Tax) Owner text was empty or label")
        
        # Extract mailing address from third row
        if len(rows) > 2:
            mailing_row = rows[2]
            mailing_cells = mailing_row.find_all('td')
            logger.debug(f"(Sublette County WY Tax) Mailing row has {len(mailing_cells)} cells")
            if len(mailing_cells) >= 2:
                mailing_text = mailing_cells[1].get_text(strip=True)
                logger.debug(f"(Sublette County WY Tax) Mailing cell text: '{mailing_text}'")
                if mailing_text and mailing_text != "Mailing Address:":
                    tax_data["mailing_address"] = mailing_text
                    logger.debug(f"(Sublette County WY Tax) Found mailing address: {tax_data['mailing_address']}")
                else:
                    logger.debug(f"(Sublette County WY Tax) Mailing text was empty or label")
        
        # Extract street address from fourth row
        if len(rows) > 3:
            street_row = rows[3]
            street_cells = street_row.find_all('td')
            logger.debug(f"(Sublette County WY Tax) Street row has {len(street_cells)} cells")
            if len(street_cells) >= 2:
                street_text = street_cells[1].get_text(strip=True)
                logger.debug(f"(Sublette County WY Tax) Street cell text: '{street_text}'")
                if street_text and street_text != "Street Address:":
                    tax_data["street_address"] = street_text
                    logger.debug(f"(Sublette County WY Tax) Found street address: {tax_data['street_address']}")
                else:
                    logger.debug(f"(Sublette County WY Tax) Street text was empty or label")
        
        # Extract legal description from fifth row
        if len(rows) > 4:
            legal_row = rows[4]
            legal_cells = legal_row.find_all('td')
            logger.debug(f"(Sublette County WY Tax) Legal row has {len(legal_cells)} cells")
            if len(legal_cells) >= 2:
                legal_text = legal_cells[1].get_text(strip=True)
                logger.debug(f"(Sublette County WY Tax) Legal cell text: '{legal_text}'")
                if legal_text and legal_text != "Legal Description:":
                    tax_data["legal_description"] = legal_text
                    logger.debug(f"(Sublette County WY Tax) Found legal description: {tax_data['legal_description']}")
                else:
                    logger.debug(f"(Sublette County WY Tax) Legal text was empty or label")
        
        # Extract current year tax information
        current_taxes = extract_current_taxes(soup, county)
        tax_data["current_taxes"] = current_taxes
        
        # Extract historical tax information
        historical_taxes = extract_historical_taxes(soup, county)
        tax_data["historical_taxes"] = historical_taxes
        
        # DEBUG: Print the complete extracted data
        logger.debug(f"(Sublette County WY Tax) ===== COMPLETE EXTRACTED DATA =====")
        logger.debug(f"(Sublette County WY Tax) County: {tax_data['county']}")
        logger.debug(f"(Sublette County WY Tax) Tax ID: {tax_data['tax_id']}")
        logger.debug(f"(Sublette County WY Tax) Account Number: {tax_data['account_number']}")
        logger.debug(f"(Sublette County WY Tax) Tax Types: {tax_data['tax_types']}")
        logger.debug(f"(Sublette County WY Tax) Current Year: {tax_data['current_year']}")
        logger.debug(f"(Sublette County WY Tax) District: {tax_data['district']}")
        logger.debug(f"(Sublette County WY Tax) Mill Levy: {tax_data['mill_levy']}")
        logger.debug(f"(Sublette County WY Tax) Owner Name: {tax_data['owner_name']}")
        logger.debug(f"(Sublette County WY Tax) Mailing Address: {tax_data['mailing_address']}")
        logger.debug(f"(Sublette County WY Tax) Street Address: {tax_data['street_address']}")
        logger.debug(f"(Sublette County WY Tax) Legal Description: {tax_data['legal_description']}")
        logger.debug(f"(Sublette County WY Tax) Current Taxes: {tax_data['current_taxes']}")
        logger.debug(f"(Sublette County WY Tax) Historical Taxes Count: {len(tax_data['historical_taxes'])}")
        logger.debug(f"(Sublette County WY Tax) ===== END EXTRACTED DATA =====")
        
        logger.debug(f"(Sublette County WY Tax) Extracted data successfully")
        return tax_data
        
    except Exception as e:
        logger.error(f"(Sublette County WY Tax) Error extracting data: {str(e)}")
        return {
            "county": county.replace("_", " ").title(),
            "error": f"Data extraction failed: {str(e)}",
            "source": f"sublette_tax_{county}",
            "scraped": False
        }

def extract_current_taxes(soup: BeautifulSoup, county: str) -> Dict:
    """Extract current year tax information."""
    try:
        logger.debug(f"(Sublette County WY Tax) Extracting current taxes")
        
        current_taxes = {}
        
        # Find the current year taxes table
        history_table = soup.find('table', class_='history')
        if not history_table:
            logger.debug(f"(Sublette County WY Tax) History table not found")
            return current_taxes
        
        logger.debug(f"(Sublette County WY Tax) Found history table")
        
        # Look for the "CURRENT YEAR TAXES" section
        rows = history_table.find_all('tr')
        
        # Find the current year total row
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:
                year_text = cells[0].get_text(strip=True)
                if 'Total' in year_text and '2025' in year_text:
                    # Extract tax levied
                    tax_levied_text = cells[1].get_text(strip=True)
                    tax_levied_match = re.search(r'\$?\s*([\d,]+\.?\d*)', tax_levied_text)
                    if tax_levied_match:
                        tax_levied = float(tax_levied_match.group(1).replace(',', ''))
                    
                    # Extract tax paid
                    tax_paid_text = cells[3].get_text(strip=True)
                    tax_paid_match = re.search(r'\$?\s*([\d,]+\.?\d*)', tax_paid_text)
                    if tax_paid_match:
                        tax_paid = float(tax_paid_match.group(1).replace(',', ''))
                    else:
                        tax_paid = 0.0
                    
                    # Extract amount due
                    amount_due_text = cells[4].get_text(strip=True)
                    amount_due_match = re.search(r'\$?\s*([\d,]+\.?\d*)', amount_due_text)
                    if amount_due_match:
                        amount_due = float(amount_due_match.group(1).replace(',', ''))
                    
                    current_taxes = {
                        "total": {
                            "tax_levied": tax_levied,
                            "tax_paid": tax_paid,
                            "amount_due": amount_due,
                            "date_paid": None
                        }
                    }
                    
                    logger.debug(f"(Sublette County WY Tax) Extracted current taxes: {current_taxes}")
                    break
        
        return current_taxes
        
    except Exception as e:
        logger.error(f"(Sublette County WY Tax) Error extracting current taxes: {str(e)}")
        return {}

def extract_historical_taxes(soup: BeautifulSoup, county: str) -> List[Dict]:
    """Extract historical tax information with proper payment structure."""
    try:
        logger.debug(f"(Sublette County WY Tax) Extracting historical taxes")
        
        historical_taxes = []
        
        # Find the history table
        history_table = soup.find('table', class_='history')
        if not history_table:
            logger.debug(f"(Sublette County WY Tax) History table not found")
            return historical_taxes
        
        # Find all rows in the history section
        rows = history_table.find_all('tr')
        
        # Look for rows that contain year totals (skip current year)
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:
                year_text = cells[0].get_text(strip=True)
                
                # Look for year totals (but not current year)
                if 'Total' in year_text and '2025' not in year_text:
                    year_match = re.search(r'(\d{4})', year_text)
                    if year_match:
                        year = year_match.group(1)
                        
                        # Extract tax levied (this is the TOTAL for the year)
                        tax_levied_text = cells[1].get_text(strip=True)
                        tax_levied_match = re.search(r'\$?\s*([\d,]+\.?\d*)', tax_levied_text)
                        if tax_levied_match:
                            tax_levied = float(tax_levied_match.group(1).replace(',', ''))
                        
                        # Extract first payment info
                        first_date_paid = cells[2].get_text(strip=True)
                        first_tax_paid_text = cells[3].get_text(strip=True)
                        first_tax_paid_match = re.search(r'\$?\s*([\d,]+\.?\d*)', first_tax_paid_text)
                        first_tax_paid = float(first_tax_paid_match.group(1).replace(',', '')) if first_tax_paid_match else 0.0
                        
                        # Check if there's a second payment row
                        second_half_paid = 0.0
                        second_half_date = None
                        
                        current_row_index = rows.index(row)
                        if current_row_index + 1 < len(rows):
                            next_row = rows[current_row_index + 1]
                            next_cells = next_row.find_all('td')
                            if len(next_cells) >= 5:
                                # Check if this is a second payment row (empty first two cells)
                                first_cell_text = next_cells[0].get_text(strip=True)
                                second_cell_text = next_cells[1].get_text(strip=True)
                                
                                if (not first_cell_text.strip() or first_cell_text.strip() == '&nbsp;') and \
                                   (not second_cell_text.strip() or second_cell_text.strip() == '&nbsp;'):
                                    # This is a second payment row
                                    second_date_paid = next_cells[2].get_text(strip=True)
                                    second_tax_paid_text = next_cells[3].get_text(strip=True)
                                    second_tax_paid_match = re.search(r'\$?\s*([\d,]+\.?\d*)', second_tax_paid_text)
                                    if second_tax_paid_match:
                                        second_half_paid = float(second_tax_paid_match.group(1).replace(',', ''))
                                        second_half_date = second_date_paid if second_date_paid and second_date_paid != '&nbsp;' else None
                        
                        # Calculate total paid
                        total_paid = first_tax_paid + second_half_paid
                        
                        # Determine payment structure
                        if second_half_paid > 0:
                            # Two payments: split them between first and second half
                            first_half_paid = first_tax_paid
                            first_half_date = first_date_paid if first_date_paid and first_date_paid != '&nbsp;' else None
                        else:
                            # Single payment: put it all in second half, first half = 0
                            first_half_paid = 0.0
                            first_half_date = None
                            second_half_paid = first_tax_paid
                            second_half_date = first_date_paid if first_date_paid and first_date_paid != '&nbsp;' else None
                        
                        historical_taxes.append({
                            "year": year,
                            "tax_levied": tax_levied,
                            "tax_paid": total_paid,
                            "date_paid": first_date_paid if first_date_paid and first_date_paid != '&nbsp;' else None,
                            "amount_due": 0.0,
                            "first_half": {
                                "tax_levied": tax_levied / 2,
                                "tax_paid": first_half_paid,
                                "date_paid": first_half_date,
                                "amount_due": 0.0  # Simplified as requested
                            },
                            "second_half": {
                                "tax_levied": tax_levied / 2,
                                "tax_paid": second_half_paid,
                                "date_paid": second_half_date,
                                "amount_due": 0.0  # Simplified as requested
                            }
                        })
        
        logger.debug(f"(Sublette County WY Tax) Extracted {len(historical_taxes)} historical records")
        return historical_taxes
        
    except Exception as e:
        logger.error(f"(Sublette County WY Tax) Error extracting historical taxes: {str(e)}")
        return []

def clean_amount(amount_str: str) -> Optional[float]:
    """Clean and convert amount string to float."""
    if not amount_str or amount_str.strip() == "" or amount_str.strip() == "&nbsp;":
        return None
    
    # Remove $ and commas
    cleaned = amount_str.replace("$", "").replace(",", "").strip()
    
    # Handle negative amounts
    if cleaned.startswith("-"):
        try:
            return -float(cleaned[1:])
        except ValueError:
            return None
    
    try:
        return float(cleaned)
    except ValueError:
        return None
