#!/usr/bin/env python3
"""
Debug script to test Lincoln County tax URLs and see what's happening
"""

import requests
from bs4 import BeautifulSoup
import sys
import os
import json
from datetime import datetime

# Add property_info_api to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'property_info_api'))


from county_config import construct_links

def test_lincoln_tax_url():
    """Test a Lincoln County tax URL to see what's happening"""
    
    print("🔍 DEBUGGING LINCOLN COUNTY TAX SCRAPING")
    print("=" * 50)
    
    # Sample data from your GeoJSON
    test_parcels = [
        {
            "property_details_key": "R0000018",
            "tax_details_key": "R0000018",
            "clerk_records_key": None
        },
        {
            "property_details_key": "R0000016", 
            "tax_details_key": "R0000016",
            "clerk_records_key": None
        }
    ]
    
    for i, test_parcel in enumerate(test_parcels):
        print(f"\n🏠 TESTING PARCEL {i+1}: {test_parcel['tax_details_key']}")
        print("-" * 30)
        
        # Build fields dict
        fields = {
            "tax_field": test_parcel["tax_details_key"],
            "property_details_field": test_parcel["property_details_key"],
            "clerk_field": test_parcel["clerk_records_key"]
        }
        
        # Get URLs
        links = construct_links("lincoln_county_wy", fields)
        tax_url = links.get("tax_field")
        
        print(f"📍 Tax URL: {tax_url}")
        
        if not tax_url:
            print("❌ No tax URL generated")
            continue
        
        # Test the URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            print("📡 Making request...")
            response = requests.get(tax_url, timeout=15, headers=headers)
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Successfully got response!")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Save full HTML for inspection
                filename = f"lincoln_tax_debug_{test_parcel['tax_details_key']}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"💾 Full HTML saved to: {filename}")
                
                # Check for key elements the scraper looks for
                print("\n🔍 CHECKING FOR EXPECTED HTML ELEMENTS:")
                
                # Check for tax year elements
                year_elements = soup.find_all('span', string=lambda text: text and ('2025' in text or '2024' in text) and ('Taxes:' in text or 'Payments:' in text))
                print(f"   📅 Tax year elements: {len(year_elements)}")
                if year_elements:
                    for elem in year_elements:
                        print(f"      Found: '{elem.get_text()}'")
                
                # Check for tax ID elements
                tax_id_elem = soup.find('span', id=lambda x: x and 'lblTaxID' in x)
                print(f"   🆔 Tax ID element: {'Found' if tax_id_elem else 'Not found'}")
                if tax_id_elem:
                    print(f"      ID: {tax_id_elem.get('id')}")
                    print(f"      Text: '{tax_id_elem.get_text()}'")
                
                # Check for tables
                tables = soup.find_all('table')
                print(f"   📊 Tables found: {len(tables)}")
                
                # Check for common tax-related elements
                tax_related_elements = soup.find_all(string=lambda text: text and any(word in text.lower() for word in ['tax', 'assessed', 'levy', 'payment']))
                print(f"   💰 Tax-related text elements: {len(tax_related_elements)}")
                if tax_related_elements:
                    print("      Sample tax-related text:")
                    for elem in tax_related_elements[:5]:  # Show first 5
                        print(f"         '{elem.strip()}'")
                
                # Show page title and meta info
                title = soup.find('title')
                print(f"\n📄 PAGE INFO:")
                print(f"   Title: {title.get_text() if title else 'No title'}")
                
                # Show first 1000 chars of HTML
                print(f"\n📄 HTML PREVIEW (first 1000 chars):")
                print(response.text[:1000])
                print("...")
                
            elif response.status_code == 403:
                print("❌ 403 FORBIDDEN - You're being blocked!")
                print(f"Response headers: {dict(response.headers)}")
                print(f"Response body: {response.text[:500]}")
                
            elif response.status_code == 404:
                print("❌ 404 NOT FOUND - URL might be wrong")
                print(f"Response: {response.text[:200]}")
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except requests.exceptions.ConnectionError:
            print("🔌 Connection error")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*50)

def test_with_actual_scraper():
    """Test using the actual scraper to see what it returns"""
    print("\n🔧 TESTING WITH ACTUAL SCRAPER")
    print("=" * 50)
    
    # Import the actual scraper
    try:
        from overrides.tax.tyler_technologies_tax import scrape_tax
        
        test_url = "https://itax.tylertech.com/LincolnWY/detail.aspx?taxid=R0000018"
        print(f"🧪 Testing scraper with URL: {test_url}")
        
        result = scrape_tax(test_url, county="lincoln_county_wy")
        
        print("📊 SCRAPER RESULT:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Scraper error: {e}")

if __name__ == "__main__":
    test_lincoln_tax_url()
    test_with_actual_scraper()
