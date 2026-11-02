# Sound effects, timed to the cut: card pops, paper crinkles (unwrapping), hammer taps (the crew),
# swishes on the painting cuts, whooshes into the hall and at the end. Writes sfx.wav (stereo, 48 kHz).
import json, numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 48000; rng = np.random.default_rng(7)
T = json.load(open('timeline.json')); N = json.load(open('shots.json'))
LEN = T['voice_end'] + 1.2; out = np.zeros((int(LEN * SR) + SR, 2))
bp = lambda x, lo, hi: sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
hp = lambda x, f: sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)
def add(sig, t, vol=1.0, pan=0.0):
  i = int(t * SR); sig = sig[: max(0, len(out) - i)] * vol
  out[i:i + len(sig), 0] += sig * (1 - max(0, pan)); out[i:i + len(sig), 1] += sig * (1 + min(0, pan))
def env(n, att, dec):   # attack then exponential decay (seconds)
  t = np.arange(n) / SR; return np.minimum(1, t / max(att, 1e-4)) * np.exp(-t / dec)
def pop():      # a paper card flicked onto the screen: a papery snap and a soft low thump
  n = int(0.12 * SR); t = np.arange(n) / SR
  snap = bp(rng.standard_normal(n), 1800, 5000) * env(n, 0.002, 0.018)
  thump = np.sin(2 * np.pi * (190 - 60 * t / 0.12) * t) * env(n, 0.003, 0.035)
  return 0.5 * snap + 0.6 * thump
def whoosh(dur, lo=300, hi=3500, rise=0.6):   # air: noise swept through a band, swelling then fading
  n = int(dur * SR); x = rng.standard_normal(n); y = np.zeros(n); k = 0; seg = 480
  for s in range(0, n, seg):
    p = s / n; f = lo + (hi - lo) * (np.sin(np.pi * p) ** 1.5)
    y[s:s + seg] = bp(x[s:s + seg + 0][:seg], max(60, f * 0.6), min(SR / 2 - 100, f * 1.6))
  t = np.arange(n) / n; e = np.where(t < rise, (t / rise) ** 2, ((1 - t) / (1 - rise)) ** 1.5)
  return y * e
def crinkle(dur):   # crackling paper (as in loading.js): sparse crackles, each decaying fast
  n = int(dur * SR); x = np.zeros(n); e = 0
  imp = rng.random(n) < 0.004; amp = 0.4 + 0.6 * rng.random(n); d = np.empty(n)
  for i in range(n):
    if imp[i]: e = amp[i]
    e *= 0.9965; d[i] = e
  x = rng.standard_normal(n) * d * (1 - np.arange(n) / n)
  return hp(bp(x, 2000 + 2400 * rng.random(), 6000), 900)
def tap():      # a hammer on a nail in the wall: a woody knock
  n = int(0.09 * SR); t = np.arange(n) / SR
  knock = (np.sin(2 * np.pi * 820 * t) + 0.5 * np.sin(2 * np.pi * 1730 * t)) * env(n, 0.0008, 0.016)
  click = hp(rng.standard_normal(n), 2500) * env(n, 0.0003, 0.004)
  return 0.7 * knock + 0.35 * click
fr = lambda f: f / 30
# the cards pop on (every section start; the cards ease in over ~0.3 s)
for k in ['hook', 'l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'outro', 'bio']:
  add(pop(), T[k] + 0.02, 0.55, rng.uniform(-0.15, 0.15))
# unwrapping: crinkles all through it
t = T['l2'] + 0.15
while t < T['crew'] - 0.2:
  add(crinkle(rng.uniform(0.22, 0.4)), t, 0.6, rng.uniform(-0.5, 0.5)); t += rng.uniform(0.28, 0.5)
# the crew: the hammer lands at 78% of its 0.62 s swing (index.html @keyframes hammer)
t = T['crew'] + 0.78 * 0.62
while t < T['l3'] - 0.05:
  add(tap(), t, 0.5, 0.25); t += 0.62
# into the hall, and the painting cuts (record.mjs: about a second each)
add(whoosh(0.9, 250, 2600), T['l4'] - 0.35, 0.22)
L = max(1, round(N['E'] / 28)); each = N['E'] // L
for j in range(1, L):
  add(whoosh(0.28, 900, 5000, 0.5), T['l5'] + fr(j * each) - 0.12, 0.16, rng.uniform(-0.3, 0.3))
# the rise away from the island
add(whoosh(2.2, 200, 1800, 0.45), T['outro'] + 0.1, 0.18)
out = out[: int(LEN * SR)]; out /= max(1e-9, np.abs(out).max()) / 0.7
wavfile.write('sfx.wav', SR, (out * 32767).astype(np.int16)); print('sfx', round(LEN, 2), 's')
