#!/usr/bin/env python3
"""Rebuild the Community Atlas (/community-atlas/) from the latest My Maps KML.

    python3 tools/build_atlas.py              # newest "...Townhomes and Condos.kml*" in ~/Downloads
    python3 tools/build_atlas.py path/to.kml

- Area      = the KML folder ("North of Del Mar Heights Road", "Torrey Hills", ...).
              Shapes in the "Carmel Valley Condos" folder take their area from the chart below.
- Home type = tools/atlas_home_types.json (condo / town / sfr). New names default to sfr;
              add them to that file to change it.
- Homes and condo/fractional flag = California Title Company community chart (2012), CHART below.
- Neighbors = six closest communities, edge to edge, in miles.
The result is written into community-atlas/index.html (the DATA line). Stdlib only.
"""
import glob
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "community-atlas", "index.html")

# KML folder -> (area key, label). Order here is the order on the page.
AREAS = [
    ("n", "North of Del Mar Heights Road"),
    ("s", "South of Del Mar Heights Road"),
    ("cch", "Carmel Country Highlands"),
    ("phr", "Pacific Highlands Ranch"),
    ("tdm", "Torrey Highlands"),
    ("th", "Torrey Hills"),
    ("dmm", "Del Mar Mesa"),
    ("rp", "Rancho Pacifica"),
]
CONDO_FOLDER = "Carmel Valley Condos"

# California Title Company chart (2012): area key, name, homes; (a) = condo/fractional ownership.
CHART = {
    "n": "Alta Mar 216;Cambria (a) 235;Del Mar Summit 5;Derby Point 10;East Bluff (a) 306;Heights 566;Lexington Summit 14;Martinique (a) 116;Mayfield 66;Pacifica (a) 192;Palmilla (a) 92;Promontory 190;Regentz Square (a) 29;San Remo 289;Santa Fe Summit 187;Stallions Crossing 48;Sundowner Estates 6;Torrey Del Mar 47;Torrey Glen 151;Venezia 42;Vista Santa Barbara 85;Windmill Estates 6;4x4 Construction 4",
    "s": "Amador 38;Andalucia (a) 184;Antares (a) 100;Arborlake (a) 189;Bayshore 149;Cantamar 227;Canyon Ridge (a) 116;Carmel Point (a) 202;Carmel Village 51;Carmel Villas (a) 316;Chateau Village (a) 170;Coral Cove (a) 118;Creek Park 155;Crest Del Mar (a) 197;Del Mar Bluffs 120;Del Mar Place 241;Del Mar Villas (a) 241;Elysian (a) 160;Estates 99;Granada 73;Groves (a) 173;Halcyon (a) 184;Heights 566;Hunt Club 50;Huntington Heights 132;La Plage (a) 126;Lakes (a) 192;Montemar (a) 118;Palacio 422;Palermo (a) 188;Palisades 164;Palma Del Mar 78;Pelagos (a) 99;Pell Place (a) 317;Pines 176;Private Collection 40;Promontory 190;Provence 57;San Remo 289;Seabridge 171;Sonoma 219;Stone Canyon (a) 99;Sunstream (a) 260;The Heights (a) 267;Triple Crown 41;Verona 8;Watercolors 79;Wild Horse 55;Windwood (a) 167",
    "cch": "Belmont 316;Breakers 72;Bridleridge 53;Carriage Run 169;Derby Hill 172;Highlands Village (a) 127;Lexington 265;Saratoga 114;Steeplechase 193",
    "phr": "Airoso (a) 256;Arabella 140;Bordeaux 106;Brightwater 77;Costa Del Sol 165;Hampton Lane 118;Manzanita Trail 148;Portico 186;Rancho Glens 33;Santa Barbara 98;Santa Rosa 124;Soleil at Bordeaux 163",
    "th": "Coves 108;Gables 44;Greenbriar 107;La Strada 69;Monte Claire 50;Montecito 81;San Raphael (a) 125;Sands 107;Sansonnet 183;Sausalito (a) 100;Sea Country 53;Searidge 57;Shores 111;St. Augustine 108;Torrey Point 81;Torrey View 121;Torrey Woods Estates 93;Trilogy 189;Vantage Point 24",
    "dmm": "Alta Del Mar 216;Bougainvillea 76;Duck Pond Ranch 15;Meadows Del Mar 200;Paso Fino 12;Ridge 19;Ridge Estates 19;Silver Oaks Estates 8;The Preserve 14;Three Canyons 12;Valencia 7;Whitehorse 19",
    "tdm": "Collins Ranch 53;Fairbanks Highlands 93;Palma Real 82;Terrazzo 59;Valencia Collection 8;Villamontes 124",
    "rp": "Rancho Pacifica 148",
}
# map name -> chart name, where they're spelled differently
ALIAS = {"regents square": "regentz square", "the lakes": "lakes", "the groves": "groves", "carmel pointe": "carmel point",
         "torrey del mar west": "torrey del mar", "bridle ridge": "bridleridge",
         "silver oaks estates / anderson estates": "silver oaks estates", "rancho glens estates": "rancho glens"}


def latest_kml():
    files = glob.glob(os.path.expanduser("~/Downloads/Carmel Valley Neighborhoods Townhomes and Condos.kml*"))
    if not files:
        sys.exit("No KML found in ~/Downloads")
    return max(files, key=os.path.getmtime)


def parse_chart():
    out = {}
    for area, txt in CHART.items():
        for part in txt.split(";"):
            m = re.match(r"(.+?)\s*(\(a\))?\s+(\d+)$", part.strip())
            name = m.group(1).strip()
            out.setdefault(name.lower(), []).append({"name": name, "area": area, "homes": int(m.group(3)), "condo": bool(m.group(2))})
    return out


def parse_kml(path):
    s = open(path, encoding="utf-8").read()
    shapes = {}
    for fm in re.finditer(r"<Folder>\s*<name>(.*?)</name>(.*?)</Folder>", s, re.S):
        folder = fm.group(1).strip()
        for pm in re.finditer(r"<Placemark>\s*<name>(.*?)</name>(.*?)</Placemark>", fm.group(2), re.S):
            c = re.search(r"<coordinates>(.*?)</coordinates>", pm.group(2), re.S)
            if not c:
                continue
            pts = [tuple(map(float, p.split(",")[:2])) for p in c.group(1).split()]
            shapes.setdefault((folder, pm.group(1).strip()), []).append(pts)
    return shapes


LAT0 = 32.95
KX = math.cos(math.radians(LAT0)) * 69.17


def xy(p):  # lng,lat -> miles
    return ((p[0] + 117.2) * KX, (p[1] - LAT0) * 69.0)


def segd(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def edge(A, B):
    m = 99
    for P in A:
        for Q in B:
            for p in P:
                for i in range(len(Q) - 1):
                    m = min(m, segd(p, Q[i], Q[i + 1]))
            for p in Q:
                for i in range(len(P) - 1):
                    m = min(m, segd(p, P[i], P[i + 1]))
    return m


def main(argv):
    kml = argv[0] if argv else latest_kml()
    print("KML:", kml)
    shapes = parse_kml(kml)
    folder_area = {label: key for key, label in AREAS}
    chart = parse_chart()
    types = json.load(open(os.path.join(ROOT, "tools", "atlas_home_types.json")))
    comms = []
    for (folder, name), polys in shapes.items():
        P = [[xy(p) for p in poly] for poly in polys]
        pts = [p for poly in P for p in poly]
        k = ALIAS.get(name.lower(), name.lower())
        area = folder_area.get(folder)
        entries = chart.get(k, [])
        e = next((x for x in entries if x["area"] == area), entries[0] if entries else None)
        if area is None and folder == CONDO_FOLDER and e:
            area = e["area"]
        comms.append({"n": name, "cat": types.get(name, "sfr"), "sub": area, "folder": folder,
                      "homes": e["homes"] if e else None, "condo": e["condo"] if e else None, "chart": e["name"] if e else None,
                      "P": P, "c": (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)),
                      "p": [[[round(p[1], 5), round(p[0], 5)] for p in poly] for poly in polys]})
    for i, a in enumerate(comms):
        cand = sorted((math.hypot(a["c"][0] - b["c"][0], a["c"][1] - b["c"][1]), j) for j, b in enumerate(comms) if j != i)[:20]
        a["nb"] = [[j, round(d, 2)] for d, j in sorted((edge(a["P"], comms[j]["P"]), j) for _, j in cand)[:6]]
    for a in comms:  # a folder that isn't an area: borrow the nearest neighbor's area
        if a["sub"] is None:
            for j, _ in a["nb"]:
                if comms[j]["sub"]:
                    a["sub"], a["est"] = comms[j]["sub"], True
                    break
    used = {(ALIAS.get(c["n"].lower(), c["n"].lower())) for c in comms if c["chart"]}
    missing = [x for k, v in chart.items() if k not in used for x in v]
    unknown_folders = sorted({c["folder"] for c in comms if c["folder"] not in folder_area and c["folder"] != CONDO_FOLDER})
    out = {"c": [{k: v for k, v in c.items() if k not in ("P", "c", "folder") and v is not None} for c in comms],
           "subs": [[k, l] for k, l in AREAS], "missing": missing}
    s = open(PAGE, encoding="utf-8").read()
    s = re.sub(r"var DATA=\{.*?\};\n", lambda m: "var DATA=" + json.dumps(out, separators=(",", ":")) + ";\n", s, count=1, flags=re.S)
    open(PAGE, "w", encoding="utf-8").write(s)
    print(f"{len(comms)} communities, {sum(1 for c in comms if c['chart'])} matched to the chart; "
          f"chart names not on the map: {', '.join(x['name'] for x in missing) or 'none'}")
    if unknown_folders:
        print("folders that aren't areas (area estimated):", ", ".join(unknown_folders))
    newnames = sorted(c["n"] for c in comms if c["n"] not in types)
    if newnames:
        print("new names (home type defaulted to single-family):", ", ".join(newnames))


if __name__ == "__main__":
    main(sys.argv[1:])
