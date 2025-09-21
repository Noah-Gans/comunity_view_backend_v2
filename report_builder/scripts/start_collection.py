#!/usr/bin/env python3
"""
Start the mass property data collection process
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import ReportBuilderMain

async def main():
    """Run a test collection with limited parcels"""
    
    print("Starting Report Builder Mass Collection")
    print("=" * 50)
    
    # Initialize the main collector
    collector = ReportBuilderMain()
    
    # Run collection with limited parcels for testing
    await collector.run_collection(
        counties=["fremont_county_wy", "lincoln_county_wy", "sublette_county_wy"],
        max_parcels_per_county=10  # Start with 10 parcels per county for testing
    )

if __name__ == "__main__":
    asyncio.run(main())
