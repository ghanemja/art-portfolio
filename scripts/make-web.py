#!/usr/bin/env python3
"""Make the in-world copies of the paintings: artworks/web/<name>.webp (≤768 px), and print a
collection.js row for any painting not listed there yet. Needs Pillow (pip install pillow)."""
import glob, os, re
from PIL import Image
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
listed = open(os.path.join(root, 'js', 'collection.js')).read()
os.makedirs(os.path.join(root, 'artworks', 'web'), exist_ok=True)
for f in sorted(glob.glob(os.path.join(root, 'artworks', '*.jpg')) + glob.glob(os.path.join(root, 'artworks', '*.png'))):
    name = os.path.splitext(os.path.basename(f))[0]
    out = os.path.join(root, 'artworks', 'web', name + '.webp')
    im = Image.open(f)
    w, h = im.size
    if not os.path.exists(out):
        im = im.convert('RGB'); im.thumbnail((768, 768), Image.LANCZOS); im.save(out, 'WEBP', quality=82)
        print('made', os.path.relpath(out, root))
    if f"file: '{name}'" not in listed:
        print(f"  {{ file: '{name}', title: 'Untitled', year: '', medium: '', w: {w}, h: {h} }},")
