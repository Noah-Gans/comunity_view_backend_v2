"""Tyler Technologies tax scraper for Sublette, Fremont, and Lincoln counties."""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List
import time
import os
import re
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

def scrape_tax(url: str, county: str = None) -> Dict:
    """Scrape tax information from Tyler Technologies systems including history."""
    try:
        logger.info(f"(Tyler Technologies Tax) Starting Tyler Technologies tax scrape for {county}")
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
        
        # Step 1: Visit the main tax detail page to establish session
        logger.debug(f"(Tyler Technologies Tax) Step 1: Visiting main tax page to establish session")
        response1 = session.get(url, timeout=15, headers=headers)
        response1.raise_for_status()
        
        fetch_time = time.time() - start_time
        logger.debug(f"(Tyler Technologies Tax) Fetch time: {fetch_time:.2f}s")
        
        soup1 = BeautifulSoup(response1.text, 'html.parser')
        
        # Step 2: Navigate to history page using the same session
        base_url = url.split('/detail.aspx')[0]  # Extract base URL
        history_url = f"{base_url}/history.aspx"
        logger.debug(f"(Tyler Technologies Tax) Step 2: Visiting history page: {history_url}")
        
        response2 = session.get(history_url, timeout=15, headers=headers)
        response2.raise_for_status()
        
        soup2 = BeautifulSoup(response2.text, 'html.parser')
        
        # Debug files disabled for mass collection
        # logger.debug(f"(Tyler Technologies Tax) Debug files disabled for mass collection")
        
        # Extract current tax data from detail page
        current_data = extract_tyler_tax_data(soup1, county)
        
        # Extract historical data from history page
        historical_data = extract_historical_data(soup2, county)
        
        # Create standardized return format
        standardized_data = create_standardized_tax_data(current_data, historical_data, county)
        
        total_time = time.time() - start_time
        logger.info(f"(Tyler Technologies Tax) Tyler Technologies tax scrape completed in {total_time:.2f}s for {county}")
        
        return standardized_data
        
    except Exception as e:
        logger.error(f"(Tyler Technologies Tax) Error: {e}")
        return {"error": str(e), "source": f"tyler_technologies_tax_{county}"}

def extract_tyler_tax_data(soup: BeautifulSoup, county: str) -> Dict:
    """Extract tax data from Tyler Technologies page structure."""
    try:
        logger.debug(f"(Tyler Technologies Tax) Extracting data for {county}")
        
        # Tyler Technologies common patterns
        tax_data = {
            "tax_year": None,
            "assessed_value": None,
            "tax_amount": None,
            "due_date": None,
            "taxable_value": None,
            "net_taxable": None,
            "first_half": None,
            "second_half": None,
            "first_half_due_date": None,
            "second_half_due_date": None,
            "source": f"tyler_technologies_tax_{county}",
            "scraped": True
        }
        
        # Extract tax year from the "2025 Taxes:" or "2025 Payments:" headers
        year_elements = soup.find_all('span', string=lambda text: text and ('2025' in text or '2024' in text) and ('Taxes:' in text or 'Payments:' in text))
        if year_elements:
            year_match = re.search(r'20\d{2}', year_elements[0].get_text())
            if year_match:
                tax_data["tax_year"] = year_match.group(0)
                logger.debug(f"(Tyler Technologies Tax) Found tax year: {tax_data['tax_year']}")
        
        # Extract Tax ID
        logger.debug(f"(Tyler Technologies Tax) Searching for Tax ID element...")
        tax_id_elem = soup.find('span', id=lambda x: x and 'lblTaxID' in x)
        if tax_id_elem:
            tax_id_text = tax_id_elem.get_text(strip=True)
            tax_id_id = tax_id_elem.get('id', 'no-id')
            logger.debug(f"(Tyler Technologies Tax) Found tax ID element with ID: {tax_id_id}")
            logger.debug(f"(Tyler Technologies Tax) Tax ID element text: '{tax_id_text}'")
            tax_data["tax_id"] = tax_id_text
            logger.debug(f"(Tyler Technologies Tax) Found tax ID: {tax_data['tax_id']}")
        else:
            logger.debug(f"(Tyler Technologies Tax) No tax ID element found")
        
        # Extract Levy District
        logger.debug(f"(Tyler Technologies Tax) Searching for Levy District element...")
        levy_elem = soup.find('span', id=lambda x: x and 'lblLevy' in x and 'District' not in x)
        if levy_elem:
            levy_text = levy_elem.get_text(strip=True)
            levy_id = levy_elem.get('id', 'no-id')
            logger.debug(f"(Tyler Technologies Tax) Found levy element with ID: {levy_id}")
            logger.debug(f"(Tyler Technologies Tax) Levy element text: '{levy_text}'")
            tax_data["levy_district"] = levy_text
            logger.debug(f"(Tyler Technologies Tax) Found levy district: {tax_data['levy_district']}")
        else:
            logger.debug(f"(Tyler Technologies Tax) No levy element found")
        
        # Extract market value (assessed value)
        market_value_elem = soup.find('span', id=lambda x: x and 'lblValueMarket' in x)
        if market_value_elem:
            tax_data["assessed_value"] = market_value_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found assessed value: {tax_data['assessed_value']}")
        
        # Extract taxable value
        taxable_value_elem = soup.find('span', id=lambda x: x and 'lblValueTaxable' in x)
        if taxable_value_elem:
            tax_data["taxable_value"] = taxable_value_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found taxable value: {tax_data['taxable_value']}")
        
        # Extract net taxable
        net_taxable_elem = soup.find('span', id=lambda x: x and 'lblNetTaxable' in x)
        if net_taxable_elem:
            tax_data["net_taxable"] = net_taxable_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found net taxable: {tax_data['net_taxable']}")
        
        # Extract first half tax amount
        first_half_elem = soup.find('span', id=lambda x: x and 'lblTaxFirstHalf' in x)
        if first_half_elem:
            tax_data["first_half"] = first_half_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found first half: {tax_data['first_half']}")
        
        # Extract second half tax amount
        second_half_elem = soup.find('span', id=lambda x: x and 'lblTaxSecondHalf' in x)
        if second_half_elem:
            tax_data["second_half"] = second_half_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found second half: {tax_data['second_half']}")
        
        # Extract first half due date
        first_due_elem = soup.find('span', id=lambda x: x and 'lblFirstDueDate' in x)
        if first_due_elem:
            tax_data["first_half_due_date"] = first_due_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found first half due date: {tax_data['first_half_due_date']}")
        
        # Extract second half due date
        second_due_elem = soup.find('span', id=lambda x: x and 'lblSecondDueDate' in x)
        if second_due_elem:
            tax_data["second_half_due_date"] = second_due_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found second half due date: {tax_data['second_half_due_date']}")
        
        # Extract total tax amount
        total_tax_elem = soup.find('span', id=lambda x: x and 'lblTaxTotal' in x)
        if total_tax_elem:
            tax_data["tax_amount"] = total_tax_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found tax amount: {tax_data['tax_amount']}")
        
        # Extract due dates (get the latest one) - fallback for older systems
        due_date_elems = soup.find_all('span', id=lambda x: x and 'DueDate' in x)
        if due_date_elems:
            # Get the second due date (usually the later one)
            if len(due_date_elems) >= 2:
                tax_data["due_date"] = due_date_elems[1].get_text(strip=True)
                logger.debug(f"(Tyler Technologies Tax) Found due date: {tax_data['due_date']}")
            elif len(due_date_elems) == 1:
                tax_data["due_date"] = due_date_elems[0].get_text(strip=True)
                logger.debug(f"(Tyler Technologies Tax) Found due date: {tax_data['due_date']}")
        
        # Extract payment information
        logger.debug(f"(Tyler Technologies Tax) Searching for payment elements...")
        
        # Extract first half payment
        first_half_payment_elem = soup.find('span', id=lambda x: x and 'lblPayFirstHalf' in x)
        if first_half_payment_elem:
            tax_data["first_half_payment"] = first_half_payment_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found first half payment: {tax_data['first_half_payment']}")
        else:
            logger.debug(f"(Tyler Technologies Tax) No first half payment element found")
        
        # Extract second half payment
        second_half_payment_elem = soup.find('span', id=lambda x: x and 'lblPaySecondHalf' in x)
        if second_half_payment_elem:
            tax_data["second_half_payment"] = second_half_payment_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found second half payment: {tax_data['second_half_payment']}")
        else:
            logger.debug(f"(Tyler Technologies Tax) No second half payment element found")
        
        # Extract total payment
        total_payment_elem = soup.find('span', id=lambda x: x and 'lblPayTotal' in x)
        if total_payment_elem:
            tax_data["total_payment"] = total_payment_elem.get_text(strip=True)
            logger.debug(f"(Tyler Technologies Tax) Found total payment: {tax_data['total_payment']}")
        else:
            logger.debug(f"(Tyler Technologies Tax) No total payment element found")
        
        return tax_data
        
    except Exception as e:
        logger.error(f"(Tyler Technologies Tax) Extraction error: {e}")
        return {
            "error": f"Data extraction failed: {str(e)}",
            "source": f"tyler_technologies_tax_{county}"
        }

def extract_historical_data(soup: BeautifulSoup, county: str) -> Dict:
    """Extract historical tax data from the history page."""
    try:
        logger.debug(f"(Tyler Technologies Tax) Extracting historical data for {county}")
        
        historical_data = {
            "years": [],
            "historical_taxes": [],
            "source": f"tyler_technologies_history_{county}"
        }
        
        # Find the specific history DataGrid table
        history_table = soup.find('table', {'id': '_ctl0_ContentPlaceHolder1_dgHistory'})
        if not history_table:
            logger.debug(f"(Tyler Technologies Tax) History DataGrid table not found")
            return historical_data
        
        logger.debug(f"(Tyler Technologies Tax) Found history DataGrid table")
        
        # Extract rows from the DataGrid (skip header row)
        rows = history_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 6:  # Should have: Tax Year, Statement#, Bill Date, Bill Amount, Date Paid, Paid Amount
                # Extract data from each cell
                tax_year = cells[0].get_text(strip=True)
                statement_num = cells[1].get_text(strip=True)
                bill_date = cells[2].get_text(strip=True)
                bill_amount = cells[3].get_text(strip=True)
                
                # For payment dates and amounts, we need to handle <br> tags properly
                payment_dates_cell = cells[4]
                paid_amounts_cell = cells[5]
                
                # Clean up the bill amount (remove $ and commas)
                if bill_amount and bill_amount.startswith("$"):
                    bill_amount_clean = bill_amount[1:].replace(",", "")
                else:
                    bill_amount_clean = bill_amount
                
                # Parse payment dates - handle <br> tags by getting text with separators
                payment_dates_text = payment_dates_cell.get_text(separator='|', strip=True)
                payment_dates_split = payment_dates_text.split('|') if payment_dates_text else []
                
                # Parse paid amounts - handle <br> tags by getting text with separators  
                paid_amounts_text = paid_amounts_cell.get_text(separator='|', strip=True)
                paid_amounts_split = paid_amounts_text.split('|') if paid_amounts_text else []
                
                # Extract first and second half data
                first_half_payment_date = payment_dates_split[0].strip() if len(payment_dates_split) > 0 else None
                second_half_payment_date = payment_dates_split[1].strip() if len(payment_dates_split) > 1 else None
                
                first_half_paid_amount = paid_amounts_split[0].strip() if len(paid_amounts_split) > 0 else None
                second_half_paid_amount = paid_amounts_split[1].strip() if len(paid_amounts_split) > 1 else None
                
                # Clean up paid amounts (remove $ and commas)
                if first_half_paid_amount and first_half_paid_amount.startswith("$"):
                    first_half_paid_amount = first_half_paid_amount[1:].replace(",", "")
                if second_half_paid_amount and second_half_paid_amount.startswith("$"):
                    second_half_paid_amount = second_half_paid_amount[1:].replace(",", "")
                
                # Debug output to see what we're getting
                logger.debug(f"(Tyler Technologies Tax) Year {tax_year}: Payment dates raw: '{payment_dates_text}' -> Split: {payment_dates_split}")
                logger.debug(f"(Tyler Technologies Tax) Year {tax_year}: Paid amounts raw: '{paid_amounts_text}' -> Split: {paid_amounts_split}")
                
                tax_record = {
                    "year": tax_year,
                    "statement_number": statement_num,
                    "bill_date": bill_date,
                    "bill_amount": bill_amount_clean,
                    "first_half_payment_date": first_half_payment_date,
                    "first_half_paid_amount": first_half_paid_amount,
                    "second_half_payment_date": second_half_payment_date,
                    "second_half_paid_amount": second_half_paid_amount,
                    "source": f"tyler_technologies_history_{county}"
                }
                
                historical_data["historical_taxes"].append(tax_record)
                
                if tax_year not in historical_data["years"]:
                    historical_data["years"].append(tax_year)
                    logger.debug(f"(Tyler Technologies Tax) Found historical year: {tax_year} - ${bill_amount}")
        
        logger.debug(f"(Tyler Technologies Tax) Extracted {len(historical_data['historical_taxes'])} historical records")
        return historical_data
        
    except Exception as e:
        logger.error(f"(Tyler Technologies Tax) Historical extraction error: {e}")
        return {"error": f"Historical data extraction failed: {str(e)}"}

def create_standardized_tax_data(current_data: Dict, historical_data: Dict, county: str) -> Dict:
    """Create a standardized tax data format."""
    try:
        # Clean up current data values
        assessed_value = current_data.get("assessed_value", "")
        if assessed_value and assessed_value.startswith("$"):
            assessed_value = assessed_value[1:].replace(",", "")
        
        tax_amount = current_data.get("tax_amount", "")
        if tax_amount and tax_amount.startswith("$"):
            tax_amount = tax_amount[1:].replace(",", "")
        
        taxable_value = current_data.get("taxable_value", "")
        if taxable_value and taxable_value.startswith("$"):
            taxable_value = taxable_value[1:].replace(",", "")
        
        net_taxable = current_data.get("net_taxable", "")
        if net_taxable and net_taxable.startswith("$"):
            net_taxable = net_taxable[1:].replace(",", "")
        
        # Clean up first half and second half amounts
        first_half = current_data.get("first_half", "")
        if first_half and first_half.startswith("$"):
            first_half = first_half[1:].replace(",", "")
        
        second_half = current_data.get("second_half", "")
        if second_half and second_half.startswith("$"):
            second_half = second_half[1:].replace(",", "")
        
        # Clean up payment amounts
        first_half_payment = current_data.get("first_half_payment", "")
        if first_half_payment and first_half_payment.startswith("$"):
            first_half_payment = first_half_payment[1:].replace(",", "")
        
        second_half_payment = current_data.get("second_half_payment", "")
        if second_half_payment and second_half_payment.startswith("$"):
            second_half_payment = second_half_payment[1:].replace(",", "")
        
        total_payment = current_data.get("total_payment", "")
        if total_payment and total_payment.startswith("$"):
            total_payment = total_payment[1:].replace(",", "")
        
        # Create standardized format
        standardized = {
            "county": county.replace("_", " ").title(),
            "tax_year": current_data.get("tax_year"),
            "tax_id": current_data.get("tax_id"),
            "levy_district": current_data.get("levy_district"),
            "assessed_value": float(assessed_value) if assessed_value and assessed_value.replace(".", "").isdigit() else None,
            "taxable_value": float(taxable_value) if taxable_value and taxable_value.replace(".", "").isdigit() else None,
            "net_taxable": float(net_taxable) if net_taxable and net_taxable.replace(".", "").isdigit() else None,
            "tax_amount": float(tax_amount) if tax_amount and tax_amount.replace(".", "").isdigit() else None,
            "first_half": float(first_half) if first_half and first_half.replace(".", "").isdigit() else None,
            "second_half": float(second_half) if second_half and second_half.replace(".", "").isdigit() else None,
            "first_half_payment": float(first_half_payment) if first_half_payment and first_half_payment.replace(".", "").isdigit() else None,
            "second_half_payment": float(second_half_payment) if second_half_payment and second_half_payment.replace(".", "").isdigit() else None,
            "total_payment": float(total_payment) if total_payment and total_payment.replace(".", "").isdigit() else None,
            "first_half_due_date": current_data.get("first_half_due_date"),
            "second_half_due_date": current_data.get("second_half_due_date"),
            "due_date": current_data.get("due_date"),
            "status": "Current",
            "historical_years": sorted(historical_data.get("years", []), reverse=True),
            "historical_taxes": historical_data.get("historical_taxes", []),
            "source": f"tyler_technologies_tax_{county}",
            "scraped": True
        }
        
        logger.debug(f"(Tyler Technologies Tax) Standardized data created successfully")
        
        return standardized
        
    except Exception as e:
        logger.error(f"(Tyler Technologies Tax) Standardization error: {e}")
        return {
            "error": f"Data standardization failed: {str(e)}",
            "source": f"tyler_technologies_tax_{county}"
        }
