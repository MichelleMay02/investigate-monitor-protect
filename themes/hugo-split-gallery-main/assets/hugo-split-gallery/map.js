var Promise = window.Promise || JSZip.external.Promise;
var map = null;
var mapgroups = [];
var mapmarkers = [];
var colorMap = {
  'red': '#D63E2A', 'orange': '#F59630', 'green': '#72B026', 'blue': '#38AADD', 'purple': '#D252B9',
  'darkred': '#A23336', 'darkblue': '#0067A3', 'darkgreen': '#728224', 'darkpurple': '#5B396B', 'cadetblue': '#436978',
  'lightred': '#FF8E7F', 'beige': '#FFCB92', 'lightgreen': '#BBF970', 'lightblue': '#8ADAFF', 'pink': '#FF91EA',
  'white': '#FBFBFB', 'lightgray': '#A3A3A3', 'gray': '#575757', 'black': '#303030'
};
var colors = ['blue', 'green', 'orange', 'purple', 'red', 'darkblue', 'darkpurple', 'lightblue', 'lightgreen', 'beige', 'pink', 'lightred'];
var currentColor = 0;
var bounds = null;

var iconDefault = L.AwesomeMarkers.icon({
  icon: 'camera',
  markerColor: 'gray',
  prefix: 'fa'
});
var iconSelected = L.AwesomeMarkers.icon({
  icon: 'camera',
  markerColor: 'purple',
  prefix: 'fa'
});
var iconsMap = {
  'cadetblue': L.AwesomeMarkers.icon({
    icon: 'location-arrow',
    markerColor: 'cadetblue',
    prefix: 'fa'
  })
};

function initMap() {
  if ($("#mapid").length === 0) return;

  map = L.map('mapid');
  L.tileLayer(
    'https://tile.thunderforest.com/outdoors/{z}/{x}/{y}{r}.png?apikey=bcecc6dc7a9a46cca6d1eff04dd595cf',
    {
      maxZoom: 18,
      attribution:
        'Maps © <a href="http://www.thunderforest.com">Thunderforest</a>, Data © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }
  ).addTo(map);
}

function nextColor() {
  currentColor = (currentColor + 1) % colors.length;
  return currentColor;
}

function showTrack(track, color) {
  var start = null;
  var end = null;
  var featuregroup = L.featureGroup();

  if (!(color in iconsMap)) {
    iconsMap[color] = L.AwesomeMarkers.icon({
      icon: 'location-arrow',
      markerColor: color,
      prefix: 'fa'
    });
  }

  var line = new L.geoJSON(track);
  var layers = line.getLayers();
  for (let i = 0; i < layers.length; i += 1) {
    if (layers[i] instanceof L.Polyline && layers[i].feature.geometry.type === 'LineString') {
      layers[i].setStyle({ weight: 5, color: colorMap[color], opacity: 0.75 });
      layers[i].addTo(featuregroup);

      var latlngs = layers[i].getLatLngs();

      if (start === null) {
        start = latlngs[0];
        L.marker(start, {
          icon: iconsMap[color],
          zIndexOffset: 10,
        }).addTo(featuregroup);
      }
      end = latlngs[latlngs.length - 1];
    } /*
    Not sure we want to display other features
    else if (layers[i] instanceof L.Path) {
      // Add layer (polygon, etc.) with custom style
      layers[i].setStyle({ weight: 5, color: colorMap[color], opacity: 0.75 });
      layers[i].addTo(featuregroup);
    } else {
      // Add layer (marker, etc.) as-is
      layers[i].addTo(featuregroup);
    }*/
  }

  if (start !== null && end !== null) {
    if (!start.equals(end, 100)) {
      L.marker(end, {
        icon: iconsMap[color],
        zIndexOffset: 10,
      }).addTo(featuregroup);
    }
  }

  if (featuregroup.getLayers().length > 0) {
    featuregroup.addTo(map);
    addBounds(featuregroup.getBounds());

    return featuregroup;
  }
  console.warn("Empty track");
  return null;
}

function addBounds(o) {
  bounds = (bounds === null) ? o.pad(0.5) : bounds.extend(o.pad(0.5));
}

function addMarker(latlng, idx) {
  var marker = L.marker(latlng, {
    draggable: false, opacity: 0.5, icon: iconDefault
  }).on('click', function () {
    $('.split-grid a').eq(idx).trigger('click');
  }).addTo(map);
  addBounds(latlng.toBounds(100));

  $('.split-grid a').eq(idx).hover(function () {
    map.flyTo(marker.getLatLng());
    marker.setZIndexOffset(1000);
    marker.setIcon(iconSelected);
    marker.setOpacity(1);
  }, function () {
    marker.setZIndexOffset(0);
    marker.setIcon(iconDefault);
    marker.setOpacity(0.5);
    if (bounds) map.flyToBounds(bounds);
  });
  return marker;
}

function highlightFeaturegroup(featuregroup) {
  featuregroup.bringToFront();
  featuregroup.eachLayer(function (layer) {
    if (layer instanceof L.Marker) {
      layer.setZIndexOffset(1000);
      layer.setIcon(iconsMap['cadetblue']);
      layer.setOpacity(1);
    } else {
      layer.setStyle({ weight: 8, color: colorMap['cadetblue'], opacity: 1 });
    }
  });
}

function lowlightAll() {
  $.each(mapgroups, function (i, group) {
    group.eachLayer(function (layer) {
      if (layer instanceof L.Marker) {
        layer.setOpacity(0.6);
      } else {
        layer.setStyle({ weight: 5, color: colorMap[group._color], opacity: 0.6 });
      }
    });
  });
  $.each(mapmarkers, function (i, marker) {
    marker.setOpacity(0.2);
  });
}

function restoreHilowlight() {
  $.each(mapgroups, function (i, group) {
    group.eachLayer(function (layer) {
      if (layer instanceof L.Marker) {
        layer.setZIndexOffset(10);
        layer.setIcon(iconsMap[group._color]);
        layer.setOpacity(1);
      } else {
        layer.setStyle({ weight: 5, color: colorMap[group._color], opacity: 0.75 });
      }
    });
  });
  $.each(mapmarkers, function (i, marker) {
    marker.setOpacity(0.5);
  });
}

function onMouseOverTrack(featuregroup) {
  lowlightAll();
  highlightFeaturegroup(featuregroup);
  featuregroup.once('mouseout', function () {
    onMouseOutTrack(featuregroup);
  });
}

function onMouseOutTrack(featuregroup) {
  restoreHilowlight();
  featuregroup.once('mouseover', function () {
    onMouseOverTrack(featuregroup);
  });
}

function add(tracks, markers, index) {
  var b = null;
  var featuregroups = [];
  $.each(tracks, function (i, track) {
    var color = colors[nextColor()];
    var featuregroup = showTrack(track[0], color);
    if (featuregroup) {
      featuregroup._color = color;
      mapgroups.push(featuregroup);
      // For some reason, mouseover is triggered continuously, and not only when mouse enter the feature group
      // So we have to juggle with binding mouseover/mouseout
      featuregroup.once('mouseover', function () {
        onMouseOverTrack(featuregroup);
      });
      var featuregroupbounds = featuregroup.getBounds().pad(0.5);
      featuregroup.bindPopup(track[1]);
      b = (b === null) ? featuregroupbounds : b.extend(featuregroupbounds);
      featuregroups.push(featuregroup);
    }
  });
  $.each(markers, function (i, marker) {
    var m = addMarker(marker[0], marker[1]);
    mapmarkers.push(m);
    if (marker.length > 2) m.bindPopup(marker[2]);
  });

  if (index !== undefined && tracks.length > 0) {
    $('.split-grid a').eq(index).hover(function () {
      map.flyTo(b.getCenter());
      lowlightAll();
      $.each(featuregroups, function (i, featuregroup) {
        highlightFeaturegroup(featuregroup);
      })
    }, function () {
      if (bounds) map.flyToBounds(bounds);
      restoreHilowlight();
    });
  }
}

function finalizeMap() {
  if (bounds) map.fitBounds(bounds);
}