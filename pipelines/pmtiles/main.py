"""
Enhanced PMTiles pipeline entry point with ownership pipeline integration
"""

import os
import sys
import subprocess
import tempfile
import argparse
from pathlib import Path
from google.cloud import storage

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Download a file from GCS"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(f"✅ Downloaded {source_blob_name} to {destination_file_name}")

def run_legacy_pipeline():
    """Run the original main.py pipeline (single county from GCS)"""
    print("🔄 Running legacy single-county pipeline...")
    
    try:
        # GCS paths
        bucket_name = "teton-county-gis-bucket"
        geojson_path = "geojsons/teton_county_wy/ownership_data_20250807.geojson"
        
        # Create tiles directory in backend root
        backend_root = Path(__file__).parent.parent
        tiles_dir = backend_root / "tiles"
        tiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Tiles will be output to: {tiles_dir}")
        
        # Download GeoJSON from GCS
        print("📥 Downloading test GeoJSON from GCS...")
        geojson_file = tiles_dir / "teton_county_wy_ownership.geojson"
        download_from_gcs(bucket_name, geojson_path, str(geojson_file))
        
        # Generate MBTiles v2 using tippecanoe with improved settings
        print(" Generating MBTiles v2 using tippecanoe...")
        mbtiles_file = tiles_dir / "teton_county_wy_ownership.mbtiles"
        
        # Remove old file if it exists
        if mbtiles_file.exists():
            mbtiles_file.unlink()
            print("🗑️ Removed old MBTiles file")
        
        cmd = [
            "tippecanoe",
            "-o", str(mbtiles_file),
            "-l", "teton_county_wy_ownership",  # Layer name
            "-n", "teton_county_wy_ownership",  # Source name
            "-Z", "7",                           # Minimum zoom (higher for better coverage)
            "-z", "15",                          # Maximum zoom (higher for detail)
            "--drop-densest-as-needed",
            "--extend-zooms-if-still-dropping",
            "--coalesce",
            "--coalesce-densest-as-needed",
            "--detect-shared-borders",
            "--force",                           # Force overwrite
            str(geojson_file)
        ]
        
        subprocess.run(cmd, check=True, timeout=7200)
        print("✅ MBTiles v2 generated successfully!")
        
        # Convert MBTiles to PMTiles using Python library
        print(" Converting MBTiles to PMTiles...")
        pmtiles_file = tiles_dir / "teton_county_wy_ownership.pmtiles"
        
        try:
            from pmtiles import convert
            print(f"Converting {mbtiles_file} to {pmtiles_file}")
            convert.mbtiles_to_pmtiles(str(mbtiles_file), str(pmtiles_file), maxzoom=15)
            
            # Verify the file was created and has content
            if pmtiles_file.exists() and pmtiles_file.stat().st_size > 0:
                print("✅ PMTiles conversion completed!")
                print(f"PMTiles file size: {pmtiles_file.stat().st_size} bytes")
                
                # Clean up MBTiles file
                if mbtiles_file.exists():
                    mbtiles_file.unlink()
                    print("🗑️ Cleaned up MBTiles file")
                
                return str(pmtiles_file)
            else:
                print("❌ PMTiles file is empty or missing!")
                return None
                
        except Exception as e:
            print(f"❌ Error converting MBTiles to PMTiles: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    except Exception as e:
        print(f"❌ Error in legacy pipeline: {e}")
        return None


def main():
    """Main function with enhanced pipeline options"""
    
    parser = argparse.ArgumentParser(description="PMTiles Ownership Pipeline")
    
    # County selection
    parser.add_argument("--county", type=str, help="Single county to process")
    parser.add_argument("--counties", nargs='+', help="Multiple counties to process")
    
    # Pipeline steps (boolean flags - combine as needed)
    parser.add_argument("--process", action="store_true", help="Download & process new data")
    parser.add_argument("--validate", action="store_true", help="Validate data (blocks upload/tiles if invalid)")
    parser.add_argument("--upload", action="store_true", help="Upload to GCS")
    parser.add_argument("--generate-tiles", action="store_true", help="Generate PMTiles")
    
    args = parser.parse_args()
    
    print("🚀 Starting Ownership Pipeline...")
    
    # Initialize pipeline
    from ownership_pipeline import OwnershipPipeline
    pipeline = OwnershipPipeline()
    
    # Get county list
    if args.counties:
        county_list = args.counties
    elif args.county:
        county_list = [args.county]
    else:
        # No counties specified - process all
        county_list = pipeline.get_available_counties()
    
    # Map flags directly to pipeline steps
    process_data = args.process
    validate = args.validate
    upload = args.upload
    generate_tiles = args.generate_tiles
    
    # If no flags specified, default to process
    if not any([process_data, validate, upload, generate_tiles]):
        print("⚠️ No steps specified, defaulting to --process")
        process_data = True
    
    # Run pipeline with selected steps
    try:
        validation_passed = pipeline.process_ownership(
            county_list=county_list,
            process_data=process_data,
            validate=validate,
            upload=upload,
            generate_tiles=generate_tiles
        )
        result = "Pipeline completed" if validation_passed else "Pipeline stopped - validation failed"
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        result = None
    
    # Check result
    if result:
        print(f"\n✅ Pipeline completed successfully!")
        print(f"📁 Final output: {result}")
        
        # Show final directory contents
        backend_root = Path(__file__).parent.parent
        tiles_dir = backend_root / "tiles"
        if tiles_dir.exists():
            print(f"\n📁 Final output in tiles directory:")
            for file in tiles_dir.glob("*"):
                if file.is_file():
                    size_mb = file.stat().st_size / (1024 * 1024)
                    print(f"  {file.name}: {size_mb:.1f} MB")
    else:
        print("\n❌ Pipeline failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 