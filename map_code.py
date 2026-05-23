import pandas as pd
import numpy as np
import folium
import branca.colormap as cm
from folium.plugins import TreeLayerControl
from branca.element import Element


df = pd.read_csv("C:/Users/socce/IMPACTS/Plankton IDs (3).csv")
# --------------------------------------------------
# 1. Clean + prepare
# --------------------------------------------------
cols_needed = [
    'Sample Date', 'Sample Site', 'Sample Time',
    'Water Temperature (C)', 'Air Temperature (C)',
    'Salinity (PSU)', 'Latitude', 'Longitude',
    'Type', 'ID', 'Relative Abundance'
]

df_map = (
    df[cols_needed]
    .dropna(subset=['Latitude', 'Longitude'])
    .copy()
)

df_map['Sample Date'] = df_map['Sample Date'].astype(str)
df_map['Relative Abundance'] = (
    df_map['Relative Abundance']
    .fillna('')
    .astype(str)
    .str.strip()
)

# numeric versions for color scaling
df_map['Salinity (PSU)'] = pd.to_numeric(df_map['Salinity (PSU)'], errors='coerce')
df_map['Water Temperature (C)'] = pd.to_numeric(df_map['Water Temperature (C)'], errors='coerce')
df_map['Air Temperature (C)'] = pd.to_numeric(df_map['Air Temperature (C)'], errors='coerce')

# --------------------------------------------------
# 2. Map center + 5x5 km bounds (overall)
# --------------------------------------------------
center_lat = df_map['Latitude'].mean()
center_lon = df_map['Longitude'].mean()

half_km = 2.5
lat_delta = half_km / 111.0
lon_delta = half_km / (111.0 * np.cos(np.deg2rad(center_lat)))

bounds = [
    [center_lat - lat_delta, center_lon - lon_delta],
    [center_lat + lat_delta, center_lon + lon_delta]
]

# --------------------------------------------------
# 3. Shared color scales across all dates/locations
# --------------------------------------------------
def safe_min_max(series):
    s = series.dropna()
    if s.empty:
        return 0, 1
    vmin, vmax = s.min(), s.max()
    if vmin == vmax:
        return vmin - 0.5, vmax + 0.5
    return vmin, vmax

sal_min, sal_max = safe_min_max(df_map['Salinity (PSU)'])
wt_min, wt_max   = safe_min_max(df_map['Water Temperature (C)'])
at_min, at_max   = safe_min_max(df_map['Air Temperature (C)'])

salinity_colormap = cm.LinearColormap(
    colors=['blue', 'cyan', 'green', 'yellow', 'orange', 'red'],
    vmin=sal_min,
    vmax=sal_max,
    caption='Salinity (PSU)'
)

water_colormap = cm.LinearColormap(
    colors=['darkblue', 'blue', 'cyan', 'yellow', 'orange', 'red'],
    vmin=wt_min,
    vmax=wt_max,
    caption='Water Temperature (°C)'
)
air_colormap = cm.LinearColormap(
    colors=['purple', 'blue', 'cyan', 'yellow', 'orange', 'red'],
    vmin=at_min,
    vmax=at_max,
    caption='Air Temperature (°C)'
)

# --------------------------------------------------
# 4. Create base map (Google Satellite)
# --------------------------------------------------
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=17,
    tiles=None
)

folium.TileLayer(
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google",
    name="Google Satellite",
    overlay=False,
    control=False
).add_to(m)

# --------------------------------------------------
# 5. Helper for popup
# --------------------------------------------------
def build_popup_html(site, sample_date, sample_time, water_temp, air_temp, salinity, group):
    elevated_rows = group[group['Relative Abundance'].str.lower() == 'elevated']

    extra_html = ""
    if not elevated_rows.empty:
        extra_html += "<hr><b>Elevated Entries:</b><br><ul style='padding-left:18px; margin:6px 0;'>"
        for _, r in elevated_rows[['Type', 'ID', 'Relative Abundance']].drop_duplicates().iterrows():
            t = r['Type'] if pd.notna(r['Type']) else "N/A"
            id_ = r['ID'] if pd.notna(r['ID']) else "N/A"
            ra = r['Relative Abundance'] if pd.notna(r['Relative Abundance']) else "N/A"

            extra_html += f"""
            <li>
                <b>Type:</b> {t}<br>
                <b>ID:</b> {id_}<br>
                <b>Relative Abundance:</b> {ra}
            </li>
            """
        extra_html += "</ul>"

    salinity_display = f"{salinity:.2f}" if pd.notna(salinity) else "N/A"
    water_display    = f"{water_temp:.2f}" if pd.notna(water_temp) else "N/A"
    air_display      = f"{air_temp:.2f}" if pd.notna(air_temp) else "N/A"

    popup_html = f"""
    <div style="width:320px; font-size:13px;">
        <h4>{site}</h4>
        <b>Date:</b> {sample_date}<br>
        <b>Time:</b> {sample_time}<br>
        <b>Water Temp:</b> {water_display} °C<br>
        <b>Air Temp:</b> {air_display} °C<br>
        <b>Salinity:</b> {salinity_display} PSU
        {extra_html}
    </div>
    """
    return popup_html, salinity_display, water_display, air_display

# --------------------------------------------------
# 6. Build layers by date and parameter
# --------------------------------------------------
date_tree_children = []

# store actual JS layer variable names so legend visibility can be updated
legend_layer_map = {
    "salinity": [],
    "water": [],
    "air": []
}

for i, date in enumerate(sorted(df_map['Sample Date'].unique())):
    show_general = (i == 0)

    fg_general = folium.FeatureGroup(name=f"{date} - General", show=show_general)
    fg_sal     = folium.FeatureGroup(name=f"{date} - Salinity", show=False)
    fg_water   = folium.FeatureGroup(name=f"{date} - Water Temp", show=False)
    fg_air     = folium.FeatureGroup(name=f"{date} - Air Temp", show=False)

    df_day = df_map[df_map['Sample Date'] == date].copy()

    grouped = df_day.groupby(
        ['Sample Date', 'Sample Site', 'Latitude', 'Longitude'],
        dropna=False
    )

    for (sample_date, site, lat, lon), group in grouped:
        sample_time = group['Sample Time'].dropna().iloc[0] if group['Sample Time'].notna().any() else "N/A"
        water_temp = group['Water Temperature (C)'].dropna().iloc[0] if group['Water Temperature (C)'].notna().any() else np.nan
        air_temp   = group['Air Temperature (C)'].dropna().iloc[0] if group['Air Temperature (C)'].notna().any() else np.nan
        salinity   = group['Salinity (PSU)'].dropna().iloc[0] if group['Salinity (PSU)'].notna().any() else np.nan

        popup_html, salinity_display, water_display, air_display = build_popup_html(
            site, sample_date, sample_time, water_temp, air_temp, salinity, group
        )


        # General marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=site,
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(fg_general)

        # Salinity-colored marker
        sal_color = salinity_colormap(salinity) if pd.notna(salinity) else "gray"
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{site} | Salinity: {salinity_display} PSU",
            color=sal_color,
            fill=True,
            fill_color=sal_color,
            fill_opacity=0.9,
            weight=2
        ).add_to(fg_sal)

        # Water-temperature-colored marker
        water_color = water_colormap(water_temp) if pd.notna(water_temp) else "gray"
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{site} | Water Temp: {water_display} °C",
            color=water_color,
            fill=True,
            fill_color=water_color,
            fill_opacity=0.9,
            weight=2
        ).add_to(fg_water)

        # Air-temperature-colored marker
        air_color = air_colormap(air_temp) if pd.notna(air_temp) else "gray"
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=f"{site} | Air Temp: {air_display} °C",
            color=air_color,
            fill=True,
            fill_color=air_color,
            fill_opacity=0.9,
            weight=2
        ).add_to(fg_air)

    fg_general.add_to(m)
    fg_sal.add_to(m)
    fg_water.add_to(m)
    fg_air.add_to(m)

    legend_layer_map["salinity"].append(fg_sal.get_name())
    legend_layer_map["water"].append(fg_water.get_name())
    legend_layer_map["air"].append(fg_air.get_name())

    # tree structure for checkbox control
    date_tree_children.append({
        "label": f"<b>{date}</b>",
        "children": [
            {"label": "General", "layer": fg_general},
            {"label": "Salinity", "layer": fg_sal},
            {"label": "Water Temperature", "layer": fg_water},
            {"label": "Air Temperature", "layer": fg_air},
        ]
    })
# --------------------------------------------------
# 7. Add tree layer control (checkboxes, organized)
# --------------------------------------------------
TreeLayerControl(
    overlay_tree={
        "label": "<b>Sampling Layers</b>",
        "children": date_tree_children
    },
    collapsed=False
).add_to(m)

# --------------------------------------------------
# 8. Add custom CSS to keep control usable on screen
# --------------------------------------------------
custom_css = """
<style>
.leaflet-control-layers {
    max-height: 420px !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
    width: 280px !important;
    font-size: 13px !important;
    padding-right: 6px !important;
}
.leaflet-control-layers-list {
    max-height: 380px !important;
    overflow-y: auto !important;
}
</style>
"""
m.get_root().html.add_child(Element(custom_css))
# --------------------------------------------------
# 9. Add custom legends (hidden by default)
# --------------------------------------------------
def gradient_css(colors):
    return ", ".join(colors)

sal_colors = ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']
wt_colors  = ['darkblue', 'blue', 'cyan', 'yellow', 'orange', 'red']
at_colors  = ['purple', 'blue', 'cyan', 'yellow', 'orange', 'red']

legend_html = f"""
<div id="legend-salinity" style="
    display:none;
    position: fixed;
    bottom: 30px;
    left: 20px;
    z-index: 9999;
    background-color: white;
    border: 2px solid gray;
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    min-width: 220px;
">
    <div><b>Salinity (PSU)</b></div>
    <div style="height:14px; margin:6px 0; background: linear-gradient(to right, {gradient_css(sal_colors)});"></div>
    <div style="display:flex; justify-content:space-between;">
        <span>{sal_min:.2f}</span>
        <span>{sal_max:.2f}</span>
    </div>
</div>
<div id="legend-water" style="
    display:none;
    position: fixed;
    bottom: 120px;
    left: 20px;
    z-index: 9999;
    background-color: white;
    border: 2px solid gray;
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    min-width: 220px;
">
    <div><b>Water Temperature (°C)</b></div>
    <div style="height:14px; margin:6px 0; background: linear-gradient(to right, {gradient_css(wt_colors)});"></div>
    <div style="display:flex; justify-content:space-between;">
        <span>{wt_min:.2f}</span>
        <span>{wt_max:.2f}</span>
    </div>
</div>
<div id="legend-air" style="
    display:none;
    position: fixed;
    bottom: 210px;
    left: 20px;
    z-index: 9999;
    background-color: white;
    border: 2px solid gray;
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    min-width: 220px;
">
    <div><b>Air Temperature (°C)</b></div>
    <div style="height:14px; margin:6px 0; background: linear-gradient(to right, {gradient_css(at_colors)});"></div>
    <div style="display:flex; justify-content:space-between;">
        <span>{at_min:.2f}</span>
        <span>{at_max:.2f}</span>
    </div>
</div>
"""
m.get_root().html.add_child(Element(legend_html))

# --------------------------------------------------
# 10. JS to show/hide legends based on active overlays
# --------------------------------------------------
map_name = m.get_name()

sal_layer_names = legend_layer_map["salinity"]
water_layer_names = legend_layer_map["water"]
air_layer_names = legend_layer_map["air"]

legend_js = f"""
<script>
document.addEventListener("DOMContentLoaded", function() {{
    var map = {map_name};

    var salLayerNames = {sal_layer_names};
    var waterLayerNames = {water_layer_names};
    var airLayerNames = {air_layer_names};

    function anyLayerVisible(layerNames) {{
        for (var i = 0; i < layerNames.length; i++) {{
            var layerName = layerNames[i];
            if (window[layerName] && map.hasLayer(window[layerName])) {{
                return true;
            }}
        }}
        return false;
    }}

    function updateLegends() {{
        var salOn = anyLayerVisible(salLayerNames);
        var waterOn = anyLayerVisible(waterLayerNames);
        var airOn = anyLayerVisible(airLayerNames);

        var salLegend = document.getElementById('legend-salinity');
        var waterLegend = document.getElementById('legend-water');
        var airLegend = document.getElementById('legend-air');

        if (salLegend) {{
            salLegend.style.display = salOn ? 'block' : 'none';
        }}
        if (waterLegend) {{
            waterLegend.style.display = waterOn ? 'block' : 'none';
        }}
        if (airLegend) {{
            airLegend.style.display = airOn ? 'block' : 'none';
        }}
    }}

    map.on('overlayadd', updateLegends);
    map.on('overlayremove', updateLegends);

    // run once after map fully loads
    setTimeout(updateLegends, 300);
}});
</script>
"""
m.get_root().html.add_child(Element(legend_js))

# --------------------------------------------------
# 11. Save map into Hugo-compatible structure
# --------------------------------------------------
from pathlib import Path

# Run this notebook/script from your Hugo project folder:
# C:\Users\socce\IMPACTS

hugo_root = Path.cwd()

maps_dir = hugo_root / "static" / "maps"
shortcodes_dir = hugo_root / "layouts" / "shortcodes"
content_dir = hugo_root / "content" / "maps"

maps_dir.mkdir(parents=True, exist_ok=True)
shortcodes_dir.mkdir(parents=True, exist_ok=True)
content_dir.mkdir(parents=True, exist_ok=True)

# Save interactive Folium map
map_filename = "sampling_sites_updated_4_18_26.html"
map_path = maps_dir / map_filename

m.fit_bounds(bounds)
m.save(str(map_path))

# Create reusable Hugo shortcode
shortcode_path = shortcodes_dir / "iframe-map.html"

shortcode_path.write_text("""<iframe
  src="{{ .Get "src" }}"
  width="100%"
  height="{{ .Get "height" | default "650" }}"
  style="border:0; border-radius:12px;"
  loading="lazy">
</iframe>
""", encoding="utf-8")

# Create Hugo page that embeds the map
page_path = content_dir / "index.md"

page_path.write_text("""---
title: "Interactive Sampling Map"
date: 2026-04-18
draft: false
---

# Interactive Sampling Map

This map shows sampling sites, salinity, water temperature, air temperature, and elevated biological observations.

{{< iframe-map src="/maps/sampling_sites_updated_4_18_26.html" height="700" >}}
""", encoding="utf-8")

print("Created:")
print(map_path)
print(shortcode_path)
print(page_path)
