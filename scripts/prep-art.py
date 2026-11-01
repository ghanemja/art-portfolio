#!/usr/bin/env python3
"""Make the gallery's pictures from the original photos in artworks/originals/:
  - crop away the wall / table / backdrop around the canvas (found by its difference from the
    colour round the photo's edge), leaving just the painting;
  - turn the ones photographed sideways the right way up (ROTATE below);
  - notice round canvases, so they hang in oval frames (collection.js shape: 'oval');
then write artworks/<name>.jpg (full size, for the close look), artworks/web/<name>.webp (≤768 px,
in-world), and update each painting's size and shape in js/collection.js.
Needs Pillow and numpy:  pip install pillow numpy
Fix a bad crop by hand in CROP (fractions of the original: left, top, right, bottom)."""
import glob, os, re
from collections import deque
import numpy as np
from PIL import Image, ImageOps

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# photographed lying sideways (the sky on the right): turn a quarter anticlockwise
ROTATE = {n: 90 for n in ['IMG_9596', 'IMG_9597', 'IMG_9603', 'IMG_9606', 'IMG_9607', 'IMG_9608', 'IMG_9609',
                          'IMG_9610', 'IMG_9613', 'IMG_9615', 'IMG_9618', 'IMG_9620', 'IMG_9623']}
CROP = {'IMG_5557': ((0.059, 0.218, 0.802, 0.776), True), 'IMG_8352': ((0, 0, 1, 1), True),
        'IMG_8538': ((0.112, 0.15, 0.855, 0.7115), True)}   # name → ((l, t, r, b), round?) to override the automatic crop
# the paint runs to the photo's edges (a thin strip of something else doesn't count): leave them be
NO_CROP = {'IMG_0658', 'IMG_5263', 'IMG_7208', 'IMG_9506', 'IMG_9595', 'IMG_9621', 'cows_in_storm', 'space_heist_mice'}

def ycc(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return np.stack([y, (b - y) * 0.564, (r - y) * 0.713], -1)

def find(im):
    """→ (l, t, r, b) fractions of the canvas in the photo, and whether it's round; None: no backdrop"""
    sm = im.copy(); sm.thumbnail((260, 260)); a = ycc(np.asarray(sm.convert('RGB'), dtype=np.float32))
    h, w = a.shape[:2]; e = max(2, int(min(h, w) * 0.04))
    border = np.concatenate([a[:e].reshape(-1, 3), a[-e:].reshape(-1, 3), a[:, :e].reshape(-1, 3), a[:, -e:].reshape(-1, 3)])
    bg = np.median(border, 0)
    dist = lambda x: np.sqrt(((x - bg) * np.array([0.35, 1.6, 1.6])) ** 2).sum(-1) if False else np.sqrt((((x - bg) * np.array([0.35, 1.6, 1.6])) ** 2).sum(-1))
    if (dist(border) < 26).mean() < 0.55: return None            # the art runs to the photo's edges
    fg = dist(a) > 26
    for _ in range(2):                                             # tidy: a 3×3 majority vote
        p = np.pad(fg, 1).astype(np.int8)
        fg = sum(p[i:i + h, j:j + w] for i in range(3) for j in range(3)) >= 5
    # the biggest connected blob
    lab = np.zeros((h, w), np.int32); best, bestn, cur = 0, 0, 0
    for sy in range(h):
        for sx in range(w):
            if not fg[sy, sx] or lab[sy, sx]: continue
            cur += 1; q = deque([(sy, sx)]); lab[sy, sx] = cur; n = 0
            while q:
                y, x = q.popleft(); n += 1
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < h and 0 <= xx < w and fg[yy, xx] and not lab[yy, xx]: lab[yy, xx] = cur; q.append((yy, xx))
            if n > bestn: best, bestn = cur, n
    m = lab == best
    ys, xs = np.where(m)
    t, b, l, r = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    # round (or oval): about π/4 of its box filled, and all four corners empty
    box = m[t:b, l:r]; ch, cw = max(1, (b - t) // 8), max(1, (r - l) // 8)
    corners = [box[:ch, :cw].mean(), box[:ch, -cw:].mean(), box[-ch:, :cw].mean(), box[-ch:, -cw:].mean()]
    round_ = 0.68 < box.mean() < 0.86 and max(corners) < 0.2
    if round_:
        if (b - t) * (r - l) > 0.94 * h * w: return None
        return (l / w, t / h, r / w, b / h), True
    # trim ragged edges: rows / columns less than half full (shadows, the canvas's side)
    while b - t > 8 and m[t, l:r].mean() < 0.5: t += 1
    while b - t > 8 and m[b - 1, l:r].mean() < 0.5: b -= 1
    while r - l > 8 and m[t:b, l].mean() < 0.5: l += 1
    while r - l > 8 and m[t:b, r - 1].mean() < 0.5: r -= 1
    if (b - t) * (r - l) > 0.94 * h * w: return None
    dx, dy = (r - l) * 0.015, (b - t) * 0.015                      # a sliver in from the edge: no backdrop left
    l, r, t, b = l + dx, r - dx, t + dy, b - dy
    return (l / w, t / h, r / w, b / h), False

def main():
    col_path = os.path.join(ROOT, 'js', 'collection.js'); col = open(col_path).read()
    os.makedirs(os.path.join(ROOT, 'artworks', 'web'), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(ROOT, 'artworks', 'originals', '*.jpg'))):
        name = os.path.splitext(os.path.basename(f))[0]; key = name.replace('art_', '')
        im = ImageOps.exif_transpose(Image.open(f)).convert('RGB')
        found = None if key in NO_CROP else CROP[key] if key in CROP else find(im)
        shape = 'rect'
        if found:
            (l, t, r, b), rnd = found
            im = im.crop((round(l * im.width), round(t * im.height), round(r * im.width), round(b * im.height)))
            if rnd: shape = 'oval'
        if key in ROTATE: im = im.rotate(ROTATE[key], expand=True)
        im.save(os.path.join(ROOT, 'artworks', name + '.jpg'), quality=90)
        sm = im.copy(); sm.thumbnail((768, 768), Image.LANCZOS); sm.save(os.path.join(ROOT, 'artworks', 'web', name + '.webp'), 'WEBP', quality=82)
        # its row in collection.js: the new size, and the frame's shape
        pat = re.compile(r"(\{ file: '" + re.escape(name) + r"'[^\n]*?)w: \d+, h: \d+(, shape: '\w+')?")
        col, n = pat.subn(lambda mm: mm.group(1) + f"w: {im.width}, h: {im.height}" + (", shape: 'oval'" if shape == 'oval' else ''), col)
        print(f"{name:34s} {'cropped' if found else '-------'} {shape:5s} {im.width}×{im.height}" + (' (turned)' if key in ROTATE else '') + ('' if n else '  ← not in collection.js'))
    open(col_path, 'w').write(col)

if __name__ == '__main__':
    main()
