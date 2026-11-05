"""Soundtrack for a painting reel: only nature sounds and paper/crayon/paint
effects, nothing tonal or melodic. Everything is filtered noise.

  unwrap   the parcel lands (thump), the twine snaps, each flap rustles back,
           the paper crumples (crackle) and whooshes away
  doodle   crayon scratching
  flood    a soft wet plop for each region (brighter as they go), a watery
           shimmer as the crayon lines wash away, a muffled settle thump
  life     ambient beds matched to what moves: waves, a waterfall's rush,
           rustling leaves, wind, an airy breeze, galloping hooves
  twinkles at most a barely-there airy shimmer, no pitch

The effects keep most of their energy between 500 Hz and 4 kHz so they come
through phone speakers. master() makes the final mix -14 LUFS integrated,
true peak under -1 dBTP (two-pass ffmpeg loudnorm, then a gain top-up).
"""
import json, os, re, subprocess, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _band(x, lo, hi):
    sos = butter(2, [lo, min(hi, SR / 2 - 100)], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def _bandnoise(n, lo, hi, rng):
    return _band(rng.standard_normal(n), lo, hi)


def _env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _burst(rng, dur, lo, hi, decay, attack=0.002):
    L = int(dur * SR)
    t = np.arange(L) / SR
    return _bandnoise(L, lo, hi, rng) * np.exp(-t * decay) * np.minimum(1, t / attack)


def _crackle(rng, dur, density, lo=1500, hi=8000):
    """Paper crackle: sparse random clicks through a band-pass, over a soft rustle."""
    L = int(dur * SR)
    imp = (rng.random(L) < density / SR) * rng.uniform(-1, 1, L) * rng.uniform(0.3, 1, L)
    return _band(imp, lo, hi) * 6 + 0.35 * _bandnoise(L, 700, 4500, rng)


def _add(mix, y, at):
    a = int(at)
    if a >= len(mix) or a < 0:
        return
    y = y[: len(mix) - a]
    mix[a:a + len(y)] += y


def make(ev, path, seed=0):
    rng = np.random.default_rng(seed)
    fps = ev["fps"]
    n = int(SR * ev["frames"] / fps) + SR // 2
    at = lambda f: SR * f / fps
    mix = np.zeros(n)

    # --- the parcel
    u = ev.get("unwrap")
    if u:
        _add(mix, 0.5 * _burst(rng, 0.25, 70, 500, 18) + 0.18 * _burst(rng, 0.12, 700, 3500, 45), at(u["land"]))
        _add(mix, 0.55 * _burst(rng, 0.06, 2000, 9000, 260, 0.0005) + 0.25 * _burst(rng, 0.1, 500, 2000, 90),
             at(u["snap"]))
        for f in u["flaps"]:
            d = 0.42
            y = _crackle(rng, d, 160) * _env(int(d * SR), 0.03, 0.2)
            _add(mix, 0.11 * y, at(f))
        for i, f in enumerate(u["crumple"]):
            d = 0.35
            y = _crackle(rng, d, 900) * _env(int(d * SR), 0.01, 0.12)
            _add(mix, 0.13 * y, at(f))
        # whoosh: a band of noise sliding up as the paper leaves
        d = 0.6
        L = int(d * SR)
        t = np.linspace(0, 1, L)
        w = (_bandnoise(L, 250, 1000, rng) * (1 - t) + _bandnoise(L, 900, 3000, rng) * np.sin(np.pi * t)
             + _bandnoise(L, 2500, 7000, rng) * t)
        _add(mix, 0.16 * w * np.sin(np.pi * t) ** 1.5, at(u["whoosh"]))

    # --- crayon scratching while drawing: strokes at ~6-9 per second
    d0, d1 = ev["draw"]
    a, b = int(at(d0)), int(at(d1))
    L = b - a
    scratch = _bandnoise(L, 1200, 5500, rng) + 0.6 * _bandnoise(L, 500, 1200, rng)
    t = np.arange(L) / SR
    rate = 7.5 + 1.5 * np.sin(2 * np.pi * 0.3 * t)
    strokes = (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / SR)) ** 1.5
    grit = 0.7 + 0.3 * (rng.random(L) > 0.5)
    _add(mix, 0.09 * scratch * strokes * grit * _env(L, 0.05, 0.15), a)

    # --- a soft wet plop for each region that floods with paint
    for i, f in enumerate(ev["blooms"]):
        fc = 600 * 1.06 ** i
        y = 0.9 * _burst(rng, 0.14, fc * 0.55, fc * 1.7, 30, 0.004) + 0.25 * _burst(rng, 0.03, 2500, 6000, 220, 0.0008)
        _add(mix, 0.22 * y, at(f))

    # --- the crayon lines wash away: a watery shimmer of noise
    wa = at(ev["wash"])
    L = int(0.8 * SR)
    sh = (_bandnoise(L, 2500, 7000, rng) + 0.5 * _crackle(rng, 0.8, 120, 3000, 9000)) * np.sin(np.linspace(0, np.pi, L)) ** 2
    _add(mix, 0.07 * sh, wa)

    # --- settle: one muffled thump
    _add(mix, 0.28 * _burst(rng, 0.2, 180, 1300, 20, 0.003) + 0.06 * _burst(rng, 0.03, 2000, 5000, 200), at(ev["done"]))

    # --- twinkles: a barely-there airy shimmer, no pitch
    for tw in ev.get("twinkles", []):
        L = int(0.3 * SR)
        _add(mix, 0.012 * _bandnoise(L, 5000, 11000, rng) * np.sin(np.linspace(0, np.pi, L)) ** 2, at(tw))

    # --- ambient beds for the moving painting, fading in with the motion
    if ev.get("ambient"):
        a0 = int(at(ev["anim"]))
        L = n - a0
        t = np.arange(L) / SR
        fade_in = np.minimum(1, t / 0.8)
        for kind in ev["ambient"]:
            if kind == "waves":      # swells every 3-5 s
                nz = _bandnoise(L, 250, 2200, rng) + 0.5 * _bandnoise(L, 2200, 4500, rng)
                per = rng.uniform(3.2, 4.6)
                sw = 0.25 + 0.75 * np.sin(np.pi * (t + rng.uniform(0, per)) / per) ** 2
                y = 0.10 * nz * sw
            elif kind == "rush":     # waterfall / river: steady pink-ish rush
                y = 0.07 * (_bandnoise(L, 300, 1200, rng) + 0.8 * _bandnoise(L, 1200, 5000, rng))
                y *= 0.9 + 0.1 * np.sin(2 * np.pi * 0.4 * t)
            elif kind == "rustle":   # leaves: soft high-passed bursts
                nz = _bandnoise(L, 2000, 8000, rng)
                env = np.zeros(L)
                tt = rng.uniform(0, 0.4)
                while tt < L / SR:
                    d = rng.uniform(0.25, 0.7)
                    i0, i1 = int(tt * SR), min(L, int((tt + d) * SR))
                    env[i0:i1] += np.sin(np.linspace(0, np.pi, i1 - i0)) ** 2 * rng.uniform(0.5, 1)
                    tt += rng.uniform(0.35, 1.1)
                y = 0.09 * nz * env
            elif kind == "wind":     # slow, breathy wind
                y = 0.08 * _bandnoise(L, 300, 1400, rng) * (0.45 + 0.55 * np.sin(2 * np.pi * 0.17 * t + 1) ** 2)
            elif kind in ("pad", "airy"):   # an airy breeze for magical skies: high, soft, slowly breathing
                y = (0.05 * _bandnoise(L, 1500, 6000, rng) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.21 * t) ** 2)
                     + 0.04 * _bandnoise(L, 400, 1500, rng) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t + 2)))
            elif kind == "gallop":   # ta-da-dum hoofbeats, muffled, with a splash on each stride
                g = ev.get("gallop", {"freq": 2.4, "phases": [0.0, 0.37, 0.71]})
                per = 1.0 / g["freq"]
                y = np.zeros(L)
                for j, ph in enumerate(g["phases"][:3]):
                    gain = [1.0, 0.75, 0.6][j]
                    s = ph * per
                    while s < L / SR:
                        for off, amp in ((0.0, 0.6), (0.07, 0.75), (0.15, 1.0)):
                            hit = 0.8 * _burst(rng, 0.09, 90, 700, 38) + 0.35 * _burst(rng, 0.04, 700, 2500, 90)
                            _add(y, gain * amp * hit, (s + off) * SR)
                        _add(y, gain * 0.35 * _burst(rng, 0.12, 1500, 6000, 40), (s + 0.17) * SR)
                        s += per
                y = 0.16 * y
            else:
                continue
            _add(mix, 0.65 * y * fade_in, a0)

    mix = np.tanh(mix * 2.0) / np.tanh(2.0)
    fade = int(0.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.abs(mix).max() + 1e-9
    st = np.stack([mix, mix], 1) * 0.7
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def master(src, dst, target=-14.0, tp=-1.5, lra=11):
    """Two-pass ffmpeg loudnorm: measure, then normalise linearly to `target` LUFS.
    True-peak target sits a little under -1 dBTP so AAC encoding stays below -1."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", p.stderr)[-1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
          f":linear=true:print_format=summary")
    tmp = dst + ".pass2.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", str(SR), "-ac", "2", tmp],
                   check=True)
    # linear loudnorm can land a little short when the peaks limit it; top up with
    # plain gain, never past the true-peak target
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", p.stderr)[-1])
    gain = min(target - float(m["input_i"]), tp - float(m["input_tp"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"volume={max(0.0, gain):.2f}dB",
                    "-ar", str(SR), "-ac", "2", dst], check=True)
    os.remove(tmp)
    return dst
