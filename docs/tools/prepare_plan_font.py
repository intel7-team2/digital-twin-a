"""Subset the installed reference heading font for browser/PDF rendering.

Requires fonttools. Re-serializing cmap also fixes Chromium's rejection of the
installed legacy font's sentinel glyph reference. Only document title/heading
characters are included; the original system font remains unchanged.
"""
from pathlib import Path
import html
import re
import sys
from fontTools import subset
from fontTools.ttLib import TTFont

base = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('C:/Windows/Fonts/H2HDRM.TTF')
plan = base / (sys.argv[2] if len(sys.argv) > 2 else 'plan_v0.8.html')
markup = plan.read_text(encoding='utf-8')
headings = re.findall(r'<h[12][^>]*>(.*?)</h[12]>|<div class="task">(.*?)</div>', markup, re.S)
text = html.unescape(' '.join(re.sub(r'<[^>]+>', ' ', a or b) for a, b in headings))
font = TTFont(source)
if font['OS/2'].fsType & 2:
    raise ValueError('Reference font prohibits document embedding')
missing = {ord(c) for c in text if not c.isspace()} - font.getBestCmap().keys()
if missing:
    raise ValueError(f'Reference font lacks heading characters: {missing}')
options = subset.Options()
options.recalc_timestamp = False
worker = subset.Subsetter(options=options)
worker.populate(text=text)
worker.subset(font)
target = base / 'assets' / f'{plan.stem}-headline.ttf'
font.save(target)
print(f'Prepared {target.name}: {len(set(text))} heading characters')
