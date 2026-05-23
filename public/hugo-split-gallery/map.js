function initMap() {
  if ($("#mapid").length === 0) return;

  $("#mapid").html(`
    <iframe
      src="/maps/sampling_sites_updated_4_18_26.html"
      width="100%"
      height="100%"
      style="border:none;"
      loading="lazy">
    </iframe>
  `);
}

function add(tracks, markers, index) {
  // Disabled because the Folium iframe handles all map layers.
}

function finalizeMap() {
  // Disabled because the Folium iframe handles zoom/bounds.
}