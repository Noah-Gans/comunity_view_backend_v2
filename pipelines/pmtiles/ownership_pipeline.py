import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add the pmtiles directory to Python path for imports
pmtiles_cycle_dir = Path(__file__).parent
sys.path.insert(0, str(pmtiles_cycle_dir))

from downloading_and_geojson_processing.data_merger import DataMerger
from downloading_and_geojson_processing.data_standardizer import DataStandardizer
from downloading_and_geojson_processing.cloud_gcs_uploader import upload_geojson_to_gcs

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
            
        # Use the passed output_dir (should be intermediate_data/)
        # and create county-specific subdirectory
        base_output_dir = Path(output_dir)
        full_output_dir = base_output_dir / f"{county_name}_data_files"
        return county_classes[county_name](county_name, str(full_output_dir))

class OwnershipPipeline:
    """Orchestrates the ownership data pipeline with PMTiles generation"""
    
    def __init__(self, output_dir="intermediate_data"):
        # Ensure paths are relative to pmtiles pipeline directory
        self.pmtiles_cycle_dir = Path(__file__).parent
        self.output_dir = self.pmtiles_cycle_dir / output_dir
        
        # Create DataMerger and DataStandardizer with correct paths
        self.merger = DataMerger(str(self.output_dir))
        config_path = self.pmtiles_cycle_dir / "download_and_file_config.json"
        self.standardizer = DataStandardizer(str(self.output_dir), str(config_path))
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _archive_final_parcels(self):
        """Archive entire final_parcels directory to final_parcels_previous (overwrites old archive)"""
        final_parcels = self.pmtiles_cycle_dir / "final_parcels"
        archive_path = self.pmtiles_cycle_dir / "final_parcels_previous"
        
        if not final_parcels.exists():
            print("📭 No final_parcels to archive (first run)")
            return None
        
        # Remove old archive if it exists
        if archive_path.exists():
            print(f"🗑️ Removing old archive: {archive_path}")
            shutil.rmtree(archive_path)
        
        # Create new archive
        print(f"📦 Archiving final_parcels → final_parcels_previous")
        shutil.copytree(final_parcels, archive_path)
        print(f"✅ Previous cycle archived to: final_parcels_previous/")
        print(f"   You can compare new results with this folder")
        
        return str(archive_path)
    
    def _clear_directory(self, directory):
        """Clear all contents of a directory"""
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
    
    def _count_features_in_geojson(self, geojson_path):
        """Count features in a GeoJSON file"""
        try:
            import json
            with open(geojson_path, 'r') as f:
                data = json.load(f)
                return len(data.get('features', []))
        except Exception as e:
            print(f"⚠️ Could not count features in {geojson_path}: {e}")
            return 0
    
    def validate_and_report(self):
        """
        Compare final_parcels vs final_parcels_previous and generate validation report
        Writes report to validation_report.txt for email integration
        
        Returns:
            bool: True if data is valid, False if invalid/suspicious
        """
        report_path = self.pmtiles_cycle_dir / "validation_report.txt"
        
        # Clear previous report
        if report_path.exists():
            report_path.unlink()
        
        final_dir = self.pmtiles_cycle_dir / "final_parcels"
        previous_dir = self.pmtiles_cycle_dir / "final_parcels_previous"
        
        # Check if directories exist
        if not final_dir.exists():
            report = "❌ ERROR: No final_parcels directory found!\n"
            report_path.write_text(report)
            return False
        
        if not previous_dir.exists():
            # First run - no previous data to compare against
            from datetime import datetime
            report = []
            report.append("=" * 70)
            report.append("OWNERSHIP DATA VALIDATION REPORT")
            report.append("=" * 70)
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            report.append("⚠️ FIRST RUN - No previous data for comparison")
            report.append("=" * 70)
            report.append("")
            report.append("📊 CURRENT DATA SUMMARY")
            report.append("-" * 70)
            
            current_data = self._scan_directory_data(final_dir)
            total_features = 0
            
            for county, data in sorted(current_data.items()):
                total_features += data['features']
                report.append(f"\n{county}:")
                report.append(f"   Features: {data['features']:,}")
                report.append(f"   Size: {data['size_mb']:.1f} MB")
            
            report.append("")
            report.append("=" * 70)
            report.append("TOTALS")
            report.append("-" * 70)
            report.append(f"Total Counties: {len(current_data)}")
            report.append(f"Total Features: {total_features:,}")
            
            report.append("")
            report.append("=" * 70)
            report.append("RECOMMENDATION")
            report.append("-" * 70)
            report.append("✅ PASSED: First run - auto-approved")
            report.append("   → This data will become the baseline for future comparisons")
            report.append("=" * 70)
            
            report_text = "\n".join(report)
            report_path.write_text(report_text)
            
            # First run: auto-pass (no baseline to compare against)
            return True
        
        # Scan both directories
        current_data = self._scan_directory_data(final_dir)
        previous_data = self._scan_directory_data(previous_dir)
        
        # Build report
        from datetime import datetime
        report = []
        report.append("=" * 70)
        report.append("OWNERSHIP DATA VALIDATION REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 70)
        report.append(f"Current Counties: {len(current_data)}")
        report.append(f"Previous Counties: {len(previous_data)}")
        
        current_counties = set(current_data.keys())
        previous_counties = set(previous_data.keys())
        new_counties = current_counties - previous_counties
        removed_counties = previous_counties - current_counties
        common_counties = current_counties & previous_counties
        
        if new_counties:
            report.append(f"✨ New Counties: {', '.join(new_counties)}")
        if removed_counties:
            report.append(f"⚠️ Removed Counties: {', '.join(removed_counties)}")
        report.append("")
        
        # Detailed comparison
        report.append("📋 DETAILED COMPARISON")
        report.append("-" * 70)
        
        total_current_features = 0
        total_previous_features = 0
        
        for county in sorted(common_counties):
            curr = current_data[county]
            prev = previous_data[county]
            
            size_change = curr['size_mb'] - prev['size_mb']
            size_pct = (size_change / prev['size_mb'] * 100) if prev['size_mb'] > 0 else 0
            
            feature_change = curr['features'] - prev['features']
            feature_pct = (feature_change / prev['features'] * 100) if prev['features'] > 0 else 0
            
            total_current_features += curr['features']
            total_previous_features += prev['features']
            
            status = "✅" if abs(feature_pct) < 5 else "⚠️"  # Flag if >=5% change
            
            report.append(f"\n{status} {county}")
            report.append(f"   Features: {prev['features']:,} → {curr['features']:,} ({feature_change:+,}, {feature_pct:+.1f}%)")
            report.append(f"   Size: {prev['size_mb']:.1f} MB → {curr['size_mb']:.1f} MB ({size_change:+.1f} MB, {size_pct:+.1f}%)")
        
        # New counties detail
        for county in sorted(new_counties):
            curr = current_data[county]
            total_current_features += curr['features']
            report.append(f"\n✨ {county} (NEW)")
            report.append(f"   Features: {curr['features']:,}")
            report.append(f"   Size: {curr['size_mb']:.1f} MB")
        
        # Summary stats
        report.append("")
        report.append("=" * 70)
        report.append("TOTALS")
        report.append("-" * 70)
        report.append(f"Total Features: {total_previous_features:,} → {total_current_features:,}")
        total_change = total_current_features - total_previous_features
        total_pct = (total_change / total_previous_features * 100) if total_previous_features > 0 else 0
        report.append(f"Change: {total_change:+,} features ({total_pct:+.1f}%)")
        
        # Recommendation
        report.append("")
        report.append("=" * 70)
        report.append("RECOMMENDATION")
        report.append("-" * 70)
        
        # Determine validity
        is_valid = True
        
        if abs(total_pct) >= 5:
            report.append("❌ FAILED: Total feature count changed by 5% or more")
            report.append("   → Manual review required before proceeding")
            is_valid = False
        elif any(abs((current_data[c]['features'] - previous_data[c]['features']) / previous_data[c]['features'] * 100) >= 5 
                 for c in common_counties if previous_data[c]['features'] > 0):
            report.append("⚠️ WARNING: One or more counties changed by ≥5%")
            report.append("   → Recommend manual review before proceeding")
            is_valid = False
        else:
            report.append("✅ PASSED: Changes are within expected range (<5%)")
            report.append("   → Safe to proceed with upload and tile generation")
        
        report.append("=" * 70)
        
        # Write to file
        report_text = "\n".join(report)
        report_path.write_text(report_text)
        
        return is_valid
    
    def _scan_directory_data(self, directory):
        """Scan directory and return data dict for each county"""
        data = {}
        
        if not directory.exists():
            return data
        
        for county_dir in directory.iterdir():
            if not county_dir.is_dir():
                continue
            
            county_name = county_dir.name.replace("_data_files", "")
            
            # Find the final ownership GeoJSON
            geojson_path = county_dir / f"{county_name}_final_ownership.geojson"
            
            if geojson_path.exists():
                size_mb = geojson_path.stat().st_size / (1024 * 1024)
                features = self._count_features_in_geojson(geojson_path)
                
                data[county_name] = {
                    'size_mb': size_mb,
                    'features': features,
                    'path': str(geojson_path)
                }
        
        return data
    
    def _rollback_to_previous(self):
        """Rollback: delete bad final_parcels and restore from previous"""
        final_dir = self.pmtiles_cycle_dir / "final_parcels"
        previous_dir = self.pmtiles_cycle_dir / "final_parcels_previous"
        
        if not previous_dir.exists():
            print("⚠️ No previous data to rollback to!")
            return False
        
        print("🔄 Rolling back bad data...")
        
        # Delete bad final_parcels
        if final_dir.exists():
            shutil.rmtree(final_dir)
            print("   ✅ Deleted bad final_parcels/")
        
        # Restore from previous
        shutil.copytree(previous_dir, final_dir)
        print("   ✅ Restored from final_parcels_previous/")
        print("✅ Rollback complete - previous good data is now current")
        
        return True
    
    def process_county(self, county_name):
        """Process a single county through the pipeline - DOES NOT UPLOAD"""
        print(f"🏁 Starting pipeline for {county_name}")
        
        # Note: Archiving and clearing is done once for ALL counties at the start
        # by process_all_counties(), not per-county
        
        # Clear this county's working directories
        county_data_dir = self.pmtiles_cycle_dir / "intermediate_data" / f"{county_name}_data_files"
        final_data_dir = self.pmtiles_cycle_dir / "final_parcels" / f"{county_name}_data_files"
        self._clear_directory(str(county_data_dir))
        self._clear_directory(str(final_data_dir))
        
        # Create county instance
        county = CountyFactory.create_county(county_name, self.output_dir)
        
        # Run county-specific processing
        standardized_data = county.collect_and_organize_county_ownership_data()
        
        print(f"✅ Generated new final data for {county_name}")
        
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
            geojson_path = self.pmtiles_cycle_dir / "final_parcels" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
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
        
        # Save combined file to tiles directory in backend root
        backend_root = self.pmtiles_cycle_dir.parent.parent  # Go up to backend root
        tiles_dir = backend_root / "tiles"
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
        
        # Create tiles directory in backend root
        backend_root = self.pmtiles_cycle_dir.parent.parent  # Go up to backend root
        tiles_dir = backend_root / "tiles"
        tiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Tiles will be output to: {tiles_dir}")
        
        # Stage 1: Generate tiles for zoom levels 6-12 with moderate simplification
        print("📊 Stage 1: Generating low zoom tiles (6-12) with moderate simplification...")
        tile_output_low = tiles_dir / "tiles_low.mbtiles"
        subprocess.run([
            'tippecanoe',
            '-o', str(tile_output_low),
            '--maximum-zoom', '11',
            '--minimum-zoom', '6',  # ← Your original min zoom
            '--simplification=2',
            '--detect-shared-borders',
            '--maximum-tile-bytes', '300000',
            '--coalesce', '--coalesce-densest-as-needed',
            '--drop-densest-as-needed', '--drop-fraction-as-needed',
            '--extend-zooms-if-still-dropping',  # Allow larger tiles
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
            '--minimum-zoom', '12',
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
            local_geojson_path = self.pmtiles_cycle_dir / "final_parcels" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
            if local_geojson_path.exists():
                print(f"Uploading {local_geojson_path} to GCS...")
                upload_geojson_to_gcs(str(local_geojson_path), county_name)
            else:
                print(f"❌ GeoJSON file not found for upload: {local_geojson_path}")
    
    def get_available_counties(self):
        """Get list of available counties"""
        return ["teton_county_wy", "lincoln_county_wy", "sublette_county_wy", "teton_county_id", "fremont_county_wy"]
    
    def validate_county(self, county_name):
        """Validate that a county is supported"""
        available_counties = self.get_available_counties()
        if county_name not in available_counties:
            raise ValueError(f"County '{county_name}' not supported. Available counties: {', '.join(available_counties)}")
        return True

    def process_ownership(self, county_list, 
                         process_data=False,
                         validate=False,
                         upload=False,
                         generate_tiles=False):
        """
        Main orchestrator for the ownership pipeline
        
        Args:
            county_list: List of counties to process
            process_data: Download & process new data (archive, clear, generate GeoJSONs)
            validate: Validate data and block upload/tiles if invalid
            upload: Upload validated GeoJSONs to GCS
            generate_tiles: Generate PMTiles from validated GeoJSONs
        """
        print(f"\n🏁 Ownership Pipeline: {', '.join(county_list)}")
        steps = []
        if process_data: steps.append("Process")
        if validate: steps.append("Validate")
        if upload: steps.append("Upload")
        if generate_tiles: steps.append("Tiles")
        print(f"📋 Steps: {' → '.join(steps)}\n")
        
        validation_passed = True  # Track validation state
        
        # STEP: Process Data
        if process_data:
            print("📦 Archiving previous run...")
            self._archive_final_parcels()
            
            print("🗑️ Clearing working directories...")
            intermediate_dir = self.pmtiles_cycle_dir / "intermediate_data"
            final_dir = self.pmtiles_cycle_dir / "final_parcels"
            self._clear_directory(str(intermediate_dir))
            self._clear_directory(str(final_dir))
            
            print(f"🔄 Processing {len(county_list)} counties...\n")
            for county_name in county_list:
                try:
                    print(f"   • {county_name}...", end=" ")
                    self.process_county(county_name)
                    print("✅")
                except Exception as e:
                    print(f"❌ {e}")
                    continue
            print("✅ Data processing complete!\n")
        
        # STEP: Validate (always runs if enabled, blocks upload/tiles if fails)
        if validate:
            print("🔍 Running validation...")
            validation_passed = self.validate_and_report()
            
            # Read and print report
            report_path = self.pmtiles_cycle_dir / "validation_report.txt"
            if report_path.exists():
                report = report_path.read_text()
                print(report)
            
            print(f"\n📄 Full report saved to: validation_report.txt")
            
            if validation_passed:
                print("✅ VALIDATION PASSED - Safe to proceed\n")
            else:
                print("❌ VALIDATION FAILED - Data quality issues detected!")
                if process_data:  # Only rollback if we just generated new data
                    print("🔄 Rollback triggered - restoring previous good data...\n")
                    self._rollback_to_previous()
                print("⚠️ Upload and tile generation BLOCKED\n")
        
        # STEP: Upload to GCS (only if validation passed or not run)
        if upload:
            if validate and not validation_passed:
                print("⏭️ Skipping upload - validation failed\n")
            else:
                print("☁️ Uploading to GCS...")
                self.upload_only(county_list)
                print("✅ Upload complete!\n")
        
        # STEP: Generate PMTiles (only if validation passed or not run)
        if generate_tiles:
            if validate and not validation_passed:
                print("⏭️ Skipping tile generation - validation failed\n")
            else:
                print("🗺️ Generating PMTiles...")
                pmtiles_file = self.generate_pmtiles(county_list)
                if pmtiles_file:
                    print(f"✅ Tiles generated: {pmtiles_file}\n")
                else:
                    print("❌ Tile generation failed\n")
        
        if validation_passed:
            print("✅ Pipeline complete!")
        else:
            print("⚠️ Pipeline stopped - validation failed")
        
        return validation_passed

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
