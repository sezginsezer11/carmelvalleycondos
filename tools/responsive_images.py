#!/usr/bin/env python3
"""Give every <img src="/images/..."> on the site its size and smaller copies.

For each photo tag on each page this adds, when missing:
  - width / height    the file's real pixel size, so the page doesn't jump
                      while the photo loads (CLS)
  - srcset / sizes    the smaller WebP copies in /images (NAME-640.webp,
                      NAME-960.webp, NAME-1280.webp) so phones download a
                      small file instead of the full-size original

The original file stays as src (and as the largest srcset entry unless a
-1280 copy exists), so og:image, schema and old links keep working.
A generator can set its own sizes="..." on a tag; otherwise a default is used.

Making the WebP copies for a NEW photo needs Pillow (not part of the build):
    python3 -m venv /tmp/img && /tmp/img/bin/pip install pillow
    then save 640 / 960 / 1280 px wide WebP copies at quality 74, and keep a
    copy only if it is clearly smaller than the original.

Run directly, or let tools/build_llm_files.py run it (it does, first).
    python3 tools/responsive_images.py
Stdlib only.
"""
import glob
import os
import re
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTHS = (640, 960, 1280)
DEFAULT_SIZES = "(max-width: 900px) 100vw, 50vw"
IMG_RE = re.compile(r"<img\b[^>]*>")


def image_size(path):
    """(width, height) of a JPEG, PNG or WebP file, or None."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X":
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L":
            b = int.from_bytes(data[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        return None
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def add_attrs(tag, attrs):
    end = "/>" if tag.endswith("/>") else ">"
    return tag[: -len(end)].rstrip() + "".join(f' {k}="{v}"' for k, v in attrs) + end


def fix_tag(tag):
    m = re.search(r'\ssrc="(/images/[^"?#]+)"', tag)
    if not m:
        return tag
    src = m.group(1)
    path = os.path.join(ROOT, src.lstrip("/"))
    size = image_size(path)
    attrs = []
    if size and not re.search(r"\swidth=", tag) and not re.search(r"\sheight=", tag):
        attrs += [("width", size[0]), ("height", size[1])]
    if "srcset=" not in tag and size:
        base = os.path.splitext(src)[0]
        cands, has_large = [], False
        for w in WIDTHS:
            u = f"{base}-{w}.webp"
            s = image_size(os.path.join(ROOT, u.lstrip("/")))
            if s:
                cands.append((s[0], u))   # real width (a "-1280" copy of a 1275px photo is 1275w)
                has_large = has_large or w == WIDTHS[-1]
        if cands:
            if not has_large:
                cands.append((size[0], src))
            attrs.append(("srcset", ", ".join(f"{u} {w}w" for w, u in cands)))
            if "sizes=" not in tag:
                attrs.append(("sizes", DEFAULT_SIZES))
    return add_attrs(tag, attrs) if attrs else tag


def pages():
    return [os.path.join(ROOT, "index.html")] + sorted(glob.glob(os.path.join(ROOT, "*", "index.html")))


def fix_page(fp):
    with open(fp, encoding="utf-8") as f:
        s = f.read()
    s2 = IMG_RE.sub(lambda m: fix_tag(m.group(0)), s)
    if s2 == s:
        return False
    mode = os.stat(fp).st_mode
    os.chmod(fp, mode | 0o200)   # index.html is kept read-only
    try:
        with open(fp, "w", encoding="utf-8") as f:
            f.write(s2)
    finally:
        os.chmod(fp, mode)
    return True


def main():
    for fp in pages():
        if fix_page(fp):
            print("responsive images:", os.path.relpath(fp, ROOT))


if __name__ == "__main__":
    main()
