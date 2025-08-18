import json
import os
from tqdm import tqdm
import geopandas as gpd

class DataStandardizer:
    """Standardizes ownership data to a common format across all counties"""
    
    def __init__(self, output_dir="geojson_files", config_path="download_and_file_config.json"):
        self.output_dir = output_dir
        # If config_path is relative, make it relative to the tile_cycle directory
        if not os.path.isabs(config_path):
            from pathlib import Path
            tile_cycle_dir = Path(__file__).parent.parent
            config_path = tile_cycle_dir / config_path
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_mappings(self, county_name):
        # Find the mappings for the county's ownership layer
        county_cfg = self.config.get(county_name, {})
        ownership_cfg = county_cfg.get("ownership", {})
        return ownership_cfg.get("standardization_mappings", {})
    
    def get_links_config(self, county_name):
        county_cfg = self.config.get(county_name, {})
        ownership_cfg = county_cfg.get("ownership", {})
        return ownership_cfg.get("standardized_links", {})
    
    def detect_coordinate_system(self, geojson_data):
        """
        Detect if a GeoJSON uses State Plane or WGS84 coordinates.
        Returns the detected CRS string.
        """
        if not geojson_data.get('features'):
            return 'EPSG:4326'  # Default to WGS84 if no features
        
        # Check if CRS is explicitly defined
        if 'crs' in geojson_data:
            crs_name = geojson_data['crs'].get('properties', {}).get('name', '')
            if '3738' in crs_name:
                return 'EPSG:3738'  # Wyoming State Plane NAD83 1927    
            elif 'EPSG:3739' in crs_name or 'EPSG:2677' in crs_name:
                return 'EPSG:3739'  # Wyoming State Plane NAD83
            elif 'EPSG:4326' in crs_name:
                return 'EPSG:4326'  # WGS84
        
        # Find first feature with valid geometry
        first_valid_feature = None
        for feature in geojson_data['features']:
            if (feature.get('geometry') and 
                feature['geometry'] is not None and 
                'coordinates' in feature['geometry'] and 
                feature['geometry']['coordinates']):
                first_valid_feature = feature
                break
        
        if not first_valid_feature:
            print("  ⚠️  No valid geometries found, defaulting to WGS84")
            return 'EPSG:4326'  # Default to WGS84 if no valid geometries
        
        # Check coordinates from first valid feature (handle both Polygon and MultiPolygon)
        geometry = first_valid_feature['geometry']
        coords = None
        
        if geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0][0]  # First point of first ring
        elif geometry['type'] == 'MultiPolygon':
            coords = geometry['coordinates'][0][0][0]  # First point of first ring of first polygon
        
        if not coords:
            print("  ⚠️  Could not extract coordinates, defaulting to WGS84")
            return 'EPSG:4326'
        
        x, y = coords[0], coords[1]  # Take only first two values (x, y)
        
        # Detect coordinate system
        if -180 <= x <= 180 and -90 <= y <= 90:
            return 'EPSG:4326'  # WGS84 lat/lng
        elif x > 1000000 or y > 1000000:
            return 'EPSG:3739'  # Wyoming State Plane
        
        return 'EPSG:4326'  # Default to WGS84
    
    def convert_to_2d_coordinates(self, geojson_data):
        """
        Convert all 3D coordinates to 2D by dropping the Z coordinate.
        """
        print("  🔄 Converting 3D coordinates to 2D...")
        
        for feature in geojson_data['features']:
            if (feature.get('geometry') and 
                feature['geometry'] is not None and 
                'coordinates' in feature['geometry']):
                
                geometry = feature['geometry']
                if geometry['type'] == 'Polygon':
                    # Convert each ring in the polygon
                    for ring in geometry['coordinates']:
                        for i, coord in enumerate(ring):
                            if len(coord) > 2:
                                ring[i] = [coord[0], coord[1]]  # Keep only x, y
                elif geometry['type'] == 'MultiPolygon':
                    # Convert each polygon in the multipolygon
                    for polygon in geometry['coordinates']:
                        for ring in polygon:
                            for i, coord in enumerate(ring):
                                if len(coord) > 2:
                                    ring[i] = [coord[0], coord[1]]  # Keep only x, y
        
        print("  ✅ 3D to 2D conversion complete")
        return geojson_data
    
    def transform_coordinates(self, geojson_data, source_crs='EPSG:3739', target_crs='EPSG:4326'):
        """
        Transform coordinates in GeoJSON data from one CRS to another.
        
        Args:
            geojson_data: GeoJSON data dictionary
            source_crs: Source coordinate reference system
            target_crs: Target coordinate reference system
            
        Returns:
            Transformed GeoJSON data
        """
        print(f"🔄 Transforming coordinates from {source_crs} to {target_crs}")
        
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
        
        # Set the CRS
        gdf.set_crs(source_crs, inplace=True)
        
        print(f"  Original CRS: {gdf.crs}")
        print(f"  Number of features: {len(gdf)}")
        
        # Transform to target CRS
        gdf_transformed = gdf.to_crs(target_crs)
        
        print(f"  Transformed CRS: {gdf_transformed.crs}")
        
        # Convert back to GeoJSON
        transformed_geojson = {
            'type': 'FeatureCollection',
            'features': json.loads(gdf_transformed.to_json())['features']
        }
        
        print(f"  ✅ Coordinate transformation complete")
        
        # Show sample coordinates
        if len(gdf_transformed) > 0:
            sample_geom = gdf_transformed.iloc[0].geometry
            if sample_geom:
                coords = list(sample_geom.exterior.coords)[:2]  # First 2 points
                print(f"  Sample coordinates after transform:")
                for i, coord in enumerate(coords):
                    print(f"    Point {i+1}: {coord}")
        
        return transformed_geojson
    
    def standardize_ownership(self, county_data, county_name):
        """Convert county-specific format to standard format"""
        mappings = self.get_mappings(county_name)
        links_cfg = self.get_links_config(county_name)
        standardized_features = []

        print(f"Standardizing {county_name} data...")

        # Step 1: Detect and transform coordinates if needed
        detected_crs = self.detect_coordinate_system(county_data)
        print(f"  Detected coordinate system: {detected_crs}")

        if detected_crs in ['EPSG:3739', 'EPSG:2677', 'EPSG:3738']:
            print(f"  🔄 State Plane coordinates detected - transforming to WGS84...")
            county_data = self.transform_coordinates(county_data, detected_crs, 'EPSG:4326')
        else:
            print(f"  ✅ Coordinates already in WGS84 format")

        # Step 2: Convert 3D coordinates to 2D
        county_data = self.convert_to_2d_coordinates(county_data)

        # Step 3: Standardize properties
        for i, feature in enumerate(tqdm(county_data["features"], desc="Standardizing features"), start=1):
            props = feature.get("properties", {})
            unique_id = f"{county_name.lower()}_{str(i).zfill(6)}"

            # Calculate bbox for this specific feature
            feature_bbox = self._calculate_feature_bbox(feature.get("geometry"))

            # Extract link keys/IDs only (not full URLs)
            def extract_link_key(link_info):
                if not link_info:
                    return None
                field = link_info.get("field")
                if field:
                    return props.get(field)
                return None

            property_details_key = extract_link_key(links_cfg.get("property_details"))
            tax_details_key = extract_link_key(links_cfg.get("tax_details"))
            clerk_records_key = extract_link_key(links_cfg.get("clerk_records"))

            # Standardize property fields (trimmed and renamed)
            standardized_props = {
                "GFI": unique_id,
                "county": county_name,
                "county_parcel_id": self._extract_from_mapping(props, mappings, "parcel_id"),
                "owner_name": self._extract_from_mapping(props, mappings, "owner_name"),
                "physical": self._extract_from_mapping(props, mappings, "physical_address"),
                "mail": self._extract_mailing_address(props, mappings),
                "acre": self._extract_from_mapping(props, mappings, "acreage"),
                "property_value": self._extract_from_mapping(props, mappings, "property_value"),
                "property_details_key": property_details_key or None,
                "tax_details_key": tax_details_key or None,
                "clerk_records_key": clerk_records_key or None,
                "bbox": feature_bbox,
            }

            standardized_features.append({
                "type": "Feature",
                "properties": standardized_props,
                "geometry": feature.get("geometry")
            })

        return {
            "type": "FeatureCollection",
            "features": standardized_features
        }
    
    def _extract_from_mapping(self, props, mappings, field):
        """Extract a value from props using the first mapping for the field, if present."""
        mapping = mappings.get(field, [])
        if mapping:
            key = mapping[0]
            return props.get(key)
        return None
    
    def _extract_mailing_address(self, props, mappings):
        mailing_mapping = mappings.get("mailing_address", [])
        # Always treat as a list of fields to combine
        parts = []
        for key in mailing_mapping:
            val = props.get(key, "")
            if val and isinstance(val, str):
                val = val.strip()
                if val:
                    parts.append(val)
        # Join all non-empty parts with ', '
        address = ', '.join(parts)
        # Clean up double commas, extra spaces, and trailing commas
        while ', ,' in address:
            address = address.replace(', ,', ',')
        address = address.replace(' ,', ',').replace(',  ', ', ').strip(', ').replace(',,', ',')
        return address if address else None
    
    def _calculate_feature_bbox(self, geometry):
        """
        Calculate bounding box for a single feature geometry.
        Returns [min_lon, min_lat, max_lon, max_lat] or None if invalid.
        """
        if not geometry or geometry.get('type') not in ['Polygon', 'MultiPolygon']:
            return None
        
        coordinates = geometry.get('coordinates', [])
        if not coordinates:
            return None
        
        # Flatten coordinates to get all points
        def flatten_coords(coords):
            points = []
            if not coords or not isinstance(coords, (list, tuple)) or len(coords) == 0:
                return points
                
            # Handle empty first element
            if len(coords[0]) == 0:
                return points
                
            if isinstance(coords[0], (list, tuple)):
                if isinstance(coords[0][0], (list, tuple)):
                    # MultiPolygon or Polygon with holes
                    for part in coords:
                        if not part or len(part) == 0:  # Skip empty parts
                            continue
                        if isinstance(part[0][0], (list, tuple)):
                            # MultiPolygon
                            for ring in part:
                                if ring:  # Only process non-empty rings
                                    points.extend(ring)
                        else:
                            # Polygon ring
                            points.extend(part)
                else:
                    # Simple coordinate array
                    points = coords
            return points
        
        all_points = flatten_coords(coordinates)
        if not all_points:
            return None
        
        # Filter and extract coordinates with better error handling
        lons = []
        lats = []
        for point in all_points:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                try:
                    lon = float(point[0])
                    lat = float(point[1])
                    lons.append(lon)
                    lats.append(lat)
                except (ValueError, TypeError, IndexError) as e:
                    # Skip invalid coordinate points
                    continue
        
        if not lons or not lats:
            return None
        
        # Calculate bbox: [min_lon, min_lat, max_lon, max_lat]
        bbox = [min(lons), min(lats), max(lons), max(lats)]
        
        return bbox
    
    def save_standardized_data(self, standardized_data, county_name):
        """Save standardized data to file"""
        # Ensure the path is relative to tile_cycle directory
        from pathlib import Path
        tile_cycle_dir = Path(__file__).parent.parent
        output_path = tile_cycle_dir / "geojsons_for_db_upload" / f"{county_name}_data_files" / f"{county_name}_final_ownership.geojson"
        output_dir = output_path.parent
        os.makedirs(output_dir, exist_ok=True)
        output_path = str(output_path)
        with open(output_path, 'w') as f:
            json.dump(standardized_data, f, indent=2)
        print(f"✅ Saved standardized data to {output_path}")
        return output_path
