"""Soundtrack for a painting reel: only nature sounds and paper/crayon/paint
effects, nothing melodic. Everything is filtered noise, but for the tiny
chirp inside each lip-pop.

  unwrap   the parcel lands (thump), the twine snaps, each flap rustles back
           and slaps down, then swishes softly as it falls away
  doodle   crayon scratching
  flood    a light lip-pop for each region (lip_pop), a watery shimmer as the
           crayon lines wash away (a soft wet wipe in reels without sparkle),
           a muffled settle thump
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


def _sum(*parts):
    """Add sounds of different lengths, all starting together."""
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def _add(mix, y, at):
    a = int(at)
    if a >= len(mix) or a < 0:
        return
    y = y[: len(mix) - a]
    mix[a:a + len(y)] += y


def _highpass(x, fc):
    sos = butter(2, fc, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x)


def lip_pop(rng, pitch=None, dur=None):
    """A light lip-pop, like pressing your lips together and releasing: about 50-80 ms long,
    a 1 ms attack, a tiny highpassed click, then a sine chirping 650 -> 1500 Hz in about
    10 ms, decaying as exp(-t*90). Each pop is pitched +-10 % at random."""
    if pitch is None:
        pitch = rng.uniform(0.9, 1.1)
    dur = dur if dur is not None else rng.uniform(0.05, 0.08)
    L = int(dur * SR)
    t = np.arange(L) / SR
    f = 650 * (1500 / 650) ** np.minimum(1.0, t / 0.010) * pitch      # exponential chirp, then holds
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.minimum(1.0, t / 0.001) * np.exp(-t * 90)
    body = np.sin(phase) * env
    nc = int(0.004 * SR)
    click = np.zeros(L)
    click[:nc] = _highpass(rng.standard_normal(nc), 3000) * np.exp(-np.arange(nc) / SR * 900)
    y = body + 0.35 * click
    y[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))       # no click at the tail
    return y


def make(ev, path, seed=0):
    rng = np.random.default_rng(seed)
    fps = ev["fps"]
    n = int(SR * ev["frames"] / fps) + SR // 2
    at = lambda f: SR * f / fps
    mix = np.zeros(n)
    side = np.zeros(n)      # left minus right, for sounds placed across the frame
    sparkle = ev.get("sparkle", True)

    # --- the parcel
    u = ev.get("unwrap")
    if u:
        _add(mix, _sum(0.5 * _burst(rng, 0.25, 70, 500, 18), 0.18 * _burst(rng, 0.12, 700, 3500, 45)), at(u["land"]))
        _add(mix, _sum(0.55 * _burst(rng, 0.06, 2000, 9000, 260, 0.0005), 0.25 * _burst(rng, 0.1, 500, 2000, 90)),
             at(u["snap"]))
        if "flap_dur" in u:
            # parchment rustling with each curl: soft as it starts to peel, swelling as it flops over,
            # and a papery slap as it lands
            for f, fl, st in zip(u["flaps"], u["flops"], u["settles"]):
                d = (st - f) / fps + 0.12
                L = int(d * SR)
                tt = np.arange(L) / SR
                tf = (fl - f) / fps
                env = np.where(tt < tf, 0.2 + 0.8 * (tt / tf) ** 2, np.exp(-(tt - tf) * 9))
                env *= np.minimum(1, tt / 0.03)
                y = (_crackle(rng, d, 90, 1200, 7000) * 0.8 + 0.6 * _bandnoise(L, 600, 3000, rng)) * env
                _add(mix, 0.10 * y, at(f))
                _add(mix, _sum(0.10 * _burst(rng, 0.09, 250, 1400, 40, 0.004),
                               0.05 * _burst(rng, 0.05, 1500, 5000, 80)), at(st))
            # then each sheet drops away: a soft swish of air with every swing as it falls, fading out
            for f in u.get("falls", []):
                d = u["fall_dur"] * 0.8
                L = int(d * SR)
                tt = np.arange(L) / SR
                swing = np.abs(np.sin(2 * np.pi * 0.85 * tt + rng.uniform(0, 3))) ** 3
                env = swing * np.minimum(1, tt / 0.15) * np.exp(-tt * 1.6)
                y = (_bandnoise(L, 400, 2200, rng) + 0.35 * _crackle(rng, d, 40, 1500, 6000)) * env
                _add(mix, 0.07 * y, at(f))
        else:
            for f in u["flaps"]:
                d = 0.42
                y = _crackle(rng, d, 160) * _env(int(d * SR), 0.03, 0.2)
                _add(mix, 0.11 * y, at(f))
            for i, f in enumerate(u["crumple"]):
                d = 0.35
                y = _crackle(rng, d, 900) * _env(int(d * SR), 0.01, 0.12)
                _add(mix, 0.13 * y, at(f))
        # whoosh: a band of noise sliding up as each paper ball leaves
        wh = u.get("whoosh", [])
        wh = wh if isinstance(wh, list) else [wh]
        for f in wh:
            d = 0.45
            L = int(d * SR)
            t = np.linspace(0, 1, L)
            w = (_bandnoise(L, 250, 1000, rng) * (1 - t) + _bandnoise(L, 900, 3000, rng) * np.sin(np.pi * t)
                 + _bandnoise(L, 2500, 7000, rng) * t)
            _add(mix, 0.1 * w * np.sin(np.pi * t) ** 1.5, at(f))

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

    # --- a light lip-pop for each region that floods with paint
    for i, f in enumerate(ev["blooms"]):
        _add(mix, 0.2 * lip_pop(rng), at(f))

    # --- the crayon lines wash away: a watery shimmer of noise (or, without sparkle, a soft wet wipe)
    wa = at(ev["wash"])
    L = int(0.8 * SR)
    if sparkle:
        sh = (_bandnoise(L, 2500, 7000, rng) + 0.5 * _crackle(rng, 0.8, 120, 3000, 9000)) * np.sin(np.linspace(0, np.pi, L)) ** 2
        _add(mix, 0.07 * sh, wa)
    else:
        sh = _bandnoise(L, 350, 1800, rng) * np.sin(np.linspace(0, np.pi, L)) ** 2
        _add(mix, 0.06 * sh, wa)

    # --- settle: one muffled thump
    _add(mix, _sum(0.28 * _burst(rng, 0.2, 180, 1300, 20, 0.003), 0.06 * _burst(rng, 0.03, 2000, 5000, 200)), at(ev["done"]))

    # --- twinkles: a barely-there airy shimmer, no pitch
    for tw in (ev.get("twinkles", []) if sparkle else []):
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
            elif kind == "river":    # a river running fast: a broad rush with a burbling, gurgling texture
                gurgle = 0.6 + 0.4 * np.abs(_band(rng.standard_normal(L), 2, 9)) / 0.05
                gurgle = np.clip(gurgle / (np.percentile(gurgle, 95) + 1e-9), 0.3, 1.2)
                y = 0.038 * (_bandnoise(L, 250, 900, rng) + 0.9 * _bandnoise(L, 900, 3500, rng) * gurgle)
            elif kind == "rustle" and ev.get("gust"):   # leaves tossing in gusts of the gallop's wind
                gu = ev["gust"]
                swell = (0.5 + 0.5 * np.sin(2 * np.pi * gu["freq"] * (t + a0 / SR - gu["start"]) + gu["phase"])) ** 1.5
                flick = 0.7 + 0.3 * np.abs(_band(rng.standard_normal(L), 4, 25)) / 0.03
                flick = np.clip(flick / (np.percentile(flick, 95) + 1e-9), 0.2, 1.2)
                y = (0.05 * _bandnoise(L, 2000, 8000, rng) * flick + 0.03 * _bandnoise(L, 400, 1500, rng)) \
                    * (0.25 + 0.75 * swell)
            elif kind == "pour" and ev.get("pour"):
                # the river pouring off the canvas: a stream from the start, then a heavy splashing
                # roar once it lands (off the bottom of the screen)
                po = ev["pour"]
                ts = t - (po["start"] - a0 / SR)
                tl = t - (po["land"] - a0 / SR)
                fl1 = np.abs(_band(rng.standard_normal(L), 6, 40))
                fl1 = np.clip(fl1 / (np.percentile(fl1, 95) + 1e-9), 0.25, 1.3)
                stream = _bandnoise(L, 700, 4500, rng) * np.clip(ts / 0.4, 0, 1)
                roar = (_bandnoise(L, 160, 900, rng) + 0.8 * _bandnoise(L, 900, 3500, rng) * fl1) \
                    * np.clip(tl / 0.5, 0, 1)
                y = 0.035 * stream + 0.07 * roar
            elif kind in ("splash", "mist"):   # carried by the hoofbeats and the rush
                continue
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
            elif kind == "gallop" and ev.get("hooves"):
                # each hoof as it lands in the shallows: a muffled thud and knock, then the splash,
                # placed across the stereo field where that horse is
                y = np.zeros(L)
                ys = np.zeros(L)
                hg = [1.0, 0.85, 0.7, 0.9, 0.75]
                for hv in ev["hooves"]:
                    th, pan, ramp, hi = hv[:4]
                    wet, near = (hv[4], hv[5]) if len(hv) > 5 else (1.0, 1.0)
                    s0 = (th - a0 / SR) * SR
                    g = hg[int(hi) % len(hg)] * (0.3 + 0.7 * ramp) * rng.uniform(0.75, 1.05) * min(near, 2.2) ** 0.9
                    hit = _sum(0.7 * _burst(rng, 0.08, 110, 650, 42, 0.002), 0.3 * _burst(rng, 0.03, 700, 2400, 120, 0.001))
                    spl = _sum(0.35 * _burst(rng, 0.2, 1300, 6500, 16, 0.006), 0.22 * _burst(rng, 0.14, 450, 1500, 24, 0.004))
                    snd = _sum(g * hit, np.concatenate([np.zeros(int(0.012 * SR)), g * wet * spl]))
                    _add(y, snd, s0)
                    _add(ys, 0.45 * pan * snd, s0)
                _add(side, 0.65 * 0.17 * ys * fade_in[:len(ys)], a0)
                y = 0.17 * y
            elif kind == "gallop":   # ta-da-dum hoofbeats, muffled, with a splash on each stride
                g = ev.get("gallop", {"freq": 2.4, "phases": [0.0, 0.37, 0.71]})
                per = 1.0 / g["freq"]
                y = np.zeros(L)
                for j, ph in enumerate(g["phases"][:3]):
                    gain = [1.0, 0.75, 0.6][j]
                    s = ph * per
                    while s < L / SR:
                        for off, amp in ((0.0, 0.6), (0.07, 0.75), (0.15, 1.0)):
                            hit = _sum(0.8 * _burst(rng, 0.09, 90, 700, 38), 0.35 * _burst(rng, 0.04, 700, 2500, 90))
                            _add(y, gain * amp * hit, (s + off) * SR)
                        _add(y, gain * 0.35 * _burst(rng, 0.12, 1500, 6000, 40), (s + 0.17) * SR)
                        s += per
                y = 0.16 * y
            else:
                continue
            _add(mix, 0.65 * y * fade_in, a0)

    Lc, Rc = mix + side, mix - side
    Lc = np.tanh(Lc * 2.0) / np.tanh(2.0)
    Rc = np.tanh(Rc * 2.0) / np.tanh(2.0)
    fade = int(0.5 * SR)
    st = np.stack([Lc, Rc], 1)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    st = st / (np.abs(st).max() + 1e-9) * 0.7
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def master(src, dst, target=-14.0, tp=-2.8, lra=11):
    """Two-pass ffmpeg loudnorm: measure, then normalise linearly to `target` LUFS.
    The true-peak target sits well under -1 dBTP: AAC encoding adds about 1 dB on sharp transients."""
    # tame the sharpest transients (twine snap, plops) first, so they don't cap the loudness
    lim = src + ".lim.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    "alimiter=limit=0.25:attack=0.5:release=30:level=false", "-ar", str(SR), lim], check=True)
    src = lim
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
    os.remove(tmp); os.remove(lim)
    return dst
