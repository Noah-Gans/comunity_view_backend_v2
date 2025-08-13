import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add the PMTiles_Cycle directory to Python path for imports
pmtiles_cycle_dir = Path(__file__).parent
sys.path.insert(0, str(pmtiles_cycle_dir))

from downloading_and_geojson_processing.data_merger import DataMerger
from downloading_and_geojson_processing.data_standardizer import DataStandardizer
from downloading_and_geojson_processing.cloud_gcs_uploader import upload_geojson_to_gcs

# Utility function to clear a directory
def clear_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

class CountyFactory:
    """Factory to create the right county class"""
    
    @staticmethod
    def create_county(county_name, output_dir="geojson_files"):
        # Import here to avoid circular imports
        from counties.counties import TetonCountyWy, LincolnCountyWy, SubletteCountyWy, TetonCountyId, FremontCountyWy
        
        county_classes = {
            "teton_county_wy": TetonCountyWy,
            "lincoln_county_wy": LincolnCountyWy,
            "sublette_county_wy": SubletteCountyWy,
            "teton_county_id": TetonCountyId,
            "fremont_county_wy": FremontCountyWy,
        }
        
        if county_name not in county_classes:
            raise ValueError(f"Unknown county: {county_name}")
            
        # Ensure output directory is relative to PMTiles_Cycle
        pmtiles_cycle_dir = Path(__file__).parent
        full_output_dir = pmtiles_cycle_dir / f"{county_name}_data_files"
        return county_classes[county_name](county_name, str(full_output_dir))

class OwnershipPipeline:
    """Orchestrates the ownership data pipeline with PMTiles generation"""
    
    def __init__(self, output_dir="Processed_Geojsons"):
        # Ensure paths are relative to PMTiles_Cycle directory
        self.pmtiles_cycle_dir = Path(__file__).parent
        self.output_dir = self.pmtiles_cycle_dir / output_dir
        
        # Create DataMerger and DataStandardizer with correct paths
        self.merger = DataMerger(str(self.output_dir))
        config_path = self.pmtiles_cycle_dir / "download_and_file_config.json"
        self.standardizer = DataStandardizer(str(self.output_dir), str(config_path))
        os.makedirs(self.output_dir, exist_ok=True)
    
    def process_county(self, county_name, upload_to_gcs=True, skip_gcs_upload=False):
        """Process a single county through the pipeline"""
        print(f"🏁 Starting pipeline for {county_name}")
        
        # Clear relevant directories before processing
        county_data_dir = self.pmtiles_cycle_dir / f"{county_name}_data_files"
        db_upload_dir = self.pmtiles_cycle_dir / "geojsons_for_db_upload" / f"{county_name}_data_files"
        clear_directory(str(county_data_dir))
        clear_directory(str(db_upload_dir))
        
        # Create county instance
        county = CountyFactory.create_county(county_name, self.output_dir)
        
        # Run county-specific processing
        standardized_data = county.collect_and_organize_county_ownership_data()
        
        # Upload to GCS
        if upload_to_gcs and not skip_gcs_upload:
            local_geojson_path = self.pmtiles_cycle_dir / "geojsons_for_db_upload" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
            if local_geojson_path.exists():
                upload_geojson_to_gcs(str(local_geojson_path), county_name)
            else:
                print(f"❌ GeoJSON file not found for upload: {local_geojson_path}")
        elif skip_gcs_upload:
            print(f"⏭️ Skipping GCS upload for {county_name}")
        
        return standardized_data
    
    def combine_county_geojsons(self, county_list=None):
        """Combine multiple county GeoJSON files into a single ownership layer"""
        print("🔄 Combining county GeoJSON files into single ownership layer...")
        
        # If no county list provided, use all available counties
        if county_list is None:
            county_list = self.get_available_counties()
        
        # Collect all GeoJSON files
        geojson_files = []
        total_features = 0
        combined_features = []
        
        for county_name in county_list:
            geojson_path = self.pmtiles_cycle_dir / "geojsons_for_db_upload" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
            if geojson_path.exists():
                print(f"📥 Loading {county_name} data...")
                with open(geojson_path, 'r') as f:
                    county_data = json.load(f)
                    feature_count = len(county_data.get('features', []))
                    total_features += feature_count
                    combined_features.extend(county_data.get('features', []))
                print(f"✅ Loaded {county_name}: {feature_count:,} features")
            else:
                print(f"⚠️ No GeoJSON found for {county_name}")
        
        if not combined_features:
            print("❌ No features found to combine")
            return None
        
        # Create combined GeoJSON
        combined_geojson = {
            "type": "FeatureCollection",
            "features": combined_features
        }
        
        # Save combined file to tiles directory (same as main.py)
        tiles_dir = Path.home() / "tiles"
        tiles_dir.mkdir(parents=True, exist_ok=True)
        combined_file = tiles_dir / "combined_ownership.geojson"
        with open(combined_file, 'w') as f:
            json.dump(combined_geojson, f)
        
        print(f"✅ Combined {len(county_list)} counties: {total_features:,} total features")
        print(f"📁 Combined file saved to: {combined_file}")
        
        return str(combined_file)
    
    def generate_pmtiles(self, county_list=None):
        """Generate PMTiles from processed GeoJSON files with three-stage detail optimization"""
        print("🔄 Generating PMTiles from GeoJSON files with three-stage detail optimization...")
        
        # If no county list provided, use all available counties
        if county_list is None:
            county_list = self.get_available_counties()
        
        # First combine all counties into a single GeoJSON
        combined_file = self.combine_county_geojsons(county_list)
        print(f"Combined file: {combined_file}")
        if not combined_file:
            print("❌ Failed to combine county data")
            return None
        
        # Create tiles directory for Martin to serve from
        tiles_dir = Path.home() / "tiles"
        tiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Tiles will be output to: {tiles_dir}")
        
        # Stage 1: Generate tiles for zoom levels 6-12 with moderate simplification
        print("📊 Stage 1: Generating low zoom tiles (6-12) with moderate simplification...")
        tile_output_low = tiles_dir / "tiles_low.mbtiles"
        subprocess.run([
            'tippecanoe',
            '-o', str(tile_output_low),
            '--maximum-zoom', '12',
            '--minimum-zoom', '6',  # ← Your original min zoom
            '--simplify-only-low-zooms',  # Apply simplifications only to lower zooms
            '--coalesce-smallest-as-needed',  # Coalesce smaller features to reduce detail but retain structure
            '--simplification=5',  # ← Your original simplification value
            '--no-tile-size-limit',  # Allow larger tiles
            '--force',
            str(combined_file)
        ], check=True)
        print(f"✅ Lower zoom levels processed (6-12): {tile_output_low}")

        # Stage 2: Generate tiles for zoom levels 13-16 with less simplification
        print("📊 Stage 2: Generating mid zoom tiles (13-16) with less simplification...")
        tile_output_mid = tiles_dir / "tiles_mid.mbtiles"
        subprocess.run([
            'tippecanoe',
            '-o', str(tile_output_mid),
            '--minimum-zoom', '13',
            '--maximum-zoom', '16',
            '--coalesce-smallest-as-needed',  # Coalesce for more compact but detailed representation
            '--no-tile-size-limit',  # Allow larger tiles for high zooms
            '--force',
            str(combined_file)
        ], check=True)
        print(f"✅ Mid zoom levels processed (13-16): {tile_output_mid}")

        # Stage 3: Generate tiles for zoom level 17 with no simplification
        print("📊 Stage 3: Generating high zoom tiles (17) with no simplification...")
        tile_output_high = tiles_dir / "tiles_high.mbtiles"
        subprocess.run([
            'tippecanoe',
            '-o', str(tile_output_high),
            '--minimum-zoom', '17',
            '--maximum-zoom', '17',
            '--no-tile-size-limit',
            '--force',
            str(combined_file)
        ], check=True)
        print(f"✅ High zoom level processed (17): {tile_output_high}")

        # Stage 4: Merge the tilesets into a single MBTiles file
        print("🔄 Stage 4: Merging tilesets into single MBTiles...")
        mbtiles_file = tiles_dir / "combined_ownership.mbtiles"
        
        # Remove old file if it exists
        if mbtiles_file.exists():
            mbtiles_file.unlink()
            print("🗑️ Removed old MBTiles file")
        
        subprocess.run([
            'tile-join',
            '--force',
            '--no-tile-size-limit',  # Ensure merged tiles have no size limits
            '-o', str(mbtiles_file),
            str(tile_output_low),
            str(tile_output_mid),
            str(tile_output_high)
        ], check=True)
        print("✅ Tilesets merged successfully!")
        
        # Clean up intermediate MBTiles files
        tile_output_low.unlink()
        tile_output_mid.unlink()
        tile_output_high.unlink()
        print("🗑️ Cleaned up intermediate MBTiles files")
        
        # Convert MBTiles to PMTiles using Python library
        print("🔄 Converting MBTiles to PMTiles...")
        pmtiles_file = tiles_dir / "combined_ownership.pmtiles"
        
        try:
            from pmtiles import convert
            print(f"Converting {mbtiles_file} to {pmtiles_file}")
            convert.mbtiles_to_pmtiles(str(mbtiles_file), str(pmtiles_file), maxzoom=17)  # ← Updated to 17
            
            # Verify the file was created and has content
            if pmtiles_file.exists() and pmtiles_file.stat().st_size > 0:
                print("✅ PMTiles conversion completed!")
                print(f"PMTiles file size: {pmtiles_file.stat().st_size} bytes")
                
                # Clean up MBTiles file
                if mbtiles_file.exists():
                    mbtiles_file.unlink()
                    print("🗑️ Cleaned up MBTiles file")
                
                print(f"📊 Combined {len(county_list)} counties into single ownership layer")
                
                return str(pmtiles_file)
            else:
                print("❌ PMTiles file is empty or missing!")
                return None
                
        except Exception as e:
            print(f"❌ Error converting MBTiles to PMTiles: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_only(self, county_list):
        """Upload finalized geojsons for each county to GCS without processing."""
        for county_name in county_list:
            local_geojson_path = self.pmtiles_cycle_dir / "geojsons_for_db_upload" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
            if local_geojson_path.exists():
                print(f"Uploading {local_geojson_path} to GCS...")
                upload_geojson_to_gcs(str(local_geojson_path), county_name)
            else:
                print(f"❌ GeoJSON file not found for upload: {local_geojson_path}")

    def process_all_counties(self, county_list, upload_to_gcs=True, skip_gcs_upload=False, generate_pmtiles=True):
        """Process multiple counties and optionally generate PMTiles"""
        print(f"🏁 Starting pipeline for {len(county_list)} counties: {', '.join(county_list)}")

        for county_name in county_list:
            print(f"\n{'='*50}")
            print(f"Processing {county_name}...")
            print(f"{'='*50}")
            try:
                self.process_county(county_name, upload_to_gcs=upload_to_gcs, skip_gcs_upload=skip_gcs_upload)
                print(f"✅ Successfully processed {county_name}")
            except Exception as e:
                print(f"❌ Failed to process {county_name}: {e}")
                continue

        print(f"\n🎉 Pipeline completed for all counties!")
        
        # Generate PMTiles if requested
        if generate_pmtiles:
            print("\n🔄 Generating PMTiles from processed data...")
            pmtiles_file = self.generate_pmtiles(county_list)
            if pmtiles_file:
                print(f"✅ PMTiles generation completed: {pmtiles_file}")
            else:
                print("❌ PMTiles generation failed")
    
    def get_available_counties(self):
        """Get list of available counties"""
        return ["teton_county_wy", "lincoln_county_wy", "sublette_county_wy", "teton_county_id", "fremont_county_wy"]
    
    def validate_county(self, county_name):
        """Validate that a county is supported"""
        available_counties = self.get_available_counties()
        if county_name not in available_counties:
            raise ValueError(f"County '{county_name}' not supported. Available counties: {', '.join(available_counties)}")
        return True

def main():
    """Main function to run the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process county ownership data and generate PMTiles")
    parser.add_argument("--county", type=str, help="Single county to process")
    parser.add_argument("--all", action="store_true", help="Process all available counties")
    parser.add_argument("--output-dir", type=str, default="Processed_Geojsons", help="Output directory")
    parser.add_argument("--upload-only", action="store_true", help="Skip processing and only upload finalized geojsons to GCS")
    parser.add_argument("--pmtiles-only", action="store_true", help="Skip processing and only generate PMTiles from existing GeoJSON files")
    parser.add_argument("--skip-gcs-upload", action="store_true", help="Skip uploading to GCS bucket")
    parser.add_argument("--skip-pmtiles", action="store_true", help="Skip PMTiles generation")
    
    args = parser.parse_args()
    
    pipeline = OwnershipPipeline(
        output_dir=args.output_dir,
    )

    # Determine which counties to operate on
    if args.all:
        county_list = pipeline.get_available_counties()
    elif args.county:
        pipeline.validate_county(args.county)
        county_list = [args.county]
    else:
        print("Please specify either --county <county_name> or --all")
        print(f"Available counties: {', '.join(pipeline.get_available_counties())}")
        return

    # PMTiles only mode: skip processing, just generate PMTiles
    if args.pmtiles_only:
        print("Generating PMTiles from existing GeoJSON files...")
        pmtiles_file = pipeline.generate_pmtiles(county_list)
        if pmtiles_file:
            print(f"✅ PMTiles generation completed: {pmtiles_file}")
        else:
            print("❌ PMTiles generation failed")
        return

    # Upload only mode: skip processing, just upload geojsons to GCS
    if args.upload_only:
        if not args.skip_gcs_upload:
            pipeline.upload_only(county_list)
        else:
            print("⏭️ Skipping GCS upload due to --skip-gcs-upload flag")
        return

    # Normal processing mode
    pipeline.process_all_counties(
        county_list, 
        upload_to_gcs=True, 
        skip_gcs_upload=args.skip_gcs_upload,
        generate_pmtiles=not args.skip_pmtiles
    )

if __name__ == "__main__":
    main()
