"""Painting Doodles: an Instagram reel for one painting.

A crayon doodle of the painting is scribbled onto paper, real paint floods into
each crayon shape (a soft bloop each), the outlines wash away, the painting
settles with a little bounce, then parts of it come alive (water flows, trees
sway, clouds drift; see animate.py) with ambient sound, while the artist's handle
fades in at the bottom.

    python3 render_reel.py art_IMG_0658 [art_IMG_5557 ...] [--res 1080] [--still FRAME] [--out out/] [--handle @name]

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
import animate  # noqa: E402
import unwrap  # noqa: E402

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

    sx, sy = w / sw, h / shh   # exact registration: small grid -> the painting's box
    to_page = lambda p: np.stack([x0 + (p[:, 0] + 0.5) * sx, y0 + (p[:, 1] + 0.5) * sy], 1)
    strokes = []

    # the canvas edge, scribbled first
    if oval:
        a = np.linspace(0, 2 * np.pi * 1.08, 220) + rng.uniform(0, 6)
        pts = np.stack([x0 + w / 2 + w * 0.485 * np.cos(a), y0 + h / 2 + h * 0.485 * np.sin(a)], 1)
    else:
        c = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0), (x0 + w * 0.15, y0)]
        pts = resample(c, 6)
    pts = resample(pts, 5)
    n = len(pts)
    pts = pts + np.stack([smooth_noise_1d(n, rng, 4 * k), smooth_noise_1d(n, rng, 4 * k)], 1)
    strokes.append(dict(pts=pts, col=(70, 60, 55), width=7, kind="edge", rid=-1))

    spacing = 23.0 * k / s
    for rid, r in enumerate(regions):
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
                    strokes.append(dict(pts=to_page(np.array(st)), col=fill, width=10, kind="hatch", rid=rid))
            open_strokes = new_open
        for st in open_strokes:
            strokes.append(dict(pts=to_page(np.array(st)), col=fill, width=10, kind="hatch", rid=rid))
        # outline
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            if len(c) < 12:
                continue
            c = cv2.approxPolyDP(c, 1.0, True)[:, 0, :].astype(float)
            c = np.concatenate([c, c[:2]])
            pg = resample(to_page(c), 5)
            n = len(pg)
            pg = pg + np.stack([smooth_noise_1d(n, rng, 4 * k), smooth_noise_1d(n, rng, 4 * k)], 1)
            strokes.append(dict(pts=pg, col=line, width=6, kind="outline", rid=rid))

    # jitter hatching a little so it looks hand made
    for st in strokes:
        if st["kind"] == "hatch":
            st["pts"] = resample(st["pts"], 6)
            st["pts"] = st["pts"] + rng.normal(0, 2.2 * k, st["pts"].shape)
    return strokes, [r["mask"] for r in regions]


# ------------------------------------------------------------------ the reel
def build(name, res, out_dir, still=None, artist=None, works=None, seed=None, sheet_frames=None,
          handle="@janelle.builds"):
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
    x0, y0 = int(W / 2 - w / 2), int(860 * k - h / 2)
    cx, cy = x0 + w / 2, y0 + h / 2
    paint = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
    paint_f = paint.astype(np.float32)

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

    # ---------------- doodle strokes, registered to the painting's box
    strokes, rmasks = make_doodle(paint, (x0, y0, w, h), oval, rng, k)
    for st in strokes:
        st["pts"] = st["pts"].astype(np.float32)
        seg = np.linalg.norm(np.diff(st["pts"], axis=0), axis=1)
        st["cum"] = np.concatenate([[0], np.cumsum(seg)])
        st["len"] = float(st["cum"][-1])
    total_len = sum(st["len"] for st in strokes)
    starts = np.cumsum([0] + [st["len"] for st in strokes[:-1]])
    for st, a in zip(strokes, starts):
        st["start"] = a

    # ---------------- timeline (frames)
    nreg = max(1, len(rmasks))
    NW = min(nreg, 12)                       # flood waves; regions grouped in drawing order
    wave_of = [i * NW // nreg for i in range(nreg)]
    STAG, FDUR = 4, 22                       # 0.13 s apart, each floods over ~0.5 s
    T_DRAW0 = unwrap.END + 4                 # after the parcel is unwrapped
    T_DRAW1 = T_DRAW0 + 120
    T_FLOOD = T_DRAW1 + 6
    wave_start = [T_FLOOD + i * STAG for i in range(NW)]
    T_GLOBAL = wave_start[-1] + 8            # last gaps fill in
    GDUR = 14
    T_WASH = T_GLOBAL + 6                    # crayon outlines wash away
    WDUR = 16
    T_DONE = T_GLOBAL + GDUR                 # painting complete: settle bounce
    T_ANIM = T_DONE + 8                      # the painting starts to move as the bounce settles
    T_HANDLE = T_DONE + 40                   # the handle fades in while it moves
    N = T_DONE + 14 + 140                    # ~4.7 s of life after the settle

    if still is not None:
        print(f"timeline: flood {T_FLOOD} done {T_DONE} anim {T_ANIM} handle {T_HANDLE} end {N}", file=sys.stderr)

    def pen_at(f):
        t = (f - T_DRAW0) / (T_DRAW1 - T_DRAW0)
        t = min(1, max(0, t))
        return total_len * (0.6 * t + 0.4 * ease(t))  # quick start, eases into the finish

    # ---------------- painting with alpha and shadow
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
    anim = animate.Animator(name, paint, pad, k, rng)

    # twinkles on the brightest spots, once the painting is alive
    gray = cv2.cvtColor(paint, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    g2 = cv2.GaussianBlur(gray, (0, 0), 3)
    peaks = (g2 == cv2.dilate(g2, np.ones((25, 25), np.uint8))) & (g2 > np.percentile(g2, 92)) & (alpha > 0.99)
    pys, pxs = np.nonzero(peaks)
    order = rng.permutation(len(pys))[:18]
    twinkles = [(pxs[i], pys[i], rng.uniform(0, 1), rng.uniform(0.7, 1.3)) for i in order]

    # ---------------- the flood: paint bleeds out from each region's crayon lines
    def raster(sts, width_mul=1.0):
        m = np.zeros((h, w), np.uint8)
        for st in sts:
            p = np.round((st["pts"] - [x0, y0]) * 4).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(m, [p], False, 255, max(1, int(st["width"] * k * width_mul)), cv2.LINE_AA, shift=2)
        return m

    rough = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 3 * k)
    rough = rough / (rough.std() + 1e-6) * 4 * k
    feather = 3.5 * k
    waves = []
    for wi in range(NW):
        rids = [r for r in range(nreg) if wave_of[r] == wi]
        hm = raster([st for st in strokes if st["kind"] == "hatch" and st["rid"] in rids])
        reg = np.zeros((h, w), np.float32)
        for r in rids:
            reg = np.maximum(reg, cv2.resize(rmasks[r].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR))
        reg = (reg > 0.5).astype(np.uint8)
        reg = cv2.dilate(reg, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(9 * k) | 1, int(9 * k) | 1)))
        soft = cv2.GaussianBlur(reg.astype(np.float32), (0, 0), 3 * k) * alpha
        if hm.max() == 0:
            hm = (reg * 255).astype(np.uint8)
        dist = cv2.distanceTransform((hm < 128).astype(np.uint8), cv2.DIST_L2, 5)
        inside = soft > 0.5
        dmax = float(np.percentile(dist[inside], 99.5)) if inside.any() else 20 * k
        ys_, xs_ = np.nonzero(soft > 0.01)
        bb = (ys_.min(), ys_.max() + 1, xs_.min(), xs_.max() + 1) if len(ys_) else (0, 1, 0, 1)
        waves.append(dict(start=wave_start[wi], dist=dist, soft=soft, dmax=dmax + 12 * k, bb=bb))
    all_lines = raster(strokes)
    dist_all = cv2.distanceTransform((all_lines < 128).astype(np.uint8), cv2.DIST_L2, 5)
    dmax_all = float(dist_all[alpha > 0.5].max()) + 12 * k

    def flood_alpha(f):
        """How much real paint has soaked in, per pixel of the painting, at frame f."""
        A = np.zeros((h, w), np.float32)
        for wv in waves:
            t = (f - wv["start"]) / FDUR
            if t <= 0:
                continue
            y_0, y_1, x_0, x_1 = wv["bb"]
            if t >= 1:
                sub = wv["soft"][y_0:y_1, x_0:x_1]
            else:
                r = ease(t) ** 0.8 * wv["dmax"]
                sub = np.clip((r - wv["dist"][y_0:y_1, x_0:x_1] - rough[y_0:y_1, x_0:x_1]) / feather, 0, 1)
                sub = sub * wv["soft"][y_0:y_1, x_0:x_1]
            np.maximum(A[y_0:y_1, x_0:x_1], sub, out=A[y_0:y_1, x_0:x_1])
        tg = (f - T_GLOBAL) / GDUR
        if tg > 0:
            if tg >= 1:
                A[:] = alpha
            else:
                r = ease(tg) * dmax_all
                np.maximum(A, np.clip((r - dist_all - rough) / feather, 0, 1) * alpha, out=A)
        return A

    # outlines dissolve with a wet shimmer
    wash_noise = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 7 * k)
    wash_noise = (wash_noise - wash_noise.min()) / (wash_noise.max() - wash_noise.min() + 1e-6)

    # ---------------- handle, small and centred, inside Instagram's safe area
    handle_img = render_handle(W, H, k, handle, ink=(72, 62, 58)) if handle else None

    # ---------------- sound events
    events = dict(fps=FPS, frames=N, draw=[T_DRAW0, T_DRAW1], blooms=[ws + 2 for ws in wave_start],
                  wash=T_WASH, done=T_DONE, ambient=anim.sounds, anim=T_ANIM, twinkles=[],
                  unwrap=unwrap.EVENTS)
    for sp in anim.specs:
        if sp["kind"] == "gallop":
            events["gallop"] = dict(freq=sp.get("freq", 2.4),
                                    phases=[(hs["phase"] / (2 * math.pi)) % 1 for hs in sp["horses"]])

    # two crayon layers: hatching sits under the paint, outlines on top until they wash away
    ink_h = np.zeros((H, W, 3), np.float32); ink_ha = np.zeros((H, W), np.float32)
    ink_o = np.zeros((H, W, 3), np.float32); ink_oa = np.zeros((H, W), np.float32)
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
            ink, ink_a = (ink_h, ink_ha) if st["kind"] == "hatch" else (ink_o, ink_oa)
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

    shadow_still = place(shadow, 1.02, cx + 4 * k, cy + 16 * k, (H, W))

    # the blank primed canvas the doodle is drawn on (revealed by the unwrap)
    cm = place(np.dstack([np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32), rgba[..., 3]]), 1.0, cx, cy, (H, W))[..., 3]
    weave = (np.sin(xx * 2 * np.pi / (3.4 * k)) * np.sin(yy * 2 * np.pi / (3.4 * k))).astype(np.float32)
    prime = np.array([244, 241, 233], np.float32)[None, None, :] * (1 + 0.018 * weave + 0.012 * grain)[..., None]
    paper_c = paper * (1 - 0.32 * shadow_still)[..., None]
    paper_c = paper_c * (1 - cm[..., None]) + prime * cm[..., None]
    parcel = unwrap.Parcel(W, H, k, (x0, y0, w, h), rng)

    proc = None
    if still is None:
        os.makedirs(out_dir, exist_ok=True)
        wav = os.path.join(out_dir, f".{name}.wav")
        mp4 = os.path.join(out_dir, f"{name}.mp4")

    if sheet_frames is None:
        sheet_frames = [11, 24, 46, T_DRAW0 + 70, T_FLOOD + NW * STAG // 2 + 4, T_WASH + 7, T_DONE + 60, N - 2]
    out_frames = []
    for f in (range(N) if still is None else range(still + 1)):
        # doodle grows
        L = pen_at(f)
        if L > drawn_upto:
            draw_ink(drawn_upto, L)
            drawn_upto = L
        if still is not None and f != still:
            continue

        if f < T_DONE:
            # ---- the parcel unwraps, the doodle is drawn on the canvas, then paint soaks in through it
            frame = (paper if f < unwrap.T_SNAP else paper_c).copy()   # the canvas arrives inside the parcel
            a = (ink_ha * tooth)[..., None]
            frame = frame * (1 - a) + ink_h * a
            if f >= T_FLOOD:
                A = flood_alpha(f)
                wet = 4 * A * (1 - A)                       # the soaking edge looks wet and bright
                pr = paint_f + (wet * 38)[..., None]
                sub = frame[y0:y0 + h, x0:x0 + w]
                frame[y0:y0 + h, x0:x0 + w] = sub * (1 - A[..., None]) + pr * A[..., None]
            # outlines on top, washing away with a shimmer
            tw = (f - T_WASH) / WDUR
            keep = np.clip((wash_noise - (tw * 1.3 - 0.15)) / 0.15, 0, 1) if tw > 0 else 1.0
            a = (ink_oa * tooth * keep)[..., None]
            frame = frame * (1 - a) + ink_o * a
            if 0 < tw < 1.2:
                edge = 4 * keep * (1 - keep) * (ink_oa > 0.05)
                frame += edge[..., None] * np.array([60, 55, 40], np.float32)
            if f < unwrap.END:
                frame = parcel.draw(frame, f)
        else:
            frame = paper.copy()
            # ---- the finished painting: one settle bounce, then parts of it come alive
            tp = f - T_DONE
            s = float(np.interp(tp, [0, 5, 14], [1.0, 1.025, 1.0]))
            img = anim.frame(rgba, (f - T_ANIM) / FPS)
            ox, oy = cx, cy
            sh_layer = place(shadow, s * 1.02, ox + 4 * k, oy + 16 * k * s, (H, W))
            frame *= (1 - 0.32 * sh_layer)[..., None]
            lay = place(img, s, ox, oy, (H, W))
            a = np.clip(lay[..., 3:4], 0, 1)
            frame = frame * (1 - a) + np.clip(place_rgb(img, s, ox, oy, (H, W)), 0, 255) * a
            # twinkles (silent but for a barely-there airy shimmer)
            tt = (f - T_ANIM) / FPS
            if tt > 0.6:
                for (tx, ty, ph, spd) in twinkles:
                    v = math.sin(2 * math.pi * (tt * 0.45 * spd + ph))
                    if v < 0.75:
                        continue
                    a_t = ((v - 0.75) / 0.25) ** 2 * min(1.0, (tt - 0.6) / 0.6)
                    draw_star(frame, ox + (tx - w / 2) * s, oy + (ty - h / 2) * s, 15 * k * (0.6 + 0.6 * a_t), a_t)
                    if still is None and v > 0.98 and (not events["twinkles"] or f - events["twinkles"][-1] > 8):
                        events["twinkles"].append(f)

        if handle_img is not None and f >= T_HANDLE:
            a = handle_img[..., 3:4] * ease((f - T_HANDLE) / 20)
            frame = frame * (1 - a) + handle_img[..., :3] * a

        out = np.clip(frame, 0, 255).astype(np.uint8)
        if still is not None:
            return out
        if proc is None:
            proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                     "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
                                     os.path.join(out_dir, f".{name}.video.mp4")], stdin=subprocess.PIPE)
        proc.stdin.write(out.tobytes())
        if f in sheet_frames:
            out_frames.append(out)
    proc.stdin.close(); proc.wait()

    soundtrack.make(events, wav, seed=int(rng.integers(1 << 30)))
    mastered = soundtrack.master(wav, os.path.join(out_dir, f".{name}.master.wav"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out_dir, f".{name}.video.mp4"), "-i", mastered,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-shortest", "-movflags", "+faststart", mp4], check=True)
    for p in (os.path.join(out_dir, f".{name}.video.mp4"), wav, mastered):
        os.remove(p)
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


def render_handle(W, H, k, handle, ink):
    """The handle in Patrick Hand, centred about 280 px (at 1080x1920) above the bottom edge."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(os.path.join(REPO, "fonts", "patrick-hand-latin-400-normal.woff2"), int(50 * k))
    d.text((W / 2, H - 280 * k), handle, font=font, fill=(*ink, 230), anchor="mm")
    return np.asarray(img).astype(np.float32) * np.array([1, 1, 1, 1 / 255], np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+", help="file names from js/collection.js, e.g. art_IMG_0658")
    ap.add_argument("--res", type=int, default=1080, help="output width (height is 16:9 taller)")
    ap.add_argument("--still", type=int, default=None, help="only render this frame to a PNG")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--handle", default="@janelle.builds", help="shown at the bottom once the painting settles ('' for none)")
    a = ap.parse_args()
    artist, works = load_collection()
    for n in a.names:
        if n not in works:
            sys.exit(f"{n} is not in js/collection.js")
        if a.still is not None:
            img = build(n, a.res, a.out, still=a.still, artist=artist, works=works, seed=a.seed,
                        handle=a.handle)
            os.makedirs(a.out, exist_ok=True)
            p = os.path.join(a.out, f"{n}_still_{a.still:04d}.png")
            Image.fromarray(img).save(p); print(p)
        else:
            frames = build(n, a.res, a.out, artist=artist, works=works, seed=a.seed, handle=a.handle)
            os.makedirs(os.path.join(a.out, ".sheets"), exist_ok=True)
            sheet = np.concatenate([cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA) for fr in frames], 1)
            Image.fromarray(sheet).save(os.path.join(a.out, ".sheets", n + ".png"))
            print("done", n)


if __name__ == "__main__":
    main()
