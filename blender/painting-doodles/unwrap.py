"""The opening: the canvas arrives as a kraft-paper parcel tied with twine (the
same parcel as the site's loading screen, js/loading.js), drops in, the twine
snaps, the four flaps fold back one after another, and each flap is scrunched
into a ball and tossed off-screen. Underneath is the blank primed canvas, in
the painting's exact box or oval, ready for the doodle.

Timeline (frames at 30 fps): 0-9 drop and land, 12 twine snaps, 16-42 flaps fold
back, 40-60 flaps crumple and fly away. EVENTS lists them for the soundtrack.
"""
import math
import numpy as np
import cv2

KRAFT = np.array([201, 159, 104], np.float32)
KRAFT_D = np.array([169, 127, 76], np.float32)
KRAFT_L = np.array([226, 196, 149], np.float32)
TWINE = np.array([233, 220, 192], np.float32)
EDGE = np.array([96, 66, 36], np.float32)

T_LAND, T_SNAP, T_FLAP0, FLAP_STAG, FLAP_DUR, T_CRUMPLE = 9, 12, 16, 5, 13, 40
END = 60
EVENTS = dict(land=T_LAND, snap=T_SNAP, flaps=[T_FLAP0 + i * FLAP_STAG for i in range(4)],
              crumple=[T_CRUMPLE + 2 * i for i in range(4)], whoosh=T_CRUMPLE + 8, end=END)


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def kraft_texture(h, w, k, rng, pale=False):
    """Kraft paper: base colour, mottling, long fibres, speckles, a few creases."""
    base = KRAFT_L * 0.55 + KRAFT * 0.45 if pale else KRAFT.copy()
    mott = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 18 * k)
    mott /= mott.std() + 1e-6
    fib = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=7 * k, sigmaY=0.7 * k)
    fib /= fib.std() + 1e-6
    fib2 = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=0.7 * k, sigmaY=5 * k)
    fib2 /= fib2.std() + 1e-6
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    tex = base[None, None, :] * (1 + 0.045 * mott + 0.05 * fib + 0.02 * fib2 + 0.012 * grain)[..., None]
    # speckles: darker bits of wood pulp and lighter flecks
    n = int(h * w / (1100 * k * k))
    for _ in range(n):
        y, x = rng.integers(h), rng.integers(w)
        c = (150, 108, 62) if rng.random() < 0.6 else (232, 208, 168)
        cv2.circle(tex, (int(x), int(y)), max(1, int(rng.uniform(0.6, 1.6) * k)), c, -1, cv2.LINE_AA)
    # creases: a dark valley with a lit ridge beside it
    shade = np.zeros((h, w), np.float32)
    for _ in range(7):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(0.25, 0.7) * max(w, h)
        pts = []
        for i in range(6):
            t = i / 5 - 0.5
            pts.append((x0 + math.cos(a) * L * t + rng.normal(0, 4 * k), y0 + math.sin(a) * L * t + rng.normal(0, 4 * k)))
        p = np.round(np.array(pts) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(shade, [p], False, -1.0, max(1, int(2 * k)), cv2.LINE_AA, shift=2)
        p2 = np.round((np.array(pts) + [1.8 * k, 1.8 * k]) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(shade, [p2], False, 0.8, max(1, int(2 * k)), cv2.LINE_AA, shift=2)
    shade = cv2.GaussianBlur(shade, (0, 0), 1.2 * k)
    tex *= (1 + 0.18 * shade)[..., None]
    return np.clip(tex, 0, 255)


class Parcel:
    def __init__(self, W, H, k, box, rng):
        self.W, self.H, self.k = W, H, k
        x0, y0, w, h = box
        m = int(16 * k)
        self.px0, self.py0 = x0 - m, y0 - m
        self.pw, self.ph = w + 2 * m, h + 2 * m
        pw, ph = self.pw, self.ph
        self.rng = rng
        self.tex = kraft_texture(ph, pw, k, rng)
        self.under = kraft_texture(ph, pw, k, rng, pale=True)
        C = (pw / 2, ph / 2)
        TL, TR, BR, BL = (0, 0), (pw, 0), (pw, ph), (0, ph)
        self.flaps = [(TL, TR, C), (TR, BR, C), (BR, BL, C), (BL, TL, C)]   # top, right, bottom, left
        # fold lines along the diagonals, and an edge line, baked into the closed parcel
        closed = self.tex.copy()
        fold = np.zeros((ph, pw), np.float32)
        for a, b, c in self.flaps:
            p = np.round(np.array([a, c]) * 4).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(fold, [p], False, 1.0, max(1, int(2.2 * k)), cv2.LINE_AA, shift=2)
        fold = cv2.GaussianBlur(fold, (0, 0), 1.0 * k)
        closed *= (1 - 0.22 * fold)[..., None]
        self.closed = closed
        self.bow = rng.uniform(-0.2, 0.2)

    # ---- drawing helpers
    def _twine(self, img, ox, oy, sx=1.0, sy=1.0, retract=0.0, alpha=1.0):
        """The twine cross and bow. retract 0..1 pulls each half back to its edge after the snap."""
        k = self.k
        pw, ph = self.pw, self.ph
        cx, cy = ox + pw / 2 * sx, oy + ph / 2 * sy
        ends = [(ox, cy), (ox + pw * sx, cy), (cx, oy), (cx, oy + ph * sy)]
        lay = np.zeros(img.shape[:2], np.float32)
        col = np.zeros_like(img)
        for (ex, ey) in ends:
            n = 24
            pts = []
            for i in range(n + 1):
                t = i / n * (1 - retract)
                x = ex + (cx - ex) * t
                y = ey + (cy - ey) * t
                if retract > 0:   # the freed end curls and droops
                    curl = math.sin(t * math.pi) * 22 * k * retract
                    x += curl * (1 if ey == cy else 0.3)
                    y += curl * (1 if ex == cx else 0.6)
                pts.append((x, y))
            p = np.round(np.array(pts) * 4).astype(np.int32).reshape(-1, 1, 2)
            sh = np.round((np.array(pts) + [2 * k, 3 * k]) * 4).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(lay, [sh], False, -0.35, max(1, int(9 * k)), cv2.LINE_AA, shift=2)
            cv2.polylines(lay, [p], False, 1.0, max(1, int(8 * k)), cv2.LINE_AA, shift=2)
        if retract == 0:   # the bow
            for sgn in (-1, 1):
                cv2.ellipse(lay, (int(cx + sgn * 15 * k), int(cy - 7 * k)), (int(15 * k), int(9 * k)),
                            math.degrees(-sgn * 0.5 + self.bow), 0, 360, 1.0, max(1, int(5 * k)), cv2.LINE_AA)
            cv2.circle(lay, (int(cx), int(cy - 3 * k)), int(6 * k), 1.0, -1, cv2.LINE_AA)
        a = np.clip(lay, 0, 1) * alpha
        shadow = np.clip(-lay, 0, 1) * alpha
        # twisted-fibre stripes on the twine
        yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float32)
        stripe = 0.88 + 0.12 * np.sin((xx + yy) * 0.9 / k)
        img *= (1 - shadow)[..., None]
        img[:] = img * (1 - a[..., None]) + (TWINE[None, None, :] * stripe[..., None]) * a[..., None]

    def _tri(self, frame, src, tri_src, tri_dst, bright=1.0):
        """Paste the src triangle onto the frame, mapped onto tri_dst (affine)."""
        tri_dst = np.float32(tri_dst)
        x_0, y_0 = np.floor(tri_dst.min(0)).astype(int) - 2
        x_1, y_1 = np.ceil(tri_dst.max(0)).astype(int) + 2
        x_0, y_0 = max(0, x_0), max(0, y_0)
        x_1, y_1 = min(self.W, x_1), min(self.H, y_1)
        if x_1 - x_0 < 2 or y_1 - y_0 < 2:
            return
        d = tri_dst - [x_0, y_0]
        M = cv2.getAffineTransform(np.float32(tri_src), np.float32(d))
        warped = cv2.warpAffine(src, M, (x_1 - x_0, y_1 - y_0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mask = np.zeros((y_1 - y_0, x_1 - x_0), np.float32)
        cv2.fillPoly(mask, [np.round(d * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        edge = np.zeros_like(mask)
        cv2.polylines(edge, [np.round(d * 4).astype(np.int32)], True, 1.0, max(1, int(1.6 * self.k)), cv2.LINE_AA, shift=2)
        sub = frame[y_0:y_1, x_0:x_1]
        col = warped * bright
        col = col * (1 - 0.6 * edge[..., None]) + EDGE * 0.6 * edge[..., None]
        sub[:] = sub * (1 - mask[..., None]) + col * mask[..., None]

    def _shadow(self, frame, ox, oy, sx, sy, strength):
        k = self.k
        m = np.zeros((self.H, self.W), np.float32)
        cv2.rectangle(m, (int(ox + 6 * k), int(oy + 14 * k)), (int(ox + self.pw * sx + 6 * k), int(oy + self.ph * sy + 14 * k)), 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), 16 * k)
        frame *= (1 - strength * m)[..., None]

    # ---- one frame
    def draw(self, frame, f):
        """Draw the parcel over `frame` (float32 HxWx3, the paper with the primed canvas)."""
        k = self.k
        if f >= END:
            return frame
        frame = frame.copy()
        if f < T_SNAP:
            # drop in from above, land with a little squash
            t = f / T_LAND
            if t < 1:
                yoff = -(1 - ease(t) ** 1.6) * 900 * k
                sx = sy = 1.0
            else:
                tt = (f - T_LAND) / 3
                sq = math.sin(min(1, tt) * math.pi) * 0.05
                yoff, sx, sy = 0.0, 1 + sq, 1 - sq
            ox = self.px0 - (sx - 1) * self.pw / 2
            oy = self.py0 + yoff + (1 - sy) * self.ph
            self._shadow(frame, ox, oy - yoff * 0.85, sx, sy, 0.35 * (1 - min(1, abs(yoff) / (900 * k))))
            M = np.float32([[sx, 0, ox], [0, sy, oy]])
            img = cv2.warpAffine(self.closed, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            al = cv2.warpAffine(np.ones((self.ph, self.pw), np.float32), M, (self.W, self.H))
            frame = frame * (1 - al[..., None]) + img * al[..., None]
            self._twine(frame, ox, oy, sx, sy)
            return frame

        ox, oy = self.px0, self.py0
        C = np.array([ox + self.pw / 2, oy + self.ph / 2])
        if f < T_FLAP0 + 4:
            self._shadow(frame, ox, oy, 1, 1, 0.35)
        # flaps: rest (closed), folding (lifted, foreshortened), folded out (pale underside up)
        states = []
        for i, (a, b, c) in enumerate(self.flaps):
            t = (f - (T_FLAP0 + i * FLAP_STAG)) / FLAP_DUR
            th = math.pi * ease(t)
            states.append(th)
        order = sorted(range(4), key=lambda i: (states[i] > 0, -abs(states[i] - math.pi / 2)))
        for i in order:
            a, b, c = self.flaps[i]
            th = states[i]
            A = np.array([ox + a[0], oy + a[1]]); B = np.array([ox + b[0], oy + b[1]])
            Mid = (A + B) / 2
            if f >= T_CRUMPLE + 2 * i:
                self._ball(frame, i, f, A, B, Mid)
                continue
            v = C - Mid
            apex = Mid + v * math.cos(th)
            lift = math.sin(th)
            # perspective: the lifted flap swells towards the viewer and leans outwards
            out = Mid - C
            out /= np.linalg.norm(out) + 1e-6
            apex = apex + out * lift * 0.18 * np.linalg.norm(v)
            A2 = A + (A - Mid) * 0.06 * lift
            B2 = B + (B - Mid) * 0.06 * lift
            tri_src = [a, b, c]
            if th == 0:
                src, bright = self.closed, 1.0
            elif math.cos(th) > 0:
                src, bright = self.tex, 0.72 + 0.28 * math.cos(th)
            else:
                src, bright = self.under, 0.86 + 0.14 * abs(math.cos(th))
            if 0 < th < math.pi:   # the lifted flap's soft shadow on the canvas
                sm = np.zeros((self.H, self.W), np.float32)
                cv2.fillPoly(sm, [np.round(np.float32([A, B, (apex + C) / 2]) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
                sm = cv2.GaussianBlur(sm, (0, 0), 10 * k)
                frame *= (1 - 0.13 * lift * sm)[..., None]
            self._tri(frame, src, tri_src, [A2, B2, apex], bright)
        if f < T_SNAP + 7:   # the snapped twine whipping back to the edges
            r = ease((f - T_SNAP) / 6)
            self._twine(frame, ox, oy, retract=0.15 + 0.85 * r, alpha=1 - r)
        return frame

    def _ball(self, frame, i, f, A, B, Mid):
        """A flap scrunched into a ball and tossed off-screen."""
        k = self.k
        rng = np.random.default_rng(i * 17 + 3)
        C = np.array([self.px0 + self.pw / 2, self.py0 + self.ph / 2])
        out = Mid - C
        out /= np.linalg.norm(out) + 1e-6
        rest = Mid + out * 0.33 * np.linalg.norm(B - A) * 0.5        # where the folded flap's middle lies
        t0 = T_CRUMPLE + 2 * i
        tc = (f - t0) / 5                                             # scrunch
        tf = max(0.0, (f - t0 - 5) / 30)                              # fly
        r_full = 0.30 * np.linalg.norm(B - A) * 0.5
        r = r_full * (1.6 - 0.6 * ease(tc))
        vx = out[0] * 1500 * k + rng.uniform(-200, 200) * k
        vy = out[1] * 900 * k - 900 * k
        x = rest[0] + vx * tf
        y = rest[1] + vy * tf + 2600 * k * tf * tf
        if x < -2 * r or x > self.W + 2 * r or y > self.H + 2 * r:
            return
        n = 16
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + f * 0.25 * (1 if i % 2 else -1)
        rad = r * (1 + 0.22 * rng.uniform(-1, 1, n) * ease(tc))
        pts = np.stack([x + rad * np.cos(ang), y + rad * np.sin(ang)], 1)
        mask = np.zeros((self.H, self.W), np.float32)
        cv2.fillPoly(mask, [np.round(pts * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        x0, y0 = int(max(0, x - 2 * r)), int(max(0, y - 2 * r))
        x1, y1 = int(min(self.W, x + 2 * r)), int(min(self.H, y + 2 * r))
        if x1 <= x0 or y1 <= y0:
            return
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        shade = 1.05 - 0.35 * np.clip(((gx - x + 0.35 * r) ** 2 + (gy - y + 0.35 * r) ** 2) / (r * r * 2.2), 0, 1)
        col = KRAFT[None, None, :] * shade[..., None]
        sub_m = mask[y0:y1, x0:x1].copy()
        cre = np.zeros_like(sub_m)
        for _ in range(9):
            a = rng.uniform(0, 2 * np.pi)
            p = np.float32([[x - x0, y - y0], [x - x0 + math.cos(a) * r, y - y0 + math.sin(a) * r],
                            [x - x0 + math.cos(a + 0.5) * r * 0.6, y - y0 + math.sin(a + 0.5) * r * 0.6]])
            cv2.polylines(cre, [np.round(p * 4).astype(np.int32)], False, 1.0, max(1, int(1.5 * k)), cv2.LINE_AA, shift=2)
        col *= (1 - 0.45 * cre * ease(tc))[..., None]
        ring = np.zeros_like(sub_m)
        cv2.polylines(ring, [np.round((pts - [x0, y0]) * 4).astype(np.int32)], True, 1.0, max(1, int(1.8 * k)), cv2.LINE_AA, shift=2)
        col = col * (1 - 0.6 * ring[..., None]) + EDGE * 0.6 * ring[..., None]
        sub = frame[y0:y1, x0:x1]
        sub[:] = sub * (1 - sub_m[..., None]) + col * sub_m[..., None]
