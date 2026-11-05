"""Painting Doodles: an Instagram reel for one painting.

A crayon doodle of the painting is scribbled onto paper, the real painting pops
in with a bounce (and a soft pop), then it comes alive: a slow push-in with
2.5D parallax, a light sweep across the varnish, a few twinkles, and a title
card with the artist's name.

    python3 render_reel.py art_IMG_0658 [art_IMG_5557 ...] [--res 1080] [--still FRAME] [--out out/]

The doodle is made from the painting itself: it is posterised into a handful of
big colour shapes, and each shape is hatched and outlined in its own colour.
Needs numpy, scipy, Pillow, opencv-python-headless and ffmpeg.
"""
import argparse, json, math, os, re, subprocess, sys, zlib
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import soundtrack  # noqa: E402

FPS = 30


# ------------------------------------------------------------------ collection
def load_collection():
    src = open(os.path.join(REPO, "js", "collection.js"), encoding="utf-8").read()
    artist = re.search(r"name:\s*'([^']*)'", src).group(1)
    works = {}
    for m in re.finditer(r"\{\s*file:\s*'([^']+)'(.*?)\}", src):
        body = m.group(2)
        t = re.search(r"title:\s*'((?:[^'\\]|\\.)*)'", body)
        works[m.group(1)] = dict(title=t.group(1).replace("\\'", "'") if t else m.group(1),
                                 oval="shape: 'oval'" in body)
    return artist, works


# ------------------------------------------------------------------ helpers
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def smooth_noise_1d(n, rng, scale=1.0, terms=4):
    """A smooth wobble along a stroke: sum of a few low-frequency sines."""
    x = np.linspace(0, 1, n)
    out = np.zeros(n)
    for _ in range(terms):
        k = rng.uniform(1, 6)
        out += np.sin(2 * np.pi * k * x + rng.uniform(0, 6.28)) / k
    return out * scale


def crayon_colour(rgb, darker=False):
    hsv = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0, 0].astype(float)
    hsv[1] = min(255, hsv[1] * 1.3 + 12)
    if darker:
        hsv[2] *= 0.55
        hsv[1] = min(255, hsv[1] * 1.1)
    else:
        hsv[2] = min(222, hsv[2] * 1.05 + 6)
        if hsv[1] < 40:  # near-white/grey shapes: a soft tinted crayon instead of invisible white
            hsv[1] = 40 if hsv[1] > 8 else 0
            hsv[2] = min(hsv[2], 200)
    return tuple(int(c) for c in cv2.cvtColor(np.uint8([[hsv]]), cv2.COLOR_HSV2RGB)[0, 0])


def resample(pts, step):
    """Even spacing along a polyline (so wobble and reveal are smooth)."""
    pts = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    if L[-1] < 1e-6:
        return pts
    n = max(2, int(L[-1] / step) + 1)
    s = np.linspace(0, L[-1], n)
    return np.stack([np.interp(s, L, pts[:, 0]), np.interp(s, L, pts[:, 1])], 1)


# ------------------------------------------------------------------ the doodle
def make_doodle(paint, box, oval, rng, k=1.0):
    """paint: RGB display-size image. box: (x0, y0, w, h) on the page.
    Returns strokes: list of dict(pts=Nx2 page coords, col, width)."""
    x0, y0, w, h = box
    s = 8.0 * k                                   # analysis scale (display px per work px)
    sw, shh = max(8, int(w / s)), max(8, int(h / s))
    small = cv2.resize(paint, (sw, shh), interpolation=cv2.INTER_AREA)
    small = cv2.pyrMeanShiftFiltering(small, 6, 26)
    valid = np.ones((shh, sw), np.uint8)
    if oval:
        valid[:] = 0
        cv2.ellipse(valid, (sw // 2, shh // 2), (int(sw * 0.47), int(shh * 0.47)), 0, 0, 360, 1, -1)

    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    K = 8
    _, labels, centers = cv2.kmeans(lab, K, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5),
                                    4, cv2.KMEANS_PP_CENTERS)
    labels = labels.reshape(shh, sw).astype(np.uint8)
    labels = cv2.medianBlur(labels, 5)

    total = valid.sum()
    regions = []
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    for ki in range(K):
        m = ((labels == ki) & (valid > 0)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kern)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kern, iterations=2)
        n, cc, stats, _ = cv2.connectedComponentsWithStats(m)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < 0.004 * total:
                continue
            rm = (cc == i).astype(np.uint8)
            col = paint_mean = cv2.mean(cv2.resize(paint, (sw, shh), interpolation=cv2.INTER_AREA), rm)[:3]
            regions.append(dict(mask=rm, area=int(stats[i, cv2.CC_STAT_AREA]), col=paint_mean,
                                cy=stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2))
    # big shapes first (sky, sea), then the smaller things that sit on them
    regions.sort(key=lambda r: -r["area"])

    to_page = lambda p: np.stack([x0 + p[:, 0] * s, y0 + p[:, 1] * s], 1)
    strokes = []

    # the canvas edge, scribbled first
    if oval:
        a = np.linspace(0, 2 * np.pi * 1.08, 220) + rng.uniform(0, 6)
        pts = np.stack([x0 + w / 2 + w / 2 * np.cos(a), y0 + h / 2 + h / 2 * np.sin(a)], 1)
    else:
        c = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0), (x0 + w * 0.15, y0)]
        pts = resample(c, 6)
    pts = resample(pts, 5)
    n = len(pts)
    pts = pts + np.stack([smooth_noise_1d(n, rng, 10 * k), smooth_noise_1d(n, rng, 10 * k)], 1)
    strokes.append(dict(pts=pts, col=(70, 60, 55), width=7, kind="edge"))

    spacing = 23.0 * k / s
    for r in regions:
        m = r["mask"]
        fill = crayon_colour(r["col"])
        line = crayon_colour(r["col"], darker=True)
        # zig-zag hatching across the shape
        ang = math.radians(rng.choice([1, -1]) * rng.uniform(22, 62))
        d = np.array([math.cos(ang), math.sin(ang)])
        nrm = np.array([-d[1], d[0]])
        ys, xs = np.nonzero(m)
        P = np.stack([xs, ys], 1).astype(float)
        vs = P @ nrm
        us = P @ d
        open_strokes = []
        for v in np.arange(vs.min() + spacing * 0.5, vs.max(), spacing):
            u = np.arange(us.min() - 1, us.max() + 1, 0.5)
            q = v * nrm + u[:, None] * d
            qi = np.round(q).astype(int)
            ok = (qi[:, 0] >= 0) & (qi[:, 0] < sw) & (qi[:, 1] >= 0) & (qi[:, 1] < shh)
            inside = np.zeros(len(u), bool)
            inside[ok] = m[qi[ok, 1], qi[ok, 0]] > 0
            # runs of "inside"
            edges = np.diff(np.concatenate([[0], inside.astype(int), [0]]))
            starts, ends = np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0] - 1
            new_open = []
            for a_, b_ in zip(starts, ends):
                if b_ - a_ < 3:
                    continue
                pa, pb = q[a_] + d * 0.6, q[b_] - d * 0.6
                best = None
                for si, st in enumerate(open_strokes):
                    e = st[-1]
                    da, db = np.linalg.norm(e - pa), np.linalg.norm(e - pb)
                    dd = min(da, db)
                    if dd < spacing * 2.6 and (best is None or dd < best[0]):
                        best = (dd, si, da <= db)
                if best is not None:
                    st = open_strokes.pop(best[1])
                    st.extend([pa, pb] if best[2] else [pb, pa])
                    new_open.append(st)
                else:
                    new_open.append([pa, pb])
            for st in open_strokes:  # finished
                if len(st) >= 2:
                    strokes.append(dict(pts=to_page(np.array(st)), col=fill, width=10, kind="hatch"))
            open_strokes = new_open
        for st in open_strokes:
            strokes.append(dict(pts=to_page(np.array(st)), col=fill, width=10, kind="hatch"))
        # outline
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            if len(c) < 12:
                continue
            c = cv2.approxPolyDP(c, 1.0, True)[:, 0, :].astype(float)
            c = np.concatenate([c, c[:2]])
            pg = resample(to_page(c), 5)
            n = len(pg)
            pg = pg + np.stack([smooth_noise_1d(n, rng, 7 * k), smooth_noise_1d(n, rng, 7 * k)], 1)
            strokes.append(dict(pts=pg, col=line, width=6, kind="outline"))

    # jitter hatching a little so it looks hand made
    for st in strokes:
        if st["kind"] == "hatch":
            st["pts"] = resample(st["pts"], 6)
            st["pts"] = st["pts"] + rng.normal(0, 2.2 * k, st["pts"].shape)
    return strokes


# ------------------------------------------------------------------ the reel
def build(name, res, out_dir, still=None, artist=None, works=None, seed=None):
    W, H = res, int(round(res * 16 / 9))
    k = W / 1080.0
    work = works[name]
    rng = np.random.default_rng(seed if seed is not None else zlib.crc32(name.encode()))

    src = cv2.cvtColor(cv2.imread(os.path.join(REPO, "artworks", name + ".jpg")), cv2.COLOR_BGR2RGB)
    oval = work["oval"]
    ih, iw = src.shape[:2]
    maxw, maxh = 900 * k, 1060 * k
    sc = min(maxw / iw, maxh / ih)
    w, h = int(iw * sc), int(ih * sc)
    cx, cy = W / 2, 860 * k
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    paint = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)

    # timeline (frames)
    T_DRAW0, T_DRAW1 = 10, 130
    T_POP = 138
    T_SWEEP = T_POP + 40
    T_TITLE = T_POP + 100
    N = T_TITLE + 95

    # ---------------- paper
    mean_col = paint.reshape(-1, 3).mean(0)
    paper_col = 0.93 * np.array([247, 243, 236]) + 0.07 * mean_col
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    grain = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.2)
    fibre = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 9)
    vign = 1 - 0.10 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    paper = paper_col[None, None, :] * (vign * (1 + 0.025 * grain + 0.035 * fibre))[..., None]
    paper = np.clip(paper, 0, 255).astype(np.float32)
    # crayon tooth: wax only catches the paper's high points
    tooth = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.9)
    tooth = np.clip((tooth + 0.9) / 1.3, 0.0, 1.0) ** 0.8
    tooth = 0.25 + 0.75 * tooth

    # ---------------- doodle strokes
    strokes = make_doodle(paint, (x0, y0, w, h), oval, rng, k)
    for st in strokes:
        st["pts"] = st["pts"].astype(np.float32)
        seg = np.linalg.norm(np.diff(st["pts"], axis=0), axis=1)
        st["cum"] = np.concatenate([[0], np.cumsum(seg)])
        st["len"] = float(st["cum"][-1])
    total_len = sum(st["len"] for st in strokes)
    starts = np.cumsum([0] + [st["len"] for st in strokes[:-1]])
    for st, a in zip(strokes, starts):
        st["start"] = a

    def pen_at(f):
        t = (f - T_DRAW0) / (T_DRAW1 - T_DRAW0)
        t = min(1, max(0, t))
        return total_len * (0.6 * t + 0.4 * ease(t))  # quick start, eases into the finish

    # ---------------- painting with alpha, shadow, depth
    alpha = np.zeros((h, w), np.float32)
    if oval:
        cv2.ellipse(alpha, (w // 2, h // 2), (int(w * 0.485), int(h * 0.485)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    else:
        alpha[:] = 1
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
    pad = int(40 * k)
    rgba = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    rgba[..., :3] = cv2.copyMakeBorder(paint, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    rgba[pad:pad + h, pad:pad + w, 3] = alpha
    shadow = cv2.GaussianBlur(rgba[..., 3], (0, 0), 14 * k)

    # fake depth for the parallax: sky/top far, foreground near, detail a touch nearer
    gray = cv2.cvtColor(paint, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    detail = cv2.GaussianBlur(np.abs(cv2.Laplacian(cv2.GaussianBlur(gray, (0, 0), 2), cv2.CV_32F)), (0, 0), 12)
    detail /= detail.max() + 1e-6
    vy = np.linspace(0, 1, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)
    depth = 0.75 * vy ** 1.2 + 0.25 * detail
    depth = cv2.GaussianBlur(depth, (0, 0), 30 * k)
    depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-6)
    # gentle shimmer on water-ish blues in the lower half
    hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV).astype(np.float32)
    water = ((hsv[..., 0] > 85) & (hsv[..., 0] < 130) & (hsv[..., 1] > 60)).astype(np.float32) * (vy > 0.35)
    water = cv2.GaussianBlur(water, (0, 0), 6)
    lum = gray

    # twinkle spots: bright local maxima
    g2 = cv2.GaussianBlur(gray, (0, 0), 3)
    peaks = (g2 == cv2.dilate(g2, np.ones((25, 25), np.uint8))) & (g2 > np.percentile(g2, 92)) & (alpha > 0.99)
    pys, pxs = np.nonzero(peaks)
    order = rng.permutation(len(pys))[:18]
    twinkles = [(pxs[i], pys[i], rng.uniform(0, 1), rng.uniform(0.7, 1.3)) for i in order]

    # pop burst confetti, in the doodle's brightest crayons
    fills = [st["col"] for st in strokes if st["kind"] == "hatch"]
    bright = sorted(set(fills), key=lambda c: -(max(c) - min(c)))[:5] or [(240, 120, 120)]
    bright = [crayon_colour(c) for c in bright]
    burst = []
    for i in range(16):
        a = rng.uniform(0, 2 * np.pi)
        burst.append((a, rng.uniform(0.8, 1.3), rng.uniform(7, 13) * k, None))

    # ---------------- title card
    title_img = render_title(W, H, k, work["title"], artist, y_top=y0 + h + 95 * k, ink=(66, 56, 52))

    # ---------------- sound events
    events = dict(fps=FPS, frames=N, draw=[T_DRAW0, T_DRAW1], pop=T_POP, sweep=T_SWEEP,
                  title=T_TITLE, twinkles=[])

    ink = np.zeros((H, W, 3), np.float32)
    ink_a = np.zeros((H, W), np.float32)
    drawn_upto = 0.0

    def draw_ink(L0, L1):
        for st in strokes:
            a, b = st["start"], st["start"] + st["len"]
            if b <= L0 or a >= L1:
                continue
            lo, hi = max(0, L0 - a), min(st["len"], L1 - a)
            i0 = max(0, np.searchsorted(st["cum"], lo) - 1)
            i1 = np.searchsorted(st["cum"], hi)
            seg = st["pts"][i0:i1 + 1]
            if i1 < len(st["pts"]) and hi < st["len"]:
                # stop part way along the last segment
                j = min(i1, len(st["pts"]) - 1)
                if j > 0:
                    t = (hi - st["cum"][j - 1]) / max(1e-6, st["cum"][j] - st["cum"][j - 1])
                    endp = st["pts"][j - 1] + (st["pts"][j] - st["pts"][j - 1]) * t
                    seg = np.concatenate([st["pts"][i0:j], endp[None]], 0)
            if len(seg) < 2:
                continue
            wdt = max(1, int(st["width"] * k))
            bx0 = max(0, int(seg[:, 0].min()) - wdt - 2); by0 = max(0, int(seg[:, 1].min()) - wdt - 2)
            bx1 = min(W, int(seg[:, 0].max()) + wdt + 3); by1 = min(H, int(seg[:, 1].max()) + wdt + 3)
            if bx1 <= bx0 or by1 <= by0:
                continue
            p = np.round((seg - [bx0, by0]) * 4).astype(np.int32).reshape(-1, 1, 2)
            m = np.zeros((by1 - by0, bx1 - bx0), np.uint8)
            cv2.polylines(m, [p], False, 255, wdt, cv2.LINE_AA, shift=2)
            mf = (m.astype(np.float32) / 255)[..., None]
            sub = ink[by0:by1, bx0:bx1]
            ao = ink_a[by0:by1, bx0:bx1][..., None]
            an = ao * (1 - mf) + mf
            sub[:] = (sub * ao * (1 - mf) + np.array(st["col"], np.float32) * mf) / np.maximum(an, 1e-4)
            ink_a[by0:by1, bx0:bx1] = an[..., 0]

    def place_rgb(img4, s, ox, oy, dst_shape):
        hh, ww = img4.shape[:2]
        M = np.array([[s, 0, ox - s * ww / 2], [0, s, oy - s * hh / 2]], np.float32)
        return cv2.warpAffine(np.ascontiguousarray(img4[..., :3]), M, (dst_shape[1], dst_shape[0]),
                              flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    def place(img4, s, ox, oy, dst_shape):
        """Scale img4 (with pad) about its centre and put that centre at (ox, oy)."""
        hh, ww = img4.shape[:2]
        M = np.array([[s, 0, ox - s * ww / 2], [0, s, oy - s * hh / 2]], np.float32)
        return cv2.warpAffine(img4, M, (dst_shape[1], dst_shape[0]), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    frames_to_do = [still] if still is not None else range(N)
    proc = None
    if still is None:
        os.makedirs(out_dir, exist_ok=True)
        wav = os.path.join(out_dir, f".{name}.wav")
        mp4 = os.path.join(out_dir, f"{name}.mp4")

    ix = np.arange(w + 2 * pad, dtype=np.float32)[None, :].repeat(h + 2 * pad, 0)
    iy = np.arange(h + 2 * pad, dtype=np.float32)[:, None].repeat(w + 2 * pad, 1)
    depth_p = np.pad(depth, pad, mode="edge")
    water_p = np.pad(water, pad)
    lum_p = np.pad(lum, pad)

    out_frames = []
    for f in (range(N) if still is None else range(still + 1)):
        # doodle grows
        L = pen_at(f)
        if L > drawn_upto:
            draw_ink(drawn_upto, L)
            drawn_upto = L
        if still is not None and f != still:
            continue

        frame = paper.copy()
        # doodle layer (fades as the painting lands)
        dfade = 1.0 if f < T_POP else max(0.0, 1 - (f - T_POP) / 6)
        if dfade > 0:
            a = (ink_a * tooth * dfade)[..., None]
            frame = frame * (1 - a) + ink * a

        if f >= T_POP - 1:
            tp = f - T_POP
            keys = [(-1, 0.0), (0, 0.45), (4, 1.10), (8, 0.965), (12, 1.015), (16, 1.0)]
            if tp >= 16:
                s_pop = 1.0
            else:
                s_pop = float(np.interp(tp, [a for a, _ in keys], [b for _, b in keys]))
            # slow push in + drift after the pop
            ta = max(0.0, (f - T_POP - 14) / (N - T_POP - 14))
            s_push = 1 + 0.07 * ease(ta)
            tt = (f - T_POP) / FPS
            camx = math.sin(tt * 2 * math.pi / 7.0) * ease(min(1, ta * 3))
            camy = math.sin(tt * 2 * math.pi / 9.0 + 1.0) * ease(min(1, ta * 3))
            img = rgba
            if tp > 10:
                amp = 13 * k
                dx = (depth_p - 0.5) * amp * camx
                dy = (depth_p - 0.5) * amp * 0.6 * camy
                sh = water_p * 1.6 * k * np.sin(iy * 0.09 / k - tt * 3.2 + ix * 0.012)
                mapx = (ix - dx).astype(np.float32)
                mapy = (iy - dy + sh).astype(np.float32)
                img = cv2.remap(rgba, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
                img[..., 3] = rgba[..., 3]
                # light sweep across the varnish
                ts = (f - T_SWEEP) / 40.0
                if 0 <= ts <= 1:
                    band_pos = -0.3 + 1.6 * ts
                    u = (ix / (w + 2 * pad)) * 0.8 + (iy / (h + 2 * pad)) * 0.4
                    band = np.exp(-((u - band_pos) / 0.11) ** 2)
                    img = img.copy()
                    img[..., :3] += (band * (40 + 60 * lum_p))[..., None]
            s = s_pop * s_push
            ox = cx + 6 * k * camx
            oy = cy + 4 * k * camy
            sh_layer = place(shadow, s * 1.02, ox + 4 * k, oy + 16 * k * s, (H, W))
            frame *= (1 - 0.32 * sh_layer)[..., None]
            lay = place(img, s, ox, oy, (H, W))
            a = np.clip(lay[..., 3:4], 0, 1)
            # rgb is premultiplied by the warp's border (0), so un-premultiply via a separate warp of rgb
            frame = frame * (1 - a) + np.clip(place_rgb(img, s, ox, oy, (H, W)), 0, 255) * a

            # confetti dots of crayon colour flying out at the pop
            if 0 <= tp < 22:
                for (ang, sp, rad, si) in burst:
                    r0 = 0.5 * max(w, h) * 0.75
                    dist = r0 + sp * 260 * k * (1 - (1 - tp / 22) ** 2)
                    px = cx + math.cos(ang) * dist * (w / max(w, h) + 0.2)
                    py = cy + math.sin(ang) * dist * (h / max(w, h) + 0.2)
                    al = 1 - tp / 22
                    col = bright[int(ang * 100) % len(bright)]
                    ov = frame.copy()
                    cv2.circle(ov, (int(px), int(py)), int(rad), col, -1, cv2.LINE_AA)
                    frame = frame * (1 - al) + ov * al

            # twinkles
            if tp > 30:
                for (tx, ty, ph, spd) in twinkles:
                    v = math.sin(2 * math.pi * (tt * 0.45 * spd + ph))
                    if v < 0.75:
                        continue
                    a_t = ((v - 0.75) / 0.25) ** 2
                    px = ox + (tx - w / 2) * s
                    py = oy + (ty - h / 2) * s
                    draw_star(frame, px, py, 15 * k * (0.6 + 0.6 * a_t), a_t)
                    if still is None and v > 0.98 and (not events["twinkles"] or f - events["twinkles"][-1] > 8):
                        events["twinkles"].append(f)

        if f >= T_TITLE:
            ta = ease((f - T_TITLE) / 18)
            shift = int((1 - ta) * 30 * k)
            ti = np.roll(title_img, shift, axis=0) if shift else title_img
            a = ti[..., 3:4] * ta
            frame = frame * (1 - a) + ti[..., :3] * a

        out = np.clip(frame, 0, 255).astype(np.uint8)
        if still is not None:
            return out
        if proc is None:
            proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                     "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                                     os.path.join(out_dir, f".{name}.video.mp4")], stdin=subprocess.PIPE)
        proc.stdin.write(out.tobytes())
        if f in (T_DRAW0 + 60, T_POP + 2, T_POP + 70, N - 2):
            out_frames.append(out)
    proc.stdin.close(); proc.wait()

    soundtrack.make(events, wav, seed=int(rng.integers(1 << 30)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out_dir, f".{name}.video.mp4"), "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4],
                   check=True)
    os.remove(os.path.join(out_dir, f".{name}.video.mp4")); os.remove(wav)
    with open(os.path.join(out_dir, f".{name}.events.json"), "w") as fh:
        json.dump(events, fh)
    return out_frames


def draw_star(frame, x, y, r, a):
    """A soft four-point twinkle, added on top."""
    x0, y0 = int(x - r * 2), int(y - r * 2)
    sz = int(r * 4) + 1
    if x0 < 0 or y0 < 0 or x0 + sz >= frame.shape[1] or y0 + sz >= frame.shape[0]:
        return
    yy, xx = np.mgrid[0:sz, 0:sz].astype(np.float32)
    dx, dy = (xx - sz / 2) / r, (yy - sz / 2) / r
    star = np.exp(-(np.abs(dx) * 6 + dy ** 2 * 0.6)) + np.exp(-(np.abs(dy) * 6 + dx ** 2 * 0.6))
    star += 0.8 * np.exp(-(dx ** 2 + dy ** 2) * 4)
    star = np.clip(star, 0, 1.4) * a
    frame[y0:y0 + sz, x0:x0 + sz] += star[..., None] * np.array([255, 250, 225], np.float32) * 0.9
    np.clip(frame, 0, 255, out=frame)


def render_title(W, H, k, title, artist, y_top, ink):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fdir = os.path.join(REPO, "fonts")
    size = 84
    f1 = ImageFont.truetype(os.path.join(fdir, "caveat-latin-700-normal.woff2"), int(size * k))
    while d.textlength(title, font=f1) > W - 120 * k and size > 40:
        size -= 4
        f1 = ImageFont.truetype(os.path.join(fdir, "caveat-latin-700-normal.woff2"), int(size * k))
    f2 = ImageFont.truetype(os.path.join(fdir, "patrick-hand-latin-400-normal.woff2"), int(44 * k))
    y_top = min(y_top, H - 300 * k)
    d.text((W / 2, y_top), title, font=f1, fill=(*ink, 255), anchor="mt")
    yb = y_top + size * k * 1.15
    # a little crayon underline
    rng = np.random.default_rng(1)
    tw = d.textlength(title, font=f1) * 0.6
    xs = np.linspace(W / 2 - tw / 2, W / 2 + tw / 2, 40)
    ys = yb + 6 * k + np.cumsum(rng.normal(0, 0.6, 40)) * k
    d.line(list(zip(xs, ys)), fill=(232, 120, 120, 220), width=int(6 * k), joint="curve")
    d.text((W / 2, yb + 34 * k), artist, font=f2, fill=(*ink, 220), anchor="mt")
    return np.asarray(img).astype(np.float32) * np.array([1, 1, 1, 1 / 255], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+", help="file names from js/collection.js, e.g. art_IMG_0658")
    ap.add_argument("--res", type=int, default=1080, help="output width (height is 16:9 taller)")
    ap.add_argument("--still", type=int, default=None, help="only render this frame to a PNG")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    artist, works = load_collection()
    for n in a.names:
        if n not in works:
            sys.exit(f"{n} is not in js/collection.js")
        if a.still is not None:
            img = build(n, a.res, a.out, still=a.still, artist=artist, works=works, seed=a.seed)
            os.makedirs(a.out, exist_ok=True)
            p = os.path.join(a.out, f"{n}_still_{a.still:04d}.png")
            Image.fromarray(img).save(p); print(p)
        else:
            frames = build(n, a.res, a.out, artist=artist, works=works, seed=a.seed)
            os.makedirs(os.path.join(a.out, ".sheets"), exist_ok=True)
            sheet = np.concatenate([cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA) for fr in frames], 1)
            Image.fromarray(sheet).save(os.path.join(a.out, ".sheets", n + ".png"))
            print("done", n)


if __name__ == "__main__":
    main()
