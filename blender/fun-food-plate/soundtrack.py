"""Builds the soundtrack from events.json: crayon scratching while each
scribble is drawn, a bubbly pop when the food appears, a little marimba tune.

    python3 soundtrack.py frames/events.json out.wav
"""
import json, sys, wave
import numpy as np

ev = json.load(open(sys.argv[1]))
fps, frames = ev["fps"], ev["frames"]
SR = 44100
n = int(SR * frames / fps) + SR // 2
mix = np.zeros(n)
rng = np.random.default_rng(3)
t_of = lambda f: int(SR * (f - 1) / fps)

def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y

# crayon: band-limited noise in short strokes
for e in ev["events"]:
    if e["type"] != "scribble":
        continue
    a, b = t_of(e["start"]), t_of(e["end"])
    L = b - a
    noise = rng.standard_normal(L)
    hp = noise - lowpass(noise, 0.15)          # take the low rumble out
    band = lowpass(hp, 0.5)
    strokes = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * np.arange(L) / SR + rng.uniform(0, 6))
    env = np.minimum(1, np.minimum(np.arange(L), L - np.arange(L)) / (0.02 * SR))
    mix[a:b] += 0.18 * band * strokes ** 2 * env

# pops: a light lip pop ("pok") - quick upward chirp, very short
def lip_pop(pitch=1.0):
    L = int(0.08 * SR); t = np.arange(L) / SR
    f = (650 + 850 * (1 - np.exp(-t / 0.005))) * pitch
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.minimum(1, t * 1000) * np.exp(-t * 90)
    tone = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env
    click = rng.standard_normal(L) * np.exp(-t * 1500)
    click = click - lowpass(click, 0.3)
    return 0.6 * tone + 0.12 * click

for e in ev["events"]:
    a = t_of(e.get("frame", 0))
    if e["type"] == "pop":
        p = lip_pop(rng.uniform(0.9, 1.1)); mix[a:a + len(p)] += p[:len(mix) - a]
    elif e["type"] == "clear":  # soft whoosh down when the plate empties
        L = int(0.18 * SR); t = np.arange(L) / SR
        ph = 2 * np.pi * np.cumsum(900 - 3000 * t) / SR
        mix[a:a + L] += 0.3 * np.sin(ph) * np.exp(-t * 28) * np.minimum(1, t * 800)

# marimba tune, C major pentatonic, 120 bpm
notes = [72, 76, 79, 76, 81, 79, 76, 74, 72, 74, 76, 79, 84, 81, 79, 76]
beat = 0.25
t_total = n / SR
k = 0
while k * beat < t_total - 0.6:
    midi = notes[k % len(notes)] - (12 if k % 4 == 0 else 0)
    f = 440 * 2 ** ((midi - 69) / 12)
    L = int(0.6 * SR); t = np.arange(L) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 40)
    a = int(k * beat * SR)
    seg = mix[a:a + L]
    seg += 0.12 * tone[:len(seg)] * np.exp(-t[:len(seg)] * 7)
    k += 1

mix /= max(1e-6, np.abs(mix).max()) / 0.85
fade = int(0.3 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
