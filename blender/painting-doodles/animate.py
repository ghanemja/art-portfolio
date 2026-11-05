"""Bring a painting to life with its own pixels: no overlays, only gentle warps of
the paint (and, for blossom, a few petals cut from the painting's own canopy).

Each painting gets 2-3 effects from EFFECTS below. Each effect is limited to a
hand-drawn mask (polygons in 0-1 image coordinates, optionally narrowed by
colour, feathered so nothing tears) and also names the ambient sound bed it
brings with it (see soundtrack.py).

Effect kinds
  waves    rolling horizontal waves + ripples          (sea, lakes, rivers)
  flow     water scrolling along a direction, looped     (waterfalls, speed streaks)
           with two crossfaded phases so it never jumps
  sway     wind sway that grows towards the top of the   (trees, canopies, bushes)
           mask, plus a fine leaf flutter
  drift    very slow sideways drift that eases back       (clouds, brushy skies)
  swirl    slow differential rotation around a centre     (the winter sun)
  aurora   slow vertical waving of a band of sky          (aurora)
  glint    highlights sliding back and forth on water     (sun glints)
  bob      a region floating gently up and down           (a boat, a floating treat)
  shimmer  a fine moving wobble                           (snow)
  petals   a few petals cut from the canopy drift down    (cherry blossom)
"""
import math
import numpy as np
import cv2

# ---------------------------------------------------------------- per-painting config
EFFECTS = {
    "art_IMG_0658": [  # Wild Horses at the Falls
        dict(kind="flow", polys=[[(0.66, 0.0), (0.95, 0.0), (0.93, 0.12), (0.84, 0.25), (0.76, 0.42),
                                  (0.70, 0.60), (0.61, 0.62), (0.63, 0.42), (0.69, 0.24), (0.68, 0.08)]],
             colour="light", direction=(0.25, 1.0), speed=34, period=26, sound="rush"),
        dict(kind="waves", polys=[[(0.06, 0.57), (0.97, 0.60), (0.99, 0.86), (0.62, 0.96), (0.22, 0.82),
                                   (0.04, 0.68)]], amp=3.2, wavelength=70, speed=1.3, sound="waves"),
        dict(kind="sway", polys=[[(0.0, 0.0), (0.47, 0.0), (0.47, 0.36), (0.0, 0.40)],
                                 [(0.80, 0.22), (1.0, 0.18), (1.0, 0.66), (0.83, 0.66)]],
             amp=3.0, flutter=1.0, sound="rustle"),
    ],
    "art_IMG_2256": [  # Lavender Peaks Harbour
        dict(kind="drift", polys=[[(0, 0), (1, 0), (1, 0.27), (0, 0.27)]], amp=10, sound="wind"),
        dict(kind="waves", polys=[[(0, 0.80), (0.45, 0.79), (0.70, 0.785), (1, 0.75), (1, 1), (0, 1)]],
             amp=3.5, wavelength=80, speed=1.2, sound="waves"),
        dict(kind="bob", polys=[[(0.69, 0.63), (0.88, 0.63), (0.89, 0.80), (0.68, 0.80)]], amp=3.0, period=3.2),
    ],
    "art_IMG_5264": [  # Castle Above the Valley
        dict(kind="drift", polys=[[(0.33, 0.0), (1, 0.0), (1, 0.40), (0.62, 0.42), (0.33, 0.32)]],
             amp=12, sound="wind"),
        dict(kind="waves", polys=[[(0.79, 0.56), (1, 0.55), (1, 0.70), (0.84, 0.66)],
                                  [(0.47, 0.57), (0.58, 0.57), (0.55, 0.65), (0.47, 0.64)]],
             amp=2.0, wavelength=40, speed=1.0, sound="waves"),
        dict(kind="sway", polys=[[(0.36, 0.48), (1.0, 0.47), (1.0, 0.58), (0.36, 0.60)]],
             amp=2.2, flutter=0.7, sound="rustle"),
    ],
    "art_IMG_7165": [  # Winter Sun, Spinning
        dict(kind="swirl", polys=[[(0, 0), (1, 0), (1, 0.74), (0, 0.74)]], colour="not_navy",
             centre=(0.62, 0.31), amp=0.018, sound="pad"),
        dict(kind="shimmer", polys=[[(0, 0.72), (1, 0.70), (1, 1), (0, 1)]], amp=1.6, sound="wind"),
        dict(kind="sway", polys=[[(0.03, 0.0), (0.85, 0.0), (0.85, 0.60), (0.03, 0.60)]], colour="navy",
             amp=2.0, flutter=0.0),
    ],
    "art_IMG_5557": [  # Aurora Over the Sea (round)
        dict(kind="aurora", polys=[[(0, 0), (1, 0), (1, 0.52), (0, 0.52)]], colour="greenish",
             amp=4.0, sound="pad"),
        dict(kind="waves", polys=[[(0, 0.50), (1, 0.50), (1, 1), (0, 1)]], colour="not_dark",
             amp=3.0, wavelength=90, speed=1.0, sound="waves"),
        dict(kind="sway", polys=[[(0.05, 0.68), (0.36, 0.70), (0.36, 0.98), (0.05, 0.98)],
                                 [(0.68, 0.66), (0.97, 0.66), (0.97, 0.95), (0.68, 0.95)]],
             amp=2.4, flutter=1.0),
    ],
    "art_IMG_9615": [  # Sun-Melted Sea (round)
        dict(kind="glint", polys=[[(0, 0.50), (1, 0.50), (1, 1), (0, 1)]], colour="yellow", amp=6.0),
        dict(kind="waves", polys=[[(0, 0.50), (1, 0.50), (1, 1), (0, 1)]], amp=3.0, wavelength=110,
             speed=1.1, sound="waves"),
        dict(kind="drift", polys=[[(0, 0), (1, 0), (1, 0.46), (0, 0.46)]], amp=8, sound="pad"),
    ],
    "art_banana_treats_astronaut": [  # Banana Treats for the Astronaut
        dict(kind="flow", polys=[[(0, 0), (1, 0), (1, 0.42), (0.80, 0.30), (0.60, 0.22), (0.35, 0.26),
                                  (0.12, 0.34), (0, 0.34)]],
             radial=(0.42, 0.42), speed=30, period=28, sound="wind"),
        dict(kind="bob", polys=[[(0.62, 0.20), (0.82, 0.18), (0.90, 0.50), (0.96, 0.74), (0.78, 0.82),
                                 (0.61, 0.72), (0.57, 0.45)]], amp=5.0, period=3.6, sound="pad"),
    ],
    "art_IMG_7158": [  # Cherry Blossom Road
        dict(kind="sway", polys=[[(0.0, 0.32), (0.46, 0.32), (0.46, 0.57), (0.25, 0.70), (0.0, 0.64)],
                                 [(0.0, 0.57), (0.13, 0.57), (0.13, 0.86), (0.0, 0.88)],
                                 [(0.57, 0.36), (0.81, 0.36), (0.81, 0.62), (0.57, 0.62)],
                                 [(0.70, 0.44), (1.0, 0.40), (1.0, 0.84), (0.70, 0.84)]],
             colour="blossom", amp=3.0, flutter=1.4, sound="rustle"),
        dict(kind="petals", polys=[[(0.0, 0.32), (0.46, 0.32), (0.46, 0.57), (0.0, 0.60)],
                                   [(0.57, 0.36), (1.0, 0.38), (1.0, 0.70), (0.57, 0.62)]],
             colour="blossom", count=34),
        dict(kind="drift", polys=[[(0, 0.02), (1, 0.02), (1, 0.32), (0, 0.32)]], amp=9, sound="wind"),
    ],
}

# a gentle default for paintings without a config: slow drift on the top third
DEFAULT = [dict(kind="drift", polys=[[(0, 0), (1, 0), (1, 0.33), (0, 0.33)]], amp=8, sound="wind")]


# ---------------------------------------------------------------- masks
def _colour(paint, which):
    hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV).astype(np.float32)
    H, S, V = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    if which == "light":       # white/blue water
        m = (V > 0.6) & ((S < 0.22) | ((H > 180) & (H < 230) & (S > 0.25)))
    elif which == "navy":
        m = (H > 200) & (H < 260) & (V < 0.55) & (S > 0.4)
    elif which == "not_navy":
        m = ~((H > 200) & (H < 260) & (V < 0.55) & (S > 0.4))
    elif which == "greenish":  # the aurora glow, and the sky around it
        m = (V > 0.12)
    elif which == "not_dark":
        m = V > 0.25
    elif which == "yellow":    # sun reflections on the sea
        m = (H > 30) & (H < 70) & (S > 0.35) & (V > 0.55)
    elif which == "blossom":
        m = ((H < 25) | (H > 320)) & (V > 0.45) & (S > 0.12)
    else:
        m = np.ones(paint.shape[:2], bool)
    m = m.astype(np.float32)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(m, (0, 0), 2.5)


def make_mask(spec, paint, k):
    h, w = paint.shape[:2]
    m = np.zeros((h, w), np.float32)
    for poly in spec["polys"]:
        pts = np.round(np.array(poly) * [w, h] * 4).astype(np.int32)
        cv2.fillPoly(m, [pts], 1.0, cv2.LINE_AA, shift=2)
    m = cv2.GaussianBlur(m, (0, 0), 10 * k)
    if spec.get("colour"):
        m *= _colour(paint, spec["colour"])
    return np.clip(m, 0, 1)


# ---------------------------------------------------------------- the animator
class Animator:
    def __init__(self, name, paint, pad, k, rng):
        """paint: the painting at display size (h, w, 3). pad: the padding round
        the RGBA canvas the effects are applied to."""
        self.specs = EFFECTS.get(name, DEFAULT)
        self.paint, self.pad, self.k = paint, pad, k
        h, w = paint.shape[:2]
        self.h, self.w = h, w
        H2, W2 = h + 2 * pad, w + 2 * pad
        self.X = np.arange(W2, dtype=np.float32)[None, :].repeat(H2, 0)
        self.Y = np.arange(H2, dtype=np.float32)[:, None].repeat(W2, 1)
        self.fx = (self.X - pad) / w          # 0-1 painting coordinates
        self.fy = (self.Y - pad) / h
        # keep the canvas edge crisp: effects fade out near it (flows, which pull
        # pixels from further away, fade out over a whole loop length)
        ex = np.minimum(self.X - pad, pad + w - 1 - self.X)
        ey = np.minimum(self.Y - pad, pad + h - 1 - self.Y)
        edge = np.minimum(ex, ey)
        self.effects = []
        for sp in self.specs:
            m = np.pad(make_mask(sp, paint, k), pad)
            reach = (sp.get("period", 26) + 8) * k if sp["kind"] == "flow" else 14 * k
            m = m * np.clip(edge / reach, 0, 1) ** 1.5
            e = dict(spec=sp, mask=m, ph=rng.uniform(0, 6.28, 6))
            ys, xs = np.nonzero(m > 0.02)
            e["top"] = ys.min() if len(ys) else 0
            e["bot"] = ys.max() if len(ys) else H2
            if sp["kind"] == "petals":
                e["petals"] = self._make_petals(sp, m, rng)
            self.effects.append(e)
        self.sounds = sorted({sp["sound"] for sp in self.specs if sp.get("sound")})

    def _make_petals(self, sp, m, rng):
        k = self.k
        ys, xs = np.nonzero(m > 0.6)
        out = []
        src = cv2.copyMakeBorder(self.paint, self.pad, self.pad, self.pad, self.pad, cv2.BORDER_REPLICATE)
        for i in range(sp.get("count", 20)):
            j = rng.integers(len(ys))
            r = int(rng.uniform(7.0, 10.0) * k) + 1
            y, x = ys[j], xs[j]
            patch = src[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1].astype(np.float32)
            if patch.shape[0] != 2 * r + 1 or patch.shape[1] != 2 * r + 1:
                continue
            # brighten a touch towards the blossom's lightest tones so it reads as a petal
            patch = patch * 0.55 + 0.45 * np.array([252, 226, 232], np.float32)
            yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32) / r
            alpha = np.clip(1.3 - np.sqrt((xx / 1.0) ** 2 + (yy / 0.55) ** 2) * 1.3, 0, 1) ** 0.8
            out.append(dict(patch=patch, alpha=alpha, r=r, x0=float(x), y0=float(y),
                            born=rng.uniform(0, 3.0), vy=rng.uniform(42, 70) * k, vx=rng.uniform(-6, 10) * k,
                            sway=rng.uniform(6, 12) * k, fr=rng.uniform(0.6, 1.1), ph=rng.uniform(0, 6.28),
                            spin=rng.uniform(-1.5, 1.5)))
        return out

    def frame(self, rgba, t):
        """rgba: the padded painting. t: seconds since the animation started."""
        if t <= 0:
            return rgba
        k, X, Y, fx, fy = self.k, self.X, self.Y, self.fx, self.fy
        amp_in = 0.5 - 0.5 * math.cos(math.pi * min(1.0, t / 0.6))   # ease in over 0.6 s
        dx = np.zeros_like(X); dy = np.zeros_like(X)
        flows = []
        for e in self.effects:
            sp, m, ph = e["spec"], e["mask"], e["ph"]
            kd = sp["kind"]
            a = amp_in * m
            if kd == "waves":
                A = sp.get("amp", 3) * k
                lam = sp.get("wavelength", 80) * k
                sp_ = sp.get("speed", 1.2)
                kx = 2 * math.pi / lam
                dx += a * A * (np.sin(kx * 0.35 * X + 2 * math.pi * 0.07 * Y / k * 0.12 - sp_ * t + ph[0])
                               * 0.7 + 0.3 * np.sin(kx * 0.9 * X - 0.05 * Y / k - 1.7 * sp_ * t + ph[1]))
                dy += a * A * 0.55 * (np.sin(kx * Y * 0.8 + 0.01 * X / k - 1.3 * sp_ * t + ph[2])
                                      + 0.4 * np.sin(kx * 2.1 * X + 0.6 * kx * Y - 2.4 * sp_ * t + ph[3]))
            elif kd == "sway":
                A = sp.get("amp", 3) * k
                hgt = np.clip((e["bot"] - Y) / max(1.0, e["bot"] - e["top"]), 0, 1) ** 1.2   # more at the top
                wind = np.sin(1.3 * t + 0.004 * X / k + ph[0]) + 0.45 * np.sin(2.3 * t + 0.009 * X / k + ph[1])
                dx += a * A * hgt * wind
                dy += a * A * 0.25 * hgt * np.sin(1.1 * t + 0.006 * X / k + ph[2])
                fl = sp.get("flutter", 0.0) * k
                if fl:
                    dx += a * fl * np.sin(0.21 * X / k + 4.1 * t + ph[3]) * np.sin(0.17 * Y / k + 3.3 * t)
                    dy += a * fl * np.sin(0.19 * Y / k - 3.7 * t + ph[4]) * np.sin(0.23 * X / k + 2.9 * t)
            elif kd == "drift":
                A = sp.get("amp", 10) * k
                dx += a * A * np.sin(2 * math.pi * t / 9.0 + ph[0]) * (0.8 + 0.2 * np.sin(0.01 * Y / k + ph[1]))
                dy += a * A * 0.12 * np.sin(2 * math.pi * t / 7.0 + 0.008 * X / k + ph[2])
            elif kd == "swirl":
                cxp = self.pad + sp["centre"][0] * self.w
                cyp = self.pad + sp["centre"][1] * self.h
                rx, ry = X - cxp, Y - cyp
                r = np.sqrt(rx * rx + ry * ry) / (self.w * 0.5)
                ang = sp.get("amp", 0.018) * (np.sin(1.2 * t - 3.0 * r + ph[0]) + 0.5 * np.sin(0.7 * t + ph[1]))
                ang = ang * np.clip(r * 3, 0, 1)                   # the sun itself stays put
                ca, sa = np.cos(ang) - 1, np.sin(ang)
                dx += a * (ca * rx - sa * ry)
                dy += a * (sa * rx + ca * ry)
            elif kd == "aurora":
                A = sp.get("amp", 4) * k
                dy += a * A * (np.sin(0.011 * X / k + 0.9 * t + ph[0]) + 0.5 * np.sin(0.023 * X / k - 1.4 * t + ph[1]))
                dx += a * A * 0.4 * np.sin(0.015 * Y / k + 0.6 * t + ph[2])
            elif kd == "glint":
                A = sp.get("amp", 6) * k
                dx += a * A * np.sin(0.02 * Y / k + 1.6 * t + ph[0]) * np.sin(0.006 * X / k - 0.9 * t + ph[1])
            elif kd == "bob":
                A = sp.get("amp", 4) * k
                per = sp.get("period", 3.4)
                dy += a * A * np.sin(2 * math.pi * t / per + ph[0])
                dx += a * A * 0.3 * np.sin(2 * math.pi * t / (per * 1.6) + ph[1])
            elif kd == "shimmer":
                A = sp.get("amp", 1.5) * k
                dx += a * A * np.sin(0.13 * X / k + 0.07 * Y / k + 2.6 * t + ph[0])
                dy += a * A * 0.6 * np.sin(0.11 * Y / k - 2.2 * t + ph[1])
            elif kd == "flow":
                flows.append(e)
        if not flows:
            out = cv2.remap(rgba, X + dx, Y + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            # two phases of a looping scroll, crossfaded so the loop never shows
            outs, wts = [], []
            for phase in (0.0, 0.5):
                fxs, fys = dx.copy(), dy.copy()
                wsum = 0
                for e in flows:
                    sp, m = e["spec"], e["mask"] * amp_in
                    P = sp.get("period", 26) * self.k
                    u = ((t * sp.get("speed", 30) * self.k) / P + phase) % 1.0
                    off = u * P
                    if "radial" in sp:
                        cxp = self.pad + sp["radial"][0] * self.w
                        cyp = self.pad + sp["radial"][1] * self.h
                        vx, vy = X - cxp, Y - cyp
                        n = np.sqrt(vx * vx + vy * vy) + 1e-3
                        ux, uy = vx / n, vy / n
                    else:
                        d = np.array(sp.get("direction", (0, 1)), float)
                        d /= np.linalg.norm(d)
                        ux, uy = d[0], d[1]
                    fxs -= m * off * ux
                    fys -= m * off * uy
                    wsum = 1 - abs(2 * u - 1)                           # triangle weight
                outs.append(cv2.remap(rgba, X + fxs, Y + fys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
                wts.append(wsum)
            wa, wb = wts
            s = wa + wb + 1e-6
            out = outs[0] * (wa / s) + outs[1] * (wb / s)
        out[..., 3] = rgba[..., 3]

        # petals: tiny bits of the canopy drifting down
        for e in self.effects:
            if e["spec"]["kind"] != "petals":
                continue
            for p in e["petals"]:
                tp = t - p["born"]
                if tp <= 0:
                    continue
                y = p["y0"] + p["vy"] * tp
                x = p["x0"] + p["vx"] * tp + p["sway"] * math.sin(2 * math.pi * p["fr"] * tp + p["ph"])
                fade = min(1.0, tp / 0.4) * min(1.0, max(0.0, (self.pad + self.h - 6 - y) / 30))
                if fade <= 0:
                    continue
                r = p["r"]
                M = cv2.getRotationMatrix2D((r, r), math.degrees(p["spin"] * tp), 1.0)
                pa = cv2.warpAffine(p["patch"], M, (2 * r + 1, 2 * r + 1), borderMode=cv2.BORDER_REPLICATE)
                al = cv2.warpAffine(p["alpha"], M, (2 * r + 1, 2 * r + 1)) * fade
                xi, yi = int(x) - r, int(y) - r
                if xi < 0 or yi < 0 or xi + 2 * r + 1 > out.shape[1] or yi + 2 * r + 1 > out.shape[0]:
                    continue
                al = al * out[yi:yi + 2 * r + 1, xi:xi + 2 * r + 1, 3]
                sub = out[yi:yi + 2 * r + 1, xi:xi + 2 * r + 1, :3]
                sub[:] = sub * (1 - al[..., None]) + pa * al[..., None]
        return out
