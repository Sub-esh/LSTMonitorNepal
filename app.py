import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
import requests
from shapely.geometry import shape

# Set page config
st.set_page_config(layout="wide")
st.title("🌍 City Boundary Fetcher (OpenStreetMap)")

# Function to fetch boundary from OSM
def get_osm_boundary(place_name, admin_level=8):
    """Fetch boundary from OSM using Overpass API."""
    query = f """
    [out:json];
    relation["name"="{place_name}"]["admin_level"="{admin_level}"];
    out geom;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data={"data": query})
    
    if response.status_code != 200:
        st.error(f"Failed to fetch data. Error: {response.text}")
        return None
    
    data = response.json()
    features = []
    
    for element in data["elements"]:
        if element["type"] == "relation":
            coords = []
            for member in element["members"]:
                if member["type"] == "way":
                    coords.extend([(point["lon"], point["lat"]) for point in member["geometry"]])
            if coords:
                polygon = shape({"type": "Polygon", "coordinates": [coords]})
                features.append({
                    "name": element["tags"].get("name", place_name),
                    "geometry": polygon
                })
    
    if not features:
        st.warning(f"No boundary found for '{place_name}'. Try a different admin level.")
        return None
    
    return gpd.GeoDataFrame(features, crs="EPSG:4326")

# Sidebar for user input
with st.sidebar:
    st.header("Search Parameters")
    city_name = st.text_input("Enter city name", "Kathmandu")
    admin_level = st.selectbox(
        "Admin level (8=city, 6=district, 4=province/state)", 
        options=[4, 6, 8], 
        index=2
    )
    if st.button("Fetch Boundary"):
        with st.spinner(f"Fetching {city_name} boundary..."):
            gdf = get_osm_boundary(city_name, admin_level)
            if gdf is not None:
                st.session_state["gdf"] = gdf
                st.success("Boundary fetched successfully!")

# Main map display
col1, col2 = st.columns([3, 1])

with col1:
    if "gdf" in st.session_state:
        m = leafmap.Map(center=(27.7, 85.3), zoom=10)
        m.add_gdf(st.session_state["gdf"], layer_name="City Boundary")
        m.to_streamlit(height=600)
    else:
        st.info("Enter a city name and click 'Fetch Boundary'.")

with col2:
    if "gdf" in st.session_state:
        st.subheader("Boundary Data")
        st.write(st.session_state["gdf"].drop(columns="geometry"))
        st.download_button(
            label="Download GeoJSON",
            data=st.session_state["gdf"].to_json(),
            file_name=f"{city_name}_boundary.geojson",
            mime="application/json"
        )
