"""Water pouring out of the painting: the river spills over the canvas edge and
falls off the bottom (or out of the side) of the screen.

Each pour is one sheet of water leaving one edge of the canvas. On the canvas it
is a sheet running over the bank to the edge; off it, the water falls under
gravity, necks in a little, frays into streaks and turns whiter as it fills with
air. Its texture is the painting's own river, motion-blurred along the fall and
scrolled with the flow, so it is the painting's water that pours out.

    pour = Pour(W, H, k, (x0, y0, w, h), paint, specs)
    frame = pour.draw(frame, t)          # t: seconds since the painting came alive

A spec (from a "pour" effect in animate.EFFECTS):
    edge="bottom", span=(0.52, 0.86), lip=0.86, start=0.5    water runs from y=lip
                                                            over the bottom edge
    edge="right",  span=(0.63, 0.73), start=0.7              water shoots out of the
                                                            right edge and falls
"""
import math
import numpy as np
import cv2

G = 1800.0            # gravity, px/s^2 at 1080 wide


class Pour:
    def __init__(self, W, H, k, box, paint, specs, rng=None):
        self.W, self.H, self.k = W, H, k
        self.x0, self.y0, self.w, self.h = box
        self.specs = specs
        rng = rng or np.random.default_rng(7)
        h, w = paint.shape[:2]
        # the painting's river (its blue and white part), as the pouring water's texture:
        # across = u, along the fall = v. Everything here repeats seamlessly along v.
        crop = paint[int(0.64 * h):int(0.92 * h), int(0.30 * w):int(0.72 * w)].astype(np.float32)
        U, V = 192, 384
        tex = cv2.resize(crop, (U, V), interpolation=cv2.INTER_AREA)
        tex = np.concatenate([tex, tex[::-1]], 0)                     # mirrored: seamless along the fall
        tex = self._wrap_blur(tex, 1.0, 7.0)
        lum = tex.mean(2, keepdims=True)
        white = np.array([244, 246, 246], np.float32)
        self.tex = tex * 0.5 + (white * (0.7 + 0.3 * lum / 255)) * 0.5   # foamier than the river
        self.blue = np.array([118, 178, 206], np.float32)
        self.TU, self.TV = U, 2 * V
        st = self._wrap_blur(rng.normal(0, 1, (2 * V, U)).astype(np.float32), 1.2, 12)
        self.streak = st / (st.std() + 1e-6)

    @staticmethod
    def _wrap_blur(img, sx, sy):
        """Gaussian blur that wraps around top/bottom (so the texture tiles along the fall)."""
        n = img.shape[0]
        t = np.concatenate([img, img, img], 0)
        t = cv2.GaussianBlur(t, (0, 0), sigmaX=sx, sigmaY=sy, borderType=cv2.BORDER_REFLECT)
        return np.ascontiguousarray(t[n:2 * n])

    @staticmethod
    def _wob(x, ph):
        """A smooth wobble (about -1..1) for the sheet's edges."""
        return 0.55 * np.sin(x * 1.0 + ph) + 0.3 * np.sin(x * 2.3 + 1.7 * ph + 1) + 0.15 * np.sin(x * 5.1 - ph)

    def _colour(self, u, v):
        """The water's colour: the painting's river, streaked with white foam and blue."""
        col = self._tex(u, v)
        st = self._samp(self.streak, u, v)
        # keep the painting's brushwork but in clean water colours: its light parts white foam,
        # its darker parts the river's blue
        lum = col.mean(2, keepdims=True)
        ramp = np.clip((lum - 150) / 90, 0, 1)
        water = self.blue + (np.array([248, 250, 250], np.float32) - self.blue) * ramp
        col = 0.3 * col + 0.7 * water
        fo = np.clip(st, 0, 2)[..., None] * 0.22
        bl = np.clip(-st, 0, 2)[..., None] * 0.2
        return col * (1 - fo - bl) + np.array([250, 251, 251], np.float32) * fo + self.blue * bl, st

    # ------------------------------------------------------------ texture lookups
    def _tex(self, u, v):
        """Colour at (u 0..1 across, v any along; wraps)."""
        mx = np.clip(u, 0, 1) * (self.TU - 1)
        my = np.mod(v * self.TV, self.TV)
        return cv2.remap(self.tex, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_WRAP)

    def _samp(self, img, u, v):
        mx = np.clip(u, 0, 1) * (img.shape[1] - 1)
        my = np.mod(v * img.shape[0], img.shape[0])
        return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_WRAP)

    # ------------------------------------------------------------ one frame
    def draw(self, frame, t):
        for sp in self.specs:
            if sp["edge"] == "bottom":
                self._bottom(frame, t, sp)
            else:
                self._right(frame, t, sp)
        return frame

    def _comp(self, frame, sl, col, a, shadow=None):
        sub = frame[sl]
        if shadow is not None:
            sub *= (1 - shadow)[..., None]
        sub[:] = sub * (1 - a[..., None]) + col * a[..., None]

    def _bottom(self, frame, t, sp):
        k = self.k
        ts = t - sp.get("start", 0.5)
        if ts <= 0:
            return
        xa = self.x0 + sp["span"][0] * self.w
        xb = self.x0 + sp["span"][1] * self.w
        yr = self.y0 + sp.get("lip", 0.86) * self.h          # where the river starts to spill
        ye = self.y0 + self.h                                # the canvas's bottom edge
        flow = 1.1                                           # texture lengths per second
        run = ye - yr
        t_edge = 0.45                                        # the spill reaches the edge
        v0, g = 140 * k, G * k

        # --- on the canvas: a sheet running over the bank to the edge, spreading as it goes
        front = min(1.0, ts / t_edge) * run
        y_0, y_1 = int(yr), int(ye)
        x_0, x_1 = int(xa - 30 * k), int(xb + 30 * k)
        sl = (slice(max(0, y_0), y_1), slice(max(0, x_0), min(self.W, x_1)))
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        p = np.clip((yy - yr) / run, 0, 1)                   # 0 at the river, 1 at the edge
        half = (xb - xa) / 2 * (0.35 + 0.65 * np.sqrt(p))
        cx = (xa + xb) / 2
        u = (xx - (cx - half)) / (2 * half)
        wl = 4 * k * self._wob((yy - yr) / (14 * k) - ts * 5, 0.3)
        wr = 4 * k * self._wob((yy - yr) / (14 * k) - ts * 5, 2.1)
        side = np.clip(np.minimum((u * 2 * half + wl), ((1 - u) * 2 * half + wr)) / (6 * k), 0, 1)
        lead = np.clip((front - (yy - yr)) / (8 * k), 0, 1)
        top = np.clip(p / 0.35, 0, 1) ** 1.5                # grows out of the river, no hard top edge
        v = (yy - yr) / (260 * k) - ts * flow
        col, st = self._colour(u, v)
        a = side * lead * top * (0.8 + 0.15 * np.clip(st, -1, 1))
        foam = (np.clip((p - 0.55) / 0.45, 0, 1) ** 2 * 0.45)[..., None]   # whiter as it speeds over the lip
        col = col * (1 - foam) + np.array([248, 250, 250], np.float32) * foam
        self._comp(frame, sl, col, a)

        # --- off the canvas: the falling sheet
        tf = ts - t_edge                                     # how long water has been falling
        if tf <= 0:
            return
        y_0, y_1 = int(ye), self.H
        sl = (slice(y_0, y_1), slice(max(0, int(xa - 60 * k)), min(self.W, int(xb + 60 * k))))
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        dy = yy - ye
        tau = (-v0 + np.sqrt(v0 * v0 + 2 * g * np.maximum(dy, 0))) / g      # time of flight to here
        neck = 12 * k * np.minimum(tau, 0.6) - 30 * k * np.maximum(tau - 0.6, 0)   # necks in, then fans out
        xl, xr = xa + neck, xb - neck
        u = (xx - xl) / (xr - xl)
        v = -(ts - tau) * flow                               # each parcel of water keeps its texture
        amp = 3 * k + 16 * k * tau                           # the edges wobble more as it falls
        wl = amp * self._wob(tau * 9 - ts * 6, 0.4)
        wr = amp * self._wob(tau * 9 - ts * 6, 2.6)
        side = np.clip(np.minimum(u * (xr - xl) + wl, (1 - u) * (xr - xl) + wr) / (3 * k + 3 * k * tau), 0, 1)
        col, st = self._colour(u, v)
        fray = np.clip(1.3 - 0.5 * tau + 0.6 * st * np.clip(tau - 0.2, 0, 1), 0, 1)  # breaks into streaks lower down
        lead = np.clip((tf - tau) / 0.06, 0, 1)
        a = side * fray * lead * 0.94
        foam = np.clip(tau / 0.9, 0, 1)[..., None] * 0.45
        col = col * (1 - foam) + np.array([246, 248, 248], np.float32) * foam
        # rounded sheet: a little darker at its sides, a highlight running down the middle
        rnd = 1 - 0.18 * (2 * np.clip(u, 0, 1) - 1) ** 4 + 0.07 * np.exp(-((u - 0.42) / 0.12) ** 2)
        col = col * rnd[..., None]
        # its shadow on the paper behind, offset a little
        sh = cv2.GaussianBlur(a, (0, 0), 9 * k)
        d = int(10 * k)
        shadow = np.zeros_like(sh)
        shadow[:, d:] = sh[:, :-d]
        self._comp(frame, sl, col, a, 0.22 * shadow * (1 - a))
        # the lip, where the sheet curls over the canvas edge: a bright rim
        if tf > 0:
            ll = (slice(int(ye - 3 * k), int(ye + 4 * k)), slice(int(xa + 4 * k), int(xb - 4 * k)))
            yy, xx = np.mgrid[ll[0], ll[1]].astype(np.float32)
            rim = np.exp(-((yy - ye) / (1.8 * k)) ** 2) * 0.55 * min(1.0, tf / 0.1)
            self._comp(frame, ll, np.array([250, 252, 252], np.float32), rim)

    def _right(self, frame, t, sp):
        k = self.k
        ts = t - sp.get("start", 0.7)
        if ts <= 0:
            return
        xe = self.x0 + self.w
        ya = self.y0 + sp["span"][0] * self.h
        yb = self.y0 + sp["span"][1] * self.h
        vx, g = 105 * k, G * k
        flow = 1.1
        sl = (slice(int(ya - 10 * k), self.H), slice(int(xe), self.W))
        if sl[1].start >= self.W:
            return
        yy, xx = np.mgrid[sl[0], sl[1]].astype(np.float32)
        tau = (xx - xe) / vx
        drop = 0.5 * g * tau * tau
        spread = 1 + 1.6 * tau                               # the stream fans out as it falls
        mid = (ya + yb) / 2 + drop
        u = ((yy - mid) / spread + (yb - ya) / 2) / (yb - ya)
        v = -(ts - tau) * flow
        amp = 2 * k + 10 * k * tau
        wl = amp * self._wob(tau * 8 - ts * 6, 0.9)
        wr = amp * self._wob(tau * 8 - ts * 6, 3.1)
        th = (yb - ya) * spread
        side = np.clip(np.minimum(u * th + wl, (1 - u) * th + wr) / (3 * k), 0, 1)
        col, st = self._colour(u, v)
        fray = np.clip(1.2 - 0.5 * tau + 0.5 * st * np.clip(tau - 0.2, 0, 1), 0, 1)
        lead = np.clip((ts - tau) / 0.06, 0, 1)
        a = side * fray * lead * 0.92
        foam = np.clip(tau / 0.8, 0, 1)[..., None] * 0.4
        col = col * (1 - foam) + np.array([246, 248, 248], np.float32) * foam
        sh = cv2.GaussianBlur(a, (0, 0), 8 * k)
        d = int(10 * k)
        shadow = np.zeros_like(sh)
        shadow[d:, :] = sh[:-d, :]
        self._comp(frame, sl, col, a, 0.2 * shadow * (1 - a))
