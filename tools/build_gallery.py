#!/usr/bin/env python3
"""Build the gallery: previews + cards in index.html.

Usage:  python3 tools/build_gallery.py

Reads gallery.json (sections, files, captions) and:
  * creates thumbs/<section>/<name>.webp  (640px wide, for the grid)
  * creates web/<section>/<name>.webp     (full resolution, fast first view)
  * rewrites the blocks between the GALLERY / NAV markers in index.html

The original PNGs are never modified; the viewer swaps to them when zooming,
and they are what gets shared / downloaded.
"""
import html
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
THUMB_W = 640
THUMB_Q = 80
WEB_Q = 90


def fresh(dst: Path, src: Path) -> bool:
    return dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime


def make_previews(src: Path, thumb: Path, web: Path):
    with Image.open(src) as im:
        im = im.convert('RGB')
        w, h = im.size
        if not fresh(thumb, src):
            thumb.parent.mkdir(parents=True, exist_ok=True)
            t = im.resize((THUMB_W, round(THUMB_W * h / w)), Image.LANCZOS)
            t.save(thumb, 'WEBP', quality=THUMB_Q, method=6)
        if not fresh(web, src):
            web.parent.mkdir(parents=True, exist_ok=True)
            im.save(web, 'WEBP', quality=WEB_Q, method=6)
    return w, h


def main():
    data = json.loads((ROOT / 'gallery.json').read_text(encoding='utf-8'))
    esc = lambda s: html.escape(s, quote=True)
    sections_html, nav_html = [], []
    n_global = 0
    for sec in data['sections']:
        sid = sec['id']
        cards = []
        for i, item in enumerate(sec['items']):
            src = ROOT / sid / item['file']
            stem = Path(item['file']).stem
            thumb = Path('thumbs') / sid / f'{stem}.webp'
            web = Path('web') / sid / f'{stem}.webp'
            w, h = make_previews(src, ROOT / thumb, ROOT / web)
            m = re.match(r'(\d+)', stem)
            num = m.group(1) if m else f'{i + 1:02d}'
            th = round(THUMB_W * h / w)
            lazy = '' if n_global < 6 else ' loading="lazy"'
            n_global += 1
            cap = esc(item['caption'])
            cards.append(
                f'<a class="card" id="{sid}-{num}" href="#{sid}-{num}" '
                f'data-full="{sid}/{esc(item["file"])}" data-web="{web.as_posix()}" '
                f'data-w="{w}" data-h="{h}">'
                f'<img src="{thumb.as_posix()}" width="{THUMB_W}" height="{th}" alt="{cap}"{lazy} decoding="async" draggable="false" onerror="this.onerror=null;this.src=this.parentNode.dataset.full">'
                f'<span class="cap"><b>{num}</b>{cap}</span><i class="chk" aria-hidden="true"></i></a>'
            )
        count = len(sec['items'])
        sections_html.append(
            f'<section class="sec" id="{sid}" data-title="{esc(sec["title"])}">\n'
            f'<div class="sec-head"><h2>{esc(sec["title"])}</h2><span class="count">{count} תמונות</span>'
            f'<button class="btn sm sel-all" type="button" data-sec="{sid}">בחירת הכל</button></div>\n'
            f'<div class="grid">\n' + '\n'.join(cards) + '\n</div>\n</section>'
        )
        nav_html.append(f'<a href="#{sid}">{esc(sec.get("nav") or sec["title"])}<small>{count}</small></a>')

    page = ROOT / 'index.html'
    text = page.read_text(encoding='utf-8')
    for name, block in (('GALLERY', '\n'.join(sections_html)), ('NAV', ''.join(nav_html))):
        pat = re.compile(rf'(<!--{name}:START-->).*?(<!--{name}:END-->)', re.S)
        if not pat.search(text):
            raise SystemExit(f'marker {name} not found in index.html')
        text = pat.sub(lambda m: m.group(1) + '\n' + block + '\n' + m.group(2), text)
    page.write_text(text, encoding='utf-8')
    print(f'ok: {n_global} images')


if __name__ == '__main__':
    main()
