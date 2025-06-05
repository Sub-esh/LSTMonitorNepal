import requests
import geopandas as gpd
from shapely.geometry import shape

def get_osm_boundary(place_name, admin_level=8, output_format="geojson"):
    """
    Fetch administrative boundary from OpenStreetMap.
    
    Args:
        place_name (str): Name of the place (e.g., "Kathmandu").
        admin_level (int): OSM admin level (e.g., 8 for city, 6 for district).
        output_format (str): "geojson" or "shapefile".
    
    Returns:
        GeoDataFrame: Boundary geometry and attributes.
    """
    # Overpass API query
    query = 
    f """
    [out:json];
    relation["name"="{place_name}"]["admin_level"="{admin_level}"];
    out geom;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    
    if response.status_code != 200:
        raise ValueError(f"Query failed: {response.text}")

    data = response.json()
    
    # Extract geometries
    features = []
    for element in data["elements"]:
        if element["type"] == "relation":
            coords = []
            for member in element["members"]:
                if member["type"] == "way":
                    coords.extend(member["geometry"])
            polygon = shape({"type": "Polygon", "coordinates": [coords]})
            features.append({
                "name": element["tags"].get("name", place_name),
                "admin_level": element["tags"].get("admin_level"),
                "geometry": polygon
            })
    
    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    return gdf
