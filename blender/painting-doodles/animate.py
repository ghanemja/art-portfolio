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
  gallop   per-horse gallop cycle: body bob, rock and     (Wild Horses at the Falls)
           surge, legs swinging (front and back out of
           phase), mane and tail flutter
  wake     V-shaped wakes trailing behind each horse and   (Wild Horses at the Falls)
           ripple rings spreading from each hoof landing
  spray    spray kicked up at each hoof landing: drops and  (Wild Horses at the Falls)
           a puff of white made from the painting's own
           white water, plus the water there heaving up
  mist     the waterfall's own whites, blurred, drifting    (Wild Horses at the Falls)
           off it in slow wisps

The gallop also gives the hoof landings (hoof_events), so the spray, the ripples
and the hoofbeats in the soundtrack all land together.
"""
import math
import numpy as np
import cv2

# ---------------------------------------------------------------- per-painting config
RUN = (0.96, 0.28)       # Wild Horses: the way the herd runs, and the river with it
RIVER = [(0.07, 0.575), (0.72, 0.585), (1.0, 0.65), (1.0, 0.72), (0.80, 0.80), (0.93, 0.90), (0.75, 0.97),
         (0.50, 0.92), (0.30, 0.80), (0.13, 0.72), (0.05, 0.66)]
# paintings whose reel has no twinkles or shimmer at all
NO_SPARKLE = {"art_IMG_0658"}

EFFECTS = {
    "art_IMG_0658": [  # Wild Horses at the Falls: the whole scene moves with the galloping herd
        dict(kind="flow", polys=[[(0.66, 0.0), (0.95, 0.0), (0.93, 0.12), (0.84, 0.25), (0.76, 0.42),
                                  (0.70, 0.60), (0.61, 0.62), (0.63, 0.42), (0.69, 0.24), (0.68, 0.08)]],
             colour="light", direction=(0.25, 1.0), speed=40, period=26, sound="rush"),
        # the river runs the way the herd runs (left to right, towards us), under and past the horses
        dict(kind="flow", polys=[RIVER], direction=RUN, speed=34, period=34, avoid_horses=True, sound="river"),
        dict(kind="waves", polys=[RIVER], amp=1.5, wavelength=55, speed=1.8, avoid_horses=True),
        dict(kind="wake", polys=[RIVER], direction=RUN, amp=2.6, avoid_horses=True),
        # the trees and bushes toss in the wind of the gallop
        dict(kind="sway", polys=[[(0.0, 0.0), (0.66, 0.0), (0.66, 0.29), (0.47, 0.30), (0.40, 0.285),
                                  (0.31, 0.32), (0.21, 0.345), (0.0, 0.37)],
                                 [(0.0, 0.47), (0.10, 0.49), (0.13, 0.70), (0.0, 0.73)],
                                 [(0.0, 0.86), (0.32, 0.87), (0.32, 1.0), (0.0, 1.0)]],
             amp=3.4, flutter=1.5, gust=1.0, avoid_horses=True, sound="rustle"),
        dict(kind="sway", polys=[[(0.82, 0.12), (1.0, 0.08), (1.0, 0.67), (0.80, 0.67), (0.80, 0.40)]],
             colour="not_light", amp=3.2, flutter=1.4, gust=1.0),
        # five horses, left to right: palomino, dark bay, grey, bay with the white patch, dark brown
        # after galloping in place for a moment they break out: one after another each horse charges
        # out of the painting towards us and off the bottom of the screen
        dict(kind="gallop", freq=2.4, sound="gallop",
             breakout=dict(start=1.7, stagger=0.3, order=[3, 1, 4, 2, 0], dir=(1.0, 0.0), vp=(0.42, 0.40)),
             horses=[
            dict(body=[(0.07, 0.40), (0.12, 0.38), (0.20, 0.355), (0.27, 0.34), (0.30, 0.37), (0.29, 0.45),
                       (0.24, 0.50), (0.15, 0.52), (0.08, 0.50)],
                 legs=[(0.12, 0.49), (0.235, 0.49), (0.245, 0.585), (0.11, 0.585)],
                 hair=[[(0.055, 0.40), (0.11, 0.40), (0.11, 0.52), (0.06, 0.50)],
                       [(0.18, 0.35), (0.27, 0.33), (0.28, 0.38), (0.20, 0.40)]], phase=0.0, front=-1),
            dict(body=[(0.25, 0.40), (0.30, 0.36), (0.35, 0.34), (0.39, 0.38), (0.40, 0.47), (0.38, 0.53),
                       (0.27, 0.53), (0.24, 0.47)],
                 legs=[(0.24, 0.51), (0.40, 0.51), (0.40, 0.61), (0.24, 0.61)],
                 hair=[[(0.30, 0.34), (0.36, 0.33), (0.36, 0.40), (0.30, 0.40)]], phase=2.3, front=1),
            dict(body=[(0.38, 0.33), (0.43, 0.31), (0.46, 0.34), (0.46, 0.50), (0.42, 0.54), (0.38, 0.50)],
                 legs=[(0.39, 0.50), (0.46, 0.50), (0.46, 0.59), (0.39, 0.59)],
                 hair=[[(0.42, 0.31), (0.46, 0.31), (0.46, 0.37), (0.43, 0.37)]], phase=4.4, front=-1,
                 light_coat=True),
            dict(body=[(0.44, 0.40), (0.50, 0.37), (0.56, 0.35), (0.60, 0.38), (0.60, 0.46), (0.57, 0.52),
                       (0.46, 0.52), (0.44, 0.47)],
                 legs=[(0.45, 0.50), (0.60, 0.50), (0.60, 0.63), (0.45, 0.63)],
                 hair=[[(0.55, 0.34), (0.59, 0.34), (0.59, 0.40), (0.55, 0.40)]], phase=1.1, front=1),
            dict(body=[(0.58, 0.36), (0.62, 0.34), (0.66, 0.36), (0.66, 0.48), (0.63, 0.52), (0.59, 0.50)],
                 legs=[(0.58, 0.50), (0.66, 0.50), (0.665, 0.60), (0.58, 0.60)],
                 hair=[[(0.63, 0.38), (0.67, 0.38), (0.67, 0.50), (0.64, 0.50)]], phase=3.3, front=1),
        ]),
        # spray kicked up by each hoof as it lands, and mist drifting off the waterfall
        dict(kind="spray", direction=RUN, sound="splash"),
        # the river spills over the canvas: across the bank and over the bottom edge, and out of the
        # right edge where it meets it, pouring off the screen (spill.py)
        dict(kind="pour", pours=[dict(edge="bottom", span=(0.52, 0.86), lip=0.80, start=0.5),
                                 dict(edge="right", span=(0.635, 0.725), start=0.75)], sound="pour"),
        dict(kind="mist", polys=[[(0.58, 0.16), (0.82, 0.12), (0.90, 0.40), (0.84, 0.66), (0.62, 0.64), (0.60, 0.40)]],
             source=[[(0.66, 0.0), (0.95, 0.0), (0.84, 0.25), (0.72, 0.62), (0.60, 0.62), (0.67, 0.24)]],
             direction=(-0.85, -0.45), sound="mist"),
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
             centre=(0.62, 0.31), amp=0.018, sound="airy"),
        dict(kind="shimmer", polys=[[(0, 0.72), (1, 0.70), (1, 1), (0, 1)]], amp=1.6, sound="wind"),
        dict(kind="sway", polys=[[(0.03, 0.0), (0.85, 0.0), (0.85, 0.60), (0.03, 0.60)]], colour="navy",
             amp=2.0, flutter=0.0),
    ],
    "art_IMG_5557": [  # Aurora Over the Sea (round)
        dict(kind="aurora", polys=[[(0, 0), (1, 0), (1, 0.52), (0, 0.52)]], colour="greenish",
             amp=4.0, sound="airy"),
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
        dict(kind="drift", polys=[[(0, 0), (1, 0), (1, 0.46), (0, 0.46)]], amp=8, sound="airy"),
    ],
    "art_banana_treats_astronaut": [  # Banana Treats for the Astronaut
        dict(kind="flow", polys=[[(0, 0), (1, 0), (1, 0.42), (0.80, 0.30), (0.60, 0.22), (0.35, 0.26),
                                  (0.12, 0.34), (0, 0.34)]],
             radial=(0.42, 0.42), speed=30, period=28, sound="wind"),
        dict(kind="bob", polys=[[(0.62, 0.20), (0.82, 0.18), (0.90, 0.50), (0.96, 0.74), (0.78, 0.82),
                                 (0.61, 0.72), (0.57, 0.45)]], amp=5.0, period=3.6, sound="airy"),
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
    elif which == "not_light":
        m = ~((V > 0.6) & ((S < 0.22) | ((H > 180) & (H < 230) & (S > 0.25))))
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
    if "polys" not in spec:
        return np.ones((h, w), np.float32)
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
            if sp["kind"] == "gallop":
                e["horses"] = [self._make_horse(hs) for hs in sp["horses"]]
            self.effects.append(e)
        self.horses, self.gfreq = [], 2.4
        for e in self.effects:
            if e["spec"]["kind"] == "gallop":
                self.horses, self.gfreq = e["horses"], e["spec"].get("freq", 2.4)
        if self.horses:
            herd = np.clip(sum(hz["whole"] for hz in self.horses), 0, 1)
            herd = np.maximum(herd, cv2.GaussianBlur(herd, (0, 0), 3 * k))
            for e in self.effects:
                if e["spec"].get("avoid_horses"):
                    e["mask"] = e["mask"] * (1 - herd)
        self.light = np.pad(_colour(paint, "light"), pad)
        self.leave = {}
        for e in self.effects:
            if e["spec"]["kind"] == "gallop" and e["spec"].get("breakout"):
                self._setup_breakout(e["spec"], rng)
        src = cv2.copyMakeBorder(paint, pad, pad, pad, pad, cv2.BORDER_REPLICATE).astype(np.float32)
        for e in self.effects:
            kd = e["spec"]["kind"]
            if kd == "spray":
                # each horse's spray takes its colour from the white water round its own hooves
                for hz in self.horses:
                    y0_, y1_ = int(hz["lbot"] - 40 * k), int(hz["lbot"] + 10 * k)
                    x0_, x1_ = int(hz["lmid"] - hz["lhalf"]), int(hz["lmid"] + hz["lhalf"])
                    win = src[y0_:y1_, x0_:x1_].reshape(-1, 3)
                    lum = win.mean(1)
                    hz["spray_col"] = win[lum >= np.percentile(lum, 85)].mean(0)
            if kd == "mist":
                sm = self._poly_mask(e["spec"]["source"], 8) * self.light
                sig = 9 * k
                e["mA"] = cv2.GaussianBlur(sm, (0, 0), sig).astype(np.float32)
                e["mC"] = (cv2.GaussianBlur(src * sm[..., None], (0, 0), sig)
                           / (e["mA"][..., None] + 1e-4)).astype(np.float32)
        self.sounds = sorted({sp["sound"] for sp in self.specs if sp.get("sound")})

    # ---------------------------------------------------------- the breakout
    def _setup_breakout(self, sp, rng):
        """Cut each horse out of the painting (GrabCut, seeded by its polygons and told that white
        water and green forest are background), and paint what was behind the herd: the forest
        carried down from above, then white spray, from the painting's own colours, with brushy
        strokes. A horse's reflection in the river goes with it."""
        k, pad, paint = self.k, self.pad, self.paint
        h, w = paint.shape[:2]
        bo = sp["breakout"]
        for j, hi in enumerate(bo.get("order", range(len(self.horses)))):
            self.leave[hi] = bo.get("start", 1.7) + j * bo.get("stagger", 0.3)
        d = np.array(bo.get("dir", (0.28, 1.0)), float)
        self.run_out = d / np.linalg.norm(d)
        self.vp = bo.get("vp", (0.42, 0.40))
        hsv = cv2.cvtColor(paint, cv2.COLOR_RGB2HSV).astype(np.float32)
        V, Sa, Hh = hsv[..., 2] / 255, hsv[..., 1] / 255, hsv[..., 0] * 2
        white = ((V > 0.72) & (Sa < 0.2)) | ((V > 0.6) & (Hh > 170) & (Hh < 230) & (Sa > 0.2))
        green = (Hh > 60) & (Hh < 180) & (Sa > 0.15)
        whiteness = np.clip((V - 0.6) / 0.25, 0, 1) * np.clip((0.3 - Sa) / 0.15, 0, 1)

        def poly(ps):
            m = np.zeros((h, w), np.uint8)
            for p in ps:
                cv2.fillPoly(m, [np.round(np.array(p) * [w, h]).astype(np.int32)], 1)
            return m
        ker = lambda r: np.ones((max(1, int(r * k)) | 1,) * 2, np.uint8)
        bgr = cv2.cvtColor(paint, cv2.COLOR_RGB2BGR)
        holes = np.zeros((h, w), np.uint8)
        for hi, (hz, hs) in enumerate(zip(self.horses, sp["horses"])):
            pm = poly([hs["body"], hs["legs"]] + hs.get("hair", []))
            gc = np.full((h, w), cv2.GC_BGD, np.uint8)
            gc[cv2.dilate(pm, ker(41)) > 0] = cv2.GC_PR_BGD
            gc[pm > 0] = cv2.GC_PR_FGD
            bgish = (white if hs.get("light_coat") is None else (V > 0.86) & (Sa < 0.12)) | green
            gc[(pm > 0) & bgish] = cv2.GC_PR_BGD
            core = cv2.erode(poly([hs["body"]]), ker(27))
            gc[(core > 0) & ~bgish] = cv2.GC_FGD
            cv2.grabCut(bgr, gc, None, np.zeros((1, 65)), np.zeros((1, 65)), 8, cv2.GC_INIT_WITH_MASK)
            m = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, ker(5))
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, ker(9))
            n, cc, st, _ = cv2.connectedComponentsWithStats(m)
            if n > 1:
                m = (cc == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
            # the legs go with it, as far as they show against the white water
            wsoft = np.maximum(whiteness, cv2.GaussianBlur(white.astype(np.float32), (0, 0), 1.5 * k))
            legs = poly([hs["legs"]]).astype(np.float32) * np.clip(1 - 1.3 * wsoft, 0, 1)
            cut = np.maximum(m.astype(np.float32), legs)
            cut = cv2.GaussianBlur(cut, (0, 0), 0.8 * k)
            hz["cut"] = np.pad(cut, pad)
            # its hole: the horse, its legs, and its reflection below the waterline
            lb = int(max(p[1] for p in hs["legs"]) * h)
            refl = np.zeros((h, w), np.uint8)
            xs = [int(p[0] * w) for p in hs["legs"]]
            refl[lb:min(h, lb + int(0.09 * h)), min(xs):max(xs)] = 1
            refl &= (V < 0.55).astype(np.uint8)
            hole = cv2.dilate(((cut > 0.3) | (pm & (~white).astype(np.uint8)) > 0).astype(np.uint8), ker(9)) | refl
            hz["hole"] = np.pad(cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3 * k), pad)
            holes |= hole
        # what was behind them
        q = 4
        small = cv2.resize(paint, (w // q, h // q), interpolation=cv2.INTER_AREA)
        hs_ = cv2.dilate(cv2.resize(holes, (w // q, h // q), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        inp = cv2.resize(cv2.inpaint(small, hs_, 9, cv2.INPAINT_TELEA), (w, h), interpolation=cv2.INTER_CUBIC)
        inp = inp.astype(np.float32)

        def bn(sx, sy):
            n_ = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=sx * k, sigmaY=sy * k)
            return n_ / (n_.std() + 1e-6)
        wh = paint[white].astype(np.float32)
        lum = wh.mean(1)
        WHITE = wh[lum > np.percentile(lum, 70)].mean(0)
        BLUE = wh[(wh[:, 2] - wh[:, 0]) > 40].mean(0)
        yy = (np.arange(h)[:, None] / h).astype(np.float32)
        strokes = 0.6 * bn(14, 2.2) + 0.4 * bn(2.5, 10)
        bl = np.clip(0.02 + 0.55 * np.clip((yy - 0.53) / 0.07, 0, 1) + 0.22 * strokes, 0, 1) ** 1.3
        spray = WHITE * (1 - bl[..., None]) + BLUE * bl[..., None]
        spray = spray * (1 + 0.03 * bn(0.8, 0.8))[..., None]
        wt = np.clip((yy - 0.35 + 0.035 * bn(16, 5)) / 0.07, 0, 1)   # spray rising raggedly into the trees
        # the river below the waterline: the inpainted water, streaked sideways like the painted river
        river = np.clip((yy - 0.6) / 0.02, 0, 1)
        fill = inp * (1 + 0.05 * strokes[..., None]) * (1 - wt[..., None]) + spray * wt[..., None]
        rv = cv2.GaussianBlur(inp, (0, 0), sigmaX=10 * k, sigmaY=1.0 * k) * (1 + 0.06 * bn(18, 1.5))[..., None]
        fill = fill * (1 - river[..., None]) + rv * river[..., None]
        fill = np.clip(fill, 0, 255)
        self.bg = cv2.copyMakeBorder(fill, pad, pad, pad, pad, cv2.BORDER_REPLICATE).astype(np.float32)

    def gone(self, hi, t):
        """How far horse hi has left its place (0..1), t seconds into the animation."""
        if hi not in self.leave:
            return 0.0
        return float(np.clip((t - self.leave[hi]) / 0.12, 0, 1))

    def without_departed(self, rgba, t):
        """The painting with every horse that has run off replaced by what was behind it."""
        if not self.leave:
            return rgba
        out = rgba
        for hi, hz in enumerate(self.horses):
            g = self.gone(hi, t)
            if g > 0:
                if out is rgba:
                    out = rgba.copy()
                a = (hz["hole"] * g)[..., None]
                out[..., :3] = out[..., :3] * (1 - a) + self.bg * a
        return out

    def out_path(self, hi, tau):
        """Where a departed horse is, tau seconds after it set off: (dx, dy, scale) in painting
        pixels, about its hooves. It charges straight at us: in perspective it grows faster and
        faster and sweeps outwards from the vanishing point behind the herd, off the screen."""
        hz = self.horses[hi]
        vx, vy = self.pad + self.vp[0] * self.w, self.pad + self.vp[1] * self.h
        sc = 1 / max(0.12, 1 - (0.42 * tau + 0.32 * tau * tau))     # perspective: ever faster as it nears
        # each veers out to its own side to pass us by (and a little the way the herd runs)
        sgn = 1 if hz["lmid"] >= vx + 0.02 * self.w else -1
        veer = (sgn * (30 * tau + 90 * tau * tau) + self.run_out[0] * 40 * tau) * self.k * sc ** 0.5
        return (hz["lmid"] - vx) * (sc - 1) + veer, (hz["lbot"] - vy) * (sc - 1), sc

    @staticmethod
    def passing(sc):
        """A charging horse fades as it passes us (alpha 1 until it is 3.5 times its size, gone by 6)."""
        return float(np.clip((6.0 - sc) / 2.5, 0, 1))

    def sprites(self, rgba, t):
        """Each horse that has broken out: its galloping pixels (taken through the same warp as the
        painting) cut out, with where and how big it now is."""
        out = []
        if not self.leave or getattr(self, "last_map", None) is None:
            return out
        mx, my = self.last_map
        for hi, hz in enumerate(self.horses):
            if hi not in self.leave or t <= self.leave[hi]:
                continue
            ys, xs = np.nonzero(hz["cut"] > 0.02)
            m = int(14 * self.k)
            y0, y1 = max(0, ys.min() - m), min(rgba.shape[0], ys.max() + m)
            x0, x1 = max(0, xs.min() - m), min(rgba.shape[1], xs.max() + m)
            sx, sy = mx[y0:y1, x0:x1], my[y0:y1, x0:x1]
            rgb = cv2.remap(np.ascontiguousarray(rgba[..., :3]), sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            a = cv2.remap(hz["cut"], sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            tau = t - self.leave[hi]
            dx, dy, s = self.out_path(hi, tau)
            if self.passing(s) <= 0:
                continue
            out.append(dict(fade=self.passing(s), hi=hi, rgb=rgb, a=a, x0=x0, y0=y0, ax=hz["lmid"], ay=hz["lbot"], dx=dx, dy=dy, s=s,
                            tau=tau))
        out.sort(key=lambda d: d["s"])                       # nearer (bigger) ones on top
        return out

    # ---------------------------------------------------------- the hooves
    def hoof_events(self, t0, t1, include_gone=False):
        """Every hoof landing between t0 and t1 (seconds of animation): (t, x, y, horse, side), x and y
        in padded-painting pixels. Each leg pair lands as two quick hits, front and back half a stride
        apart, so a horse makes the ta-ta . ta-ta of a gallop."""
        out = []
        om = 2 * math.pi * self.gfreq
        for hi, hz in enumerate(self.horses):
            for s in (-1, 1):
                base = 1.5 * math.pi - hz["phase"] - 1.2 - 1.6 * s * hz["front"]
                m0 = math.floor((om * t0 - base) / (2 * math.pi)) - 1
                for m in range(m0, m0 + int((t1 - t0) * self.gfreq) + 4):
                    tl = (base + 2 * math.pi * m) / om
                    for j, dt in enumerate((0.0, 0.055)):
                        t = tl + dt
                        if include_gone is False and hi in self.leave and t > self.leave[hi] - 0.02:
                            continue
                        if t0 <= t < t1:
                            x = hz["lmid"] + s * (0.5 + 0.25 * j) * hz["lhalf"]
                            out.append((t, x, hz["lbot"] - 6 * self.k, hi, s))
        return sorted(out)

    def _poly_mask(self, polys, feather):
        h, w, pad = self.h, self.w, self.pad
        m = np.zeros((h, w), np.float32)
        for poly in polys:
            pts = np.round(np.array(poly) * [w, h] * 4).astype(np.int32)
            cv2.fillPoly(m, [pts], 1.0, cv2.LINE_AA, shift=2)
        return np.pad(cv2.GaussianBlur(m, (0, 0), feather * self.k), pad)

    def _make_horse(self, hs):
        k, pad, w, h = self.k, self.pad, self.w, self.h
        whole = self._poly_mask([hs["body"], hs["legs"]] + hs.get("hair", []), 6)
        legs = self._poly_mask([hs["legs"]], 4)
        hair = self._poly_mask(hs.get("hair", []), 4) if hs.get("hair") else None
        b = np.array(hs["body"]) * [w, h] + pad
        lg = np.array(hs["legs"]) * [w, h] + pad
        return dict(whole=whole, legs=legs, hair=hair, phase=hs["phase"], front=hs.get("front", 1),
                    cx=b[:, 0].mean(), cy=b[:, 1].mean(),
                    ltop=lg[:, 1].min(), lbot=lg[:, 1].max(), lmid=lg[:, 0].mean(),
                    lhalf=(lg[:, 0].max() - lg[:, 0].min()) / 2)

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

    # ---------------------------------------------------------- water and spray
    def _box(self, x0, y0, x1, y1):
        H2, W2 = self.X.shape
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(W2, int(x1)), min(H2, int(y1))
        return (slice(y0, y1), slice(x0, x1)) if x1 > x0 and y1 > y0 else None

    def _wakes(self, dx, dy, a, sp, t):
        """A V of ripples trailing behind each horse, travelling outwards as it runs, a churned
        streak straight behind it, and a ring of ripples from every hoof that lands."""
        k = self.k
        d = np.array(sp.get("direction", RUN), float); d /= np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        A = sp.get("amp", 2.6) * k
        tan = 0.36
        for hi, hz in enumerate(self.horses):
            here = 1 - self.gone(hi, t)                      # no wake once it has run off
            if here <= 0:
                continue
            hx, hy = hz["lmid"], hz["lbot"] - 4 * k
            bx = self._box(hx - 300 * k, hy - 50 * k, hx + 40 * k, hy + 110 * k)
            if bx is None:
                continue
            Xs, Ys = self.X[bx] - hx, self.Y[bx] - hy
            al = -(Xs * d[0] + Ys * d[1])                    # distance behind the horse
            ac = Xs * n[0] + Ys * n[1]
            on = np.clip(al / (14 * k), 0, 1) * np.exp(-np.clip(al, 0, None) / (190 * k))
            arm = np.exp(-((np.abs(ac) - al * tan) / (5 * k + 0.1 * np.abs(al))) ** 2) * on
            wave = np.sin(2 * math.pi * al / (15 * k) + 2 * math.pi * 2.2 * t + hi * 1.7)
            sg = np.sign(ac)
            m = a[bx] * here
            dx[bx] += m * A * arm * wave * sg * n[0]
            dy[bx] += m * A * arm * wave * sg * n[1] * 0.6
            core = np.exp(-(ac / (9 * k + 0.08 * np.abs(al))) ** 2) * on
            churn = np.sin(0.16 * Xs / k - 8 * t + hi) * np.sin(0.21 * Ys / k + 6.5 * t)
            dx[bx] += m * 1.8 * k * core * churn
            dy[bx] += m * 1.2 * k * core * np.cos(0.14 * Xs / k + 7 * t + hi)
        # ripple rings from each hoof landing, flattened by perspective
        for (tl, x, y, hi, side) in self.hoof_events(t - 1.1, t):
            tau = t - tl
            r = 4 * k + 75 * k * tau
            w = 4 * k * (1 + 1.5 * tau)
            amp = 2.2 * k * math.exp(-2.6 * tau)
            bx = self._box(x - r - 3 * w, y - (r + 3 * w) / 2.4, x + r + 3 * w, y + (r + 3 * w) / 2.4)
            if bx is None:
                continue
            vx, vy = self.X[bx] - x, (self.Y[bx] - y) * 2.4
            dist = np.sqrt(vx * vx + vy * vy) + 1e-3
            ring = amp * np.exp(-((dist - r) / w) ** 2) * np.sin(2 * math.pi * (dist - r) / (9 * k))
            m = a[bx]
            dx[bx] += m * ring * vx / dist
            dy[bx] += m * ring * vy / dist / 2.4

    def _crowns(self, dy, dx, t, amp_in):
        """The white water at a hoof heaves up as it lands, then falls back."""
        k = self.k
        for (tl, x, y, hi, side) in self.hoof_events(t - 0.5, t):
            tau = t - tl
            amp = 9 * k * (1 - math.exp(-tau * 40)) * math.exp(-tau * 7) * amp_in
            bx = self._box(x - 30 * k, y - 45 * k, x + 30 * k, y + 20 * k)
            if bx is None:
                continue
            vx, vy = self.X[bx] - x, self.Y[bx] - (y - 6 * k)
            bump = np.exp(-(vx / (13 * k)) ** 2 - (vy / (14 * k)) ** 2) * self.light[bx]
            dy[bx] += amp * bump
            dx[bx] += 0.35 * amp * bump * np.sin(0.4 * vy / k + 3 * hi)

    def _spray(self, out, e, t, amp_in):
        """Drops and a soft puff of white, in the colour of the white water at that horse's hooves,
        flung up and back from each landing hoof."""
        k = self.k
        sp = e["spec"]
        d = np.array(sp.get("direction", RUN), float); d /= np.linalg.norm(d)
        H2, W2 = out.shape[:2]
        acc_a = np.zeros((H2, W2), np.float32)
        acc_c = np.zeros((H2, W2, 3), np.float32)

        def stamp(cx, cy, r, stretch, ang, alpha, col):
            R = int(r * max(1.0, stretch) * 2.2) + 2
            bx = self._box(cx - R, cy - R, cx + R + 1, cy + R + 1)
            if bx is None:
                return
            vx, vy = self.X[bx] - cx, self.Y[bx] - cy
            ca, sa = math.cos(ang), math.sin(ang)
            u, v = vx * ca + vy * sa, -vx * sa + vy * ca
            g = np.exp(-(u / (r * stretch)) ** 2 - (v / r) ** 2) * alpha
            acc_a[bx] += g
            acc_c[bx] += g[..., None] * col

        for idx, (tl, x, y, hi, side) in enumerate(self.hoof_events(t - 0.8, t)):
            tau = t - tl
            rng = np.random.default_rng([int(round(tl * 1000)) & 0xffffffff, hi, side + 1])
            col = 0.75 * self.horses[hi]["spray_col"] + 0.25 * np.array([232, 238, 242], np.float32)
            for j in range(5):
                vy0 = -rng.uniform(170, 330) * k
                vx0 = (-d[0] * rng.uniform(40, 220) + rng.uniform(-90, 90)) * k
                g = 1500 * k
                life = -2 * vy0 / g * rng.uniform(0.85, 1.0)
                if tau > life:
                    continue
                px = x + rng.uniform(-6, 6) * k + vx0 * tau
                py = y - 4 * k + vy0 * tau + 0.5 * g * tau * tau
                vxt, vyt = vx0, vy0 + g * tau
                sp_ = math.hypot(vxt, vyt)
                fade = (1 - tau / life) ** 0.7 * min(1.0, tau / 0.03)
                stamp(px, py, rng.uniform(2.6, 4.2) * k, 1 + sp_ / (160 * k), math.atan2(vyt, vxt),
                      0.55 * fade * amp_in, col)
            if tau < 0.6:   # the puff of spray
                r = (9 + 26 * tau) * k
                stamp(x - d[0] * 14 * k * tau, y - 10 * k - 34 * k * tau, r, 1.3, 0.0,
                      0.5 * (1 - tau / 0.6) ** 1.3 * amp_in, col)
        A = np.clip(acc_a, 0, 0.92)
        C = acc_c / (acc_a[..., None] + 1e-5)
        A = A * out[..., 3]
        out[..., :3] = out[..., :3] * (1 - A[..., None]) + C * A[..., None]

    def _mist(self, out, e, t, amp_in):
        """The waterfall's own whites, blurred into mist, drifting off it in slow wisps."""
        k = self.k
        sp = e["spec"]
        d = np.array(sp.get("direction", (-0.85, -0.45)), float); d /= np.linalg.norm(d)
        P, v = 190 * k, 26 * k
        tx = 9 * k * np.sin(0.017 * self.Y / k + 0.6 * t) + 5 * k * np.sin(0.04 * self.X / k - 0.9 * t)
        ty = 6 * k * np.sin(0.015 * self.X / k - 0.5 * t)
        acc_a, acc_c, wsum = 0, 0, 0
        for phase in (0.0, 0.5):
            u = (t * v / P + phase) % 1.0
            wgt = 1 - abs(2 * u - 1)
            mx = (self.X - d[0] * u * P + tx).astype(np.float32)
            my = (self.Y - d[1] * u * P + ty).astype(np.float32)
            a_ = cv2.remap(e["mA"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            c_ = cv2.remap(e["mC"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            acc_a = acc_a + wgt * a_
            acc_c = acc_c + wgt * c_ * a_[..., None]
            wsum += wgt
        A = acc_a / wsum
        C = 0.45 * acc_c / (acc_a[..., None] + 1e-5) + 0.55 * np.array([244, 247, 249], np.float32)
        A = np.clip((A - 0.12) / 0.5, 0, 1) ** 1.4 * 0.3 * e["mask"] * amp_in * out[..., 3]
        out[..., :3] = out[..., :3] * (1 - A[..., None]) + C * A[..., None]

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
                gst = sp.get("gust", 0.0)
                gfac = 1.0
                if gst:
                    # gusts from the gallop: swells of wind sweeping across, the branches tossing in them
                    swell = (0.5 + 0.5 * np.sin(2 * math.pi * 0.42 * t - 0.007 * X / k + ph[5])) ** 1.5
                    toss = np.sin(3.3 * t + 0.011 * X / k + 0.006 * Y / k + ph[3]) \
                        + 0.5 * np.sin(2 * math.pi * self.gfreq * t + 0.02 * X / k)
                    wind = 0.6 * wind + gst * 1.1 * swell * toss
                    gfac = 1 + gst * swell
                dx += a * A * hgt * wind
                dy += a * A * 0.25 * hgt * np.sin(1.1 * t + 0.006 * X / k + ph[2]) * gfac
                fl = sp.get("flutter", 0.0) * k * gfac
                if np.any(fl):
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
            elif kd == "gallop":
                om = 2 * math.pi * sp.get("freq", 2.4)
                for hz in e["horses"]:
                    ph = hz["phase"]
                    wm = amp_in * hz["whole"]
                    cyc = om * t + ph
                    # the body: bob (twice per stride, like a real gallop's suspension), rock fore and aft, surge
                    bob = 2.6 * k * math.sin(2 * cyc) + 1.2 * k * math.sin(cyc + 0.6)
                    surge = 2.0 * k * math.sin(cyc + 1.0)
                    rock = 0.016 * math.sin(cyc + 1.9)
                    rx, ry = X - hz["cx"], Y - hz["cy"]
                    ca, sa = math.cos(rock) - 1, math.sin(rock)
                    dx += wm * (surge + ca * rx - sa * ry)
                    dy += wm * (bob + sa * rx + ca * ry)
                    # the legs: swing grows down to the hooves; front and back pairs half a stride apart
                    lm = amp_in * hz["legs"]
                    depth = np.clip((Y - hz["ltop"]) / max(1.0, hz["lbot"] - hz["ltop"]), 0, 1) ** 1.3
                    fb = np.tanh((X - hz["lmid"]) / (0.35 * hz["lhalf"] + 1e-3)) * hz["front"]
                    lp = cyc + 1.2 + 1.6 * fb
                    dx += lm * depth * 6.0 * k * np.sin(lp)
                    dy += lm * depth * 2.4 * k * np.maximum(0, -np.cos(lp))
                    # mane and tail flutter
                    if hz["hair"] is not None:
                        hm = amp_in * hz["hair"]
                        dx += hm * 1.7 * k * np.sin(0.30 * Y / k + 3 * cyc)
                        dy += hm * 1.3 * k * np.sin(0.27 * X / k + 3 * cyc + 1.3)
            elif kd == "wake":
                self._wakes(dx, dy, a, sp, t)
            elif kd == "spray":
                self._crowns(dy, dx, t, amp_in)
            elif kd == "splash":
                om = 2 * math.pi * sp.get("freq", 2.4)
                A = sp.get("amp", 4) * k
                kick = np.maximum(0, np.sin(om * t + 2 * math.pi * 1.7 * fx + ph[0])) ** 3
                dy += a * A * kick * (0.6 + 0.4 * np.sin(0.4 * X / k + 7 * t))
                dx += a * A * 0.5 * np.sin(0.25 * Y / k + 0.3 * X / k + 5 * t + ph[1])
        self.last_map = ((X + dx).astype(np.float32), (Y + dy).astype(np.float32))
        if not flows:
            out = cv2.remap(rgba, X + dx, Y + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        else:
            # two phases of a looping scroll, crossfaded so the loop never shows
            outs, wts = [], []
            for phase in (0.0, 0.5):
                fxs, fys = dx.copy(), dy.copy()
                wsum = np.full(X.shape, 0.5, np.float32)        # per pixel: each flow its own crossfade
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
                    me = np.clip(e["mask"] * 4, 0, 1)
                    wsum = wsum * (1 - me) + me * (1 - abs(2 * u - 1))  # triangle weight
                outs.append(cv2.remap(rgba, X + fxs, Y + fys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
                wts.append(wsum)
            wa, wb = wts
            s = wa + wb + 1e-6
            out = outs[0] * (wa / s)[..., None] + outs[1] * (wb / s)[..., None]
        out[..., 3] = rgba[..., 3]
        for e in self.effects:
            if e["spec"]["kind"] == "mist":
                self._mist(out, e, t, amp_in)
        for e in self.effects:
            if e["spec"]["kind"] == "spray":
                self._spray(out, e, t, amp_in)

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
