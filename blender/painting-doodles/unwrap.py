"""The opening: the canvas arrives as a parchment parcel tied with twine (after
the site's loading screen, js/loading.js, but in torn-edged parchment), drops in, the twine
snaps, and the four flaps peel back one after another like real paper: a curl
travels across each flap (a cylinder page-curl applied to a mesh of the flap's
texture), the paper sags and flutters, flops over and settles, then is crumpled
progressively into a ball and tossed off-screen. Underneath is the blank primed canvas, in
the painting's exact box or oval, ready for the doodle.

Timeline (frames at 30 fps): 0-9 drop and land, 12 twine snaps, from 16 a flap
starts peeling every 8 frames (22 frames each, then a 6-frame settle, a 14-frame
crumple into a ball, and the ball's flight).
EVENTS lists the moments for the soundtrack.
"""
import math
import numpy as np
import cv2

PARCH = np.array([233, 214, 172], np.float32)      # warm cream parchment
PARCH_D = np.array([196, 160, 108], np.float32)    # its handled, browned edges
PARCH_L = np.array([241, 228, 196], np.float32)    # the paler back
KRAFT = PARCH
TWINE = np.array([233, 220, 192], np.float32)
EDGE = np.array([150, 112, 66], np.float32)

T_LAND, T_SNAP, T_FLAP0, FLAP_STAG, FLAP_DUR = 9, 12, 16, 8, 22
SETTLE, CRUMPLE, FLY = 6, 14, 14       # after a flap is over: settle bounce, crumple, fly off


def flap_start(i):
    return T_FLAP0 + i * FLAP_STAG


END = flap_start(3) + FLAP_DUR + SETTLE + CRUMPLE + FLY
EVENTS = dict(land=T_LAND, snap=T_SNAP,
              flaps=[flap_start(i) for i in range(4)],                            # each curl starts
              flap_dur=FLAP_DUR / 30.0,
              flops=[flap_start(i) + int(FLAP_DUR * 0.7) for i in range(4)],      # it flops over
              settles=[flap_start(i) + FLAP_DUR for i in range(4)],               # and lands
              crumple=[flap_start(i) + FLAP_DUR + SETTLE for i in range(4)],
              crumple_dur=CRUMPLE / 30.0,
              whoosh=[flap_start(i) + FLAP_DUR + SETTLE + CRUMPLE for i in range(4)], end=END)


def _shift(a, d):
    """a moved d pixels right and down, zero-filled (no wrap-around)."""
    out = np.zeros_like(a)
    out[d:, d:] = a[:-d, :-d]
    return out


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def parchment_texture(h, w, k, rng, pale=False):
    """Parchment: a warm cream ground with soft cloudy mottling, faint long fibres, a few
    darker age stains and edges browned with handling. No specks or flecks."""
    base = PARCH_L.copy() if pale else PARCH.copy()
    def blur_noise(sx, sy=None):
        n = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), sigmaX=sx * k,
                             sigmaY=(sy if sy is not None else sx) * k)
        return n / (n.std() + 1e-6)
    cloud = 0.6 * blur_noise(40) + 0.4 * blur_noise(14)          # big soft mottling
    fib = blur_noise(9, 0.8)                                       # faint long fibres
    grain = blur_noise(0.9)
    # age: browner towards the edges, plus a few soft tea-coloured stains
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    edge = edge + 10 * k * blur_noise(20)
    burn = np.exp(-np.clip(edge, 0, None) / (34 * k))
    stain = np.zeros((h, w), np.float32)
    for _ in range(4):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(40, 120) * k
        stain += np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    stain *= 0.5 + 0.5 * np.clip(blur_noise(10), -1, 1)
    lum = 1 + 0.045 * cloud + 0.018 * fib + 0.008 * grain
    tex = base[None, None, :] * lum[..., None]
    st = np.clip(stain * (0.18 if pale else 0.38), 0, 0.5)[..., None]       # tea-coloured, not grey
    tex = tex * (1 - st) + (PARCH_D[None, None, :] * 1.05) * lum[..., None] * st
    tex = tex * (1 - burn[..., None]) + (PARCH_D[None, None, :] * (1 + 0.04 * cloud[..., None])) * burn[..., None]
    # creases: a soft dark valley with a gently lit ridge beside it
    shade = np.zeros((h, w), np.float32)
    for _ in range(6):
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
        cv2.polylines(shade, [p2], False, 0.6, max(1, int(2 * k)), cv2.LINE_AA, shift=2)
    shade = cv2.GaussianBlur(shade, (0, 0), 1.6 * k)
    tex *= (1 + 0.10 * shade)[..., None]
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
        self.M = M = int(16 * k)                 # texture margin: parchment overlaps past the flap lines
        self.tex = parchment_texture(ph + 2 * M, pw + 2 * M, k, rng)
        self.under = parchment_texture(ph + 2 * M, pw + 2 * M, k, rng, pale=True)
        self.closed = self.tex
        C = (pw / 2, ph / 2)
        TL, TR, BR, BL = (0, 0), (pw, 0), (pw, ph), (0, ph)
        self.flaps = [(TL, TR, C), (TR, BR, C), (BR, BL, C), (BL, TL, C)]   # top, right, bottom, left
        # the noise that tears the parchment's edges: soft bays and points, with a fibrous fringe
        def nz(sig):
            n = cv2.GaussianBlur(rng.normal(0, 1, (ph + 2 * M, pw + 2 * M)).astype(np.float32), (0, 0), sig * k)
            return n / (n.std() + 1e-6)
        self.tear = (nz(10), nz(3), nz(1.0))
        # the closed parcel: the four flaps at rest, each torn edge lying over its neighbour
        rgba = np.zeros((ph + 2 * M, pw + 2 * M, 4), np.float32)
        for i in range(4):
            fl = self._setup_flap(i)
            A = fl["F"][..., 3]
            sh = cv2.GaussianBlur(_shift(A, int(2 * k) + 1), (0, 0), 2.2 * k)
            rgba[..., :3] *= (1 - 0.28 * sh * (1 - A))[..., None]
            rgba[..., :3] = rgba[..., :3] * (1 - A[..., None]) + fl["F"][..., :3] * A[..., None]
            rgba[..., 3] = np.maximum(rgba[..., 3], A)
        self.closed_rgba = rgba
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
            M = np.float32([[sx, 0, ox - sx * self.M], [0, sy, oy - sy * self.M]])
            img = cv2.warpAffine(self.closed_rgba, M, (self.W, self.H), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            al = img[..., 3:4]
            frame = frame * (1 - al) + img[..., :3] * al
            self._twine(frame, ox, oy, sx, sy)
            return frame

        ox, oy = self.px0, self.py0
        if f < T_FLAP0 + 4:
            self._shadow(frame, ox, oy, 1, 1, 0.35)
        meshes = [self._flap_mesh(i, f) for i in range(4)]
        tris = []
        for m in meshes:
            if m is not None:
                tris += m["tris"]
        tris.sort(key=lambda t: t[0])                        # lowest first, so the curl rolls over the rest
        # the paper still lying flat, then the soft shadow the lifted paper casts on it and the canvas,
        # then the lifted paper itself
        for m in meshes:                                     # paper lying untouched: pasted as it is
            if m is not None and m["still"]:
                self._paste_still(frame, m)
        for t_ in tris:                                      # paper barely off the canvas
            if t_[0] < 0.5:
                self._mesh_tri(frame, *t_[1:])
        # the lifted paper goes on its own layer, so its shadow can be taken from its real (torn)
        # silhouette: soft, offset more the higher the paper is, and falling only on what is below
        lay = np.zeros((self.H, self.W, 3), np.float32)
        la = np.zeros((self.H, self.W), np.float32)
        lz = np.zeros((self.H, self.W), np.float32)
        any_lift = False
        for z, src, s_tri, d_tri, shade in tris:
            if z >= 0.5:
                any_lift = True
                self._mesh_tri(lay, src, s_tri, d_tri, shade, la, lz, z)
        if any_lift:
            hgt = np.clip(lz / (35 * k), 0, 1) * la
            sh = np.zeros_like(hgt)
            for frac, off in ((0.5, 4), (0.5, 10)):              # near and far: a shadow that spreads with height
                d = int(off * k)
                sh[d:, d // 2:] += frac * hgt[:-d, :-(d // 2) or None]
            sh = cv2.GaussianBlur(sh, (0, 0), 7 * k)
            frame *= (1 - 0.42 * np.clip(sh, 0, 1) * (1 - la))[..., None]
            frame[:] = frame * (1 - la[..., None]) + lay
        if f < T_SNAP + 7:   # the snapped twine whipping back to the edges
            r = ease((f - T_SNAP) / 6)
            self._twine(frame, ox, oy, retract=0.15 + 0.85 * r, alpha=1 - r)
        return frame

    # ---- paper physics, faked: a travelling cylinder curl on a mesh
    NG = 22
    LIGHT = np.array([-0.35, -0.55, 0.76])                   # from the upper left, towards the viewer

    def _geom(self, i, f, s1, u):
        """Where the curl puts paper at (s1 along the base edge, u from the base towards the apex):
        the bend angle phi, the height z and the new distance uu from the base."""
        D = self.D
        t = (f - flap_start(i)) / FLAP_DUR
        # the curl's travel: a slow start, then the paper flops over, overshoots and settles
        if t <= 0:
            E = 0.0
        elif t < 1:
            E = ease(t) ** 2.2 if t < 0.55 else ease(t) ** (2.2 - 1.6 * (t - 0.55) / 0.45)
        else:
            ts = min(1.0, (f - flap_start(i) - FLAP_DUR) / SETTLE)
            E = 1 + 0.06 * math.sin(math.pi * ts) * (1 - ts)
        mid = math.sin(math.pi * min(1.0, max(0.0, t)))
        R = D * (0.12 + 0.08 * mid)                          # the roll loosens as it flops
        # the bend line sags in the middle under the paper's weight and flutters a little
        p_line = (D * (1 - E) + 0.13 * D * np.sin(np.pi * s1) * math.sin(math.pi * min(1.0, E))
                  + 0.03 * D * np.sin(2 * np.pi * 2.1 * s1 + 1.4 * f) * mid
                  + 0.012 * D * np.sin(2 * np.pi * 4.3 * s1 - 2.3 * f) * mid)
        sarc = u - p_line
        phi = np.clip(sarc / R, 0, math.pi)
        uu = np.where(sarc <= 0, u, np.where(sarc <= math.pi * R, p_line + R * np.sin(phi),
                                             p_line - (sarc - math.pi * R)))
        z = np.where(sarc <= 0, 0.0, np.where(sarc <= math.pi * R, R * (1 - np.cos(phi)), 2 * R))
        # weight: the part rolled over droops back a touch and ripples while it falls
        over = np.clip((sarc - math.pi * R) / (0.5 * D), 0, 1)
        uu = uu - over * 0.05 * D * mid
        z = z + over * 0.04 * D * mid * np.sin(np.pi * 2.0 * s1 + 2.0 * f / 7)
        return phi, z, uu, t

    def _setup_flap(self, i):
        if not hasattr(self, "_fl"):
            self._fl = {}
        if i in self._fl:
            return self._fl[i]
        k, Mg = self.k, self.M
        a, b, c = [np.array(p, np.float64) for p in self.flaps[i]]
        Mid = (a + b) / 2
        D = np.linalg.norm(c - Mid)
        self.D = D
        nin = (c - Mid) / D
        eb = (b - a) / np.linalg.norm(b - a)
        Lb = np.linalg.norm(b - a)
        # torn parchment: the flap's own shape, in texture space (parcel coords + margin). The outer
        # edge is deckled a little inwards; the two free edges are torn and lie past the flap line
        # over the neighbouring flap
        Ht, Wt = self.ph + 2 * Mg, self.pw + 2 * Mg
        gy, gx = np.mgrid[0:Ht, 0:Wt].astype(np.float32)
        px, py = gx - Mg, gy - Mg
        def sd(p0, p1, toward):                      # signed distance to the line p0-p1, + towards `toward`
            d = p1 - p0
            n = np.array([-d[1], d[0]]) / np.linalg.norm(d)
            if (toward - p0) @ n < 0:
                n = -n
            return (px - p0[0]) * n[0] + (py - p0[1]) * n[1]
        n1, n2, n3 = self.tear
        d0 = sd(a, b, c) - (2.5 * k + 2.0 * k * n1 + 1.0 * k * n2 + 0.5 * k * n3)
        mo = 9 * k
        d1 = sd(a, c, b) + mo * (0.6 + 0.3 * n1 + 0.12 * n2) + 0.5 * k * n3
        d2 = sd(b, c, a) + mo * (0.6 + 0.3 * np.roll(n1, 37, 1) + 0.12 * np.roll(n2, 23, 0)) + 0.5 * k * n3
        e = np.minimum(np.minimum(d0, d1), d2)
        A = np.clip(e / (0.9 * k) + 0.5, 0, 1).astype(np.float32)
        band = np.exp(-np.clip(e, 0, None) / (1.8 * k))[..., None]          # browned, thin torn fibres
        F = np.dstack([self.tex * (1 - 0.16 * band), A]).astype(np.float32)
        U = np.dstack([self.under * (1 - 0.12 * band), A]).astype(np.float32)
        ys, xs = np.nonzero(A > 0.004)
        x_0, x_1, y_0, y_1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        # each pixel's (s1, u) for the per-pixel lighting
        rel = np.stack([px[y_0:y_1, x_0:x_1] - a[0], py[y_0:y_1, x_0:x_1] - a[1]], -1).astype(np.float64)
        u = np.clip(rel @ nin, 0, D)
        s2 = u / D
        s1 = np.clip((rel @ eb - s2 * Lb / 2) / np.maximum(1e-3, (1 - s2) * Lb), 0, 1)
        # creases in this flap that catch the light as it flexes: dark valleys with a lit ridge
        rng = np.random.default_rng(300 + i)
        cr = np.zeros((Ht, Wt), np.float32)
        for _ in range(9):
            p0 = a + rng.uniform(0.1, 0.9) * (b - a) + nin * rng.uniform(0.05, 0.8) * D + Mg
            ang = rng.uniform(0, math.pi)
            Lc = rng.uniform(0.25, 0.6) * D
            seg = np.array([p0 + Lc * (j / 6 - 0.5) * np.array([math.cos(ang), math.sin(ang)]) + rng.normal(0, 3 * k, 2)
                            for j in range(7)])
            cv2.polylines(cr, [np.round(seg * 4).astype(np.int32).reshape(-1, 1, 2)], False, -1.0,
                          max(1, int(2.2 * k)), cv2.LINE_AA, shift=2)
            cv2.polylines(cr, [np.round((seg + 1.6 * k) * 4).astype(np.int32).reshape(-1, 1, 2)], False, 0.7,
                          max(1, int(2.0 * k)), cv2.LINE_AA, shift=2)
        cr = cv2.GaussianBlur(cr, (0, 0), 1.3 * k)[y_0:y_1, x_0:x_1]
        rng2 = np.random.default_rng(100 + i)
        n = self.NG
        fl = dict(a=a, b=b, c=c, D=D, nin=nin, eb=eb, box=(x_0, y_0, x_1, y_1), s1=s1, u=u, crease=cr, F=F, U=U,
                  jit=rng2.normal(0, 1, (n + 1, n + 1, 2)), tri_shade=rng2.uniform(0.55, 1.05, (n, n, 2)),
                  tri_z=rng2.uniform(0, 1, (n, n, 2)), tri_flip=rng2.uniform(0, 1, (n, n, 2)),
                  wob=rng2.uniform(-1, 1, 7), twist=rng2.uniform(1.5, 2.6) * rng2.choice([-1, 1]))
        self._fl[i] = fl
        return fl

    def _shaded(self, i, f, fl, ec):
        """The flap's front and underside textures, lit per pixel for this frame's curl:
        the roll darkens as it turns from the light, catches a highlight, the inside of the roll
        is in shade, and creases show more the more the paper flexes."""
        x_0, y_0, x_1, y_1 = fl["box"]
        self.D = fl["D"]
        phi, z, uu, t = self._geom(i, f, fl["s1"], fl["u"])
        nin = fl["nin"]
        Lx, Ly, Lz = self.LIGHT
        ln = Lx * nin[0] + Ly * nin[1]                       # the light's component along the curl
        sp, cp = np.sin(phi), np.cos(phi)
        flat_lam = Lz
        lam_f = np.maximum(0, -sp * ln + cp * Lz)            # front normal: (-sin phi along nin, cos phi up)
        lam_u = np.maximum(0, sp * ln - cp * Lz)             # underside: the opposite
        H = np.array([Lx, Ly, Lz + 1.0]); H /= np.linalg.norm(H)
        hn = H[0] * nin[0] + H[1] * nin[1]
        spec_f = np.maximum(0, -sp * hn + cp * H[2]) ** 40 * (phi > 0.05)
        shade_f = (0.6 + 0.4 * lam_f / flat_lam)
        shade_u = (0.72 + 0.28 * lam_u / flat_lam) * (1 - 0.12 * np.exp(-((phi - math.pi / 2) / 0.45) ** 2))
        flex = np.clip(np.abs(sp) * 1.4 + 0.25 * (phi > 0.02) + 0.9 * ec, 0, 1.6)
        cre = fl["crease"] * (0.05 + 0.2 * flex)
        F, U = fl["F"].copy(), fl["U"].copy()
        F[y_0:y_1, x_0:x_1, :3] = F[y_0:y_1, x_0:x_1, :3] * (shade_f * (1 + cre))[..., None] + (np.array([46, 40, 28], np.float32) * spec_f[..., None])
        U[y_0:y_1, x_0:x_1, :3] = U[y_0:y_1, x_0:x_1, :3] * (shade_u * (1 - cre))[..., None]
        return F, U

    def _flap_mesh(self, i, f):
        k = self.k
        fl = self._setup_flap(i)
        a, b, c, D, nin = fl["a"], fl["b"], fl["c"], fl["D"], fl["nin"]
        self.D = D
        o = np.array([self.px0, self.py0], np.float64)
        t0c = flap_start(i) + FLAP_DUR + SETTLE              # crumple starts
        tc = (f - t0c) / CRUMPLE
        tf = (f - t0c - CRUMPLE) / 30.0                      # seconds in flight
        if tf * 30 > FLY + 6:
            return None
        n = self.NG
        s1 = np.linspace(0, 1, n + 1)[None, :].repeat(n + 1, 0)       # along the edge
        s2 = np.linspace(0, 1, n + 1)[:, None].repeat(n + 1, 1)       # towards the apex
        L = (1 - s2)[..., None] * (a + s1[..., None] * (b - a)) + s2[..., None] * c   # rest positions
        L = L + ((2 * s1 - 1) * 2.2 * 9 * k)[..., None] * fl["eb"]   # reach over the torn overlaps
        u = s2 * D
        foot = L - nin * u[..., None]
        ff = min(f, t0c)                                     # the curl is over once the crumple starts
        phi, z, uu, t = self._geom(i, ff, s1, u)
        P = foot + nin * uu[..., None] + o
        cen = np.array([self.W / 2, self.H * 0.45])
        P = P + (P - cen) * (z * 0.00045 / k)[..., None]     # lifted paper swells a touch towards the viewer
        ec = ease(tc) if tc > 0 else 0.0
        rng_flip = fl["tri_flip"]
        if tc > 0:
            # crumpling, progressively: every bit of the flap is gathered towards a ball of paper,
            # wrinkling on the way, then the ball is tossed off-screen spinning
            G = P.reshape(-1, 2).mean(0)
            area = 0.5 * np.linalg.norm(b - a) * D
            rb = 0.30 * math.sqrt(area)
            Lc = L - L.reshape(-1, 2).mean(0)
            th = np.arctan2(Lc[..., 1], Lc[..., 0])
            rr = np.linalg.norm(Lc, axis=-1)
            rr = (rr / rr.max()) ** 0.55
            wob = sum(fl["wob"][j] * np.sin((j + 2) * th + j) for j in range(len(fl["wob"]))) * 0.022
            th2 = th + fl["twist"] * rr
            target = G + (rb * rr * (1 + wob))[..., None] * np.stack([np.cos(th2), np.sin(th2)], -1)
            e = ec ** 1.15
            P = P * (1 - e) + target * e + fl["jit"] * (0.05 * D * math.sin(math.pi * min(1.0, ec)) + 0.04 * rb * e)
            if tf > 0:   # in flight
                out = (a + b) / 2 - c
                out /= np.linalg.norm(out) + 1e-6
                vx = out[0] * 1500 * k + (120 if i % 2 else -120) * k
                vy = out[1] * 900 * k - 1000 * k
                pos = G + np.array([vx * tf, vy * tf + 3000 * k * tf * tf])
                ang = tf * 11 * (1 if i % 2 else -1)
                ca, sa = math.cos(ang), math.sin(ang)
                d = P - G
                P = pos + np.stack([ca * d[..., 0] - sa * d[..., 1], sa * d[..., 0] + ca * d[..., 1]], -1)
                if P[..., 0].max() < -5 or P[..., 0].min() > self.W + 5 or P[..., 1].min() > self.H + 5 \
                        or P[..., 1].max() < -5:
                    return None
            z = z * (1 - ec) + ec * (20 * k)
        F, U = (self._shaded(i, ff, fl, ec) if f > flap_start(i) else (fl["F"], fl["U"]))
        tris = []
        still = []
        lifted = False
        Pc = P.reshape(-1, 2).mean(0)
        rb_now = np.linalg.norm(P - Pc, axis=-1).max() + 1e-6
        for r in range(n):
            for q in range(n):
                quad = [(r, q), (r, q + 1), (r + 1, q + 1), (r + 1, q)]
                for h, tri in enumerate(([quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]])):
                    srcp = [L[j] for j in tri]
                    e1, e2 = srcp[1] - srcp[0], srcp[2] - srcp[0]
                    if abs(e1[0] * e2[1] - e1[1] * e2[0]) < 1e-3:
                        continue
                    dstp = [P[j] for j in tri]
                    ph = float(np.mean([phi[j] for j in tri]))
                    zz = float(np.mean([z[j] for j in tri]))
                    if zz > 0.5:
                        lifted = True
                    under = ph >= math.pi / 2
                    shade = 1.0
                    if ec > 0:
                        # facets of the crumpled ball: some show the inside, all at their own angle,
                        # rounder and darker towards the ball's edge
                        if rng_flip[r, q, h] < 0.45 * ec:
                            under = not under
                        shade = 1 - ec * (1 - fl["tri_shade"][r, q, h]) * 0.8
                        dd = np.mean([P[j] for j in tri], 0) - Pc
                        rad = np.linalg.norm(dd) / rb_now
                        shade *= 1 - 0.3 * ec * rad ** 2 + 0.12 * ec * (-(dd[0] * 0.5 + dd[1] * 0.8) / rb_now)
                        zz = zz + ec * (8 * k * fl["tri_z"][r, q, h] + 4 * k * (1 - rad))
                    if ec == 0 and zz == 0 and max(phi[j] for j in tri) == 0:
                        still.append(srcp)                   # untouched: pasted in one go below
                        continue
                    tris.append((zz + 0.001 * i, U if under else F, srcp, dstp, shade))
        moving = 0 < t and tf <= 0
        return dict(tris=tris, P=P, z=z, still=still, F=F)

    def _paste_still(self, frame, m):
        """Paper still lying flat: pasted straight from its texture, with a soft contact shadow
        under its torn edge."""
        k, Mg = self.k, self.M
        pts = np.array(m["still"]).reshape(-1, 2) + Mg
        Ht, Wt = m["F"].shape[:2]
        x_0, y_0 = np.maximum(0, np.floor(pts.min(0)).astype(int) - int(12 * k))
        x_1, y_1 = np.ceil(pts.max(0)).astype(int) + int(12 * k)
        x_1, y_1 = min(Wt, x_1), min(Ht, y_1)
        mask = np.zeros((y_1 - y_0, x_1 - x_0), np.float32)
        polys = [np.round((np.array(t) + Mg - [x_0, y_0]) * 4).astype(np.int32) for t in m["still"]]
        cv2.fillPoly(mask, polys, 1.0, cv2.LINE_AA, shift=2)
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
        X0, Y0 = self.px0 - Mg + x_0, self.py0 - Mg + y_0
        fx0, fy0 = max(0, X0), max(0, Y0)
        fx1, fy1 = min(self.W, X0 + x_1 - x_0), min(self.H, Y0 + y_1 - y_0)
        if fx1 <= fx0 or fy1 <= fy0:
            return
        src = m["F"][y_0 + fy0 - Y0:y_0 + fy1 - Y0, x_0 + fx0 - X0:x_0 + fx1 - X0]
        a = mask[fy0 - Y0:fy1 - Y0, fx0 - X0:fx1 - X0] * src[..., 3]
        sh = cv2.GaussianBlur(_shift(a, int(2 * k) + 1), (0, 0), 2.2 * k)
        sub = frame[fy0:fy1, fx0:fx1]
        sub *= (1 - 0.28 * sh * (1 - a))[..., None]
        sub[:] = sub * (1 - a[..., None]) + src[..., :3] * a[..., None]

    def _mesh_tri(self, frame, src, tri_src, tri_dst, shade, la=None, lz=None, z=0.0):
        """Map a little triangle of the flap's (RGBA) texture onto its bent place, no seams.
        With la/lz, `frame` is a premultiplied layer and its alpha and height are kept too."""
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
        M = cv2.getAffineTransform(np.float32(tri_src) + self.M, np.float32(dd))
        warped = cv2.warpAffine(src, M, (x_1 - x_0, y_1 - y_0), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        mask = np.zeros((y_1 - y_0, x_1 - x_0), np.uint8)
        cv2.fillPoly(mask, [np.round(dd * 4).astype(np.int32)], 1, cv2.LINE_8, shift=2)
        sub = frame[y_0:y_1, x_0:x_1]
        msk = mask.astype(bool)
        a = warped[msk][:, 3:4]
        sub[msk] = sub[msk] * (1 - a) + np.clip(warped[msk][:, :3] * shade, 0, 255) * a
        if la is not None:
            sa = la[y_0:y_1, x_0:x_1]
            sa[msk] = sa[msk] * (1 - a[:, 0]) + a[:, 0]
            sz = lz[y_0:y_1, x_0:x_1]
            sz[msk] = sz[msk] * (1 - a[:, 0]) + z * a[:, 0]
