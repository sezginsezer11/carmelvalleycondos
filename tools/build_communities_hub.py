#!/usr/bin/env python3
"""Build the public communities hub: /carmel-valley-communities/.

    python3 tools/build_communities_hub.py

Inputs
- community-atlas/index.html   the DATA line (boundaries, areas, home counts) from tools/build_atlas.py
- tools/hub_communities.json   which communities appear (condos & townhomes), area text, links, photos
- tools/community-template.html  site CSS, masthead, contact block and footer (so the look stays in sync)
Run tools/build_atlas.py first when the map changes, and tools/build_llm_files.py after. Stdlib only.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = "/carmel-valley-communities/"
OUT = os.path.join(ROOT, "carmel-valley-communities", "index.html")
SITE = "https://carmelvalleycondos.com"
HERO = "/images/carmel-valley-condos-townhomes-san-diego.jpg"
COLORS = {"n": "#0d8f84", "s": "#1456e8", "cch": "#c27a0e", "phr": "#e0691c", "tdm": "#3f9a2a",
          "th": "#d0346f", "dmm": "#7a4ce0", "rp": "#64748b"}
SHORT = {"n": "North of Del Mar Hts Rd", "s": "South of Del Mar Hts Rd"}

e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load():
    atlas = open(os.path.join(ROOT, "community-atlas", "index.html"), encoding="utf-8").read()
    data = json.loads(re.search(r"var DATA=(\{.*?\});\n", atlas, re.S).group(1))
    hub = json.load(open(os.path.join(ROOT, "tools", "hub_communities.json"), encoding="utf-8"))
    tpl = open(os.path.join(ROOT, "tools", "community-template.html"), encoding="utf-8").read()
    return data, hub, tpl


def main():
    data, hub, tpl = load()
    by_name = {c["n"]: c for c in data["c"]}
    missing = [n for n in hub["communities"] if n not in by_name]
    if missing:
        raise SystemExit("Not on the map (check spelling in tools/hub_communities.json): " + ", ".join(missing))
    areas = [(k, l) for k, l in data["subs"]]
    comms = [by_name[n] for n in hub["communities"]]
    pages, ext, photos, atext = hub.get("pages", {}), hub.get("ext", {}), hub.get("photos", {}), hub.get("areas", {})
    groups = [(k, l, sorted((c for c in comms if c.get("sub") == k), key=lambda c: c["n"])) for k, l in areas]
    groups = [g for g in groups if g[2]]
    total_homes = sum(c.get("homes") or 0 for c in comms)
    homes_floor = f"{total_homes // 100 * 100:,}"  # some communities have no count, so show "5,700+"

    def link(c):
        return pages.get(c["n"]) or ext.get(c["n"])

    # ---------- area sections (static, crawlable) ----------
    sec = []
    for k, label, cs in groups:
        homes = sum(c.get("homes") or 0 for c in cs)
        cards = []
        for c in cs:
            u = link(c)
            ph = photos.get(c["n"])
            img = (f'<img src="{ph}" alt="{e(c["n"])} in Carmel Valley" loading="lazy" width="320" height="200">'
                   if ph else f'<div class="cc-ph" aria-hidden="true">{e(c["n"][:1])}</div>')
            meta = f'{c["homes"]} homes' if c.get("homes") else "Condos &amp; townhomes"
            cta = ""
            if c["n"] in pages:
                cta = '<span class="cc-cta">Community guide &rarr;</span>'
            elif u:
                cta = '<span class="cc-cta">See homes &rarr;</span>'
            inner = (f'{img}<div class="cc-body"><h4>{e(c["n"])}</h4><div class="cc-meta">{meta}</div>'
                     f'<button type="button" class="cc-map" data-n="{e(c["n"])}">Show on map</button>{cta}</div>')
            if u:
                cards.append(f'<li class="cc"><a class="cc-link" href="{u}"><span class="sr">{e(c["n"])}</span></a>{inner}</li>')
            else:
                cards.append(f'<li class="cc">{inner}</li>')
        sec.append(f'''<section class="area" id="area-{slug(label)}" style="--ac:{COLORS.get(k, "#64748b")}">
  <div class="wrap">
    <div class="area-head">
      <h3><span class="dot"></span>{e(label)}</h3>
      <div class="area-stats">{len(cs)} communit{"y" if len(cs) == 1 else "ies"}{f" &middot; {homes:,} homes" if homes else ""}</div>
    </div>
    <p class="area-text">{e(atext.get(k, ""))}</p>
    <ul class="cc-grid">
      {"".join(cards)}
    </ul>
  </div>
</section>''')

    chips = "".join(
        f'<a class="chip" href="#area-{slug(l)}" data-a="{k}" style="--ac:{COLORS.get(k)}"><span class="dot"></span>{e(SHORT.get(k, l))} <b>{len(cs)}</b></a>'
        for k, l, cs in groups)

    # ---------- FAQ ----------
    biggest = max(groups, key=lambda g: len(g[2]))
    n_big = len(biggest[2])
    largest = sorted((c for c in comms if c.get("homes")), key=lambda c: -c["homes"])[:3]
    faqs = [
        ("How many condo and townhome communities are in Carmel Valley?",
         f"This map shows {len(comms)} condo and townhome communities in Carmel Valley (San Diego, 92130), with more than "
         f"{homes_floor} homes between them. They are spread across {len(groups)} areas, and {n_big} of them are {biggest[1][0].lower() + biggest[1][1:]}."),
        ("Which part of Carmel Valley has the most condos?",
         f"{biggest[1]}. It has {n_big} of the {len(comms)} condo and townhome communities on this map, so it usually has the most listings "
         "and the widest range of sizes and prices."),
        ("What are the largest condo communities in Carmel Valley?",
         "By number of homes, the largest are " + ", ".join(f"{c['n']} ({c['homes']} homes)" for c in largest) +
         ". Bigger communities tend to have more sales each year, which makes prices easier to compare."),
        ("Are there newer condos and townhomes in Carmel Valley?",
         "Yes. Pacific Highlands Ranch, in the east of Carmel Valley, was built out from the 2000s onward, so its attached homes are newer. "
         "Many communities there carry a Mello-Roos tax on top of the HOA fee, so compare the full monthly cost."),
        ("How do I find out what is for sale in a specific community?",
         "Tap the community on the map or its card below. Where we have a community guide, it shows live listings, recent sales, "
         "HOA details and schools. For any other community, call or email Sez Sezer for current listings and recent sales."),
    ]
    faq_html = "\n".join(f'      <details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faqs)

    # ---------- JSON-LD ----------
    ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Carmel Valley Condo & Townhome Communities",
         "url": SITE + PATH, "about": {"@type": "Place", "name": "Carmel Valley, San Diego, CA 92130"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(comms), "itemListElement": [
             dict({"@type": "ListItem", "position": i + 1, "name": c["n"]},
                  **({"url": SITE + pages[c["n"]]} if c["n"] in pages else {}))
             for i, c in enumerate(c for _, _, cs in groups for c in cs)]}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Carmel Valley Communities", "item": SITE + PATH}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]
    jsonld = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)

    # ---------- map data ----------
    mdata = {"c": [{"n": c["n"], "a": c["sub"], "h": c.get("homes"), "u": link(c), "g": c["n"] in pages, "p": c["p"]} for c in comms],
             "areas": {k: [l, COLORS.get(k)] for k, l, _ in groups}}

    # ---------- shell from the community template ----------
    css = re.search(r"<style>(.*?)</style>", tpl, re.S).group(1)
    masthead = tpl[tpl.index("<!-- ============ PRIMARY NAVIGATION"):tpl.index("</header>") + len("</header>")]
    contact_footer = tpl[tpl.index("<!-- ============ CONTACT BLOCK"):tpl.index("</footer>") + len("</footer>")]
    contact_footer = contact_footer.replace("{{name}}", "a Carmel Valley Condo or Townhome").replace(
        "{{contact_lead}}", "Tell me what matters to you (size, budget, schools, commute) and I&rsquo;ll point you to the communities that fit, with current listings and recent sales for each.")
    hide_js = tpl[tpl.rindex("<script>"):tpl.rindex("</script>") + len("</script>")]

    title = "Carmel Valley Condo & Townhome Communities: Map by Area"
    desc = f"Map of all {len(comms)} Carmel Valley condo and townhome communities by area, with home counts and links to community guides. San Diego 92130."
    assert len(desc) <= 155, len(desc)

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{PATH}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Carmel Valley Condos">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE}{PATH}">
<meta property="og:image" content="{SITE}{HERO}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="text/markdown" href="{SITE}{PATH}index.md">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500;600&display=swap" media="print" onload="this.media='all'">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>{css}
  /* ============ COMMUNITIES HUB ============ */
  .sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
  .hub-intro{{padding:40px 0 8px;text-align:center}}
  .hub-intro .eyebrow{{display:inline-block;font-size:12.5px;color:var(--lake);background:#eaf0fe;padding:5px 14px;border-radius:100px;font-weight:700;margin-bottom:14px}}
  .hub-intro h1{{font-size:clamp(28px,4.4vw,44px);font-weight:800;line-height:1.12;letter-spacing:-.02em;max-width:820px;margin:0 auto}}
  .hub-intro p{{max-width:680px;margin:14px auto 0;color:var(--label);font-size:16px}}
  .hub-stats{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:20px}}
  .hub-stats div{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:14px;color:var(--label)}}
  .hub-stats b{{color:var(--ink);font-size:16px;margin-right:4px}}
  .map-sec{{padding:24px 0 8px}}
  .chips{{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:14px}}
  .chip{{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);background:var(--white);color:var(--ink);font-size:13.5px;font-weight:600;padding:7px 12px;border-radius:100px;cursor:pointer}}
  .chip:hover{{border-color:var(--ac);color:var(--ink)}}
  .chip b{{color:var(--label);font-weight:600}}
  .chip.on{{background:var(--ac);border-color:var(--ac);color:#fff}}
  .chip.on b{{color:rgba(255,255,255,.85)}}
  .chip.on .dot{{background:#fff}}
  .dot{{width:10px;height:10px;border-radius:50%;background:var(--ac);flex:none;display:inline-block}}
  .map-box{{position:relative;z-index:0;isolation:isolate;max-width:1100px;margin:0 auto;border:1px solid var(--line);border-radius:14px;overflow:hidden}}
  #map{{height:min(64vh,560px);background:#e8ecef}}
  .map-views{{position:absolute;top:10px;right:10px;z-index:500;display:flex;background:#fff;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.18);overflow:hidden}}
  .map-views button{{border:0;background:#fff;font:600 12.5px var(--sans);padding:7px 11px;cursor:pointer;color:#37404a}}
  .map-views button[aria-pressed="true"]{{background:var(--lake);color:#fff}}
  .map-card{{position:absolute;left:10px;bottom:10px;z-index:500;background:#fff;border-radius:12px;box-shadow:0 4px 18px rgba(0,0,0,.18);padding:14px 16px;max-width:300px;display:none}}
  .map-card.show{{display:block}}
  .map-card h3{{font-size:17px;font-weight:800;margin-right:22px}}
  .map-card .mc-area{{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--label);margin-top:4px}}
  .map-card .mc-homes{{font-size:14px;margin-top:6px}}
  .map-card a.mc-go{{display:inline-block;margin-top:10px;background:var(--lake);color:#fff;font-weight:600;font-size:13.5px;padding:8px 14px;border-radius:7px}}
  .map-card .mc-x{{position:absolute;top:8px;right:10px;border:0;background:none;font-size:20px;line-height:1;color:var(--label);cursor:pointer}}
  .map-note{{text-align:center;font-size:13px;color:var(--label);margin-top:10px}}
  .leaflet-container{{font-family:var(--sans)}}
  .leaflet-control-attribution{{font-size:9.5px!important}}
  .leaflet-tooltip.lbl{{background:none;border:0;box-shadow:none;padding:0;color:#101418;font-weight:700;font-size:11.5px;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 2px #fff;white-space:nowrap}}
  .leaflet-tooltip.lbl::before{{display:none}}
  .sat .leaflet-tooltip.lbl{{color:#fff;text-shadow:0 0 3px #000,0 0 3px #000,0 0 2px #000}}
  .areas-wrap{{padding:32px 0 8px}}
  .area{{padding:28px 0}}
  .area + .area{{border-top:1px solid var(--line)}}
  .area-head{{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}}
  .area-head h3{{display:flex;align-items:center;gap:10px;font-size:clamp(20px,2.6vw,26px);font-weight:800;letter-spacing:-.01em}}
  .area-head .dot{{width:14px;height:14px}}
  .area-stats{{font-size:14px;color:var(--label);font-weight:600}}
  .area-text{{margin:8px 0 18px;color:#333a42;font-size:15.5px;max-width:820px}}
  .cc-grid{{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}}
  .cc{{position:relative;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--white);display:flex;flex-direction:column}}
  .cc img,.cc-ph{{width:100%;aspect-ratio:16/10;object-fit:cover}}
  .cc-ph{{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--paper),var(--mist));color:var(--ac);font:700 34px var(--serif);border-bottom:3px solid var(--ac)}}
  .cc-body{{padding:12px 14px 14px;display:flex;flex-direction:column;gap:4px;flex:1}}
  .cc h4{{font-size:16px;font-weight:800}}
  .cc-meta{{font-size:13.5px;color:var(--label)}}
  .cc-cta{{font-size:13.5px;font-weight:700;color:var(--lake);margin-top:auto;padding-top:4px}}
  .cc-link{{position:absolute;inset:0;z-index:1}}
  .cc:has(.cc-link):hover{{border-color:var(--lake);box-shadow:0 4px 14px rgba(20,86,232,.12)}}
  .cc-map{{position:relative;z-index:2;align-self:flex-start;border:0;background:none;padding:0;font:600 12.5px var(--sans);color:var(--label);text-decoration:underline;cursor:pointer}}
  .cc-map:hover{{color:var(--lake)}}
  @media(max-width:760px){{
    .hub-intro{{padding:26px 0 0}}
    .hub-intro p{{font-size:15px}}
    .hub-stats{{gap:6px;flex-wrap:nowrap}}
    .hub-stats div{{padding:6px 9px;font-size:12.5px}}
    .hub-stats b{{font-size:14px;margin-right:3px}}
    .map-card{{padding:12px 14px}}
    .map-card a.mc-go{{margin-top:8px;padding:7px 12px}}
    #map{{height:58vh}}
    .chips{{flex-wrap:nowrap;overflow-x:auto;justify-content:flex-start;padding:0 2px 4px;scrollbar-width:none}}
    .chips::-webkit-scrollbar{{display:none}}
    .chip{{white-space:nowrap}}
    .map-box{{border-radius:10px}}
    .map-card{{right:10px;max-width:none}}
    .cc-grid{{grid-template-columns:1fr 1fr;gap:10px}}
    .cc h4{{font-size:14.5px}}
    .cc-body{{padding:10px 10px 12px}}
    .area{{padding:22px 0}}
  }}
</style>
</head>
<body>

{masthead}

<nav class="breadcrumb" aria-label="Breadcrumb">
  <div class="wrap"><a href="/">Home</a><span class="sep">/</span><span class="current">Carmel Valley Communities</span></div>
</nav>

<section class="hub-intro">
  <div class="wrap">
    <span class="eyebrow">Carmel Valley &middot; San Diego 92130</span>
    <h1>Carmel Valley Condo &amp; Townhome Communities</h1>
    <p>Every condo and townhome community in Carmel Valley on one map, grouped by area. Tap a community to see where it sits, how many homes it has, and where to learn more.</p>
    <div class="hub-stats"><div><b>{len(comms)}</b>communities</div><div><b>{homes_floor}+</b>homes</div><div><b>{len(groups)}</b>areas</div></div>
  </div>
</section>

<section class="map-sec" id="map-section">
  <div class="wrap">
    <div class="chips" id="chips">{chips}</div>
    <div class="map-box">
      <div id="map" role="region" aria-label="Map of Carmel Valley condo and townhome communities"></div>
      <div class="map-views" role="group" aria-label="Map view"><button type="button" data-b="map" aria-pressed="true">Map</button><button type="button" data-b="sat" aria-pressed="false">Satellite</button></div>
      <div class="map-card" id="mcard" aria-live="polite"></div>
    </div>
    <p class="map-note">Boundaries are approximate. Home counts are from the California Title Company community chart.</p>
  </div>
</section>

<div class="areas-wrap" id="areas">
<div class="wrap"><div class="sec-head" style="margin-bottom:8px"><h2>Communities by Area</h2><p>Each area has its own feel, prices and mix of homes. Start with the area, then compare the communities in it.</p></div></div>
{chr(10).join(sec)}
</div>

<section class="faq" id="faq">
  <div class="wrap">
    <div class="sec-head"><h2>Carmel Valley Communities: Common Questions</h2></div>
    <div class="faq-list">
{faq_html}
    </div>
  </div>
</section>

{contact_footer}

{jsonld}

<nav class="bottom-nav" aria-label="Jump to section">
  <a href="#map-section"><svg viewBox="0 0 24 24"><path d="M12 21s7-7.1 7-12a7 7 0 0 0-14 0c0 4.9 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>Map</a>
  <a href="#areas"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Areas</a>
  <a href="#faq"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.8-2.5 2-2.5 4"/><circle cx="12" cy="16.5" r=".6"/></svg>FAQ</a>
  <a href="#contact"><svg viewBox="0 0 24 24"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>Contact</a>
  <a href="#" class="bn-menu" onclick="event.preventDefault();window.__showMasthead&&window.__showMasthead();document.getElementById('pnav').classList.toggle('open')"><svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg>Menu</a>
</nav>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var HUB={json.dumps(mdata, separators=(",", ":"))};
(function(){{
  var C=HUB.c, A=HUB.areas, sel=-1, area=null;
  function esc(s){{return String(s).replace(/[&<>"]/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}});}}
  var map=L.map('map',{{scrollWheelZoom:false,zoomSnap:0.5}}).setView([32.94,-117.22],13);
  var ESRI='https://server.arcgisonline.com/ArcGIS/rest/services/';
  var base={{map:L.tileLayer(ESRI+'World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,attribution:'Map &copy; Esri, HERE, Garmin, OpenStreetMap contributors'}}),
    sat:L.layerGroup([L.tileLayer(ESRI+'World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,attribution:'Imagery &copy; Esri, Maxar, Earthstar Geographics'}}),
      L.tileLayer(ESRI+'Reference/World_Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19}})])}};
  var cur='map'; base.map.addTo(map);
  document.querySelectorAll('.map-views button').forEach(function(b){{b.addEventListener('click',function(){{
    map.removeLayer(base[cur]); cur=b.dataset.b; base[cur].addTo(map);
    document.getElementById('map').classList.toggle('sat',cur==='sat');
    document.querySelectorAll('.map-views button').forEach(function(x){{x.setAttribute('aria-pressed',x===b?'true':'false');}});
    style();}});}});
  var layers=C.map(function(o,i){{var l=L.polygon(o.p,{{weight:1.5}}).addTo(map);
    l.on('click',function(e){{L.DomEvent.stopPropagation(e);pick(i,false);}});
    l.bindTooltip(o.n,{{sticky:true,direction:'top'}});return l;}});
  var all=L.latLngBounds([]);layers.forEach(function(l){{all.extend(l.getBounds());}});
  function fitAll(){{map.invalidateSize();map.fitBounds(all,{{padding:[16,16]}});}}
  var touched=false;map.getContainer().addEventListener('pointerdown',function(){{touched=true;}});
  fitAll();window.addEventListener('load',fitAll);
  var rt;window.addEventListener('resize',function(){{clearTimeout(rt);rt=setTimeout(function(){{if(!touched&&!area&&sel<0)fitAll();else map.invalidateSize();}},150);}});
  var lbl=L.layerGroup().addTo(map);
  function style(){{var sat=cur==='sat';layers.forEach(function(l,i){{var o=C[i],c=A[o.a][1],dim=area&&o.a!==area,on=i===sel;
    l.setStyle({{color:on?'#101418':(sat?'#fff':c),weight:on?3:1.5,fillColor:c,fillOpacity:dim?0.06:(on?0.75:(sat?0.45:0.38)),opacity:dim?0.3:1}});}});}}
  function labels(){{lbl.clearLayers();if(map.getZoom()<15)return;var b=map.getBounds();
    C.forEach(function(o,i){{if(area&&o.a!==area)return;var c=layers[i].getBounds().getCenter();if(!b.contains(c))return;
      lbl.addLayer(L.tooltip({{permanent:true,direction:'center',className:'lbl',interactive:false}}).setLatLng(c).setContent(esc(o.n)));}});}}
  map.on('zoomend moveend',labels);
  var card=document.getElementById('mcard');
  function pick(i,zoom){{touched=true;sel=i;var o=C[i];style();
    var go=o.u?'<a class="mc-go" href="'+o.u+'">'+(o.g?'Community guide &rarr;':'See homes &rarr;')+'</a>':'<a class="mc-go" href="#contact">Ask about '+esc(o.n)+'</a>';
    card.innerHTML='<button type="button" class="mc-x" aria-label="Close">&times;</button><h3>'+esc(o.n)+'</h3><div class="mc-area"><span class="dot" style="--ac:'+A[o.a][1]+'"></span>'+esc(A[o.a][0])+'</div>'+(o.h?'<div class="mc-homes"><b>'+o.h+'</b> homes</div>':'')+go;
    card.classList.add('show');card.querySelector('.mc-x').onclick=function(){{card.classList.remove('show');sel=-1;style();}};
    if(zoom)map.flyToBounds(layers[i].getBounds(),{{maxZoom:16,duration:.6,padding:[40,40]}});}}
  map.on('click',function(){{card.classList.remove('show');sel=-1;style();}});
  function setArea(k){{touched=true;area=(area===k)?null:k;
    document.querySelectorAll('#chips .chip').forEach(function(c){{c.classList.toggle('on',c.dataset.a===area);}});
    var b=L.latLngBounds([]);layers.forEach(function(l,i){{if(!area||C[i].a===area)b.extend(l.getBounds());}});
    map.flyToBounds(b,{{padding:[20,20],duration:.6}});card.classList.remove('show');sel=-1;style();labels();}}
  document.querySelectorAll('#chips .chip').forEach(function(c){{c.addEventListener('click',function(e){{e.preventDefault();setArea(c.dataset.a);}});}});
  document.querySelectorAll('.cc-map').forEach(function(b){{b.addEventListener('click',function(){{
    var i=C.findIndex(function(o){{return o.n===b.dataset.n;}});if(i<0)return;
    if(area&&C[i].a!==area){{area=null;document.querySelectorAll('#chips .chip').forEach(function(c){{c.classList.remove('on');}});}}
    document.getElementById('map-section').scrollIntoView({{behavior:'smooth',block:'start'}});pick(i,true);}});}});
  style();
}})();
</script>
<script>
(function(){{
  var links=Array.prototype.slice.call(document.querySelectorAll('.bottom-nav a[href^="#"]')).filter(function(a){{return a.getAttribute('href').length>1&&document.getElementById(a.getAttribute('href').slice(1));}});
  if(!links.length||!('IntersectionObserver' in window))return;
  var io=new IntersectionObserver(function(es){{es.forEach(function(e){{if(!e.isIntersecting)return;
    links.forEach(function(a){{a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id);}});}});}},{{rootMargin:'-45% 0px -50% 0px'}});
  links.forEach(function(a){{io.observe(document.getElementById(a.getAttribute('href').slice(1)));}});
}})();
</script>
{hide_js}
</body>
</html>
'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(comms)} communities, {total_homes:,} homes, {len(groups)} areas, {len(page)//1024} KB")


if __name__ == "__main__":
    main()
