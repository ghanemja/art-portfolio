"""Soundtrack for a painting reel, built from the reel's events:
crayon scratching while the doodle is drawn, a soft bloop as each region floods
with paint (rising in pitch), a shimmer as the crayon lines wash away and a
gentle settle pop, over a kalimba-and-pad tune.

The sound effects keep most of their energy between 500 Hz and 4 kHz so they
come through phone speakers. master() makes the final mix loud enough to post:
-14 LUFS integrated, true peak -1 dBTP, with a two-pass ffmpeg loudnorm.
"""
import json, re, subprocess, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


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
    if a >= len(mix) or a < 0:
        return
    y = y[: len(mix) - a]
    mix[a:a + len(y)] += y


def _bloop(f, rng, dur=0.2):
    """Soft, round, water-drop pop: a quick upward glide with a couple of
    harmonics so it still reads on a small speaker, plus a tiny wet tick."""
    t = np.arange(int(dur * SR)) / SR
    fr = f * (0.62 + 0.38 * (1 - np.exp(-t * 55)))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    env = np.exp(-t * 20) * np.minimum(1, t * 900)
    y = (np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.18 * np.sin(3 * ph)) * env
    tick = _bandnoise(len(t), 1500, 4000, rng) * np.exp(-t * 260)
    return y + 0.25 * tick


def make(ev, path, seed=0):
    rng = np.random.default_rng(seed)
    fps = ev["fps"]
    n = int(SR * ev["frames"] / fps) + SR // 2
    at = lambda f: SR * f / fps
    mix = np.zeros(n)
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)

    # --- tune: kalimba plucks over a soft pad, in a key picked per reel
    roots = [60, 62, 65, 67, 57]
    root = roots[rng.integers(len(roots))]
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
    chords = [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]]
    beat = 60 / 92
    nbars = int(n / SR / (4 * beat)) + 1
    for b in range(nbars):
        for c in chords[b % 4]:  # pad
            dur = 4 * beat + 0.6
            t = np.arange(int(dur * SR)) / SR
            f = hz(root - 12 + c)
            y = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2.003 * f * t)
                 + 0.15 * np.sin(2 * np.pi * 3.01 * f * t)) * _env(len(t), 0.8, 0.8)
            _add(mix, 0.012 * y, b * 4 * beat * SR)
        for i in range(8):  # plucks on eighths, sparse
            if rng.random() < 0.45:
                continue
            m = root + 12 + scale[rng.integers(8)]
            y = _tone(hz(m), 0.9, 6, ((1, 1.0), (2.76, 0.22), (5.4, 0.08)))
            _add(mix, 0.035 * y, (b * 4 + i * 0.5) * beat * SR)

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

    # --- a bloop for every region that floods with paint, climbing the scale
    for i, f in enumerate(ev["blooms"]):
        m = root + 12 + scale[min(i, len(scale) - 1)]
        _add(mix, 0.10 * _bloop(hz(m), rng), at(f))

    # --- the crayon lines wash away: a soft watery shimmer
    wa = at(ev["wash"])
    L = int(0.8 * SR)
    sh = _bandnoise(L, 2500, 7000, rng) * np.sin(np.linspace(0, np.pi, L)) ** 2
    _add(mix, 0.05 * sh, wa)
    for i, m in enumerate([root + 24, root + 28, root + 31, root + 36]):
        _add(mix, 0.025 * _tone(hz(m), 0.7, 7), wa + 0.07 * i * SR)

    # --- settle: one gentle, slightly lower pop as the painting lands
    _add(mix, 0.09 * _bloop(hz(root + 7), rng, 0.25), at(ev["done"]))

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
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", str(SR), "-ac", "2", dst],
                   check=True)
    return dst
