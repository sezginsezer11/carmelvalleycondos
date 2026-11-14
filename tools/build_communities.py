#!/usr/bin/env python3
"""Build every community page from one shared template.

    tools/community-template.html      the page design (shared by all communities)
    tools/communities/<slug>.json      one data file per community
    -> /<path>/index.html               the generated page

Change the design once in the template, run this script, and every community
page picks it up:

    python3 tools/build_communities.py            # build all communities
    python3 tools/build_communities.py arborlake  # build one

Then run tools/build_llm_files.py so the Markdown copies, llms files and
sitemap stay in sync. Stdlib only.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SITE = "https://carmelvalleycondos.com"

FACT_ICONS = {
    "price": '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "hoa": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    "sqft": '<path d="M3 3h7v7H3zM14 14h7v7h-7z"/><path d="M10 3 21 14"/>',
    "units": '<path d="M3 21V9l6-4 6 4v12"/><path d="M15 21V11l6 2v8z"/>',
    "built": '<rect x="3" y="4" width="18" height="17" rx="1"/><path d="M3 9h18M8 2v4M16 2v4"/>',
    "mello": '<circle cx="12" cy="12" r="9"/><path d="M8 8l8 8"/>',
    "tax": '<circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M18 6 6 18"/>',
    "time": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 3.5"/>',
}
AMENITY_ICONS = {
    "lake": '<path d="M2 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0M2 13c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M12 9V3M9.5 5.5 12 3l2.5 2.5"/>',
    "pool": '<path d="M2 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M8 15V5a2 2 0 0 1 4 0M16 15V5a2 2 0 0 0-4 0M8 9h8"/>',
    "gym": '<path d="M6 7v10M18 7v10M3 9v6M21 9v6M6 12h12"/>',
    "tennis": '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6c3.5 3.5 3.5 9.3 0 12.8M18.4 5.6c-3.5 3.5-3.5 9.3 0 12.8"/>',
    "trees": '<path d="M12 22V12"/><path d="M7 12a5 5 0 1 1 10 0z"/><path d="M4 22h16"/>',
    "carport": '<path d="M3 10 12 4l9 6"/><path d="M5 10v10M19 10v10M3 20h18"/><rect x="8" y="13" width="8" height="4" rx="1"/>',
    "garage": '<path d="M3 21V9l9-6 9 6v12"/><path d="M7 21v-8h10v8M7 16h10"/>',
    "clubhouse": '<path d="M3 21h18M5 21V10l7-5 7 5v11"/><path d="M10 21v-5h4v5"/>',
    "bbq": '<path d="M5 9h14a7 7 0 0 1-14 0z"/><path d="M8 16l-2 5M16 16l2 5M9 3c0 1.5 1 2 1 3.5M13 3c0 1.5 1 2 1 3.5"/>',
    "water": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "path": '<path d="M4 20c4-1 4-6 8-7s4-6 8-7"/><circle cx="4" cy="20" r="1.5"/><circle cx="20" cy="6" r="1.5"/>',
}
ANALYSIS_TAB = ('      <button type="button" role="tab" id="tab-analysis" aria-controls="analysis" aria-selected="false" tabindex="-1">'
                '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>'
                '<path d="M14 3v6h6M8 13h8M8 17h5"/></svg>Analysis</button>')


def svg(d, attrs=' viewBox="0 0 24 24" aria-hidden="true"'):
    return f'<svg{attrs}>{d}</svg>'


def plain(s):
    """HTML snippet -> plain text (for meta and JSON-LD)."""
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def render_facts(c):
    out = []
    for f in c["facts"]:
        icon = svg(FACT_ICONS.get(f["icon"], FACT_ICONS["price"]), ' viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"')
        out.append(f'    <div class="fact">{icon}<div class="num">{f["value"]}</div><div class="lbl">{f["label"]}</div></div>')
    return "\n".join(out)


def render_schools(c):
    return "\n".join(
        f'        <li>\n          <div class="s-level">{s["level"]}</div>\n          <div class="s-name">{s["name"]}</div>\n'
        f'          <div class="s-district">{s["district"]}</div>\n        </li>' for s in c["schools"])


def render_nearby(c):
    return "\n".join(f'        <li><span>{p}</span><span>{d}</span></li>' for p, d in c["nearby"])


def render_glance_cards(c):
    out = []
    for g in c["glance"]["cards"]:
        b = g["beds"]
        out.append(f'''      <div class="glance-card" data-beds="{b}">
        <div class="gc-head"><h3>{b} Bedroom</h3><div class="gc-count" id="g{b}-count">{g["count"]}</div></div>
        <div class="glance-row"><span class="gr-lbl">Size</span><span class="gr-val" id="g{b}-size">{g["size"]}</span></div>
        <div class="glance-row"><span class="gr-lbl">Median sale price</span><span class="gr-val" id="g{b}-median">{g["median"]}</span></div>
        <div class="glance-row"><span class="gr-lbl">Price range</span><span class="gr-val" id="g{b}-range">{g["range"]}</span></div>
      </div>''')
    return "\n".join(out)


def render_glance_after(c):
    link = ' See the <a href="#analysis">full breakdown</a>.' if c.get("analysis") else ' See the <a href="#sold-data">price history</a>.'
    return f'<p class="glance-lede" style="margin-top:14px;margin-bottom:0"><span id="g-ratio">{c["glance"]["ratio"]}</span>{link}</p>'


def render_life(c):
    L = c["life"]
    reasons = "\n".join(f'      <li><strong>{t}</strong> {d}</li>' for t, d in L["reasons"])
    return f'''    <h2>Life at {c["name"]}</h2>
    <p class="lead">{L["lead"]}</p>
    <h3 class="life-sub">Why buyers choose {c["name"]}</h3>
    <ul class="reasons">
{reasons}
    </ul>'''


def render_hoa(c):
    h = c["hoa"]
    amen = "\n".join(f'          <li>{svg(AMENITY_ICONS[i])}<span>{t}</span></li>' for i, t in h["amenities"])
    rows = []
    for name, fee, width, this in h["compare"]:
        cls = "hoa-bar-row this-community" if this else "hoa-bar-row"
        rows.append(f'''        <div class="{cls}">
          <div class="hoa-bar-label"><span>{name}</span><span class="amt">{fee}</span></div>
          <div class="hoa-bar-track"><div class="hoa-bar-fill" style="width:{width}%"></div></div>
        </div>''')
    rows = "\n".join(rows)
    return f'''    <div class="sec-head">
      <div class="eyebrow">HOA</div>
      <h2>{c["name"]} HOA: Fee &amp; Amenities</h2>
      <p>{h["intro"]}</p>
    </div>
    <div class="hoa-fee">
      <div class="hf-amt">{h["fee"]}<span>/month</span></div>
      <div class="hf-text"><strong>HOA fee</strong> {h["fee_note"]}</div>
    </div>
    <div class="hoa-grid">
      <div>
        <h3 class="hoa-h">Amenities included</h3>
        <ul class="amen-grid">
{amen}
        </ul>
        <p class="hoa-also"><strong>Also covered:</strong> {h["also"]}</p>
      </div>
      <div class="hoa-compare">
        <h3>How {c["name"]}'s HOA Compares</h3>
{rows}
        <p style="margin-top:20px;font-size:13.5px;color:#7a8389">{h["compare_note"]}</p>
      </div>
    </div>'''


def render_similar(c):
    out = []
    for k in c["similar"]["cards"]:
        if k.get("img"):
            img = f'<div class="cmp-img"><img src="{k["img"]}" alt="{k["alt"]}" loading="lazy"></div>'
        else:
            img = f'<div class="cmp-img ph" aria-hidden="true">{k["name"]}</div>'
        out.append(f'''        <a class="cmp-card" href="{k["href"]}">
          {img}
          <div class="cmp-body">
            <h3>{k["name"]}</h3>
            <div class="cmp-meta">{k["meta"]}</div>
            <p>{k["desc"]}</p>
            <span class="cmp-go">{k["cta"]} &rarr;</span>
          </div>
        </a>''')
    return "\n".join(out)


def render_analysis_panel(c):
    a = c.get("analysis")
    if not a:
        return ""
    tk = "\n".join(f'        <li><strong>{t}</strong> {d}</li>' for t, d in a["takeaways"])
    return f'''    <div class="px-panel" role="tabpanel" id="analysis" aria-labelledby="tab-analysis" hidden>
      <h3 class="px-h">{a["title"]}</h3>
      <p class="data-stamp">{a["stamp"]}</p>
      <ul class="takeaways">
{tk}
      </ul>
      <details class="px-more">
        <summary><span class="cl-closed">Read the full analysis <span class="cl-icon">+</span></span><span class="cl-open">Hide the full analysis <span class="cl-icon">&ndash;</span></span></summary>
        <div class="analysis-body">
{a["body_html"]}
        </div>
      </details>
    </div>'''


def render_fit(items):
    return "\n".join(f'          <li><h4>{h}</h4><p>{p}</p></li>' for h, p in items)


def render_faq(c):
    out = []
    for f in c["faq"]:
        out.append(f'      <details>\n        <summary>{f["q"]}</summary>\n        {f["a"]}\n      </details>')
    return "\n".join(out)


def faq_answer_text(a):
    # ordered lists become "item; item" for the schema text
    a = re.sub(r"</li>\s*<li>", "; ", a)
    return plain(a)


def render_jsonld(c):
    url = SITE + c["path"]
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": c["parent_name"], "item": SITE + c["parent_url"]},
        {"@type": "ListItem", "position": 3, "name": c["name"], "item": url}]}
    agent = {"@context": "https://schema.org", "@type": "RealEstateAgent", "name": "Sez Sezer",
             "image": SITE + "/images/sez-sezer-carmel-valley-realtor.jpg", "url": url, "mainEntityOfPage": url,
             "telephone": "+1-858-436-6585", "email": "sez@carmelvalley.com", "priceRange": "$$$",
             "description": c["seo"]["jsonld_description"],
             "address": {"@type": "PostalAddress", "streetAddress": "12750 High Bluff Drive", "addressLocality": "San Diego",
                         "addressRegion": "CA", "postalCode": "92130", "addressCountry": "US"},
             "areaServed": {"@type": "Place", "name": f'{c["name"]}, Carmel Valley, San Diego, CA',
                            "geo": {"@type": "GeoCoordinates", "latitude": c["geo"]["lat"], "longitude": c["geo"]["lng"]}},
             "memberOf": {"@type": "Organization", "name": "Keller Williams Realty"}}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": plain(f["q"]), "acceptedAnswer": {"@type": "Answer", "text": faq_answer_text(f["a"])}}
        for f in c["faq"]]}
    blocks = [json.dumps(x, ensure_ascii=False, indent=2) for x in (crumbs, agent, faq)]
    return "\n".join(f'<script type="application/ld+json">\n{b}\n</script>' for b in blocks)


def build(slug):
    with open(os.path.join(TOOLS, "communities", slug + ".json"), encoding="utf-8") as f:
        c = json.load(f)
    with open(os.path.join(TOOLS, "community-template.html"), encoding="utf-8") as f:
        t = f.read()
    v = {
        "name": c["name"], "name_json": json.dumps(c["name"]), "path": c["path"],
        "parent_name": c["parent_name"], "parent_url": c["parent_url"],
        "api_community": c["api_community"].replace(" ", "%20"),
        "seo_title": c["seo"]["title"], "seo_description": html.escape(c["seo"]["description"], quote=True),
        "hero_eyebrow": c["hero"]["eyebrow"], "h1": c["hero"]["h1"], "hero_lead": c["hero"]["lead"],
        "facts_html": render_facts(c),
        "loc_intro": c["location_intro"], "lat": c["geo"]["lat"], "lng": c["geo"]["lng"],
        "boundary_json": json.dumps(c["boundary"]),
        "schools_html": render_schools(c), "nearby_html": render_nearby(c),
        "glance_h2": c["glance"]["h2"], "glance_lede": c["glance"]["lede"],
        "glance_cards_html": render_glance_cards(c), "glance_n": len(c["glance"]["cards"]), "glance_after_html": render_glance_after(c),
        "life_html": render_life(c), "hoa_html": render_hoa(c),
        "similar_h2": c["similar"]["h2"], "similar_intro": c["similar"]["intro"], "similar_aria": c["similar"]["h2"],
        "similar_cards_html": render_similar(c),
        "analysis_tab_html": ANALYSIS_TAB if c.get("analysis") else "",
        "analysis_panel_html": render_analysis_panel(c),
        "fit_good_html": render_fit(c["fit"]["good"]), "fit_weigh_html": render_fit(c["fit"]["weigh"]),
        "faq_h2": c["faq_h2"], "faq_html": render_faq(c),
        "contact_lead": c["contact_lead"], "jsonld_html": render_jsonld(c),
    }
    missing = set(re.findall(r"\{\{(\w+)\}\}", t)) - set(v)
    if missing:
        raise SystemExit(f"{slug}: template needs {sorted(missing)}")
    out = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), t)
    dest = os.path.join(ROOT, c["path"].strip("/"), "index.html")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"built {c['path']}")


def main(argv):
    slugs = argv or sorted(n[:-5] for n in os.listdir(os.path.join(TOOLS, "communities")) if n.endswith(".json"))
    for s in slugs:
        build(s)


if __name__ == "__main__":
    main(sys.argv[1:])
