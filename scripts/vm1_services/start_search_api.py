#!/usr/bin/env python3
"""
Simple startup script for the Property Search API
"""

import uvicorn
import sys
import os

# Navigate to project root and add to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Change to search_api directory
search_api_dir = os.path.join(project_root, 'services', 'search_api')
os.chdir(search_api_dir)

# Check if search index exists (warn but don't fail)
search_index = os.path.join(search_api_dir, "search_index.json")
if not os.path.exists(search_index):
    print(f"⚠️  Warning: search_index.json not found at {search_index}")
    print("   Search API will start but won't have search data until index is generated.")
    print("   Run the search index generation to create the index.")

if __name__ == "__main__":
    print("🚀 Starting Property Search API...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Use uvicorn to run the app module directly
    uvicorn.run("app:app", host="0.0.0.0", port=9001, app_dir=search_api_dir) 