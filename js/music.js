// ─── MUSIC: a gentle nature soundtrack, made live in the browser (no files) ────
// A slow, wandering piece: a warm pad breathing through four chords (Dmaj9 · Bm9 · Gmaj7 ·
// Asus), a soft bass under it, and a kalimba picking out a melody that never quite repeats,
// now and then a glassy chime, all in a big airy reverb. Under the musicBus, the island itself:
// wind wandering through the grass, the waterfall's hush, birds calling from all sides (their
// calls are art-heist's, audio.js). Inside the gallery the outdoors fades to what comes in
// through the skylight and the music gets the hall's longer echo.
// Browsers only allow sound after a click or key, so it starts on the first one. The sound
// button (or M) mutes it; the choice is remembered.

let AC = null, master, musicBus, verb, amb, outdoor, hall, noise;
let muted = false, place = 'outside', started = false;
try { muted = localStorage.getItem('portfolio-sound') === 'off'; } catch { /* private window */ }
const LEVEL = 0.6;
const rnd = (a, b) => a + Math.random() * (b - a);
const hz = (n) => 440 * 2 ** ((n - 69) / 12);          // MIDI note → Hz

// the harmony: each chord 2 bars of 4 slow beats; pad voicing, bass, and the notes the kalimba may pick
const BPM = 64, BEAT = 60 / BPM;
const CHORDS = [
  { pad: [50, 57, 61, 64, 66], bass: 38, mel: [62, 64, 66, 69, 71, 73, 74, 76, 78, 81] },   // Dmaj9
  { pad: [47, 54, 57, 61, 62], bass: 35, mel: [61, 62, 66, 69, 71, 73, 74, 78, 81] },       // Bm9
  { pad: [43, 50, 54, 57, 59], bass: 31, mel: [62, 66, 67, 69, 71, 74, 78, 79, 83] },       // Gmaj7
  { pad: [45, 52, 55, 57, 62], bass: 33, mel: [62, 64, 67, 69, 71, 74, 76, 79, 81] },       // Asus
];

function build() {
  AC = new (window.AudioContext || window.webkitAudioContext)();
  const comp = AC.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 4;
  master = AC.createGain(); master.gain.value = 0;
  master.connect(comp); comp.connect(AC.destination);
  // a big soft reverb: decaying filtered noise, a little different in each ear
  const len = AC.sampleRate * 4.5, imp = AC.createBuffer(2, len, AC.sampleRate);
  for (let c = 0; c < 2; c++) { const d = imp.getChannelData(c); let lp = 0; for (let i = 0; i < len; i++) { lp += ((Math.random() * 2 - 1) - lp) * 0.35; d[i] = lp * (1 - i / len) ** 3; } }
  const conv = AC.createConvolver(); conv.buffer = imp;
  verb = AC.createGain(); verb.gain.value = 1;
  hall = AC.createGain(); hall.gain.value = 0.55;                      // the wet level (more inside)
  verb.connect(conv); conv.connect(hall); hall.connect(master);
  const warm = AC.createBiquadFilter(); warm.type = 'lowpass'; warm.frequency.value = 3200;
  musicBus = AC.createGain(); musicBus.gain.value = 0.9; musicBus.connect(warm); warm.connect(master);
  amb = AC.createGain(); amb.gain.value = 1; amb.connect(master);
  outdoor = AC.createGain(); outdoor.gain.value = 1; outdoor.connect(amb);
  noise = AC.createBuffer(1, AC.sampleRate * 3, AC.sampleRate);
  { const d = noise.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; }
  // wind: looped noise through a slowly wandering lowpass, rising and falling
  {
    const s = loop(), lp = filt('lowpass', 380, 1.1), g = gain(0.05), lfo = AC.createOscillator(), lg = gain(220), lfo2 = AC.createOscillator(), lg2 = gain(0.035);
    lfo.frequency.value = 0.06; lfo2.frequency.value = 0.11; lfo.connect(lg); lg.connect(lp.frequency); lfo2.connect(lg2); lg2.connect(g.gain);
    s.connect(lp); lp.connect(g); g.connect(outdoor); lfo.start(); lfo2.start();
  }
  // the waterfall: a steady far hush, off to the west
  {
    const s = loop(), bp = filt('bandpass', 900, 0.4), lp = filt('lowpass', 2200), g = gain(0.035), p = AC.createStereoPanner(); p.pan.value = -0.55;
    s.connect(bp); bp.connect(lp); lp.connect(g); g.connect(p); p.connect(outdoor);
  }
  document.addEventListener('visibilitychange', () => { if (!AC) return; if (document.hidden) AC.suspend(); else if (!muted) AC.resume(); });
  setInterval(pump, 50);
}
const gain = (v = 0) => { const g = AC.createGain(); g.gain.value = v; return g; };
const filt = (type, f, Q = 0.7) => { const b = AC.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = Q; return b; };
const loop = () => { const s = AC.createBufferSource(); s.buffer = noise; s.loop = true; s.start(0, Math.random() * 2); return s; };
const pan = (p, to) => { const n = AC.createStereoPanner(); n.pan.value = p; n.connect(to); return n; };

// ── instruments ──
// the pad: each note two detuned soft oscillators, a slow swell and a slow fade, lowpassed
function pad(notes, t, dur) {
  for (const n of notes) {
    const g = gain(0), lp = filt('lowpass', 900 + rnd(-100, 200), 0.3), p = pan(rnd(-0.5, 0.5), musicBus);
    for (const det of [-6, 5]) { const o = AC.createOscillator(); o.type = 'triangle'; o.frequency.value = hz(n); o.detune.value = det + rnd(-2, 2); o.connect(lp); o.start(t); o.stop(t + dur + 3); }
    lp.connect(g); g.connect(p); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.022, t + dur * 0.35);
    g.gain.setValueAtTime(0.022, t + dur * 0.7); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 2.8);
  }
}
function bass(n, t, dur) {
  const o = AC.createOscillator(), g = gain(0); o.type = 'sine'; o.frequency.value = hz(n);
  o.connect(g); g.connect(musicBus);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.09, t + 0.9); g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 1);
  o.start(t); o.stop(t + dur + 1.1);
}
// the kalimba: a sine with two bright overtones that die fast, a soft knock at the start
function kalimba(n, t, vol = 0.06, p = 0) {
  const out = pan(p, musicBus), f = hz(n);
  for (const [mul, v, d] of [[1, 1, 1.8], [3.0, 0.22, 0.35], [5.4, 0.08, 0.12]]) {
    const o = AC.createOscillator(), g = gain(0); o.type = 'sine'; o.frequency.value = f * mul;
    o.connect(g); g.connect(out); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol * v, t + 0.006); g.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.start(t); o.stop(t + d + 0.05);
  }
}
// a glassy chime, high and far, mostly reverb
function chime(n, t) {
  const o = AC.createOscillator(), o2 = AC.createOscillator(), g = gain(0), p = pan(rnd(-0.8, 0.8), verb);
  o.frequency.value = hz(n); o2.frequency.value = hz(n) * 2.76; o.connect(g); o2.connect(g); g.connect(p); g.connect(musicBus);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.018, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 3.5);
  o.start(t); o2.start(t); o.stop(t + 3.6); o2.stop(t + 3.6);
}
// a bird: one of a few calls, a little way off (art-heist audio.js)
function bird(t, to) {
  const out = filt('lowpass', 5200, 0.5), g = gain(1); out.connect(g); g.connect(pan(rnd(-0.9, 0.9), to));
  const v = rnd(0.012, 0.03), kind = Math.random();
  const note = (t0, f0, f1, len, vol = v) => {
    const o = AC.createOscillator(), e = gain(0); o.type = 'sine';
    o.frequency.setValueAtTime(f0, t0); o.frequency.exponentialRampToValueAtTime(f1, t0 + len);
    e.gain.setValueAtTime(0.0001, t0); e.gain.exponentialRampToValueAtTime(vol, t0 + len * 0.2); e.gain.exponentialRampToValueAtTime(0.0001, t0 + len);
    o.connect(e); e.connect(out); o.start(t0); o.stop(t0 + len + 0.02);
  };
  if (kind < 0.3) {
    const f = rnd(2200, 3000); note(t, f, f * 1.18, 0.14); note(t + 0.22, f * 1.12, f * 0.86, 0.2);
    if (Math.random() < 0.4) { note(t + 0.7, f, f * 1.18, 0.14); note(t + 0.92, f * 1.12, f * 0.86, 0.2); }
  } else if (kind < 0.55) {
    const f = rnd(3000, 3800), n = 5 + (Math.random() * 6 | 0);
    for (let i = 0; i < n; i++) note(t + i * 0.055, f * (1 - i * 0.02), f * (0.94 - i * 0.02), 0.045, v * 0.8);
  } else if (kind < 0.8) {
    const f = rnd(2400, 3400), n = 3 + (Math.random() * 4 | 0);
    for (let i = 0; i < n; i++) { const up = i % 2 ? 0.85 : 1.25; note(t + i * 0.11, f, f * up, 0.08 + Math.random() * 0.04, v * rnd(0.6, 1)); }
  } else {
    const f = rnd(480, 560);
    for (const [k, len] of [[0, 0.32], [0.45, 0.22], [0.75, 0.38]]) note(t + k, f * 0.92, f, len, v * 0.9);
  }
}

// ── the score: scheduled a little ahead, beat by beat ──
let next = 0, beat = 0, mel = 4, birdAt = 0;
function pump() {
  if (!AC || AC.state !== 'running') return;
  const now = AC.currentTime;
  if (next < now) next = now + 0.1;
  while (next < now + 0.4) {
    const bar = Math.floor(beat / 4), ci = Math.floor(bar / 2) % CHORDS.length, C = CHORDS[ci], inBar = beat % 4;
    if (beat % 8 === 0) { pad(C.pad, next, BEAT * 8); bass(C.bass, next, BEAT * 8); }
    // the kalimba: a wandering line, on the beat or the off-beat, resting often
    for (const sub of [0, 0.5]) {
      const busy = 0.32 + 0.18 * Math.sin(beat / 23);                  // it breathes: busier, then sparse
      if (Math.random() < (sub ? busy * 0.6 : busy)) {
        mel = Math.max(0, Math.min(C.mel.length - 1, mel + [-2, -1, -1, 1, 1, 2, 0][Math.random() * 7 | 0]));
        const t = next + sub * BEAT + rnd(0, 0.02);
        kalimba(C.mel[mel], t, rnd(0.04, 0.07), rnd(-0.35, 0.35));
        if (Math.random() < 0.12) kalimba(C.mel[Math.max(0, mel - 2)], t + 0.01, 0.03);   // a double-stop now and then
      }
    }
    if (inBar === 0 && Math.random() < 0.18) chime(C.mel[C.mel.length - 1 - (Math.random() * 3 | 0)] + 12, next + rnd(0, BEAT));
    next += BEAT; beat++;
  }
  // birds: often outside, rarely (through the skylight) in the hall
  if (now > birdAt) {
    if (place === 'outside' || Math.random() < 0.35) bird(now + 0.05, place === 'outside' ? outdoor : amb);
    birdAt = now + (place === 'outside' ? rnd(1.6, 5) : rnd(6, 14));
  }
}

function setLevel() {
  if (!AC) return;
  const t = AC.currentTime;
  master.gain.cancelScheduledValues(t); master.gain.setTargetAtTime(muted ? 0 : LEVEL, t, muted ? 0.15 : 1.2);
  if (muted) setTimeout(() => { if (muted) AC.suspend(); }, 600); else AC.resume();
}

export const music = {
  // call on any click / key: the first one starts it (if not muted)
  start() {
    if (started) return;
    if (!AC) build();
    started = true; AC.resume(); setLevel();
  },
  setPlace(p) {
    place = p;
    if (!AC) return;
    const t = AC.currentTime, inside = p === 'inside';
    outdoor.gain.setTargetAtTime(inside ? 0.08 : 1, t, 0.8);              // the wind and water, faint through the walls
    hall.gain.setTargetAtTime(inside ? 0.85 : 0.55, t, 1.0);              // the hall's longer echo
    musicBus.gain.setTargetAtTime(inside ? 0.75 : 0.9, t, 1.0);
  },
  get muted() { return muted; },
  // for the smoke test: is it running, and how loud is it right now (RMS of the output)
  get state() { return AC ? AC.state : 'none'; },
  level() {
    if (!AC) return 0;
    if (!this._an) { this._an = AC.createAnalyser(); this._an.fftSize = 2048; master.connect(this._an); }
    const d = new Float32Array(this._an.fftSize); this._an.getFloatTimeDomainData(d);
    return Math.sqrt(d.reduce((a, x) => a + x * x, 0) / d.length);
  },
  toggle() {
    muted = !muted;
    try { localStorage.setItem('portfolio-sound', muted ? 'off' : 'on'); } catch { /* private window */ }
    if (!muted && !started) this.start(); else setLevel();
    return muted;
  },
};
