"""The opening: the canvas arrives as a kraft-paper parcel tied with twine (the
same parcel as the site's loading screen, js/loading.js), drops in, the twine
snaps, and the four flaps peel back one after another like real paper: a curl
travels across each flap (a cylinder page-curl applied to a mesh of the flap's
texture), the paper sags and flutters, flops over and settles, then is crumpled
progressively into a ball and tossed off-screen. Underneath is the blank primed canvas, in
the painting's exact box or oval, ready for the doodle.

Timeline (frames at 30 fps): 0-9 drop and land, 12 twine snaps, from 16 a flap
starts peeling every 7 frames (20 frames each, then settle, crumple, fly).
EVENTS lists the moments for the soundtrack.
"""
import math
import numpy as np
import cv2

KRAFT = np.array([201, 159, 104], np.float32)
KRAFT_D = np.array([169, 127, 76], np.float32)
KRAFT_L = np.array([226, 196, 149], np.float32)
TWINE = np.array([233, 220, 192], np.float32)
EDGE = np.array([96, 66, 36], np.float32)

T_LAND, T_SNAP, T_FLAP0, FLAP_STAG, FLAP_DUR = 9, 12, 16, 7, 20
SETTLE, CRUMPLE, FLY = 5, 10, 14       # after a flap is over: settle bounce, crumple, fly off


def flap_start(i):
    return T_FLAP0 + i * FLAP_STAG


END = flap_start(3) + FLAP_DUR + SETTLE + CRUMPLE + FLY
EVENTS = dict(land=T_LAND, snap=T_SNAP,
              flaps=[flap_start(i) + 5 for i in range(4)],                        # the curl gets going
              crumple=[flap_start(i) + FLAP_DUR + SETTLE for i in range(4)],
              whoosh=[flap_start(i) + FLAP_DUR + SETTLE + CRUMPLE for i in range(4)], end=END)


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
        if f < T_FLAP0 + 4:
            self._shadow(frame, ox, oy, 1, 1, 0.35)
        # build every flap's mesh for this frame, then: shadows, flat parts, lifted parts
        meshes = [self._flap_mesh(i, f) for i in range(4)]
        sh = np.zeros((self.H, self.W), np.float32)
        for m in meshes:
            if m is not None and m["lifted"]:
                self._mesh_shadow(sh, m)
        if sh.max() > 0:
            sh = cv2.GaussianBlur(sh, (0, 0), 9 * k)
            frame *= (1 - 0.32 * np.clip(sh, 0, 1))[..., None]
        tris = []
        for m in meshes:
            if m is not None:
                tris += m["tris"]
        tris.sort(key=lambda t: t[0])                        # lowest first, so the curl rolls over the rest
        for z, src, s_tri, d_tri, shade in tris:
            self._mesh_tri(frame, src, s_tri, d_tri, shade)
        for m in meshes:                                     # the paper's cut edge
            if m is not None and m.get("rim") is not None:
                p = np.round(m["rim"] * 4).astype(np.int32).reshape(-1, 1, 2)
                ov = frame.copy()
                cv2.polylines(ov, [p], True, EDGE.tolist(), max(1, int(1.4 * k)), cv2.LINE_AA, shift=2)
                frame[:] = frame * 0.45 + ov * 0.55
        for i in range(4):
            t0 = flap_start(i) + FLAP_DUR + SETTLE + CRUMPLE
            if f >= t0:
                self._ball(frame, i, f - t0)
        if f < T_SNAP + 7:   # the snapped twine whipping back to the edges
            r = ease((f - T_SNAP) / 6)
            self._twine(frame, ox, oy, retract=0.15 + 0.85 * r, alpha=1 - r)
        return frame

    # ---- paper physics, faked: a travelling cylinder curl on a mesh
    NG = 14

    def _flap_mesh(self, i, f):
        k = self.k
        a, b, c = [np.array(p, np.float64) for p in self.flaps[i]]
        o = np.array([self.px0, self.py0], np.float64)
        Mid = (a + b) / 2
        D = np.linalg.norm(c - Mid)
        nin = (c - Mid) / D
        t = (f - flap_start(i)) / FLAP_DUR
        tc = (f - flap_start(i) - FLAP_DUR - SETTLE) / CRUMPLE
        if tc >= 1:
            return None
        # the curl's travel: a slow start, then the paper flops over, overshoots and settles
        if t <= 0:
            E = 0.0
        elif t < 1:
            E = ease(t) ** 1.7
        else:
            ts = min(1.0, (f - flap_start(i) - FLAP_DUR) / SETTLE)
            E = 1 + 0.07 * math.sin(math.pi * ts) * (1 - ts)
        moving = 0 < t < 1.0 + SETTLE / FLAP_DUR
        R = D * (0.13 + 0.05 * math.sin(math.pi * min(1, max(0, t))))     # looser in the middle of the flop
        rng = np.random.default_rng(100 + i)
        jit = rng.normal(0, 1, (self.NG + 1, self.NG + 1, 2))
        tri_shade = rng.uniform(0.6, 1.0, (self.NG, self.NG, 2))
        n = self.NG
        s1 = np.linspace(0, 1, n + 1)[None, :].repeat(n + 1, 0)       # along the edge
        s2 = np.linspace(0, 1, n + 1)[:, None].repeat(n + 1, 1)       # towards the apex
        L = (1 - s2)[..., None] * (a + s1[..., None] * (b - a)) + s2[..., None] * c   # rest positions (local)
        u = s2 * D
        foot = L - nin * u[..., None]
        # the bend line sags and flutters: paper, not board
        p_line = D * (1 - E) + 0.12 * D * np.sin(np.pi * s1) * math.sin(math.pi * min(1.0, E)) \
            + (0.025 * D * np.sin(2 * np.pi * 2.2 * s1 + 1.3 * f) * math.sin(math.pi * min(1.0, max(0.0, t))))
        sarc = u - p_line
        phi = np.clip(sarc / R, 0, math.pi)
        uu = np.where(sarc <= 0, u, np.where(sarc <= math.pi * R, p_line + R * np.sin(phi), p_line - (sarc - math.pi * R)))
        z = np.where(sarc <= 0, 0.0, np.where(sarc <= math.pi * R, R * (1 - np.cos(phi)), 2 * R))
        # weight: the rolled-over part droops a touch as it flops
        uu = uu - (z > R) * 0.04 * D * math.sin(math.pi * min(1.0, max(0.0, t)))
        P = foot + nin * uu[..., None] + o
        # perspective: the lifted paper swells a little towards the viewer
        cen = np.array([self.W / 2, self.H * 0.45])
        P = P + (P - cen) * (z * 0.00045 / k)[..., None]
        if tc > 0:   # crumpling, progressively, towards the folded flap's middle
            e = ease(tc)
            G = P.reshape(-1, 2).mean(0)
            P = G + (P - G) * (1 - 0.62 * e) + jit * (0.07 * D * e)
        tris = []
        lifted = False
        for r in range(n):
            for q in range(n):
                quad = [(r, q), (r, q + 1), (r + 1, q + 1), (r + 1, q)]
                for h, tri in enumerate(([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]])):
                    if r == n - 1 and h == 0 and False:
                        continue
                    srcp = [L[j] for j in tri]
                    e1, e2 = srcp[1] - srcp[0], srcp[2] - srcp[0]
                    if abs(e1[0] * e2[1] - e1[1] * e2[0]) < 1e-3:
                        continue
                    dstp = [P[j] for j in tri]
                    ph = float(np.mean([phi[j] for j in tri]))
                    zz = float(np.mean([z[j] for j in tri]))
                    if zz > 0.5:
                        lifted = True
                    if ph < math.pi / 2:
                        src = self.closed if ph == 0 and f < flap_start(i) + 1 else self.tex
                        # front: darkens as it tilts away, catches light on the top of the roll
                        shade = 0.78 + 0.22 * math.cos(ph) + 0.18 * math.sin(ph) ** 6
                    else:
                        src = self.under
                        shade = 0.82 + 0.16 * math.sin(ph) + 0.10 * (1 - abs(math.cos(ph)))
                    if tc > 0:
                        shade *= 1 - 0.38 * ease(tc) * (1 - tri_shade[r, q, h])
                    tris.append((zz + 0.001 * i, src, srcp, dstp, shade))
        # outline of the flap: its two free edges plus the base
        rim = np.concatenate([P[0, :], P[1:, -1], P[-1, ::-1][1:], P[::-1, 0][1:]], 0)
        return dict(tris=tris, lifted=lifted and moving, rim=rim, P=P, z=z)

    def _mesh_shadow(self, sh, m):
        k = self.k
        P, z = m["P"], m["z"]
        n = self.NG
        for r in range(n):
            for q in range(n):
                zz = (z[r, q] + z[r + 1, q + 1]) / 2
                if zz < 0.5:
                    continue
                pts = np.float32([P[r, q], P[r, q + 1], P[r + 1, q + 1], P[r + 1, q]])
                pts = pts + np.float32([0.35 * zz + 3 * k, 0.55 * zz + 5 * k])
                cv2.fillPoly(sh, [np.round(pts * 4).astype(np.int32)], float(min(1.0, zz / (45 * k))), cv2.LINE_8, shift=2)

    def _mesh_tri(self, frame, src, tri_src, tri_dst, shade):
        """Map a little triangle of the flap's texture onto its bent place, no seams."""
        d = np.float32(tri_dst)
        g = d.mean(0)
        d = g + (d - g) * 1.06 + np.sign(d - g) * 0.4          # overlap neighbours slightly
        x_0, y_0 = np.floor(d.min(0)).astype(int) - 1
        x_1, y_1 = np.ceil(d.max(0)).astype(int) + 2
        x_0, y_0 = max(0, x_0), max(0, y_0)
        x_1, y_1 = min(self.W, x_1), min(self.H, y_1)
        if x_1 - x_0 < 1 or y_1 - y_0 < 1:
            return
        dd = d - [x_0, y_0]
        M = cv2.getAffineTransform(np.float32(tri_src), np.float32(dd))
        warped = cv2.warpAffine(src, M, (x_1 - x_0, y_1 - y_0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        mask = np.zeros((y_1 - y_0, x_1 - x_0), np.uint8)
        cv2.fillPoly(mask, [np.round(dd * 4).astype(np.int32)], 1, cv2.LINE_8, shift=2)
        sub = frame[y_0:y_1, x_0:x_1]
        msk = mask.astype(bool)
        sub[msk] = warped[msk] * shade

    def _ball(self, frame, i, tf_frames):
        """The crumpled flap, now a ball, tossed off-screen with a bounce."""
        k = self.k
        rng = np.random.default_rng(i * 17 + 3)
        a, b, c = [np.array(p, np.float64) for p in self.flaps[i]]
        o = np.array([self.px0, self.py0])
        Mid = (a + b) / 2 + o
        C = o + np.array([self.pw / 2, self.ph / 2])
        out = Mid - C
        out /= np.linalg.norm(out) + 1e-6
        D = np.linalg.norm(c - (a + b) / 2)
        start = Mid + out * D * 0.45                               # where the crumpled flap ended up
        r = 0.42 * D * 0.38 + 0.22 * np.linalg.norm(b - a) * 0.38
        tf = tf_frames / 30
        vx = out[0] * 1700 * k + rng.uniform(-200, 200) * k
        vy = out[1] * 1000 * k - 1100 * k
        x = start[0] + vx * tf
        y = start[1] + vy * tf + 3200 * k * tf * tf
        if x < -2 * r or x > self.W + 2 * r or y > self.H + 2 * r or y < -3 * r:
            return
        n = 18
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + tf * 9 * (1 if i % 2 else -1)
        rad = r * (1 + 0.2 * rng.uniform(-1, 1, n))
        pts = np.stack([x + rad * np.cos(ang), y + rad * np.sin(ang)], 1)
        x0, y0 = int(max(0, x - 2 * r)), int(max(0, y - 2 * r))
        x1, y1 = int(min(self.W, x + 2 * r)), int(min(self.H, y + 2 * r))
        if x1 <= x0 or y1 <= y0:
            return
        mask = np.zeros((y1 - y0, x1 - x0), np.float32)
        cv2.fillPoly(mask, [np.round((pts - [x0, y0]) * 4).astype(np.int32)], 1.0, cv2.LINE_AA, shift=2)
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        shade = 1.05 - 0.35 * np.clip(((gx - x + 0.35 * r) ** 2 + (gy - y + 0.35 * r) ** 2) / (r * r * 2.2), 0, 1)
        col = KRAFT[None, None, :] * shade[..., None]
        cre = np.zeros_like(mask)
        for _ in range(11):
            aa = rng.uniform(0, 2 * np.pi)
            p = np.float32([[x - x0, y - y0], [x - x0 + math.cos(aa) * r, y - y0 + math.sin(aa) * r],
                            [x - x0 + math.cos(aa + 0.5) * r * 0.6, y - y0 + math.sin(aa + 0.5) * r * 0.6]])
            cv2.polylines(cre, [np.round(p * 4).astype(np.int32)], False, 1.0, max(1, int(1.5 * k)), cv2.LINE_AA, shift=2)
        col *= (1 - 0.45 * cre)[..., None]
        ring = np.zeros_like(mask)
        cv2.polylines(ring, [np.round((pts - [x0, y0]) * 4).astype(np.int32)], True, 1.0, max(1, int(1.8 * k)), cv2.LINE_AA, shift=2)
        col = col * (1 - 0.6 * ring[..., None]) + EDGE * 0.6 * ring[..., None]
        sub = frame[y0:y1, x0:x1]
        sub[:] = sub * (1 - mask[..., None]) + col * mask[..., None]
