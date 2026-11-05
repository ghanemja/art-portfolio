"""A hand-animated galloping horse, drawn from scratch each frame: a 2D side-view
rig (barrel, chest and rump, neck, head with ears, four two-part legs with
hooves, flowing mane and tail) moved through a real gallop.

The gallop is a four-beat rotary gallop: hind left, hind right, fore left, fore
right land in turn, each leg on the ground for about 30 % of the stride, then a
moment of suspension with all four tucked up. During a leg's stance it sweeps
from reaching forward to pushing back, nearly straight. During its swing it
folds up and reaches forward again. The body bobs (highest in the suspension)
and rocks, the neck pumps, and the mane and tail stream back and ripple.

It is coloured from the painted horse it replaces (coat, mane and tail), shaded
from above, with a soft dark outline, so it reads as the same horse, animated.

    rig = HorseRig(coat, hair, length_px, rng)
    rgba, (ax, ay) = rig.draw(phase, facing)     # (ax, ay): where the hooves meet the ground
    rig.FOOTFALLS                                # stride fractions when each hoof lands
"""
import math
import numpy as np
import cv2

# stride fraction at which each leg's hoof lands: hind left, hind right, fore left, fore right
LEGS = [("hind", "far", 0.00), ("hind", "near", 0.11), ("fore", "far", 0.31), ("fore", "near", 0.42)]
STANCE = 0.30
L_UP, L_LO = 0.33, 0.31          # leg segment lengths, in body lengths
GROUND = 0.66                    # local y of the ground below the body centre


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


class HorseRig:
    FOOTFALLS = [o for _, _, o in LEGS]

    def __init__(self, coat, hair, length_px, rng):
        self.coat = np.array(coat, np.float32)
        self.hair = np.array(hair, np.float32)
        self.hoof = self.hair * 0.45 + np.array([20, 18, 16], np.float32)
        self.L = float(length_px)
        self.ss = 2                                          # supersampling
        self.w = int(2.3 * self.L)
        self.h = int(1.75 * self.L)
        self.org = np.array([1.12, 0.92]) * self.L           # local (0, 0) in sprite pixels
        n = cv2.GaussianBlur(rng.normal(0, 1, (self.h, self.w)).astype(np.float32), (0, 0), sigmaX=6, sigmaY=1.5)
        self.brush = n / (n.std() + 1e-6)                    # a little brushwork in the coat
        self.mane_ph = rng.uniform(0, 6.28, 9)

    # ------------------------------------------------------------ pose
    def _leg(self, kind, offset, p):
        """Upper-leg angle a (radians from straight down, + = forward) and fold b of the lower leg."""
        q = (p - offset) % 1.0
        fwd, back = (0.50, -0.55) if kind == "fore" else (0.42, -0.62)
        if q < STANCE:                                       # on the ground: sweep back, nearly straight
            u = q / STANCE
            a = fwd + (back - fwd) * u
            b = 0.10 * math.sin(math.pi * u)                 # the fetlock gives under the weight
        else:                                                # in the air: fold up, reach forward
            u = (q - STANCE) / (1 - STANCE)
            a = back + (fwd + 0.08 - back) * _smooth(u * 1.15) - 0.08 * _smooth((u - 0.85) / 0.15)
            b = 1.55 * math.sin(math.pi * min(1.0, u * 1.1)) ** 0.8
        return a, b

    def _pose(self, p):
        bob = -0.045 * math.cos(2 * math.pi * (p - 0.80))    # highest in the suspension
        rock = 0.07 * math.sin(2 * math.pi * (p + 0.05))
        neck = 0.12 * math.sin(2 * math.pi * (p + 0.30))
        return bob, rock, neck

    # ------------------------------------------------------------ drawing
    def _px(self, pts):
        return np.round((np.asarray(pts) * self.L + self.org) * self.ss * 4).astype(np.int32)

    def _fill(self, rgb, a, pts, col, shade=1.0):
        m = np.zeros(a.shape, np.float32)
        cv2.fillPoly(m, [self._px(pts)], 1.0, cv2.LINE_AA, shift=2)
        rgb[:] = rgb * (1 - m[..., None]) + (col * shade) * m[..., None]
        np.maximum(a, m, out=a)

    def _blob(self, rgb, a, c, rx, ry, ang, col, shade=1.0):
        t = np.linspace(0, 2 * np.pi, 40, endpoint=False)
        ca, sa = math.cos(ang), math.sin(ang)
        x, y = rx * np.cos(t), ry * np.sin(t)
        self._fill(rgb, a, np.stack([c[0] + ca * x - sa * y, c[1] + sa * x + ca * y], 1), col, shade)

    def _limb(self, rgb, a, p0, p1, w0, w1, col, shade=1.0):
        d = np.array(p1) - np.array(p0)
        n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
        self._fill(rgb, a, [p0 + n * w0 / 2, p1 + n * w1 / 2, p1 - n * w1 / 2, p0 - n * w0 / 2], col, shade)
        self._blob(rgb, a, p1, w1 / 2, w1 / 2, 0, col, shade)

    def _strands(self, rgb, a, roots, dirs, length, width, p, col, n_wave, amp):
        """Streaming hair: tapered strands from each root, rippling back."""
        for j, (r, d) in enumerate(zip(roots, dirs)):
            pts = []
            for i in range(9):
                s = i / 8
                wave = amp * s * math.sin(2 * math.pi * (n_wave * s - 2.2 * p) + self.mane_ph[j % 9])
                nrm = np.array([-d[1], d[0]])
                pts.append(np.array(r) + np.array(d) * length * s + nrm * wave)
            pts = np.array(pts)
            for i in range(8):
                wd = width * (1 - i / 8) + 0.004
                self._limb(rgb, a, pts[i], pts[i + 1], wd, wd * 0.85, col)

    def draw(self, p, facing=1):
        """The horse at stride phase p (0..1). Returns an RGBA sprite (float, alpha 0..1) and where
        its hooves meet the ground, in sprite pixels. facing: 1 runs right, -1 runs left."""
        ss = self.ss
        H, W = self.h * ss, self.w * ss
        rgb = np.zeros((H, W, 3), np.float32)
        a = np.zeros((H, W), np.float32)
        bob, rock, neck = self._pose(p)
        coat, hair, hoof = self.coat, self.hair, self.hoof
        ca, sa = math.cos(rock), math.sin(rock)

        def R(x, y):                                         # body frame -> local (rocked, bobbed)
            return np.array([ca * x - sa * y, sa * x + ca * y + bob])

        shoulder, hip = R(0.36, 0.02), R(-0.36, -0.02)

        def leg(kind, side, off, shade):
            ang, fold = self._leg(kind, off, p)
            top = shoulder if kind == "fore" else hip
            knee = top + L_UP * np.array([math.sin(ang), math.cos(ang)])
            lo = ang - fold if kind == "fore" else ang - 0.25 - fold * 0.75
            hoof_p = knee + L_LO * np.array([math.sin(lo), math.cos(lo)])
            w_top = 0.15 if kind == "hind" else 0.12
            self._limb(rgb, a, top, knee, w_top, 0.06, coat, shade)
            self._limb(rgb, a, knee, hoof_p, 0.055, 0.045, coat * 0.92, shade)
            d = hoof_p - knee
            d /= np.linalg.norm(d) + 1e-9
            self._limb(rgb, a, hoof_p - d * 0.01, hoof_p + d * 0.045, 0.06, 0.07, hoof, shade)

        for kind, side, off in LEGS:                          # the far legs, in shadow
            if side == "far":
                leg(kind, side, off, 0.68)
        # tail, streaming back from the croup
        root = R(-0.52, -0.16)
        self._blob(rgb, a, root + [-0.05, 0.03], 0.09, 0.05, -0.4, hair)
        self._strands(rgb, a, [root + [0, k * 0.022] for k in range(-2, 3)],
                      [np.array([-0.93, 0.36 + 0.06 * k]) for k in range(-2, 3)],
                      0.5, 0.075, p, hair, 1.2, 0.06)
        # the body: barrel, chest, rump, belly
        self._blob(rgb, a, R(0.0, -0.04), 0.47, 0.19, rock, coat)
        self._blob(rgb, a, R(0.34, -0.03), 0.19, 0.2, rock, coat)
        self._blob(rgb, a, R(-0.36, -0.07), 0.21, 0.2, rock, coat)
        self._blob(rgb, a, hip + R(0.02, 0.06) - R(0, 0), 0.13, 0.17, rock + 0.3, coat)    # the thigh
        # neck and head, pumping with the stride
        base = R(0.36, -0.12)
        cn, sn = math.cos(neck + rock), math.sin(neck + rock)

        def Nk(x, y):                                        # neck frame, about its base
            return base + np.array([cn * x - sn * y, sn * x + cn * y])

        # a deep neck rising out of the chest, the crest arched
        self._fill(rgb, a, [Nk(-0.22, -0.02), Nk(-0.06, -0.20), Nk(0.08, -0.40), Nk(0.22, -0.50),
                            Nk(0.34, -0.40), Nk(0.30, -0.24), Nk(0.20, 0.0), Nk(0.08, 0.17)], coat)
        # the head: broad cheek tapering to the muzzle
        self._blob(rgb, a, Nk(0.30, -0.40), 0.09, 0.075, neck + rock + 0.5, coat)
        head = [Nk(0.22, -0.50), Nk(0.32, -0.53), Nk(0.56, -0.34), Nk(0.59, -0.27), Nk(0.53, -0.22),
                Nk(0.30, -0.31)]
        self._fill(rgb, a, head, coat)
        self._blob(rgb, a, Nk(0.55, -0.28), 0.05, 0.042, neck + rock + 0.7, coat * 0.82)   # muzzle
        self._blob(rgb, a, Nk(0.56, -0.29), 0.012, 0.009, 0.6, coat * 0.45)               # nostril
        self._fill(rgb, a, [Nk(0.22, -0.50), Nk(0.19, -0.63), Nk(0.29, -0.53)], coat * 0.9)   # ears
        self._fill(rgb, a, [Nk(0.25, -0.51), Nk(0.25, -0.64), Nk(0.32, -0.53)], coat * 0.8)
        self._blob(rgb, a, Nk(0.35, -0.44), 0.02, 0.015, 0.3, np.array([25, 20, 18], np.float32))  # eye
        # the mane: a mass along the crest, streaming back into locks
        crest = [Nk(0.24 - 0.055 * i, -0.50 + 0.085 * i) for i in range(6)]
        self._fill(rgb, a, crest + [c + np.array([-0.07, 0.03]) for c in crest[::-1]], hair)
        self._strands(rgb, a, crest, [np.array([-0.9, 0.2 + 0.06 * i]) for i in range(6)],
                      0.2, 0.055, p, hair, 1.0, 0.04)
        for kind, side, off in LEGS:                          # the near legs
            if side == "near":
                leg(kind, side, off, 1.0)

        rgb = cv2.resize(rgb, (self.w, self.h), interpolation=cv2.INTER_AREA)
        a = cv2.resize(a, (self.w, self.h), interpolation=cv2.INTER_AREA)
        # light from above, a little brushwork, and a soft dark outline: drawn, but painterly
        yy = np.linspace(0, 1, self.h, dtype=np.float32)[:, None]
        rgb = rgb * (1.12 - 0.3 * yy)[..., None] * (1 + 0.05 * self.brush)[..., None]
        ring = np.clip(cv2.dilate(a, np.ones((3, 3), np.uint8)) - a, 0, 1)
        ring = cv2.GaussianBlur(ring, (0, 0), 0.6)
        out_a = np.maximum(a, ring)
        line = (hair * 0.35)
        rgb = (rgb * a[..., None] + line * ring[..., None] * (1 - a[..., None])) / (out_a[..., None] + 1e-6)
        rgba = np.dstack([np.clip(rgb, 0, 255), out_a]).astype(np.float32)
        ax, ay = self.org[0], self.org[1] + GROUND * self.L
        if facing < 0:
            rgba = rgba[:, ::-1].copy()
            ax = self.w - 1 - ax
        return rgba, (ax, ay)
