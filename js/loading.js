// ─── THE LOADING SCREEN: unwrapping the paintings, one parcel at a time ──────
// Each painting arrives as a kraft-paper parcel tied with twine and stamped FRAGILE. The twine
// snaps, the paper tears open in four flaps that peel back (creasing as they go), each flap is
// scrunched up into a crinkled ball and tossed onto a growing heap in the corner, and the
// painting pops out in a little gilt frame and flies up to hang on the wall at the top.
// Click (or tap) to help: it tears faster, and once you've clicked the paper crinkles out loud
// (browsers only allow sound after a click). The parcels keep pace with the real loading:
// the more that are waiting, the quicker they're unwrapped; at the end any backlog is opened
// in one flurry so nobody waits on the show.
const INK = '#2a2230', KRAFT = '#c99f68', KRAFT_D = '#a97f4c', KRAFT_L = '#e2c495', TWINE = '#e9dcc0';
const HAND = '"Patrick Hand", "Comic Sans MS", cursive', SCRIPT = '"Caveat", "Patrick Hand", cursive';
const QUIPS = ['careful… careful…', 'who used this much tape?', 'crinkle crinkle crinkle', 'ooh, this one!', 'mind the frame!',
  'still smells like paint', 'so. much. paper.', 'one more…', 'gently does it', 'no peeking!', 'ta-da!', 'rip!'];

// a repeatable random, so a ball keeps its crinkles
const rnd = (seed) => {
  let s = (Math.imul(seed | 0, 2654435761) >>> 0) % 2147483646 + 1;      // (spread small seeds out: 1, 2, 3… would start almost alike)
  const f = () => ((s = (s * 16807) % 2147483647) / 2147483647); f(); f();
  return f;
};
const ease = (t) => t * t * (3 - 2 * t);
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));

// the crinkle: short bursts of filtered noise, crackling (only after a click: autoplay rules)
let AC = null;
function crinkle(len = 0.35, loud = 0.5) {
  if (!AC || AC.state !== 'running') return;
  const n = Math.floor(AC.sampleRate * len), buf = AC.createBuffer(1, n, AC.sampleRate), d = buf.getChannelData(0);
  let env = 0;
  for (let i = 0; i < n; i++) {
    if (Math.random() < 0.004) env = 0.4 + Math.random() * 0.6;   // a crackle
    env *= 0.9965;
    d[i] = (Math.random() * 2 - 1) * env * (1 - i / n);
  }
  const src = AC.createBufferSource(); src.buffer = buf;
  const bp = AC.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2400 + Math.random() * 2400; bp.Q.value = 0.7;
  const hp = AC.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 900;
  const g = AC.createGain(); g.gain.value = loud;
  src.connect(bp).connect(hp).connect(g).connect(AC.destination);
  src.start();
}

export function createUnwrap(host, total) {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cv = document.createElement('canvas');
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;cursor:pointer;touch-action:manipulation';
  host.appendChild(cv);
  for (const el of host.children) if (el !== cv) el.style.display = 'none';
  const c = cv.getContext('2d');
  let W = 0, H = 0, DPR = 1;
  const size = () => { DPR = Math.min(devicePixelRatio, 2); W = host.clientWidth || innerWidth; H = host.clientHeight || innerHeight; cv.width = W * DPR; cv.height = H * DPR; };
  size(); addEventListener('resize', size);

  // kraft paper: speckles and fibres, painted once
  const kraft = (() => {
    const k = document.createElement('canvas'); k.width = k.height = 256; const x = k.getContext('2d');
    x.fillStyle = KRAFT; x.fillRect(0, 0, 256, 256);
    const R = rnd(5);
    for (let i = 0; i < 900; i++) { x.fillStyle = R() < 0.5 ? 'rgba(120,80,40,0.18)' : 'rgba(255,240,210,0.16)'; x.fillRect(R() * 256, R() * 256, 1 + R() * 2, 1 + R() * 2); }
    x.strokeStyle = 'rgba(110,72,36,0.14)'; x.lineWidth = 1;
    for (let i = 0; i < 70; i++) { const a = R() * 6.28, l = 4 + R() * 14, px = R() * 256, py = R() * 256; x.beginPath(); x.moveTo(px, py); x.lineTo(px + Math.cos(a) * l, py + Math.sin(a) * l); x.stroke(); }
    return c.createPattern(k, 'repeat');
  })();

  const queue = [];          // loaded, still wrapped
  const hung = [];           // unwrapped, on the wall: { img, slot, t }
  const balls = [];          // crumpled paper: flying, then on the heap
  const scraps = [];         // little torn bits in the air
  let cur = null, added = 0, speed = 1, ending = false, quip = QUIPS[0], helped = false;

  // where the hung paintings go: a salon wall across the top
  const slot = (i) => {
    const top = Math.max(64, H * 0.1), band = H * 0.2, cols = Math.ceil(Math.sqrt(total * (W * 0.9) / band)), rows = Math.ceil(total / cols);
    const cw = W * 0.9 / cols, ch = band / rows, s = Math.min(cw, ch) * 0.8;
    const col = i % cols, row = Math.floor(i / cols);
    return { x: W * 0.05 + cw * (col + 0.5), y: top + ch * (row + 0.5), s };
  };
  const heapAt = () => ({ x: W * 0.86, y: H * 0.9 });

  function next() {
    if (!queue.length) { cur = null; return; }
    const it = queue.shift();
    const R = rnd(17 + it.slot * 31);
    cur = { ...it, u: 0, R, idx: it.slot, tore: false, crumpled: false, seed: Math.floor(R() * 1e6),
      tilt: (R() - 0.5) * 0.12, quip: QUIPS[Math.floor(R() * QUIPS.length)] };
    quip = cur.quip;
  }

  // the parcel's size on screen for an image
  const dims = (img) => {
    const a = img.width && img.height ? img.width / img.height : 1.3, m = Math.min(W * 0.62, H * 0.36);
    return a >= 1 ? [m, m / a] : [m * a, m];
  };
  const cx = () => W / 2, cy = () => H * 0.56;

  // ── drawing bits ──
  function framed(img, x, y, w, h, rot = 0, s = 1) {
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s);
    const b = Math.max(4, Math.min(w, h) * 0.09);
    const g = c.createLinearGradient(-w / 2 - b, -h / 2 - b, w / 2 + b, h / 2 + b);
    g.addColorStop(0, '#fff0b0'); g.addColorStop(0.35, '#e3b44c'); g.addColorStop(0.7, '#a8761f'); g.addColorStop(1, '#f2d27a');
    c.fillStyle = 'rgba(42,34,48,0.25)'; c.fillRect(-w / 2 - b + 4, -h / 2 - b + 6, w + 2 * b, h + 2 * b);
    c.fillStyle = g; c.fillRect(-w / 2 - b, -h / 2 - b, w + 2 * b, h + 2 * b);
    c.drawImage(img, -w / 2, -h / 2, w, h);
    c.strokeStyle = INK; c.lineWidth = Math.max(1.5, b * 0.18);
    c.strokeRect(-w / 2 - b, -h / 2 - b, w + 2 * b, h + 2 * b); c.strokeRect(-w / 2, -h / 2, w, h);
    c.restore();
  }
  // a torn edge from a to b: zigzag, the same every frame
  function torn(ax, ay, bx, by, R, amp) {
    const n = 9; c.lineTo(ax, ay);
    for (let i = 1; i < n; i++) {
      const t = i / n, nx = -(by - ay), ny = bx - ax, l = Math.hypot(nx, ny) || 1;
      const j = (R() - 0.5) * 2 * amp;
      c.lineTo(ax + (bx - ax) * t + nx / l * j, ay + (by - ay) * t + ny / l * j);
    }
    c.lineTo(bx, by);
  }
  // a crumpled ball: lumpy outline, crease lines all over
  function ball(x, y, r, rot, seed) {
    const R = rnd(seed); c.save(); c.translate(x, y); c.rotate(rot);
    const n = 13, pts = [];
    for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2, rr = r * (0.74 + R() * 0.36); pts.push([Math.cos(a) * rr, Math.sin(a) * rr]); }
    const outline = () => { c.beginPath(); pts.forEach(([px, py], i) => i ? c.lineTo(px, py) : c.moveTo(px, py)); c.closePath(); };
    outline(); c.fillStyle = kraft; c.fill();
    c.save(); c.clip();
    c.fillStyle = 'rgba(255,240,210,0.25)'; c.beginPath(); c.arc(-r * 0.25, -r * 0.3, r * 0.45, 0, 7); c.fill();
    c.strokeStyle = 'rgba(90,60,30,0.55)'; c.lineWidth = Math.max(1, r * 0.06);
    // creases: from each dent in the outline, in toward the middle and branching
    for (let k = 0; k < n; k += 2) { const [px, py] = pts[k]; c.beginPath(); c.moveTo(px, py); const mx = px * 0.3 + (R() - 0.5) * r * 0.4, my = py * 0.3 + (R() - 0.5) * r * 0.4; c.lineTo(mx, my); c.lineTo(mx + (R() - 0.5) * r * 0.6, my + (R() - 0.5) * r * 0.6); c.stroke(); }
    c.fillStyle = 'rgba(90,60,30,0.18)'; for (let k = 0; k < 3; k++) { c.beginPath(); c.moveTo(0, 0); const a = R() * 6.28; c.lineTo(Math.cos(a) * r, Math.sin(a) * r); c.lineTo(Math.cos(a + 0.6) * r, Math.sin(a + 0.6) * r); c.fill(); }
    c.restore();
    outline(); c.strokeStyle = INK; c.lineWidth = Math.max(1.5, r * 0.08); c.lineJoin = 'round'; c.stroke();
    c.restore();
  }

  // ── one parcel, at time u (seconds at speed 1) ──
  // 0–.45 drops in, wobbles · .45–.65 the twine snaps · .65–1.25 the flaps peel back, creasing
  // 1.2–1.5 each flap is scrunched into a ball and tossed · 1.3–1.7 the painting pops · 1.75–2.2 it flies up to the wall
  function drawParcel(p, dt) {
    const [w, h] = dims(p.img), x = cx(), u = p.u;
    const drop = clamp(u / 0.45), bounce = drop < 1 ? (1 - ease(drop)) * -H * 0.5 + Math.sin(drop * Math.PI) * -20 : 0;
    const wob = u < 0.65 ? Math.sin(u * 30) * 0.03 * clamp((u - 0.3) * 4) : 0;
    const y = cy() + bounce;
    const fly = clamp((u - 1.75) / 0.45), dest = slot(p.idx);
    if (fly > 0) {                                                     // up to its place on the wall
      const e = ease(fly), s = 1 - e * (1 - dest.s / Math.max(w, h));
      const fx = x + (dest.x - x) * e, fy = y + (dest.y - y) * e - Math.sin(e * Math.PI) * H * 0.12;
      framed(p.img, fx, fy, w, h, p.tilt * (1 - e) + Math.sin(e * 9) * 0.05 * (1 - e), s);
      return;
    }
    // the painting under the paper, popping once it's free
    const pop = clamp((u - 1.3) / 0.4), ps = 1 + Math.sin(pop * Math.PI) * 0.12;
    if (u > 0.65) framed(p.img, x, y, w, h, p.tilt + wob, ps);
    if (pop > 0 && pop < 1) {                                          // sparkles
      c.save(); c.strokeStyle = '#e4b84f'; c.lineWidth = 3;
      for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2, r0 = Math.max(w, h) * (0.62 + pop * 0.3), r1 = r0 + 18 * (1 - pop); c.beginPath(); c.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0); c.lineTo(x + Math.cos(a) * r1, y + Math.sin(a) * r1); c.stroke(); }
      c.restore();
    }
    const peel = clamp((u - 0.65) / 0.6);
    if (peel > 0 && !p.tore) { p.tore = true; crinkle(0.45, 0.55); for (let k = 0; k < 14; k++) scraps.push({ x: x + (p.R() - 0.5) * w * 0.4, y: y + (p.R() - 0.5) * h * 0.4, vx: (p.R() - 0.5) * 520, vy: -200 - p.R() * 380, r: 4 + p.R() * 8, a: p.R() * 6, va: (p.R() - 0.5) * 14, life: 1.2 }); }
    // the four flaps: triangles from the parcel's corners to its middle, each folding back over its edge
    const hw = w / 2, hh = h / 2;
    const flaps = [[[-hw, -hh], [hw, -hh]], [[hw, -hh], [hw, hh]], [[hw, hh], [-hw, hh]], [[-hw, hh], [-hw, -hh]]];
    const crumple = clamp((u - 1.2) / 0.3);
    if (crumple > 0 && !p.crumpled) {                                    // scrunch them up and toss them on the heap
      p.crumpled = true; crinkle(0.6, 0.6);
      flaps.forEach(([a, b], k) => {
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, hp = heapAt();
        const n = balls.filter(q => q.landed).length;
        const R = rnd(p.seed + k * 7);
        const tx = hp.x + (R() - 0.5) * Math.min(160, 40 + n * 3), ty = hp.y - Math.min(130, Math.sqrt(n) * 14) * R();
        balls.push({ x: x + mx * 1.5, y: y + my * 1.5, sx: x + mx * 1.5, sy: y + my * 1.5, tx, ty, t: 0, r: Math.max(12, Math.min(w, h) * 0.12) * (0.8 + R() * 0.4), seed: p.seed + k, rot: R() * 6, landed: false });
      });
    }
    if (crumple >= 1) return;
    c.save(); c.translate(x, y); c.rotate(p.tilt + wob);
    flaps.forEach(([a, b], k) => {
      const R = rnd(p.seed + k * 101);
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      const f = clamp(peel * 1.25 - k * 0.08);                          // they go one after another
      const s = -1 + 2 * ease(f);                                       // the apex: middle (−1) → folded out past the edge (+1)
      const ax = mx + mx * s, ay = my + my * s;
      // scrunching: the flap shrinks toward its own middle
      const k2 = 1 - ease(crumple) * 0.85;
      const P = [a, b, [ax, ay]].map(([px, py]) => { const fx = mx * 1.5 + (px - mx * 1.5) * k2, fy = my * 1.5 + (py - my * 1.5) * k2; return crumple > 0 ? [fx, fy] : [px, py]; });
      c.beginPath(); c.moveTo(P[0][0], P[0][1]); c.lineTo(P[1][0], P[1][1]);
      torn(P[1][0], P[1][1], P[2][0], P[2][1], R, f > 0 ? 6 : 0);
      torn(P[2][0], P[2][1], P[0][0], P[0][1], R, f > 0 ? 6 : 0);
      c.closePath();
      c.fillStyle = kraft; c.fill();
      if (s > 0) { c.fillStyle = 'rgba(255,236,200,0.35)'; c.fill(); }   // folded over: its paler inside shows
      // creases: more of them the further it's pulled, and lots once it's being scrunched
      const nC = Math.floor(2 + f * 7 + crumple * 10);
      c.save(); c.clip();
      c.strokeStyle = 'rgba(90,60,30,0.45)'; c.lineWidth = 1.4;
      const CR = rnd(p.seed + k * 13);
      for (let q = 0; q < nC; q++) {
        const t1 = CR(), t2 = CR(), px = P[0][0] + (P[1][0] - P[0][0]) * t1, py = P[0][1] + (P[1][1] - P[0][1]) * t1;
        const qx = P[2][0] + (P[0][0] - P[2][0]) * t2 * 0.6, qy = P[2][1] + (P[0][1] - P[2][1]) * t2 * 0.6;
        c.beginPath(); c.moveTo(px, py); c.lineTo((px + qx) / 2 + (CR() - 0.5) * 20, (py + qy) / 2 + (CR() - 0.5) * 20); c.lineTo(qx, qy); c.stroke();
      }
      c.restore();
      c.strokeStyle = INK; c.lineWidth = 2.5; c.stroke();
    });
    // the twine, and its snap
    const snap = clamp((u - 0.45) / 0.2);
    c.strokeStyle = TWINE; c.lineWidth = 5; c.lineCap = 'round';
    if (snap < 1) {
      const o = ease(snap);
      for (const [x0, y0, x1, y1] of [[-hw, 0, hw, 0], [0, -hh, 0, hh]]) {
        c.beginPath(); c.moveTo(x0, y0); c.quadraticCurveTo(x0 * 0.5, y0 * 0.5 + o * 30, -o * 8, o * 26); c.stroke();
        c.beginPath(); c.moveTo(x1, y1); c.quadraticCurveTo(x1 * 0.5, y1 * 0.5 + o * 30, o * 8, o * 26); c.stroke();
      }
      if (snap === 0) {                                                  // the bow
        c.beginPath(); c.ellipse(-12, -6, 13, 8, 0.5, 0, 7); c.ellipse(12, -6, 13, 8, -0.5, 0, 7); c.stroke();
      }
      // the stamp and the tag
      if (peel === 0) {
        c.save(); c.rotate(-0.18); c.strokeStyle = '#c8402f'; c.fillStyle = '#c8402f'; c.lineWidth = 3;
        const sw = Math.min(140, w * 0.5); c.strokeRect(-hw * 0.9, hh * 0.25, sw, 34);
        c.font = `700 24px ${HAND}`; c.textBaseline = 'middle'; c.fillText('FRAGILE', -hw * 0.9 + 10, hh * 0.25 + 18, sw - 20); c.restore();
        c.save(); c.translate(hw * 0.55, -hh * 0.55); c.rotate(0.25 + Math.sin(u * 6) * 0.08);
        c.fillStyle = '#fbf6ea'; c.strokeStyle = INK; c.lineWidth = 2; c.beginPath(); c.roundRect(-30, -16, 60, 32, 5); c.fill(); c.stroke();
        c.fillStyle = INK; c.font = `400 18px ${HAND}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('No. ' + (p.idx + 1), 0, 1); c.restore();
      }
    }
    c.restore();
    if (snap > 0 && snap < 0.4 && !p.snapped) { p.snapped = true; crinkle(0.12, 0.3); }
  }

  const settled = () => !scraps.length && balls.every(b => b.landed) && hung.every(h => h.t >= 1);
  // (when time's up: put everything where it was going and draw it there, still)
  function settleNow() {
    if (cur) { hung.push({ img: cur.img, i: cur.idx, t: 1 }); cur = null; }
    while (queue.length) { const it = queue.shift(); hung.push({ img: it.img, i: it.slot, t: 1 }); }
    for (const b of balls) { b.x = b.tx; b.y = b.ty; b.landed = true; }
    scraps.length = 0; for (const h of hung) h.t = 1;
    last = performance.now(); frame(last); cancelAnimationFrame(raf);
  }
  let last = performance.now(), raf = 0, done = null;
  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    c.setTransform(DPR, 0, 0, DPR, 0, 0);
    c.fillStyle = '#f6efdf'; c.fillRect(0, 0, W, H);
    // the table edge
    c.fillStyle = '#efe4cc'; c.fillRect(0, H * 0.82, W, H * 0.18); c.strokeStyle = INK; c.lineWidth = 2.5;
    c.beginPath(); c.moveTo(0, H * 0.82); c.lineTo(W, H * 0.82 + 3); c.stroke();
    // title
    c.fillStyle = INK; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.font = `700 ${Math.min(52, W * 0.09)}px ${SCRIPT}`; c.fillText('unwrapping the collection…', W / 2, Math.max(34, H * 0.05));
    // the wall of what's been opened
    for (const hg of hung) { hg.t = Math.min(1, hg.t + dt * 4); const s = slot(hg.i); const [w, h] = dims(hg.img), k = s.s / Math.max(w, h); framed(hg.img, s.x, s.y, w * k, h * k, Math.sin(hg.i * 2.3) * 0.04, 0.6 + 0.4 * ease(hg.t)); }
    // the heap of crumpled paper
    for (const b of balls) {
      if (!b.landed) {
        b.t += dt * 2.2 * Math.max(1, speed * 0.6); const e = clamp(b.t);
        b.x = b.sx + (b.tx - b.sx) * e; b.y = b.sy + (b.ty - b.sy) * e - Math.sin(e * Math.PI) * H * 0.22; b.rot += dt * 9;
        if (e >= 1) b.landed = true;
      }
      ball(b.x, b.y, b.r, b.rot, b.seed);
    }
    // the parcel
    speed = reduce ? 6 : ending ? 3.2 : 1 + queue.length * 0.35;
    if (!cur) next();
    if (cur) {
      cur.u += dt * speed;
      drawParcel(cur, dt);
      if (cur.u >= 2.2) { hung.push({ img: cur.img, i: cur.idx, t: 1 }); next(); }
    }
    // scraps in the air
    for (let i = scraps.length - 1; i >= 0; i--) {
      const s = scraps[i]; s.vy += 900 * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.a += s.va * dt; s.life -= dt;
      if (s.life <= 0) { scraps.splice(i, 1); continue; }
      c.save(); c.translate(s.x, s.y); c.rotate(s.a); c.fillStyle = KRAFT_D; c.beginPath(); c.moveTo(-s.r, -s.r * 0.4); c.lineTo(s.r, -s.r * 0.2); c.lineTo(0, s.r * 0.7); c.closePath(); c.fill(); c.restore();
    }
    // the words under the parcel
    c.fillStyle = INK; c.textAlign = 'center';
    c.font = `400 ${Math.min(24, W * 0.05)}px ${HAND}`;
    const line = cur && cur.u > 1.3 ? `“${cur.title}”` : ending && !cur ? 'all unwrapped! off to the island…' : quip;
    c.fillText(line, W / 2, H * 0.86, W * 0.9);
    c.fillStyle = '#5a4e5e'; c.font = `400 ${Math.min(18, W * 0.04)}px ${HAND}`;
    c.fillText(`${hung.length} of ${total} unwrapped · ${balls.length} balls of paper` + (helped ? '' : ' · click to help!'), W / 2, H * 0.86 + 30, W * 0.94);
    void KRAFT_L;
    // all opened and everything's come to rest: hand over (the build that follows freezes the page
    // for a moment, so it should freeze on a still picture, not on a painting in mid-air)
    if (done && !cur && !queue.length && settled()) { const d = done; done = null; d(); }
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);

  // click to help: tear faster, and the paper crinkles out loud from now on
  cv.addEventListener('pointerdown', () => {
    helped = true;
    try { AC = AC || new (window.AudioContext || window.webkitAudioContext)(); AC.resume(); } catch { /* no sound */ }
    if (cur) cur.u = Math.min(2.2, cur.u + (cur.u < 0.65 ? 0.65 - cur.u : 0.3));
    crinkle(0.25, 0.5);
  });

  return {
    add(img, title) { const slot = added++; if (img && img.width) queue.push({ img, title, slot }); else hung.push({ img: blank(), i: slot, t: 1 }); },
    // everything's loaded: open the backlog in a flurry, then let the last one land (never more than ~2.5 s)
    finish() {
      ending = true;
      while (queue.length > 3) { const it = queue.pop(); hung.push({ img: it.img, i: it.slot, t: 0 }); }   // (they pop onto the wall)
      return new Promise((res) => { done = res; setTimeout(() => { if (done) { done = null; settleNow(); res(); } }, 2500); });
    },
    stop() { cancelAnimationFrame(raf); removeEventListener('resize', size); },
  };
}
function blank() { const b = document.createElement('canvas'); b.width = 4; b.height = 3; const x = b.getContext('2d'); x.fillStyle = '#efe4cc'; x.fillRect(0, 0, 4, 3); return b; }
