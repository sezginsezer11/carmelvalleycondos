#!/usr/bin/env python3
"""The neighborhood map explorer, shared by the neighborhoods hub and the school pages.

Desktop: area list on the left, sticky map on the right.
Phones: full-screen map with a pull-up list (peek / half / full); the page title scrolls away.

    from explorer import explorer
    x = explorer(comms, groups, colors, ...)   # -> {"css", "html", "js", "head_js"}

comms:  communities from atlas_data.json with n, sub, homes, p, r12 (sold range, last 12 months)
groups: [(area key, area label, [communities])]
zone:   optional Leaflet rings ([[lat, lng], ...]) of a school attendance boundary, drawn as a
        dashed outline with everything outside it shaded; the map frames the zone.
Stdlib only.
"""
import html
import json
import re

e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


CSS = """
  .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
  .map-sec{padding:12px 0 8px}
  .dot{width:10px;height:10px;border-radius:50%;background:var(--ac);flex:none;display:inline-block}
  .map-box{position:relative;z-index:0;isolation:isolate;max-width:1100px;margin:0 auto;border:1px solid var(--line);border-radius:14px;overflow:hidden}
  #map{height:min(64vh,560px);background:#e8ecef}
  .map-views{position:absolute;top:10px;right:10px;z-index:500;display:flex;background:#fff;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.18);overflow:hidden}
  .map-views button{border:0;background:#fff;font:600 12.5px var(--sans);padding:7px 11px;cursor:pointer;color:#37404a}
  .map-views button[aria-pressed="true"]{background:var(--lake);color:#fff}
  .map-card{position:absolute;left:10px;bottom:10px;z-index:500;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.18);padding:14px 16px;max-width:300px;display:none}
  .map-card.show{display:block}
  .map-card h3{font-size:17px;font-weight:800;margin-right:22px}
  .map-card .mc-area{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--label);margin-top:4px}
  .map-card .mc-homes{font-size:14px;margin-top:6px}
  .map-card a.mc-go{display:inline-block;margin-top:10px;background:var(--lake);color:#fff;font-weight:600;font-size:13.5px;padding:8px 14px;border-radius:7px}
  .map-card .mc-acts{display:flex;flex-wrap:wrap;gap:8px}
  .map-card a.mc-alt{background:#fff;color:var(--lake);box-shadow:inset 0 0 0 1.5px var(--lake)}
  .map-card .mc-x{position:absolute;top:8px;right:10px;border:0;background:none;font-size:20px;line-height:1;color:var(--label);cursor:pointer}
  .map-note{text-align:center;font-size:13px;color:var(--label);margin-top:10px}
  .leaflet-container{font-family:var(--sans)}
  .leaflet-interactive:focus{outline:none}
  .leaflet-control-attribution{font-size:9.5px!important}
  .leaflet-tooltip.lbl{background:none;border:0;box-shadow:none;padding:0;color:#101418;font-weight:700;font-size:11.5px;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 2px #fff;white-space:nowrap}
  .leaflet-tooltip.lbl::before{display:none}
  .sat .leaflet-tooltip.lbl{color:#fff;text-shadow:0 0 3px #000,0 0 3px #000,0 0 2px #000}
  /* explorer: area list left, sticky map right (stacked on phones) */
  .xp{display:grid;grid-template-columns:minmax(0,1fr);gap:14px}
  .xp-map{order:-1}
  .xp-list h2{font-size:20px;font-weight:800;letter-spacing:-.01em}
  .xp-list .xp-hint{font-size:14px;color:var(--label);margin:4px 0 12px}
  .ax{border:1px solid var(--line);border-left:4px solid var(--ac);border-radius:10px;background:var(--white);margin-bottom:8px;overflow:hidden}
  .ax summary{list-style:none;display:flex;align-items:center;gap:10px;padding:13px 14px;cursor:pointer;font-weight:700;font-size:16px}
  .ax summary::-webkit-details-marker{display:none}
  .ax summary:hover{background:var(--paper)}
  .ax-name{flex:1;min-width:0}
  .ax-n{font-size:13px;font-weight:600;color:var(--label);background:var(--paper);border-radius:100px;padding:2px 9px}
  .ax-chev{width:18px;height:18px;fill:none;stroke:var(--label);stroke-width:2;transition:transform .2s}
  .ax[open] .ax-chev{transform:rotate(180deg)}
  .ax[open] summary{border-bottom:1px solid var(--line)}
  .ax-body{padding:4px 14px 6px}
  .nr:first-child{border-top:0}
  .ax-guide{display:block;border-top:1px solid var(--line);padding:11px 4px 8px;font-size:14px;font-weight:600;color:var(--lake)}
  .nr-list{list-style:none}
  .nr{display:flex;align-items:center;gap:8px;border-top:1px solid var(--line)}
  .nr-pick{flex:1;min-width:0;text-align:left;border:0;background:none;padding:10px 4px;cursor:pointer;font:inherit;color:var(--ink);display:flex;flex-direction:column;gap:1px;border-radius:6px}
  .nr-name{font-weight:700;font-size:15px}
  .nr-meta{font-size:13px;color:var(--label)}
  .nr-pick:hover .nr-name,.nr.on .nr-name{color:var(--lake)}
  .nr.on{background:#eef5fa}
  .nr-go{flex:none;font-size:13px;font-weight:700;color:var(--lake);padding:6px 6px;white-space:nowrap}
  .xp .map-box{max-width:none}
  .sh-grab,.sh-btn{display:none}
  /* level switch (schools map): Elementary / Middle / High */
  .lv-tabs{display:flex;gap:4px;background:var(--paper);border-radius:10px;padding:4px;margin:0 0 12px}
  .lv-tabs button{flex:1;border:0;background:none;border-radius:7px;font:600 14px var(--sans);padding:9px 4px;cursor:pointer;color:#37404a;display:flex;flex-direction:column;align-items:center;gap:1px;line-height:1.2}
  .lv-tabs button small{font-size:11.5px;font-weight:500;color:var(--label)}
  .lv-tabs button[aria-selected="true"]{background:var(--lake);color:#fff;box-shadow:0 1px 3px rgba(0,0,0,.15)}
  .lv-tabs button[aria-selected="true"] small{color:#dbeaf4}
  .ax[hidden]{display:none}
  @media(max-width:979px){
    .map-sec{padding:6px 0 0}
    .xp{position:relative;display:block;height:calc(100svh - 64px);min-height:440px;padding:0}
    .xp-map{position:absolute;inset:0}
    .xp .map-box{height:100%;border-radius:0}
    .xp #map{height:100%}
    .xp .map-note{display:none}
    .xp .map-card{top:auto;bottom:160px;left:10px;right:10px;max-width:none;transition:bottom .25s ease}
    .xp-list.dragging~.xp-map .map-card{transition:none}
    .xp-list{position:absolute;left:0;right:0;bottom:0;z-index:600;height:150px;display:flex;flex-direction:column;
      background:var(--white);border-radius:16px 16px 12px 12px;box-shadow:0 -4px 18px rgba(0,0,0,.18);transition:height .25s ease}
    .xp-list.dragging{transition:none}
    .sh-head{position:relative;flex:none;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:16px 14px 10px;touch-action:none;cursor:grab;-webkit-user-select:none;user-select:none}
    .sh-grab{display:block;position:absolute;top:6px;left:50%;width:38px;height:5px;margin-left:-19px;border-radius:3px;background:#c9cfd6}
    .sh-head h2{font-size:17px}
    .sh-btn{display:block;border:1px solid var(--line);background:var(--white);border-radius:100px;font:600 13px var(--sans);color:var(--lake);padding:6px 12px;cursor:pointer}
    .xp-list .lv-tabs{flex:none;margin:0 12px 8px}
    .xp-lv .xp-list{height:206px}
    .xp-lv .map-card{bottom:216px}
    .sh-body{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:0 12px 12px}
    .xp-list .xp-hint{display:none}
    .xp .leaflet-control-zoom{display:none}
  }
  @media(min-width:980px){
    .xp{grid-template-columns:minmax(0,400px) minmax(0,1fr);gap:24px;align-items:start}
    .xp-map{order:0;position:sticky;top:76px}
    .xp #map{height:calc(100vh - 150px);min-height:460px;max-height:820px}
  }
  @media(max-width:760px){
    .map-card{padding:12px 14px}
    .map-card a.mc-go{margin-top:8px;padding:7px 12px}
    #map{height:58vh}
    .map-box{border-radius:10px}
    .map-card{right:10px;max-width:none}
  }
"""

# phones: take over links to an area (#area-...) so the browser doesn't jump into the list panel
HEAD_JS = """<script>
(function(){var h=location.hash;if(h.indexOf('#area-')===0&&window.innerWidth<980&&history.replaceState){
  window.__area=h;history.replaceState(null,'',location.pathname+location.search);}})();
</script>"""


def explorer(comms, groups, colors, pages, area_pages, *, list_title, hint, map_aria, map_note, zone=None, label_zoom=15, frame=None, levels=None):
    def link(c):
        return pages.get(c["n"])

    sec, ids = [], set()
    for k, label, cs, *lv in groups:
        gid = "area-" + slug(label) + (f"-{lv[0]}" if lv and "area-" + slug(label) in ids else "")
        ids.add(gid)
        homes = sum(c.get("homes") or 0 for c in cs)
        rows = []
        for c in cs:
            u = link(c)
            meta = " &middot; ".join(x for x in [f'{c["homes"]} homes' if c.get("homes") else "",
                                                  f'sold {c["r12"]} (12 mo)' if c.get("r12") else "",
                                                  c.get("note") or ""] if x) or "Condos &amp; townhomes"
            go = ""
            if c["n"] in pages:
                go = f'<a class="nr-go" href="{u}">Guide<span class="sr"> to {e(c["n"])}</span> &rarr;</a>'
            dot = f'<span class="dot" style="--ac:{c["c"]};margin-right:7px"></span>' if c.get("c") else ""
            rows.append(f'<li class="nr"><button type="button" class="nr-pick" data-n="{e(c["n"])}">'
                        f'<span class="nr-name">{dot}{e(c["n"])}</span><span class="nr-meta">{meta}</span></button>{go}</li>')
        guide = f'\n    <a class="ax-guide" href="{area_pages[k]}">{e(label)} area guide &rarr;</a>' if k in area_pages else ""
        sec.append(f'''<details class="ax" id="{gid}" data-a="{k}"{f' data-lv="{lv[0]}"' if lv else ""} style="--ac:{colors.get(k, "#64748b")}">
  <summary><span class="dot"></span><span class="ax-name">{e(label)}</span><span class="ax-n">{len(cs)}</span><svg class="ax-chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
  <div class="ax-body">
    <ul class="nr-list">{"".join(rows)}</ul>{guide}
  </div>
</details>''')

    mdata = {"c": [{"n": c["n"], "a": c["sub"], "h": c.get("homes"), "u": link(c), "g": c["n"] in pages, "m": c.get("r12"), "p": c["p"],
                    "s": "n-" + slug(c["n"]),
                    **{k: c[k] for k in ("c", "hu", "gu", "gl", "x", "l", "lp", "v") if c.get(k) is not None}} for c in comms],
             "areas": {g[0]: [g[1], colors.get(g[0]), area_pages.get(g[0])] for g in groups}}
    if levels:
        mdata["lv"] = levels
    if zone:
        mdata["z"] = zone
    mdata["lz"] = label_zoom
    if frame:
        mdata["fb"] = frame  # [[south, west], [north, east]]: what the map frames at first

    def lv_count(k):
        return sum(len(g[2]) for g in groups if g[3:] and g[3] == k)
    tabs = ('\n      <div class="lv-tabs" role="tablist" aria-label="School level">' + "".join(
        f'<button type="button" role="tab" data-lv="{k}" aria-selected="{"true" if i == 0 else "false"}">{e(l)}<small>{lv_count(k)} school{"s" if lv_count(k) != 1 else ""}</small></button>'
        for i, (k, l) in enumerate(levels)) + "</div>") if levels else ""
    body = f'''<section class="map-sec" id="map-section">
  <div class="wrap xp{' xp-lv' if levels else ''}">
    <div class="xp-list" id="areas">
      <div class="sh-head" id="shHead"><span class="sh-grab" aria-hidden="true"></span>
        <h2>{e(list_title)}</h2>
        <button type="button" class="sh-btn" id="shBtn" aria-controls="areas" aria-expanded="false">Show list</button>
      </div>{tabs}
      <div class="sh-body">
      <p class="xp-hint">{hint}</p>
{chr(10).join(sec)}
      </div>
    </div>
    <div class="xp-map">
      <div class="map-box">
        <div id="map" class="sat" role="region" aria-label="{e(map_aria)}"></div>
        <div class="map-views" role="group" aria-label="Map view"><button type="button" data-b="sat" aria-pressed="true">Satellite</button><button type="button" data-b="map" aria-pressed="false">Map</button></div>
        <div class="map-card" id="mcard" aria-live="polite"></div>
      </div>
      <p class="map-note">{map_note}</p>
    </div>
  </div>
</section>'''

    js = '''<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" integrity="sha384-NElt3Op+9NBMCYaef5HxeJmU4Xeard/Lku8ek6hoPTvYkQPh3zLIrJP7KiRocsxO" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
<script src="/assets/basemap.js"></script>
<script>
var HUB=''' + json.dumps(mdata, separators=(",", ":")) + ''';
(function(){
  var C=HUB.c, A=HUB.areas, sel=-1, area=null;
  var wide=window.matchMedia('(min-width:980px)');
  var XP=document.querySelector('.xp'), SH=document.getElementById('areas');
  // keep the area being shown clear of the pull-up panel on phones
  // phones: leave room for the Satellite/Map switch above, and the list panel plus the neighborhood card below
  function pad(p){if(wide.matches)return {padding:[p,p]};
    var c=window.card&&card.classList.contains('show')?card.offsetHeight+10:0;
    return {paddingTopLeft:[p,p+44],paddingBottomRight:[p,off()+hts()[state||'peek']+c+p]};}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]});}
  var map=L.map('map',{scrollWheelZoom:false,zoomSnap:wide.matches?0.5:0.1}).setView([32.94,-117.22],13);
  var cur='sat', BM=CVBase(map);
  CVBase.bind(BM,document.querySelector('.map-views'),function(k){cur=k;
    document.getElementById('map').classList.toggle('sat',k==='sat');style();});
  // school pages: shade everything outside the attendance boundary and outline it
  var zone=null;
  if(HUB.z){map.createPane('zone');map.getPane('zone').style.zIndex=390;map.getPane('zone').style.pointerEvents='none';
    L.polygon([[[85,-180],[85,180],[-85,180],[-85,-180]]].concat(HUB.z),{pane:'zone',stroke:false,fillColor:'#0e1a24',fillOpacity:.5,interactive:false}).addTo(map);
    zone=L.polygon(HUB.z,{pane:'zone',fill:false,weight:3,dashArray:'8 6',interactive:false}).addTo(map);}
  // school levels: only one level's zones are on the map at a time
  var lv=HUB.lv?HUB.lv[0][0]:null;function inLv(i){return !lv||C[i].v===lv;}
  var layers=C.map(function(o,i){var l=L.polygon(o.p,{weight:1.5});if(inLv(i))l.addTo(map);
    l.on('click',function(e){L.DomEvent.stopPropagation(e);pick(i,false);});
    l.bindTooltip(o.n,{sticky:true,direction:'top'});return l;});
  var all=L.latLngBounds([]);if(HUB.fb)all=L.latLngBounds(HUB.fb);else if(zone)all.extend(zone.getBounds());else layers.forEach(function(l){all.extend(l.getBounds());});
  // phones: fill the screen width with the neighborhoods (fine zoom steps, slim side margins)
  function fitAll(){map.invalidateSize();map.fitBounds(all,pad(wide.matches?16:6));}
  var touched=false;map.getContainer().addEventListener('pointerdown',function(){touched=true;});
  // has the visitor panned or zoomed the map themselves? then leave their view alone
  var userMoved=false;map.on('dragstart',function(){userMoved=true;});
  map.getContainer().addEventListener('touchstart',function(e){if(e.touches.length>1)userMoved=true;},{passive:true});
  map.on('dblclick',function(){userMoved=true;});
  var boot=false;
  fitAll();window.addEventListener('load',function(){if(!area&&sel<0)fitAll();});
  var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){if(!touched&&!area&&sel<0)fitAll();else map.invalidateSize();},150);});
  var lbl=L.layerGroup().addTo(map);
  function style(){var sat=cur==='sat';if(zone)zone.setStyle({color:sat?'#fff':'#0b5c8c'});
    layers.forEach(function(l,i){var o=C[i],c=o.c||A[o.a][1],dim=area&&o.a!==area,on=i===sel;
    l.setStyle({color:on?'#101418':(sat?'#fff':c),weight:on?3:1.5,fillColor:c,fillOpacity:dim?0.06:(on?0.75:(sat?0.45:0.38)),opacity:dim?0.3:1});});}
  function labels(){lbl.clearLayers();if(map.getZoom()<(HUB.lz||15))return;var b=map.getBounds();
    C.forEach(function(o,i){if(area&&o.a!==area||!inLv(i))return;var c=o.lp?L.latLng(o.lp):layers[i].getBounds().getCenter();if(!b.contains(c))return;
      lbl.addLayer(L.tooltip({permanent:true,direction:'center',className:'lbl',interactive:false}).setLatLng(c).setContent(esc(o.l||o.n)));});}
  map.on('zoomend moveend',labels);
  var card=window.card=document.getElementById('mcard');
  function pick(i,zoom){touched=true;sel=i;var o=C[i];style();
    // neighborhoods with a page: one button per section of it (live listings first, then the guide)
    // no page of its own yet: both buttons go to its area's page (listings, and the neighborhood's row there)
    var ap=A[o.a][2],
      home=o.hu!==undefined?o.hu:o.u?o.u+'#listings':ap?ap+'#listings':'',
      guide=o.gu!==undefined?o.gu:o.g?o.u+'#location':ap?ap+'#'+o.s:'';
    var go=home?'<div class="mc-acts"><a class="mc-go" href="'+home+'">See homes &rarr;</a>'+(guide?'<a class="mc-go mc-alt" href="'+guide+'">'+(o.gl||'Community guide')+'</a>':'')+'</div>'
      :'<a class="mc-go" href="#contact">Ask about '+esc(o.n)+'</a>';
    card.innerHTML='<button type="button" class="mc-x" aria-label="Close">&times;</button><h3>'+esc(o.n)+'</h3><div class="mc-area"><span class="dot" style="--ac:'+(o.c||A[o.a][1])+'"></span>'+esc(o.x||A[o.a][0])+'</div>'+(o.h||o.m?'<div class="mc-homes">'+(o.h?'<b>'+o.h+'</b> homes':'')+(o.h&&o.m?' &middot; ':'')+(o.m?'sold <b>'+o.m+'</b> (12 mo)':'')+'</div>':'')+go;
    card.classList.add('show');card.querySelector('.mc-x').onclick=function(){card.classList.remove('show');sel=-1;style();};
    if(zoom)map.flyToBounds(layers[i].getBounds(),Object.assign({maxZoom:16,duration:.6},pad(40)));}
  map.on('click',function(){card.classList.remove('show');sel=-1;style();});
  var AX=Array.prototype.slice.call(document.querySelectorAll('.ax')), quiet=false;
  var PICKS=Array.prototype.slice.call(document.querySelectorAll('.nr-pick'));
  function rowFor(i){for(var k=0;k<PICKS.length;k++)if(PICKS[k].dataset.n===C[i].n)return PICKS[k];return null;}
  function mark(i){document.querySelectorAll('.nr.on').forEach(function(r){r.classList.remove('on');});
    var b=i>=0&&rowFor(i);if(b)b.parentNode.classList.add('on');return b;}
  function setArea(k,fly){touched=true;area=k;card.classList.remove('show');sel=-1;mark(-1);style();labels();
    if(fly){var b=L.latLngBounds([]);layers.forEach(function(l,i){if(!area||C[i].a===area)b.extend(l.getBounds());});
      if(boot)map.fitBounds(b,pad(20));else map.flyToBounds(b,Object.assign({duration:.6},pad(20)));}}
  AX.forEach(function(d){d.addEventListener('toggle',function(){
    if(quiet||d._code)return;
    if(d.open){quiet=true;AX.forEach(function(o){if(o!==d)o.open=false;});quiet=false;setArea(d.dataset.a,true);}
    else if(area===d.dataset.a){setArea(null,false);fitAll();}});});
  // map click on a neighborhood: open its area in the list and highlight the row
  var pick0=pick;pick=function(i,zoom){
    var d=document.querySelector('.ax[data-a="'+C[i].a+'"]');
    if(d&&!d.open){AX.forEach(function(o){if(o.open!==(o===d)){o._code=true;o.open=o===d;}});area=C[i].a;labels();}
    pick0(i,zoom);var b=mark(i);
    if(b&&!zoom&&wide.matches)b.scrollIntoView({block:'nearest',behavior:'smooth'});};
  document.querySelectorAll('.nr-pick').forEach(function(b){
    var i=C.findIndex(function(o){return o.n===b.dataset.n;});if(i<0)return;
    b.addEventListener('click',function(){if(!wide.matches)snap('peek');pick(i,true);});
    b.addEventListener('mouseenter',function(){if(sel<0){layers[i].setStyle({color:'#101418',weight:3,fillOpacity:.7});}});
    b.addEventListener('mouseleave',function(){if(sel<0)style();});});
  map.on('click',function(){mark(-1);});
  // ---- phone pull-up panel: peek / half / full ----
  function place(h){card.style.bottom=(off()+h+10)+'px';card.style.visibility=h>XP.clientHeight*.7?'hidden':'';}
  var head=document.getElementById('shHead'), btn=document.getElementById('shBtn'), state='peek';
  function off(){return wide.matches?0:Math.max(0,Math.round(XP.getBoundingClientRect().top));}
  function hts(){var H=XP.clientHeight-off();return {peek:HUB.lv?206:150,half:Math.round(H*.55),full:H-8};}
  function snap(st){if(wide.matches){SH.style.height='';card.style.bottom='';return;}state=st;SH.style.height=hts()[st]+'px';place(hts()[st]);
    btn.textContent=st==='full'?'Show map':'Show list';btn.setAttribute('aria-expanded',st==='peek'?'false':'true');}
  btn.addEventListener('click',function(e){e.stopPropagation();snap(state==='full'?'peek':'full');});
  var y0=null,h0=0,moved=false,dragDown=0;
  head.addEventListener('pointerdown',function(e){if(wide.matches||e.target===btn)return;y0=e.clientY;h0=SH.offsetHeight;moved=false;
    SH.classList.add('dragging');head.setPointerCapture(e.pointerId);});
  head.addEventListener('pointermove',function(e){if(y0===null)return;var dy=y0-e.clientY;if(Math.abs(dy)>4)moved=true;dragDown=-dy;
    var t=hts(),nh=Math.max(t.peek,Math.min(t.full,h0+dy));SH.style.height=nh+'px';place(nh);});
  function end(){if(y0===null)return;y0=null;SH.classList.remove('dragging');var t=hts(),h=SH.offsetHeight;
    if(!moved){snap(state==='peek'?'half':state==='half'?'full':'peek');return;}
    if(state==='peek'&&h0-h<=0&&dragDown>50){snap('peek');toTitle();return;}
    var best='peek';['peek','half','full'].forEach(function(k){if(Math.abs(t[k]-h)<Math.abs(t[best]-h))best=k;});snap(best);}
  head.addEventListener('pointerup',end);head.addEventListener('pointercancel',end);
  // opening an area raises the panel halfway so its neighborhoods show with the map above
  var body=SH.querySelector('.sh-body');
  function toTop(el){body.scrollTo({top:Math.max(0,el.offsetTop-body.offsetTop-4),behavior:'smooth'});}
  AX.forEach(function(d){d.addEventListener('toggle',function(){if(!d.open||wide.matches||d._code)return;
    if(state==='peek'&&!quiet)snap('half');setTimeout(function(){toTop(d);},30);});});
  wide.addEventListener&&wide.addEventListener('change',function(){snap(wide.matches?state:'peek');map.invalidateSize();});
  // phones: the map fills the screen between the title and the bottom menu
  function fit(){if(wide.matches){XP.style.height='';return;}var nav=document.querySelector('.bottom-nav');
    var top=XP.getBoundingClientRect().top+window.scrollY,nh=nav?nav.offsetHeight:0;
    XP.style.height=Math.max(440,window.innerHeight-nh)+'px';map.invalidateSize();}
  // phones: the title scrolls away and the map takes the whole screen.
  // Touching the map or the list, or a scroll that stops part-way, settles the page on the map.
  function xpTop(){return XP.getBoundingClientRect().top+window.scrollY;}
  function toMap(){if(wide.matches)return;var t=xpTop();if(window.scrollY<t-2)window.scrollTo({top:t,behavior:boot?'auto':'smooth'});}
  function toTitle(){if(wide.matches)return;if(window.__showMasthead)window.__showMasthead();window.scrollTo({top:0,behavior:'smooth'});}
  map.getContainer().addEventListener('pointerdown',toMap);
  head.addEventListener('pointerdown',function(){if(state!=='peek')toMap();});
  AX.forEach(function(d){d.addEventListener('toggle',function(){if(d.open&&!d._code)toMap();});});
  // registered last: clear the "changed in code" mark once every toggle listener has seen it
  AX.forEach(function(d){d.addEventListener('toggle',function(){d._code=false;});});
  // until the page settles on the map, keep the panel in view above the bottom menu
  function lift(){if(wide.matches)return;SH.style.bottom=off()+'px';if(state==='full')SH.style.height=hts().full+'px';place(SH.offsetHeight);}
  lift();
  var lastY=window.scrollY,down=true,se;
  window.addEventListener('scroll',function(){lift();var y=window.scrollY;if(y!==lastY)down=y>lastY;lastY=y;
    clearTimeout(se);se=setTimeout(function(){if(wide.matches||boot)return;var t=xpTop(),y=window.scrollY;
      if(y>4&&y<t-2){(down?toMap:toTitle)();return;}
      // settled: the map changed size on screen, so center all the neighborhoods again
      if(!userMoved&&!area&&sel<0)fitAll();},140);},{passive:true});
  fit();window.addEventListener('resize',function(){fit();snap(state);});
  snap('peek');
  // frame the neighborhoods again now that the map and panel have their final sizes
  function refit(){if(!userMoved&&!area&&sel<0)fitAll();}
  refit();setTimeout(refit,400);window.addEventListener('load',function(){setTimeout(refit,100);});
  // open the area named in the URL (#area-...)
  var hh=window.__area||location.hash, h=hh&&document.getElementById(decodeURIComponent(hh.slice(1)));
  // an area named in the link opens straight away, without animation;
  // on phones the page settles on the full map (not on the area inside the panel)
  if(h&&h.classList.contains('ax')){boot=true;h.open=true;
    var settle=function(){if(!wide.matches){window.scrollTo(0,xpTop());lift();}
      if(area)setArea(area,true);};
    window.addEventListener('load',function(){settle();setTimeout(function(){settle();boot=false;
      if(window.__area)history.replaceState(null,'',location.pathname+location.search+window.__area);},400);});}
  // level switch (in the list): swap the zones and the district groups shown.
  // A tap shows that level's zones; a level with one district opens it so its schools show at once.
  var LT=document.querySelector('.lv-tabs');
  function setLv(v,tap){lv=v;card.classList.remove('show');sel=-1;area=null;mark(-1);
    layers.forEach(function(l,i){if(inLv(i))l.addTo(map);else map.removeLayer(l);});
    var shown=[];AX.forEach(function(d){var on=d.dataset.lv===v;if(d.open&&(tap||!on)){d._code=true;d.open=false;}d.hidden=!on;if(on)shown.push(d);});
    if(LT)LT.querySelectorAll('button').forEach(function(b){b.setAttribute('aria-selected',b.dataset.lv===v?'true':'false');});
    style();labels();if(!tap)return;
    body.scrollTop=0;
    if(shown.length===1)setTimeout(function(){shown[0]._code=false;shown[0].open=true;},0);
    else{if(!wide.matches&&state==='peek')snap('half');var b=L.latLngBounds([]);layers.forEach(function(l,i){if(inLv(i))b.extend(l.getBounds());});
      map.flyToBounds(b,Object.assign({duration:.6},pad(20)));}}
  if(LT){LT.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(e){e.stopPropagation();setLv(b.dataset.lv,true);});});
    setLv(lv);}
  style();
})();
</script>'''
    return {"css": CSS, "html": body, "js": js, "head_js": HEAD_JS}
