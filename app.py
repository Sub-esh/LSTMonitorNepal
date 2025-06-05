'''
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
    query = f"""
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
'''
import streamlit as st
import ee
import geemap.foliumap as geemap
from datetime import datetime

def get_lst_ndvi(start_date, end_date):
    kathmandu = ee.Geometry.Rectangle([85.25, 27.65, 85.45, 27.75], 'EPSG:4326', False)

    dataset = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
        .filterDate(start_date, end_date) \
        .filterBounds(kathmandu)

def process_image(image):
        # LST
        lst = image.select(['ST_B10']).multiply(0.00341802).add(-85.0).rename('LST')
        # NDVI
        nir = image.select('SR_B5')
        red = image.select('SR_B4')
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        return image.select([]).addBands([lst, ndvi])

    processed = dataset.map(process_image)
    composite = processed.select(['LST', 'NDVI']).median().clip(kathmandu)
    return composite
#Streamlit APP 
# Initialize GEE
try:
    ee.Initialize()
except Exception as e:
    ee.Authenticate()

st.set_page_config(layout="wide")
st.title("🌡️ Urban Heat Monitoring Dashboard – Kathmandu")

# Date inputs
start_date = st.date_input("Start Date", value=datetime(2023, 6, 1))
end_date = st.date_input("End Date", value=datetime(2023, 9, 30))

if start_date > end_date:
    st.error("End date must be after start date.")
else:
    with st.spinner("Fetching satellite data..."):
        image = get_lst_ndvi(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    st.success("Data retrieved successfully!")

    # Map visualization
    m = geemap.Map(center=(27.7, 85.3), zoom=11)

    # Add layers
    lst_vis = {'min': 25, 'max': 45, 'palette': ['blue', 'white', 'red']}
    ndvi_vis = {'min': -1, 'max': 1, 'palette': ['brown', 'yellow', 'green']}

    m.addLayer(image.select('LST'), lst_vis, 'Land Surface Temperature')
    m.addLayer(image.select('NDVI'), ndvi_vis, 'NDVI')

    # Display map
    m.to_streamlit(height=700)

    # Optional: Show histogram or stats
    if st.checkbox("Show Statistics"):
        region = ee.Geometry.Rectangle([85.25, 27.65, 85.45, 27.75])
        stats = image.reduceRegion(ee.Reducer.mean().combine({
            reducer2: ee.Reducer.stdDev(),
            sharedInputs: True
        }), region, 30)
        st.write(stats.getInfo())
