#!/usr/bin/env python3
"""Google Sheet <-> community data files.

The "Carmel Valley Communities Database" Google Sheet is the place to edit
community facts and FAQs. This script moves data between it and
tools/communities/<slug>.json (which tools/build_communities.py turns into pages).

    python3 tools/community_sheet.py export out.xlsx
        Write a workbook from the current data files (used to create the sheet).

    python3 tools/community_sheet.py import sheet.xlsx
        Read the sheet (exported from Google Sheets as .xlsx) and update the
        data files: facts, intros and FAQs. Then run build_communities.py and
        build_llm_files.py.

Stdlib only. Answers are plain text in the sheet:
    - a blank line starts a new paragraph
    - lines starting "1." "2." ... become a numbered list
    - **bold** works anywhere
"""
import html
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape as xesc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDIR = os.path.join(ROOT, "tools", "communities")

FACT_LABELS = ["Price", "HOA Fee", "Square Feet", "Total Units", "Year Built", "Mello-Roos", "Tax Rate", "Time to Sell"]
COMM_HEADERS = ["Community ID", "Community", "Page", "Hero intro", "Location", *FACT_LABELS, "Contact intro"]
BANK_HEADERS = ["Question ID", "Question (use {community} for the name)", "Topic", "Communities using it"]
FAQ_HEADERS = ["Community ID", "Question ID", "Question as shown", "Answer", "Order", "Status", "Notes"]

# Questions every community can draw from. {community} is replaced by the name.
BANK = [
    ("price-range", "What is the price range for {community} condos?", "Prices"),
    ("hoa-covers", "What do {community} HOA fees cover?", "HOA"),
    ("mello-roos", "Does {community} have Mello-Roos?", "Taxes"),
    ("unit-sizes", "How big are the units at {community}?", "Homes"),
    ("parking", "What is parking like at {community}?", "Homes"),
    ("compare", "How does {community} compare to other Carmel Valley condo communities?", "Comparison"),
    ("how-fast", "How quickly do {community} condos sell?", "Market"),
    ("tour-checklist", "What should I check when I tour a {community} condo?", "Buying"),
    ("pets", "Are pets allowed at {community}?", "Rules"),
    ("rentals", "Can I rent out my {community} condo?", "Rules"),
    ("schools", "Which schools serve {community}?", "Schools"),
    ("investment", "Is {community} a good investment?", "Market"),
    ("special-assessments", "Has {community} had any special assessments?", "HOA"),
    ("ev-charging", "Is there EV charging at {community}?", "Homes"),
]


# ---------------------------------------------------------------- text <-> html
def html_to_text(a):
    """FAQ answer HTML -> plain text for the sheet."""
    a = re.sub(r"<strong>(.*?)</strong>", r"**\1**", a, flags=re.S)
    items = re.findall(r"<li>(.*?)</li>", a, flags=re.S)
    if items:
        a = re.sub(r"<ol[^>]*>.*?</ol>", "\n".join(f"{i}. {t.strip()}" for i, t in enumerate(items, 1)), a, flags=re.S)
    a = re.sub(r"</p>\s*<p>", "\n\n", a)
    a = re.sub(r"<[^>]+>", "", a)
    return html.unescape(a).strip()


def text_to_html(t):
    """Sheet plain text -> FAQ answer HTML."""
    def inline(s):
        s = html.escape(s.strip(), quote=False)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    out = []
    for block in re.split(r"\n\s*\n", (t or "").strip()):
        lines = [l for l in block.split("\n") if l.strip()]
        if lines and all(re.match(r"\s*\d+[.)]\s", l) for l in lines):
            num = re.compile(r"^\s*\d+[.)]\s+")
            lis = "".join("<li>" + inline(num.sub("", l)) + "</li>" for l in lines)
            out.append(f'<ol class="faq-ol">{lis}</ol>')
        elif lines:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n        ".join(out)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def to_html_text(s):
    """Sheet text for a fact/intro -> safe HTML (keeps any links typed as HTML)."""
    s = (s or "").strip()
    return s if "<a " in s else html.escape(s, quote=False)


# ---------------------------------------------------------------- xlsx writer
def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheet_xml(rows, widths, freeze=True, validation=None, wrap_cols=()):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if freeze:
        out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    out.append("<cols>" + "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)) + "</cols>")
    out.append("<sheetData>")
    for r, row in enumerate(rows, 1):
        cells = []
        for c, v in enumerate(row):
            if v is None or v == "":
                continue
            ref = f"{col_letter(c)}{r}"
            style = 1 if r == 1 and freeze else (2 if c in wrap_cols else 0)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(f'<c r="{ref}" s="{style}"><v>{v}</v></c>')
            elif isinstance(v, str) and v.startswith("="):
                cells.append(f'<c r="{ref}" s="{style}"><f>{xesc(v[1:])}</f></c>')
            else:
                cells.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{xesc(str(v))}</t></is></c>')
        out.append(f'<row r="{r}">{"".join(cells)}</row>')
    out.append("</sheetData>")
    if validation:
        out.append('<dataValidations count="1">' + validation + "</dataValidations>")
    out.append("</worksheet>")
    return "".join(out)


STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font></fonts>'
          '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
          '<fill><patternFill patternType="solid"><fgColor rgb="FF1456E8"/><bgColor indexed="64"/></patternFill></fill></fills>'
          '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
          '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
          '<cellXfs count="3">'
          '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>'
          '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
          '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
          '</cellXfs></styleSheet>')


def write_xlsx(path, sheets):
    """sheets: list of (name, xml)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets) + 1))
                   + "</Types>")
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{xesc(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, (n, _) in enumerate(sheets, 1))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1))
                   + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("xl/styles.xml", STYLES)
        for i, (_, x) in enumerate(sheets, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", x)


def load_all():
    out = []
    for n in sorted(os.listdir(CDIR)):
        if n.endswith(".json"):
            with open(os.path.join(CDIR, n), encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def match_bank(q, name):
    g = q.replace(name, "{community}")
    g = re.sub(r"\ban \{community\}", "a {community}", g)
    for qid, text, _ in BANK:
        if text == g:
            return qid
    return None


def export(path):
    comms = load_all()
    guide = [["Carmel Valley Communities Database"], [""],
             ["What each tab is for"],
             ["Communities: one row per community. Edit the intro text and the 8 quick facts shown on its page."],
             ["FAQ Bank: the library of questions. Write {community} where the community name goes. Add new questions at the bottom with a new Question ID."],
             ["Community FAQs: which questions each community shows, in what order, and its answer."],
             [""],
             ["How to edit FAQs"],
             ["Add a row with the Community ID and a Question ID from the FAQ Bank. Question as shown fills in automatically; type over it to use different wording for that community."],
             ["Write the answer in plain text. A blank line starts a new paragraph. Lines starting 1. 2. 3. become a numbered list. **double asterisks** make text bold."],
             ["Status: Published shows on the page. Draft is saved here but not shown."],
             ["Order: lower numbers show first."],
             [""],
             ["How updates reach the website"],
             ["Tell Claude \"sync the community database\". It reads this sheet, rebuilds every community page and pushes the update after you approve."],
             ["Prices, sold data and bedroom cards are not edited here. They come from MLS closed sales automatically."]]
    comm_rows = [COMM_HEADERS]
    for c in comms:
        facts = {f["label"]: plain(f["value"]) for f in c["facts"]}
        comm_rows.append([c["slug"], c["name"], "https://www.carmelvalleycondos.com" + c["path"], plain(c["hero"]["lead"]),
                          plain(c["location_intro"]), *[facts.get(l, "") for l in FACT_LABELS], plain(c["contact_lead"])])
    bank_rows = [BANK_HEADERS]
    for i, (qid, text, topic) in enumerate(BANK, 2):
        bank_rows.append([qid, text, topic, f"=COUNTIF('Community FAQs'!B:B,A{i})"])
    faq_rows = [FAQ_HEADERS]
    r = 2
    for c in comms:
        for n, f in enumerate(c["faq"], 1):
            q = plain(f["q"])
            qid = match_bank(q, c["name"]) or "custom"
            default = (f"=SUBSTITUTE(VLOOKUP(B{r},'FAQ Bank'!A:B,2,FALSE),\"{{community}}\",VLOOKUP(A{r},Communities!A:B,2,FALSE))")
            # keep the formula when it reproduces the live question; otherwise store the exact text
            bank_text = next((t for i2, t, _ in BANK if i2 == qid), None)
            shown = default if bank_text and bank_text.replace("{community}", c["name"]) == q else q
            faq_rows.append([c["slug"], qid, shown, html_to_text(f["a"]), n * 10, "Published", ""])
            r += 1
    sheets = [
        ("How to Use", sheet_xml(guide, [120], freeze=False)),
        ("Communities", sheet_xml(comm_rows, [16, 16, 34, 60, 50, 14, 12, 14, 11, 12, 12, 10, 13, 50], wrap_cols=(3, 4, 13))),
        ("FAQ Bank", sheet_xml(bank_rows, [20, 70, 14, 16], wrap_cols=(1,))),
        ("Community FAQs", sheet_xml(faq_rows, [16, 18, 50, 80, 8, 12, 30], wrap_cols=(2, 3, 6),
                                     validation='<dataValidation type="list" allowBlank="1" showErrorMessage="1" sqref="F2:F1000"><formula1>"Published,Draft"</formula1></dataValidation>')),
    ]
    write_xlsx(path, sheets)
    print(f"wrote {path}: {len(comms)} communities, {len(BANK)} bank questions, {len(faq_rows)-1} FAQs")


# ---------------------------------------------------------------- xlsx reader
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx(path):
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    out = {}
    for s in wb.iter(NS + "sheet"):
        rid = s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        t = target[rid].lstrip("/")
        t = t if t.startswith("xl/") else "xl/" + t
        rows = []
        for row in ET.fromstring(z.read(t)).iter(NS + "row"):
            vals = {}
            for c in row.iter(NS + "c"):
                col = re.match(r"[A-Z]+", c.get("r")).group(0)
                idx = 0
                for ch in col:
                    idx = idx * 26 + ord(ch) - 64
                typ = c.get("t")
                if typ == "s":
                    v = shared[int(c.find(NS + "v").text)]
                elif typ == "inlineStr":
                    v = "".join(x.text or "" for x in c.iter(NS + "t"))
                else:
                    ve = c.find(NS + "v")
                    v = ve.text if ve is not None else ""
                vals[idx - 1] = v
            rows.append([vals.get(i, "") for i in range(max(vals) + 1)] if vals else [])
        out[s.get("name")] = rows
    return out


def as_dicts(rows):
    if not rows:
        return []
    head = [h.strip() for h in rows[0]]
    return [{head[i]: (r[i] if i < len(r) else "") for i in range(len(head))} for r in rows[1:] if any(str(x).strip() for x in r)]


def import_(path):
    book = read_xlsx(path)
    comms = {r["Community ID"].strip(): r for r in as_dicts(book.get("Communities", []))}
    faqs = as_dicts(book.get("Community FAQs", []))
    bank = {r.get(BANK_HEADERS[0], "").strip(): r.get(BANK_HEADERS[1], "") for r in as_dicts(book.get("FAQ Bank", []))}
    names = {k: v.get("Community", "") for k, v in comms.items()}
    for f in faqs:  # a formula cell can arrive without a value: rebuild it from the bank
        if not f.get("Question as shown", "").strip():
            tmpl = bank.get(f.get("Question ID", "").strip(), "")
            name = names.get(f.get("Community ID", "").strip(), "")
            if tmpl and name:
                f["Question as shown"] = tmpl.replace("{community}", name)
    changed = []
    for c in load_all():
        slug = c["slug"]
        row = comms.get(slug)
        before = json.dumps(c, sort_keys=True)
        if row:
            if row.get("Hero intro", "").strip():
                c["hero"]["lead"] = to_html_text(row["Hero intro"])
            if row.get("Location", "").strip():
                c["location_intro"] = to_html_text(row["Location"])
            if row.get("Contact intro", "").strip():
                c["contact_lead"] = to_html_text(row["Contact intro"])
            for f in c["facts"]:
                v = row.get(f["label"], "").strip()
                if v:
                    f["value"] = html.escape(v, quote=False)
        mine = [f for f in faqs if f.get("Community ID", "").strip() == slug and f.get("Status", "").strip().lower() == "published"
                and f.get("Question as shown", "").strip() and f.get("Answer", "").strip()]
        if mine:
            def order(f):
                try:
                    return float(f.get("Order") or 9999)
                except ValueError:
                    return 9999
            mine.sort(key=order)
            c["faq"] = [{"q": html.escape(f["Question as shown"].strip(), quote=False), "a": text_to_html(f["Answer"])} for f in mine]
        if json.dumps(c, sort_keys=True) != before:
            with open(os.path.join(CDIR, slug + ".json"), "w", encoding="utf-8") as fh:
                json.dump(c, fh, indent=2, ensure_ascii=False)
            changed.append(slug)
    unknown = sorted(set(comms) - {c["slug"] for c in load_all()})
    print("updated:", ", ".join(changed) or "nothing changed")
    if unknown:
        print("not built yet (no data file):", ", ".join(unknown))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("export", "import"):
        sys.exit(__doc__)
    (export if sys.argv[1] == "export" else import_)(sys.argv[2])
