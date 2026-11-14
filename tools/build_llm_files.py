#!/usr/bin/env python3
"""Build the AI/LLM-readable layer of carmelvalleycondos.com.

Generates, from the live HTML pages in this repo:
  - <page>/index.md      clean Markdown mirror of each page's visible content
  - /llms.txt            llms.txt index (llmstxt.org format)
  - /llms-full.txt       every page's Markdown combined into one file

Run from the repo root after editing any page:
    python3 tools/build_llm_files.py

Stdlib only (no pip installs). The .md files mirror what visitors see on the
HTML page: site chrome (menus, footers' link lists, bottom nav) is dropped, and
sections the page fills in live from the MLS with JavaScript are marked as such
with a link back to the page instead of being invented or omitted.
"""
import html
import os
import re
import sys
from html.parser import HTMLParser

SITE = "https://carmelvalleycondos.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Key pages, in the order they appear in llms.txt / llms-full.txt.
# (path, llms.txt section, one-line description)
PAGES = [
    ("/", "Overview",
     "Home page: Carmel Valley (San Diego, CA 92130) condos and townhomes for sale, communities, and how to work with Sez Sezer."),
    ("/carmel-valley-condos-for-sale/", "Communities",
     "Guide to Carmel Valley condo communities, prices, HOA fees, and live 92130 condo listings."),
    ("/carmel-valley-townhomes-for-sale/", "Communities",
     "Guide to Carmel Valley townhome communities, prices, HOA fees, and live 92130 townhome listings."),
    ("/arborlake-condos-for-sale/", "Communities",
     "Arborlake: 190-unit lake-and-waterfall condo community (built 1986-1989) - prices by bedroom count, HOA, sold data, schools, FAQs."),
    ("/carmel-pointe-condos-for-sale/", "Communities",
     "Carmel Pointe: 200-unit condo community (built 2001-2002) with underground garage parking and a utility-inclusive HOA - prices by bedroom count, HOA, sold data, schools, FAQs."),
    ("/camino-villas-condos-for-sale/", "Communities",
     "Camino Villas: established central Carmel Valley condo community with a community pool - overview, listings, FAQs."),
    ("/the-heights-townhomes-for-sale/", "Communities",
     "The Heights: Carmel Valley townhome community - overview, listings, FAQs."),
    ("/carmel-valley-condo-market-report/", "Guides",
     "Carmel Valley condo and townhome market report: 92130 prices, trends, and what they mean for buyers and sellers."),
    ("/home-value/", "Guides",
     "Free home value estimate for Carmel Valley condos and townhomes, and how valuations are prepared."),
]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
SKIP_TAGS = {"script", "style", "svg", "noscript", "button", "template",
             "nav", "select", "textarea", "input", "label", "canvas"}
SKIP_CLASSES = {"fs-bar", "map-click-catch", "map-expand-hint", "quick-rail",
                "bottom-nav", "hero-ctas", "listings-tag", "cl-open",
                "cl-closed", "cl-icon", "trend-legend", "loc-map-tools", "am-num", "tour-num", "vp-num", "masthead"}
# Placeholders that JavaScript replaces with live MLS data on the HTML page.
LIVE_CLASSES = {"snap-state", "sold-state", "trend-state"}
# Two-part "value + label" widgets rendered as one "Label: value" line.
PAIR_CLASSES = {"fact", "glance-row", "hoa-bar-label", "stat", "stat-box",
                "hero-stat", "kpi", "analysis-chip"}
BLOCK = {"p", "div", "section", "article", "main", "aside", "ul", "ol", "li",
         "table", "thead", "tbody", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
         "details", "summary", "blockquote", "figure", "figcaption", "form",
         "footer", "header", "dl", "dt", "dd", "hr", "iframe", "img", "fieldset", "realscout-home-value"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.parent = parent

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def find(node, pred):
    if isinstance(node, str):
        return None
    if pred(node):
        return node
    for c in node.children:
        r = find(c, pred)
        if r:
            return r
    return None


def text_of(node):
    if isinstance(node, str):
        return node
    if node.tag in ("script", "style", "svg"):
        return ""
    return "".join(text_of(c) for c in node.children)


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def absurl(href, page_path):
    if not href:
        return href
    if href.startswith(("http://", "https://", "mailto:", "tel:")):
        return href
    if href.startswith("#"):
        return SITE + page_path + href
    if href.startswith("/"):
        return SITE + href
    return SITE + page_path + href


def is_hidden(node):
    style = (node.attrs.get("style") or "").replace(" ", "").lower()
    # Tab panels are hidden only until a visitor clicks their tab, so they count as visible content.
    hidden_attr = "hidden" in node.attrs and node.attrs.get("role") != "tabpanel"
    return ("display:none" in style or node.attrs.get("aria-hidden") == "true"
            or hidden_attr)


class MdRenderer:
    def __init__(self, page_path):
        self.page = page_path
        self.blocks = []
        self.buf = []

    # ---- inline ----
    def inline(self, node):
        if isinstance(node, str):
            return html.unescape(node) if "&" in node else node
        if node.tag in SKIP_TAGS or node.classes & SKIP_CLASSES or is_hidden(node):
            return ""
        if node.tag == "br":
            return "\n"
        inner = "".join(self.inline(c) for c in node.children)
        if node.tag == "a":
            label = norm(inner)
            href = absurl(node.attrs.get("href", ""), self.page)
            if not label:
                return ""
            if not href or href.startswith("javascript:"):
                return label
            return f"[{label}]({href})"
        if node.tag in ("strong", "b"):
            t = norm(inner)
            return f"**{t}**" if t else ""
        if node.tag in ("em", "i"):
            t = norm(inner)
            return f"*{t}*" if t else ""
        if node.tag == "img":
            return ""
        return inner

    def has_block_child(self, node):
        for c in node.children:
            if isinstance(c, Node) and not (
                    c.tag in SKIP_TAGS or c.classes & SKIP_CLASSES or is_hidden(c)):
                if c.tag in BLOCK or self.has_block_child(c):
                    return True
        return False

    def flush(self):
        t = norm("".join(self.buf))
        self.buf = []
        if t:
            self.blocks.append(t)

    def emit(self, text):
        self.flush()
        if text:
            self.blocks.append(text)

    # ---- blocks ----
    def block(self, node):
        if isinstance(node, str):
            self.buf.append(node)
            return
        tag, cls = node.tag, node.classes
        if tag in SKIP_TAGS or cls & SKIP_CLASSES or is_hidden(node):
            return
        if cls & LIVE_CLASSES:
            anchor = self.section_anchor(node)
            self.emit(f"*Live MLS data: this section loads current closed-sale figures on the web page. "
                      f"See {SITE}{self.page}{anchor}*")
            return
        if tag == "footer":
            disc = find(node, lambda n: "disclaimer" in n.classes)
            if disc:
                self.emit("---")
                self.emit(norm(self.inline(disc)))
            return
        if re.fullmatch(r"h[1-6]", tag):
            t = norm(self.inline(node))
            self.emit(("#" * int(tag[1])) + " " + t if t else "")
            return
        if tag == "p" or (tag in ("div", "span", "figcaption", "dt", "dd") and not self.has_block_child(node)):
            if cls & PAIR_CLASSES:
                self.emit(self.pair(node))
                return
            if "eyebrow" in cls:
                t = norm(self.inline(node))
                self.emit(f"*{t}*" if t else "")
                return
            self.flush()
            t = norm(self.inline(node))
            if t:
                self.blocks.append(t)
            return
        if cls & PAIR_CLASSES:
            self.emit(self.pair(node))
            return
        if tag in ("ul", "ol"):
            self.flush()
            items = []
            n = 0
            for li in node.children:
                if isinstance(li, Node) and li.tag == "li" and not is_hidden(li):
                    n += 1
                    t = self.li_text(li)
                    if t:
                        items.append((f"{n}. " if tag == "ol" else "- ") + t)
            if items:
                self.blocks.append("\n".join(items))
            return
        if tag == "table":
            self.emit(self.table(node))
            return
        if tag == "details":
            summ = find(node, lambda n: n.tag == "summary")
            q = norm(self.inline(summ)) if summ else ""
            if q and "px-more" not in node.classes:  # FAQ-style accordion: question becomes a heading
                self.emit("### " + q)
            for c in node.children:
                if c is not summ:
                    self.block(c)
            self.flush()
            return
        if tag == "summary":
            return
        if tag == "img":
            alt = norm(node.attrs.get("alt", ""))
            src = absurl(node.attrs.get("src", ""), self.page)
            if alt and src:
                self.emit(f"![{alt}]({src})")
            return
        if tag == "iframe":
            title = norm(node.attrs.get("title", "")) or "Embedded content"
            src = html.unescape(node.attrs.get("src", "") or node.attrs.get("data-src", ""))
            if src:
                self.emit(f"[{title}]({src})")
            return
        if tag == "realscout-home-value":
            self.emit(f"*An instant home value estimate tool (RealScout) is available on the web page: {SITE}{self.page}#valuation-form*")
            return
        if tag == "form":
            self.flush()
            for c in node.children:
                self.block(c)
            self.emit(f"*An online request form is available on the web page: {SITE}{self.page}*")
            return
        if tag == "hr":
            self.emit("---")
            return
        if tag == "blockquote":
            t = norm(self.inline(node))
            self.emit("> " + t if t else "")
            return
        if tag == "a" and self.has_block_child(node):
            # Card-style link wrapping blocks: render the blocks, then turn the
            # card's last line (its call to action) into the link.
            self.flush()
            start = len(self.blocks)
            for c in node.children:
                self.block(c)
            self.flush()
            href = absurl(node.attrs.get("href", ""), self.page)
            if len(self.blocks) > start and href:
                self.blocks[-1] = f"[{self.blocks[-1]}]({href})"
            return
        inline_tag = tag not in BLOCK
        if inline_tag and not self.has_block_child(node):
            self.buf.append(" " + self.inline(node) + " ")
            return
        if "eyebrow" in cls:
            t = norm(self.inline(node))
            self.emit(f"*{t}*" if t else "")
            return
        if not inline_tag:
            self.flush()
        for c in node.children:
            if inline_tag and isinstance(c, Node) and c.tag not in BLOCK:
                self.buf.append(self.inline(c))
            else:
                self.block(c)
        if not inline_tag:
            self.flush()

    def li_text(self, li):
        elems = [c for c in li.children if isinstance(c, Node)
                 and not (c.tag in SKIP_TAGS or c.classes & SKIP_CLASSES or is_hidden(c))]
        loose = norm("".join(c for c in li.children if isinstance(c, str)))
        elems = list(self.flatten(elems))
        if loose or len(elems) < 2 or all(e.tag not in BLOCK and e.tag != "span" for e in elems):
            return norm(self.inline(li))
        parts = []
        for e in elems:
            t = norm(self.inline(e))
            if t:
                parts.append(f"**{t}**" if re.fullmatch(r"h[1-6]", e.tag) else t)
        return " — ".join(parts)

    def flatten(self, elems):
        for e in elems:
            kids = [c for c in e.children if isinstance(c, Node) and c.tag in BLOCK]
            if kids and e.tag == "div":
                yield from self.flatten(kids)
            else:
                yield e

    def section_anchor(self, node):
        n = node
        while n is not None and isinstance(n, Node):
            if n.tag == "section" and n.attrs.get("id"):
                return "#" + n.attrs["id"]
            n = n.parent
        return ""

    def pair(self, node):
        parts = [norm(self.inline(c)) for c in node.children if isinstance(c, Node)]
        parts = [p for p in parts if p]
        if not parts:
            return ""
        if node.classes & {"fact", "analysis-chip", "stat"} and len(parts) == 2:  # value then label
            return f"- **{parts[1]}:** {parts[0]}"
        if len(parts) == 2:
            return f"- **{parts[0]}:** {parts[1]}"
        return "- " + " · ".join(parts)

    def table(self, node):
        rows = []
        for tr in iter_nodes(node):
            if tr.tag == "tr":
                cells = [norm(self.inline(c)).replace("|", "\\|")
                         for c in tr.children if isinstance(c, Node) and c.tag in ("th", "td")]
                if cells:
                    rows.append(cells)
        if not rows:
            return ""
        w = max(len(r) for r in rows)
        rows = [r + [""] * (w - len(r)) for r in rows]
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w]
        out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join(out)


def iter_nodes(node):
    for c in node.children:
        if isinstance(c, Node):
            yield c
            yield from iter_nodes(c)


def tidy(blocks):
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        b = re.sub(r"\s+([,.;:!?])", r"\1", b) if not b.startswith("|") else b
        if out and out[-1] == b:
            continue
        if out and b.startswith("- ") and out[-1].startswith("- "):
            out[-1] += "\n" + b
            continue
        out.append(b)
    # A heading immediately followed by another heading of same/higher level
    # with nothing between is fine in Markdown; collapse stray '---' at ends.
    while out and out[0] == "---":
        out.pop(0)
    return "\n\n".join(out) + "\n"


def convert(page_path):
    src = os.path.join(ROOT, page_path.strip("/"), "index.html") if page_path != "/" else os.path.join(ROOT, "index.html")
    with open(src, encoding="utf-8") as f:
        raw = f.read()
    tb = TreeBuilder()
    tb.feed(raw)
    title_node = find(tb.root, lambda n: n.tag == "title")
    title = norm(text_of(title_node)) if title_node else ""
    desc_node = find(tb.root, lambda n: n.tag == "meta" and n.attrs.get("name") == "description")
    desc = norm(html.unescape(desc_node.attrs.get("content", ""))) if desc_node else ""
    body = find(tb.root, lambda n: n.tag == "body")
    r = MdRenderer(page_path)
    r.block(body)
    r.flush()
    url = SITE + page_path
    front = [f"# {title}", f"> {desc}" if desc else "",
             f"Source page: {url}"]
    md = tidy(front + r.blocks)
    # The page's own <h1> repeats the title as a second H1; demote it so the
    # file has exactly one H1 (the page title).
    lines = md.split("\n")
    seen_h1 = False
    for i, line in enumerate(lines):
        if line.startswith("# "):
            if seen_h1:
                lines[i] = "#" + line
            seen_h1 = True
    return title, desc, "\n".join(lines)


def md_path(page_path):
    return "/index.md" if page_path == "/" else page_path + "index.md"


def html_file(page_path):
    return os.path.join(ROOT, "index.html") if page_path == "/" else os.path.join(ROOT, page_path.strip("/"), "index.html")


def add_alternate_link(page_path):
    """Insert <link rel="alternate" type="text/markdown"> after the canonical tag (idempotent).
    Restores the file's original permissions (index.html is kept read-only)."""
    fp = html_file(page_path)
    with open(fp, encoding="utf-8") as f:
        s = f.read()
    tag = f'<link rel="alternate" type="text/markdown" href="{SITE}{md_path(page_path)}">'
    if tag in s:
        return False
    s2, n = re.subn(r'(<link rel="canonical"[^>]*>)', r"\1\n" + tag, s, count=1)
    if not n:
        s2 = s.replace("</head>", tag + "\n</head>", 1)
    mode = os.stat(fp).st_mode
    os.chmod(fp, mode | 0o200)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            f.write(s2)
    finally:
        os.chmod(fp, mode)
    return True


def lastmod(rel):
    import subprocess
    try:
        d = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    except OSError:
        d = ""
    import datetime
    return d or datetime.date.today().isoformat()


def write_sitemap():
    """Sitemap of pages that exist in this repo, plus their .md mirrors and the llms files."""
    prio = {"/": "1.0"}
    entries = []
    for path, section, _ in PAGES:
        rel = "index.html" if path == "/" else path.strip("/") + "/index.html"
        entries.append((SITE + path, lastmod(rel), "weekly", prio.get(path, "0.8" if section != "Communities" or path.startswith("/carmel-valley") else "0.7")))
    for path, _, _ in PAGES:
        rel = "index.html" if path == "/" else path.strip("/") + "/index.html"
        entries.append((SITE + md_path(path), lastmod(rel), "weekly", "0.3"))
    for f in ("llms.txt", "llms-full.txt", "data/communities.json"):
        entries.append((f"{SITE}/{f}", lastmod(f), "weekly", "0.3"))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm, cf, pr in entries:
        out += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{lm}</lastmod>",
                f"    <changefreq>{cf}</changefreq>", f"    <priority>{pr}</priority>", "  </url>"]
    out.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def write_headers():
    """Cloudflare _headers: serve Markdown/text as UTF-8 and point each .md
    back to its HTML page as canonical so search engines don't see duplicates."""
    out = ["# Generated by tools/build_llm_files.py",
           "/images/*", "  Cache-Control: public, max-age=2592000, stale-while-revalidate=86400", "",
           "/assets/*", "  Cache-Control: public, max-age=86400, stale-while-revalidate=604800", "",
           "/llms.txt", "  Content-Type: text/plain; charset=utf-8", "",
           "/llms-full.txt", "  Content-Type: text/plain; charset=utf-8", "",
           "/data/communities.json", "  Content-Type: application/json; charset=utf-8",
           "  Access-Control-Allow-Origin: *", ""]
    for path, _, _ in PAGES:
        out += [md_path(path),
                "  Content-Type: text/markdown; charset=utf-8",
                f'  Link: <{SITE}{path}>; rel="canonical"', ""]
    with open(os.path.join(ROOT, "_headers"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    results = []
    for path, section, blurb in PAGES:
        if add_alternate_link(path):
            print(f"added markdown alternate link to {path}")
        title, desc, md = convert(path)
        out = os.path.join(ROOT, md_path(path).lstrip("/"))
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        results.append((path, section, blurb, title, md))
        print(f"wrote {md_path(path)}  ({len(md):,} chars)")

    # ---------- llms.txt ----------
    L = ["# Carmel Valley Condos", "",
         "> Carmel Valley condos and townhomes for sale in San Diego, CA 92130. "
         "Community guides, sold data, HOA details, and market reports by Sez Sezer, "
         "Keller Williams Realty (DRE #01988197) - 858-436-6585, sez@carmelvalley.com, "
         "12750 High Bluff Drive, San Diego, CA 92130.", "",
         "Every page listed below has a clean Markdown version at the same path "
         "(index.md). Structured community facts are in "
         f"[communities.json]({SITE}/data/communities.json); the full text of every page is in "
         f"[llms-full.txt]({SITE}/llms-full.txt).", ""]
    for section in ("Overview", "Communities", "Guides"):
        L += [f"## {section}", ""]
        for path, sec, blurb, title, _ in results:
            if sec == section:
                name = title.split("|")[0].strip()
                L.append(f"- [{name}]({SITE}{md_path(path)}): {blurb}")
        L.append("")
    L += ["## FAQs", ""]
    for path, sec, blurb, title, md in results:
        n = len(re.findall(r"(?m)^### .+\?$", md))
        if n:
            name = title.split("|")[0].strip()
            L.append(f"- [{name} - FAQs]({SITE}{md_path(path)}): {n} questions and answers "
                     f"(the FAQ section near the end of {SITE}{path}).")
    L += ["", "## Contact", "",
          "- Sez Sezer, Keller Williams Realty, California DRE #01988197",
          "- Phone: [858-436-6585](tel:+18584366585)",
          "- Email: [sez@carmelvalley.com](mailto:sez@carmelvalley.com)",
          "- Office: 12750 High Bluff Drive, San Diego, CA 92130",
          f"- [Free home value estimate]({SITE}/home-value/): request a valuation for a Carmel Valley condo or townhome.",
          "", "## Optional", "",
          f"- [Community data (JSON)]({SITE}/data/communities.json): structured facts per community, with unverified fields flagged.",
          f"- [Full site text]({SITE}/llms-full.txt): all pages above combined into one Markdown file.",
          f"- [Sitemap]({SITE}/sitemap.xml)", ""]
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("wrote /llms.txt")

    # ---------- llms-full.txt ----------
    F = ["# Carmel Valley Condos - Full Site Text", "",
         "> Full text of every key page on carmelvalleycondos.com, combined. "
         "Sez Sezer, Keller Williams Realty, DRE #01988197, 858-436-6585, "
         "sez@carmelvalley.com, 12750 High Bluff Drive, San Diego, CA 92130.", ""]
    for path, _, _, title, md in results:
        # Demote every heading one level so each page sits under one H2.
        body = re.sub(r"(?m)^(#{1,5}) ", r"#\1 ", md)
        F += ["", "---", "", body.strip(), ""]
    with open(os.path.join(ROOT, "llms-full.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(F) + "\n")
    print("wrote /llms-full.txt")

    write_headers()
    print("wrote /_headers")
    write_sitemap()
    print("wrote /sitemap.xml")


if __name__ == "__main__":
    sys.exit(main())
