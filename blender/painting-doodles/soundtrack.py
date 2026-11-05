"""Soundtrack for a painting reel, built from the reel's events:
crayon scratching while the doodle is drawn, a soft pop as the painting lands,
a shimmer for the light sweep, tiny bells on the twinkles, a chime for the
title, over a gentle kalimba-and-pad tune. Fixed gains, so the pop stays subtle.
"""
import wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100


def _bandnoise(n, lo, hi, rng):
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, rng.standard_normal(n))


def _env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _tone(f, dur, decay, harm=((1, 1.0),)):
    t = np.arange(int(dur * SR)) / SR
    y = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * decay * h ** 0.5) for h, a in harm)
    return y * np.minimum(1, t * 400)


def _add(mix, y, at):
    a = int(at)
    if a >= len(mix):
        return
    y = y[: len(mix) - a]
    mix[a:a + len(y)] += y


def make(ev, path, seed=0):
    rng = np.random.default_rng(seed)
    fps = ev["fps"]
    n = int(SR * ev["frames"] / fps) + SR
    at = lambda f: SR * f / fps
    mix = np.zeros(n)

    # --- tune: kalimba plucks over a soft pad, in a key picked per reel
    roots = [60, 62, 65, 67, 57]
    root = roots[rng.integers(len(roots))]
    scale = [0, 2, 4, 7, 9, 12, 14, 16]
    chords = [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]]
    bpm = 92
    beat = 60 / bpm
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    nbars = int(n / SR / (4 * beat)) + 1
    for b in range(nbars):
        ch = chords[b % 4]
        for c in ch:  # pad
            dur = 4 * beat + 0.6
            t = np.arange(int(dur * SR)) / SR
            f = hz(root - 12 + c)
            y = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.003 * f * t)) * _env(len(t), 0.8, 0.8)
            _add(mix, 0.018 * y, b * 4 * beat * SR)
        for i in range(8):  # plucks on eighths, sparse
            if rng.random() < 0.45:
                continue
            m = root + 12 + scale[rng.integers(len(scale))]
            y = _tone(hz(m), 0.9, 6, ((1, 1.0), (2.76, 0.18), (5.4, 0.06)))
            _add(mix, 0.05 * y, (b * 4 + i * 0.5) * beat * SR)

    # --- crayon scratching while drawing: strokes at ~6-9 per second
    d0, d1 = ev["draw"]
    a, b = int(at(d0)), int(at(d1))
    L = b - a
    scratch = _bandnoise(L, 1400, 7000, rng) + 0.5 * _bandnoise(L, 400, 1400, rng)
    t = np.arange(L) / SR
    rate = 7.5 + 1.5 * np.sin(2 * np.pi * 0.3 * t)
    phase = 2 * np.pi * np.cumsum(rate) / SR
    strokes = (0.5 + 0.5 * np.sin(phase)) ** 1.5
    grit = 0.7 + 0.3 * (rng.random(L) > 0.5)
    _add(mix, 0.07 * scratch * strokes * grit * _env(L, 0.05, 0.15), a)

    # --- the pop: a soft, low bloop with a tiny click
    p = at(ev["pop"])
    t = np.arange(int(0.16 * SR)) / SR
    f = 190 + 330 * (1 - np.exp(-t * 40))
    bloop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26) * np.minimum(1, t * 600)
    click = _bandnoise(len(t), 2000, 6000, rng) * np.exp(-t * 300)
    _add(mix, 0.16 * bloop + 0.02 * click, p - 0.006 * SR)
    # a little rising sparkle right after
    for i, m in enumerate([root + 24, root + 28, root + 31]):
        _add(mix, 0.022 * _tone(hz(m), 0.8, 7), p + (0.05 + 0.06 * i) * SR)

    # --- light sweep shimmer
    s = at(ev["sweep"])
    L = int(1.2 * SR)
    sh = _bandnoise(L, 5000, 11000, rng) * np.sin(np.linspace(0, np.pi, L)) ** 2
    _add(mix, 0.025 * sh, s)

    # --- twinkles: tiny high bells
    for tw in ev.get("twinkles", []):
        m = root + 36 + scale[rng.integers(5)]
        _add(mix, 0.012 * _tone(hz(m), 0.6, 9), at(tw))

    # --- title chime
    ti = at(ev["title"])
    for i, m in enumerate([root + 12, root + 19, root + 24]):
        _add(mix, 0.04 * _tone(hz(m), 1.6, 3, ((1, 1.0), (2, 0.2))), ti + 0.12 * i * SR)

    mix = np.tanh(mix * 1.6) / np.tanh(1.6)
    fade = int(0.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([mix, mix], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767 * 0.9).astype(np.int16).tobytes())
