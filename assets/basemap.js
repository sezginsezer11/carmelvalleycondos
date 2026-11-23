/* Shared base maps for every Leaflet map on the site.
   Satellite (Esri imagery + road overlay) is the default. "Map" is the
   OpenFreeMap "Bright" street style, drawn with MapLibre; its libraries load
   only the first time someone switches to it, so pages stay fast.

   Usage:
     var base = CVBase(map, {places: true});           // places: extra place-name labels on satellite
     CVBase.bind(base, toggleContainer, function(kind){ ... });  // buttons with data-b="sat" / "map"
*/
(function () {
  var ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  var ML = 'https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl';
  var MLL = 'https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.0.22/leaflet-maplibre-gl.js';
  var STYLE = 'https://tiles.openfreemap.org/styles/bright';
  var libs = null;

  function load(src, css) {
    return new Promise(function (res, rej) {
      var n = document.createElement(css ? 'link' : 'script');
      if (css) { n.rel = 'stylesheet'; n.href = src; } else { n.src = src; }
      n.onload = res; n.onerror = rej;
      document.head.appendChild(n);
    });
  }
  function maplibre() {
    if (!libs) {
      libs = Promise.all([load(ML + '.css', true), load(ML + '.js')]).then(function () { return load(MLL); });
      libs.catch(function () { libs = null; });
    }
    return libs;
  }

  window.CVBase = function (map, opts) {
    opts = opts || {};
    var satLayers = [
      L.tileLayer(ESRI + 'World_Imagery/MapServer/tile/{z}/{y}/{x}', {maxZoom: 19, attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics'}),
      L.tileLayer(ESRI + 'Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {maxZoom: 19})
    ];
    if (opts.places) satLayers.push(L.tileLayer(ESRI + 'Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {maxZoom: 19}));
    var sat = L.layerGroup(satLayers), street = null, cur = null;

    function set(kind) {
      if (kind === cur) return Promise.resolve(kind);
      if (kind === 'sat') {
        if (street) map.removeLayer(street);
        sat.addTo(map); cur = 'sat';
        return Promise.resolve(cur);
      }
      return maplibre().then(function () {
        if (!street) street = L.maplibreGL({
          style: STYLE,
          attribution: '&copy; <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> &copy; OpenMapTiles &copy; OpenStreetMap contributors'
        });
        map.removeLayer(sat); street.addTo(map); cur = 'map';
        return cur;
      }).catch(function () { return cur; }); // street map unavailable: stay on satellite
    }
    set(opts.start || 'sat');
    return {set: set, get: function () { return cur; }};
  };

  window.CVBase.bind = function (base, box, onChange) {
    if (!box) return;
    var btns = box.querySelectorAll('[data-b]');
    function mark(k) { btns.forEach(function (x) { x.setAttribute('aria-pressed', x.dataset.b === k ? 'true' : 'false'); }); }
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        base.set(b.dataset.b).then(function (k) { mark(k); if (onChange) onChange(k); });
      });
    });
    mark(base.get());
  };
})();
