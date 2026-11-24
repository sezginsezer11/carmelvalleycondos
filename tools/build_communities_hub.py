#!/usr/bin/env python3
"""Build the home page: the directory of every Carmel Valley condo and townhome community.

    python3 tools/build_communities_hub.py

The SEO plan (~/seo-plan/plans/carmelvalleycondos.com.md, Option A, chosen 2026-11-23) makes the home page
a directory: title/H1/meta from the plan, map with an area list beside it (shared explorer), cards, how to choose, FAQ. The old
/carmel-valley-communities/ hub 301s here (see _redirects).

Inputs
- community-atlas/index.html   the DATA line (boundaries, areas, home counts) from tools/build_atlas.py
- tools/hub_communities.json   which communities appear (condos & townhomes), area text, links, photos
- tools/atlas_home_types.json  condo / townhome type per community
- tools/communities/*.json     verified year built, for communities with a guide
- tools/community-template.html  site CSS, masthead, contact block and footer (so the look stays in sync)
Run tools/build_atlas.py first when the map changes, and tools/build_llm_files.py after. Stdlib only.
"""
import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from explorer import explorer  # noqa: E402  (shared with carmelvalleyhomesforsale.com)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = "/"
OUT = os.path.join(ROOT, "index.html")
SITE = "https://www.carmelvalleycondos.com"
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


def verified_facts():
    """Year built from the community guides (MLS-verified). Other communities show a dash."""
    built = {}
    for f in glob.glob(os.path.join(ROOT, "tools", "communities", "*.json")):
        c = json.load(open(f, encoding="utf-8"))
        for fact in c.get("facts", []):
            if fact.get("icon") == "built":
                built[c["name"]] = html.unescape(fact["value"])
    return built


def main():
    data, hub, tpl = load()
    types = json.load(open(os.path.join(ROOT, "tools", "atlas_home_types.json"), encoding="utf-8"))
    built = verified_facts()
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
            img = (f'<img src="{ph}" alt="{e(c["n"])} in Carmel Valley" loading="lazy" width="320" height="200" sizes="(max-width: 460px) 92vw, 260px">'
                   if ph else f'<div class="cc-ph" aria-hidden="true">{e(c["n"][:1])}</div>')
            dt = "Detached condos" if hub.get("types", {}).get(c["n"]) == "detached" else ""
            meta = " &middot; ".join(s for s in [f'{c["homes"]} homes' if c.get("homes") else "", dt] if s) or "Condos &amp; townhomes"
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
        sec.append(f'''<section class="area" id="cards-{slug(label)}" style="--ac:{COLORS.get(k, "#64748b")}">
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

    # ---------- map explorer (same as carmelvalleyhomesforsale.com): area list beside the map ----------
    # Map card buttons: "See homes" and "Community guide".
    #   our guide:            See homes -> guide#listings, Community guide -> guide#location
    #   carmelvalley.com page: See homes -> that page,     second button -> Ask about (contact)
    #   neither:              See homes -> live listings full screen (#expand-map), second -> Ask about
    tname = {"condo": "Condo", "town": "Townhome", "detached": "Detached condo (single-family home)"}
    types.update({k: v for k, v in hub.get("types", {}).items() if not k.startswith("_")})
    xcomms = []
    for c in comms:
        n = c["n"]
        x = dict(c)
        t = tname.get(types.get(n))
        x["note"] = " &middot; ".join(s for s in [t or "", f"built {e(built[n])}" if n in built else ""] if s)
        if n in pages:
            x["hu"], x["gu"] = pages[n] + "#listings", pages[n] + "#location"
        else:
            x["hu"] = ext.get(n) or "#expand-map"
            x["gu"], x["gl"] = "#contact", "Ask about " + n
        xcomms.append(x)
    xgroups = [(k, l, [x for x in xcomms if x["sub"] == k and x["n"] in {c["n"] for c in cs}]) for k, l, cs in groups]
    xgroups = [(k, l, sorted(cs, key=lambda c: c["n"])) for k, l, cs in xgroups]
    xp = explorer(xcomms, xgroups, COLORS, pages, {}, list_title="Communities by Area",
                  hint="Every condo and townhome community in Carmel Valley, grouped by area. Open an area to see its communities, their type and how many homes each has, then tap one to find it on the map.",
                  map_aria="Map of Carmel Valley condo and townhome communities",
                  map_note="Boundaries are approximate. Home counts are from the California Title Company community chart. Year built is shown only where verified from MLS records.")

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
        ("Is there a list of every condo community in Carmel Valley?",
         f"Yes. The list beside the map on this page has all {len(comms)} condo and townhome communities in Carmel Valley, grouped by area, "
         "with their type and number of homes. Open an area, then tap a community to see it on the map."),
        ("How do I find out what is for sale in a specific community?",
         "Tap the community on the map, then See homes. Where we have a community guide, it shows live listings, recent sales, "
         "monthly dues and schools. For any other community, call or email Sez Sezer for current listings and recent sales."),
    ]
    faq_html = "\n".join(f'      <details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faqs)

    # ---------- JSON-LD ----------
    ld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": "Carmel Valley Condos", "url": SITE + "/"},
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Every Condo and Townhome Community in Carmel Valley",
         "url": SITE + PATH, "isPartOf": {"@type": "WebSite", "url": SITE + "/"},
         "about": {"@type": "Place", "name": "Carmel Valley, San Diego, CA 92130"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(comms), "itemListElement": [
             dict({"@type": "ListItem", "position": i + 1, "name": c["n"]},
                  **({"url": SITE + pages[c["n"]]} if c["n"] in pages else {}))
             for i, c in enumerate(c for _, _, cs in groups for c in cs)]}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"}]},
        {"@context": "https://schema.org", "@type": "RealEstateAgent", "name": "Sez Sezer",
         "image": SITE + "/images/sez-sezer-carmel-valley-realtor.jpg", "url": SITE + "/", "mainEntityOfPage": SITE + "/",
         "telephone": "+1-858-436-6585", "email": "sez@carmelvalley.com", "priceRange": "$$$",
         "description": "Real estate agent with Keller Williams Realty (DRE #01988197) specializing in Carmel Valley condo and townhome communities in San Diego, with more than 11 years of local experience.",
         "address": {"@type": "PostalAddress", "streetAddress": "12750 High Bluff Drive", "addressLocality": "San Diego",
                     "addressRegion": "CA", "postalCode": "92130", "addressCountry": "US"},
         "areaServed": {"@type": "Place", "name": "Carmel Valley, San Diego, CA 92130"},
         "memberOf": {"@type": "Organization", "name": "Keller Williams Realty"},
         "sameAs": ["https://www.carmelvalley.com/", "https://www.carmelvalleyhomesforsale.com/",
                    "https://www.homesforsaleinranchosantafe.com/"]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]},
    ]
    jsonld = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)

    # ---------- shell from the community template ----------
    css = re.search(r"<style>(.*?)</style>", tpl, re.S).group(1)
    masthead = tpl[tpl.index("<!-- ============ PRIMARY NAVIGATION"):tpl.index("</header>") + len("</header>")]
    contact_footer = tpl[tpl.index("<!-- ============ CONTACT BLOCK"):tpl.index("</footer>") + len("</footer>")]
    contact_footer = contact_footer.replace("{{name}}", "a Carmel Valley Condo or Townhome").replace(
        "{{contact_lead}}", "Tell me what matters to you (size, budget, schools, commute) and I&rsquo;ll point you to the communities that fit, with current listings and recent sales for each.")
    hide_js = tpl[tpl.rindex("<script>"):tpl.rindex("</script>") + len("</script>")]

    title = "Carmel Valley Condo & Townhome Communities (Directory)"
    desc = "A directory of every condo and townhome community in Carmel Valley, San Diego, with home counts and links to each community guide."
    assert len(title) <= 60 and len(desc) <= 155, (len(title), len(desc))
    listings = tpl[tpl.index('<section class="listings" id="listings"'):]
    listings = listings[:listings.index("</section>") + len("</section>")]
    listings = listings.replace('style="padding-top:12px;padding-bottom:16px"', 'style="padding:8px 0 24px"').replace(
        "{{name}} Homes for Sale Listings", "Carmel Valley Condo and Townhome Listings")

    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{PATH}">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
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
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" integrity="sha384-c6Rcwz4e4CITMbu/NBmnNS8yN2sC3cUElMEMfP3vqqKFp7GOYaaBBCqmaWBjmkjb" crossorigin="anonymous" referrerpolicy="no-referrer">
<link rel="stylesheet" href="/assets/rs-embed.css?v=3">
<script src="/assets/rs-embed.js?v=3" defer></script>
<style>{css}
  /* ============ HOME: DIRECTORY ============ */
  .hub-intro .lead-links{{max-width:680px;margin:10px auto 0;font-size:15px;color:var(--label)}}
  .hub-intro .lead-links a{{font-weight:600}}
  .choose{{padding:36px 0 8px}}
  .choose-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;max-width:1100px;margin:0 auto}}
  .choose-grid div{{background:var(--white);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
  .choose-grid h3{{font-size:16.5px;font-weight:800;margin-bottom:6px}}
  .choose-grid p{{font-size:15px;color:#333a42}}
  .choose .answer{{max-width:820px;margin:0 auto 18px;font-size:16px;color:#333a42}}
  /* ============ COMMUNITIES HUB ============ */
  .hub-intro{{padding:40px 0 8px;text-align:center}}
  .hub-intro .eyebrow{{display:inline-block;font-size:12.5px;color:var(--lake);background:#eaf0fe;padding:5px 14px;border-radius:100px;font-weight:700;margin-bottom:14px}}
  .hub-intro h1{{font-size:clamp(28px,4.4vw,44px);font-weight:800;line-height:1.12;letter-spacing:-.02em;max-width:820px;margin:0 auto}}
  .hub-intro p{{max-width:680px;margin:14px auto 0;color:var(--label);font-size:16px}}
  .hub-stats{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:20px}}
  .hub-stats div{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:14px;color:var(--label)}}
  .hub-stats b{{color:var(--ink);font-size:16px;margin-right:4px}}
{xp["css"]}
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
    .cc-grid{{grid-template-columns:1fr 1fr;gap:10px}}
    .cc h4{{font-size:14.5px}}
    .cc-body{{padding:10px 10px 12px}}
    .area{{padding:22px 0}}
  }}
</style>
{xp["head_js"]}
</head>
<body>

{masthead}

<section class="hub-intro">
  <div class="wrap">
    <span class="eyebrow">Carmel Valley &middot; San Diego 92130</span>
    <h1>Every Condo and Townhome Community in Carmel Valley</h1>
    <p data-speakable>Carmel Valley (San Diego, 92130) has {len(comms)} condo and townhome communities with more than {homes_floor} homes between them, spread across {len(groups)} areas. This directory shows each one on a map and in a list by area, with its type and number of homes, and links to a full guide where one exists.</p>
    <p class="lead-links">For everything currently on the market, browse <a href="https://www.carmelvalley.com/condos-for-sale/">Carmel Valley condos for sale</a> or <a href="https://www.carmelvalley.com/townhomes-for-sale/">Carmel Valley townhomes for sale</a>.</p>
    <div class="hub-stats"><div><b>{len(comms)}</b>communities</div><div><b>{homes_floor}+</b>homes</div><div><b>{len(groups)}</b>areas</div></div>
  </div>
</section>

{xp["html"]}

<div class="areas-wrap" id="communities">
<div class="wrap"><div class="sec-head" style="margin-bottom:8px"><h2>Carmel Valley Condo and Townhome Complexes by Area</h2><p>Each area has its own feel, prices and mix of homes. Start with the area, then compare the communities in it.</p></div></div>
{chr(10).join(sec)}
</div>

<section class="choose" id="choose">
  <div class="wrap">
    <div class="sec-head" style="margin-bottom:14px"><h2>How to Choose a Carmel Valley Condo Community</h2></div>
    <p class="answer">Start with location, then compare what you pay each month and what you get for it. Two homes at the same price can cost very different amounts to own once monthly dues and Mello-Roos are added, and a community&rsquo;s age, size and layout shape day-to-day life more than its name does.</p>
    <div class="choose-grid">
      <div><h3>Area and commute</h3><p>Communities south of Del Mar Heights Road are closest to the shops, offices and I-5/SR-56. Pacific Highlands Ranch is newer and further east; Torrey Hills sits near Sorrento Valley.</p></div>
      <div><h3>Condo or townhome</h3><p>Condos are often single-level with shared walls above or below. Townhomes usually have two or more levels, an attached garage and no one overhead.</p></div>
      <div><h3>Full monthly cost</h3><p>Add the monthly dues, any Mello-Roos tax and property tax to the mortgage. Newer communities often carry Mello-Roos; older ones may have lower dues but older systems.</p></div>
      <div><h3>Schools</h3><p>Most of Carmel Valley is in the Del Mar Union and San Dieguito Union districts, but school assignment depends on the address. Each community guide lists its schools.</p></div>
      <div><h3>Size and turnover</h3><p>Larger communities have more sales each year, so prices are easier to compare and there is more to choose from. Smaller ones come up less often.</p></div>
      <div><h3>Rules and amenities</h3><p>Pools, gyms, pet rules and rental limits differ by community. Ask for the HOA documents before you commit, and check the reserves.</p></div>
    </div>
  </div>
</section>

<section class="listings-head" style="padding:36px 0 0">
  <div class="wrap"><div class="sec-head" style="margin-bottom:12px"><h2>Condos and Townhomes on the Market Now</h2><p>Live MLS listings across Carmel Valley (92130). Tap to search full screen.</p></div></div>
</section>
{listings}

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
  <a href="#expand-map"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>Find Homes</a>
  <a href="#map-section"><svg viewBox="0 0 24 24"><path d="M12 21s7-7.1 7-12a7 7 0 0 0-14 0c0 4.9 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>Map</a>
  <a href="#communities"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>Communities</a>
  <a href="#contact"><svg viewBox="0 0 24 24"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>Contact</a>
  <a href="#" class="bn-menu" onclick="event.preventDefault();window.__showMasthead&&window.__showMasthead();document.getElementById('pnav').classList.toggle('open')"><svg viewBox="0 0 24 24"><path d="M3 6h18M3 12h18M3 18h18"/></svg>Menu</a>
</nav>

{xp["js"]}
<script>
// area cards: "Show on map" picks the community in the list beside the map
document.querySelectorAll('.cc-map').forEach(function(b){{b.addEventListener('click',function(){{
  var r=document.querySelector('.nr-pick[data-n="'+b.dataset.n.replace(/"/g,'\\"')+'"]');if(!r)return;
  document.getElementById('map-section').scrollIntoView({{behavior:'smooth',block:'start'}});setTimeout(function(){{r.click();}},350);}});}});
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
