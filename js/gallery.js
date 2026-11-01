// ─── INSIDE: the great hall, every painting hung in a real museum frame ───────
// The frames are art-heist's frame kit (museum.js frameKit: swept mouldings, carved corners,
// gilt, walnut, silver), passed { art } so each holds its painting instead of the torn canvas
// the thief left. The room borrows art-heist's crime-scene gallery (rooms.js): damask
// wallpaper, a wainscot with a chair rail, a picture rail with wires down to each frame, a
// basketweave parquet floor, a gilt stanchion or two. A long skylight runs down the middle.
//
// The hall grows to fit the collection: paintings are hung in order along the walls (west
// wall, the far wall, east wall, then both faces of the free-standing partitions down the
// middle), and if they don't fit, the hall is made longer.
//
// Frame: the doorway is at the origin in the front wall, the hall runs to −z. +Y up.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { paint, ink, mergeStatic, PAL } from './style.js';
import { frameKit } from './museum.js';
import { ARTIST, WORKS } from './collection.js';

const W = 16, H = 4.8;                       // hall width and height (the length, D, fits the art)
const EYE = 1.62;                             // a visitor's eye height
const HANG_Y = 1.86;                          // the centre line paintings hang on
const GAP = 0.7, END = 0.6;                  // between frames, and clear of each wall's ends
const PART_L = 6.0, PART_T = 0.32, PART_H = 3.3, PART_GAP = 3.0;   // the partitions
const PART_X = [-3.4, 3.4];                   // two lines of them, an aisle each side and one down the middle
const INKC = '#2a2230';
const HAND = '"Patrick Hand", "Comic Sans MS", cursive', SCRIPT = '"Caveat", "Patrick Hand", cursive';
// every painting keeps one frame, on the wall and in the close look (viewer.js)
export const frameStyle = (i) => STYLES[i % STYLES.length];
const STYLES = [['baroque', 'gold'], ['walnut', 'walnut'], ['deep', 'antique'], ['fluted', 'gold'], ['corners', 'silver'], ['scallop', 'gold'], ['deep', 'walnut'], ['corners', 'antique']];

const rb = (w, h, d, r = 0.03) => new RoundedBoxGeometry(w, h, d, Math.min(w, h, d) > 0.6 ? 2 : 1, Math.max(1e-3, Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3)));
function canvasTex(w, h, draw, repeat = null) {
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  draw(cv.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); }
  return t;
}
// shrink a line of lettering until it fits
function fit(c, text, px, font, maxW, weight = 400) {
  let s = px; c.font = `${weight} ${s}px ${font}`;
  while (c.measureText(text).width > maxW && s > 8) { s -= 1; c.font = `${weight} ${s}px ${font}`; }
  return s;
}

// the painting's frame: outer size for a picture of aspect a, about A m² of canvas showing
export function frameSize(a, A = 0.95) {
  let ih = Math.sqrt(A / a), iw = a * ih;
  const k = Math.min(1, 1.9 / iw, 1.55 / ih); iw *= k; ih *= k;
  // the kit's moulding is 0.18 × the frame's smaller side, each side
  let ow, oh;
  if (iw >= ih) { oh = ih / 0.64; ow = iw + 0.36 * oh; } else { ow = iw / 0.64; oh = ih + 0.36 * ow; }
  return { ow, oh, iw, ih };
}

export function buildGallery(scene, { textures }) {
  // ── 1. plan the hang: how long must the hall be? ──
  const sizes = WORKS.map(w => frameSize(w.w / w.h));
  const need = (i) => sizes[i].ow + GAP;
  // wall runs for a hall of length D: [start x,z] → along a direction, facing a normal
  const runs = (D) => {
    const R = [];
    R.push({ x: -W / 2, z: -0.4, dx: 0, dz: -1, nx: 1, nz: 0, len: D - 0.4 });           // west wall, front to back
    R.push({ x: -W / 2, z: -D, dx: 1, dz: 0, nx: 0, nz: 1, len: W });                    // the far wall
    R.push({ x: W / 2, z: -D, dx: 0, dz: 1, nx: -1, nz: 0, len: D - 0.4 });               // east wall, back to front
    // partitions down the middle: both faces of each
    const n = Math.max(0, Math.floor((D - 4.5 - 2.5) / (PART_L + PART_GAP) + 0.2));
    const span = n * PART_L + (n - 1) * PART_GAP, z0 = -D / 2 - 0.6 + span / 2;
    for (const lx of PART_X) for (let i = 0; i < n; i++) {
      const zf = z0 - i * (PART_L + PART_GAP);                // its front end
      R.push({ x: lx + PART_T / 2, z: zf - PART_L, dx: 0, dz: 1, nx: 1, nz: 0, len: PART_L, part: i });     // east face
      R.push({ x: lx - PART_T / 2, z: zf, dx: 0, dz: -1, nx: -1, nz: 0, len: PART_L, part: i });          // west face
    }
    return { R, n, z0 };
  };
  const tryHang = (D) => {
    const { R } = runs(D), out = [];
    let i = 0;
    for (const r of R) {
      let u = END;
      const row = [];
      while (i < WORKS.length && u + sizes[i].ow <= r.len - END + 1e-6) { row.push({ i, u: u + sizes[i].ow / 2 }); u += need(i); i++; }
      // spread the row out evenly along the wall
      if (row.length) {
        const used = row.reduce((s, p) => s + sizes[p.i].ow, 0), spare = r.len - 2 * END - used, g = spare / (row.length + 1);
        let at = END + g;
        for (const p of row) { p.u = at + sizes[p.i].ow / 2; at += sizes[p.i].ow + g; out.push({ ...p, r }); }
      }
    }
    return i >= WORKS.length ? out : null;
  };
  let D = 16, hang = null;
  while (!(hang = tryHang(D)) && D < 200) D += 1;
  const { n: NPART, z0: PZ0 } = runs(D);

  // ── 2. the room ──
  const room = new THREE.Group(); scene.add(room);
  const solid = new THREE.Group(); room.add(solid);           // inked, then merged
  const put = (geo, mat, x, y, z, rot, parent = solid) => {
    const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); if (rot) m.rotation.set(...rot); parent.add(m); return m;
  };
  const flat = (w, h, mat, x, y, z, rot, parent = room) => { const m = put(new THREE.PlaneGeometry(w, h), mat, x, y, z, rot, parent); m.userData.noInk = true; return m; };

  scene.add(new THREE.HemisphereLight(0xfff6e8, 0xb7a9a0, 1.25));
  const sun = new THREE.DirectionalLight(0xfff1dc, 0.9); sun.position.set(3, 10, 2); scene.add(sun);
  scene.background = new THREE.Color(0xf3ead7);

  // damask wallpaper (rooms.js 'gallery' theme), wainscot, parquet
  const damask = (rep) => canvasTex(256, 256, (c, w, h) => {
    c.fillStyle = '#c9bbd9'; c.fillRect(0, 0, w, h);
    const motif = (x, y) => {
      c.fillStyle = 'rgba(110,80,140,0.26)';
      c.beginPath(); c.ellipse(x, y, 18, 42, 0, 0, 7); c.fill();
      for (const s of [-1, 1]) { c.beginPath(); c.ellipse(x + s * 26, y + 10, 10, 26, s * 0.6, 0, 7); c.fill(); c.beginPath(); c.arc(x + s * 14, y - 40, 8, 0, 7); c.fill(); }
      c.fillStyle = 'rgba(228,184,79,0.35)'; c.beginPath(); c.arc(x, y, 6, 0, 7); c.fill();
    };
    for (const ox of [-w, 0, w]) for (const oy of [-h, 0, h]) { motif(w * 0.25 + ox, h * 0.25 + oy); motif(w * 0.75 + ox, h * 0.75 + oy); }
  }, rep);
  const wallMat = (len) => paint(0xffffff, { map: damask([len / 1.1, (H - 1.0) / 1.1]), hatch: 0, unique: true });
  const panel = paint(0x5d4a6e), trim = paint(0xfffaf0), gilt = paint(PAL.gold), dark = paint(0x2a2230, { hatch: 0 });
  const floorTex = canvasTex(256, 256, (c, w, h) => {
    const cols = ['#b58a5e', '#a77c52', '#c09468', '#9c7048'], cell = w / 4;
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      const vert = (i + j) % 2, x = i * cell, y = j * cell;
      for (let k = 0; k < 3; k++) {
        c.fillStyle = cols[(i * 3 + j * 5 + k) % cols.length];
        if (vert) c.fillRect(x + k * cell / 3, y, cell / 3, cell); else c.fillRect(x, y + k * cell / 3, cell, cell / 3);
        c.strokeStyle = 'rgba(40,24,16,0.35)'; c.lineWidth = 1.5;
        if (vert) c.strokeRect(x + k * cell / 3, y, cell / 3, cell); else c.strokeRect(x, y + k * cell / 3, cell, cell / 3);
      }
    }
  }, [W / 1.4, D / 1.4]);
  const floor = flat(W, D, paint(0xffffff, { map: floorTex, hatch: 0 }), 0, 0, -D / 2, [-Math.PI / 2, 0, 0]);
  floor.name = 'floor';
  // a long runner down each aisle
  const runner = canvasTex(64, 256, (c, w, h) => {
    c.fillStyle = '#8e3b3f'; c.fillRect(0, 0, w, h);
    c.fillStyle = '#e4b84f'; c.fillRect(4, 0, 3, h); c.fillRect(w - 7, 0, 3, h);
    c.fillStyle = 'rgba(228,184,79,0.4)'; for (let y = 16; y < h; y += 32) { c.beginPath(); c.moveTo(w / 2, y - 8); c.lineTo(w / 2 + 8, y); c.lineTo(w / 2, y + 8); c.lineTo(w / 2 - 8, y); c.fill(); }
  }, [1, D / 2.2]);
  for (const x of NPART ? [-(W / 2 + PART_X[1]) / 2, 0, (W / 2 + PART_X[1]) / 2] : [0]) {
    const r = flat(1.4, D - 1.2, paint(0xffffff, { map: runner, hatch: 0, unique: true }), x, 0.006, -D / 2 - 0.3, [-Math.PI / 2, 0, 0]);
    r.renderOrder = 1;
  }

  // a wall: wallpaper above the wainscot, the panelling, chair rail, skirting, picture rail, cornice
  const wall = (cx, cz, len, ry) => {
    const g = new THREE.Group(); g.position.set(cx, 0, cz); g.rotation.y = ry; room.add(g);
    flat(len, H - 1.0, wallMat(len), 0, 1.0 + (H - 1.0) / 2, 0, null, g);
    const sg = new THREE.Group(); g.add(sg);
    put(rb(len, 1.0, 0.06, 0.01), panel, 0, 0.5, 0.03, null, sg);
    put(rb(len, 0.07, 0.1, 0.02), trim, 0, 1.0, 0.05, null, sg);                // chair rail
    put(rb(len, 0.16, 0.08, 0.02), trim, 0, 0.08, 0.06, null, sg);              // skirting
    put(rb(len, 0.05, 0.06, 0.015), gilt, 0, 3.25, 0.03, null, sg);             // picture rail
    put(rb(len, 0.22, 0.16, 0.04), trim, 0, H - 0.11, 0.08, null, sg);          // cornice
    // raised panels on the wainscot
    const n = Math.max(1, Math.round(len / 1.4)), pw = len / n;
    for (let k = 0; k < n; k++) put(rb(pw - 0.24, 0.62, 0.03, 0.012), paint(0x6b5880), -len / 2 + pw * (k + 0.5), 0.52, 0.07, null, sg);
    solid.attach(sg);
    return g;
  };
  wall(-W / 2, -D / 2, D, Math.PI / 2);            // west
  wall(W / 2, -D / 2, D, -Math.PI / 2);            // east
  wall(0, -D, W, 0);                               // far
  // the front wall, either side of the doorway (it faces in: −z is inside, so turn it round)
  const DW = 2.0, DH = 3.0;
  for (const s of [-1, 1]) wall(s * (DW / 2 + (W - DW) / 4), 0, (W - DW) / 2, Math.PI);
  {
    // over the doorway: wallpaper, and a gilt sign
    flat(DW, H - DH, wallMat(DW), 0, DH + (H - DH) / 2, -0.001, [0, Math.PI, 0]);
    put(rb(DW + 0.5, 0.25, 0.22, 0.05), trim, 0, DH + 0.12, -0.08);
    for (const s of [-1, 1]) put(rb(0.22, DH, 0.24, 0.05), trim, s * (DW / 2 + 0.09), DH / 2, -0.08);
    // the bright day outside, through the doorway
    const out = canvasTex(128, 192, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#a9c8d8'); gr.addColorStop(0.62, '#f6e7cc'); gr.addColorStop(0.63, '#b4c58f'); gr.addColorStop(1, '#93ad74');
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = '#e6d6b8'; c.beginPath(); c.moveTo(w * 0.42, h * 0.63); c.lineTo(w * 0.58, h * 0.63); c.lineTo(w * 0.9, h); c.lineTo(w * 0.1, h); c.fill();
      c.fillStyle = '#6d9358'; for (const x of [0.15, 0.85]) { c.beginPath(); c.ellipse(w * x, h * 0.5, 8, 30, 0, 0, 7); c.fill(); }
    });
    const doorway = flat(DW, DH, new THREE.MeshBasicMaterial({ map: out, toneMapped: false }), 0, DH / 2, 0.25, [0, Math.PI, 0]);
    doorway.name = 'exit';
    // the welcome sign over the door, inside
    flat(1.9, 0.42, paint(0xffffff, { map: canvasTex(640, 140, (c, w, h) => {
      c.fillStyle = '#f6efdf'; c.strokeStyle = INKC; c.lineWidth = 5; c.beginPath(); c.roundRect(6, 6, w - 12, h - 12, 26); c.fill(); c.stroke();
      c.fillStyle = INKC; c.textAlign = 'center'; c.textBaseline = 'middle'; fit(c, 'way out · back to the island', 52, HAND, w - 60); c.fillText('way out · back to the island', w / 2, h / 2 + 2);
    }), hatch: 0 }), 0, DH + 0.62, -0.2, [0, Math.PI, 0]);
  }

  // the ceiling, and a long skylight down the middle
  {
    const ceil = flat(W, D, paint(0xf6efdf, { hatch: 0.3, side: THREE.DoubleSide }), 0, H, -D / 2, [Math.PI / 2, 0, 0]);
    void ceil;
    const SW = 3.2, sky = canvasTex(64, 256, (c, w, h) => {
      const gr = c.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, '#cfe3ec'); gr.addColorStop(0.5, '#f4fbfd'); gr.addColorStop(1, '#cfe3ec');
      c.fillStyle = gr; c.fillRect(0, 0, w, h);
      c.fillStyle = 'rgba(255,255,255,0.8)'; c.beginPath(); c.ellipse(w * 0.4, h * 0.3, 14, 30, 0, 0, 7); c.fill();
    }, [1, D / 6]);
    flat(SW, D - 1.6, new THREE.MeshBasicMaterial({ map: sky, toneMapped: false }), 0, H - 0.01, -D / 2, [Math.PI / 2, 0, 0]);
    for (const s of [-1, 1]) put(rb(0.18, 0.2, D - 1.4, 0.04), trim, s * (SW / 2 + 0.09), H - 0.1, -D / 2);
    for (let z = -1.6; z > -D + 0.8; z -= 1.4) put(rb(SW, 0.06, 0.06, 0.02), paint(0x8a8392), 0, H - 0.05, z);
  }

  // the partitions: free-standing walls down the middle, wallpapered both faces
  const cols = [];      // walk-blockers, [x0, x1, z0, z1]
  for (let i = 0; i < NPART; i++) {
    const zf = PZ0 - i * (PART_L + PART_GAP), zc = zf - PART_L / 2;
    for (const lx of PART_X) {
      put(rb(PART_T, PART_H, PART_L, 0.04), paint(0xc9bbd9), lx, PART_H / 2, zc);
      for (const s of [-1, 1]) flat(PART_L - 0.02, PART_H - 1.1, wallMat(PART_L), lx + s * (PART_T / 2 + 0.003), 1.0 + (PART_H - 1.1) / 2 + 0.05, zc, [0, s * Math.PI / 2, 0]);
      put(rb(PART_T + 0.12, 0.16, PART_L + 0.12, 0.03), trim, lx, PART_H + 0.06, zc);       // a cap
      put(rb(PART_T + 0.1, 1.0, PART_L + 0.06, 0.02), panel, lx, 0.5, zc);                  // wainscot
      put(rb(PART_T + 0.16, 0.07, PART_L + 0.1, 0.02), trim, lx, 1.0, zc);                  // chair rail
      put(rb(PART_T + 0.14, 0.16, PART_L + 0.1, 0.02), trim, lx, 0.08, zc);                 // skirting
      cols.push([lx - PART_T / 2 - 0.45, lx + PART_T / 2 + 0.45, zc - PART_L / 2 - 0.45, zc + PART_L / 2 + 0.45]);
    }
    // a bench in the gap after it (facing the art across the aisle)
    if (i < NPART - 1) {
      const bz = zf - PART_L - PART_GAP / 2;
      bench(put, bz);
      cols.push([-1.1, 1.1, bz - 0.5, bz + 0.5]);
    }
  }
  if (!NPART) { bench(put, -D / 2); cols.push([-1.1, 1.1, -D / 2 - 0.5, -D / 2 + 0.5]); }
  // potted palms in the corners
  for (const [x, z] of [[-W / 2 + 0.7, -D + 0.7], [W / 2 - 0.7, -D + 0.7], [-W / 2 + 0.7, -0.8], [W / 2 - 0.7, -0.8]]) {
    palm(put, x, z);
    cols.push([x - 0.5, x + 0.5, z - 0.5, z + 0.5]);
  }

  // the artist's name, lettered on the far wall above the hang
  flat(6.2, 0.95, paint(0xffffff, { map: canvasTex(1400, 214, (c, w, h) => {
    c.clearRect(0, 0, w, h);
    c.textAlign = 'center'; c.textBaseline = 'middle';
    fit(c, ARTIST.name, 150, SCRIPT, w - 80, 700); c.fillStyle = '#fff7e6'; c.fillText(ARTIST.name, w / 2 + 4, h * 0.42 + 4);
    c.fillStyle = INKC; c.fillText(ARTIST.name, w / 2, h * 0.42);
    fit(c, ARTIST.tagline, 46, HAND, w - 200); c.fillStyle = '#5a4e5e'; c.fillText('— ' + ARTIST.tagline + ' —', w / 2, h * 0.86);
  }), hatch: 0, opacity: 0.999 }), 0, 3.85, -D + 0.04);

  // ── 3. the paintings ──
  const FG = new THREE.Group(); room.add(FG);
  const { ornateFrame } = frameKit({ S: (col, o = {}) => paint(col, { map: o.map, side: o.side, hatch: o.map ? 0 : 0.35 }), GOLD: gilt, lite: true });
  const wireM = paint(0x8a8392, { hatch: 0 }), brass = paint(0xc89b45), lampGlow = paint(0xfff3d6, { emissive: 0xffe2a8, hatch: 0 });
  const pieces = [];
  const _Y = new THREE.Vector3(0, 1, 0);
  hang.forEach(({ i, u, r }, k) => {
    const work = WORKS[i], sz = sizes[i];
    const x = r.x + r.dx * u + r.nx * 0.07, z = r.z + r.dz * u + r.nz * 0.07;
    const ry = Math.atan2(r.nx, r.nz);
    const g = new THREE.Group(); g.position.set(x, HANG_Y, z); g.rotation.y = ry; FG.add(g);
    const [style, finish] = frameStyle(i);
    const tex = textures.get(work.file);
    const F = ornateFrame(sz.ow, sz.oh, g, style, { finish, art: tex });
    const canvas = F.userData.canvas;
    canvas.userData.work = i;
    // the wires up to the picture rail
    const top = sz.oh / 2, hook = new THREE.Vector3(0, 3.22 - HANG_Y, -0.02);
    for (const s of [-1, 1]) {
      const a = new THREE.Vector3(s * sz.ow * 0.2, top - 0.03, -0.03);
      const wire = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, a.distanceTo(hook), 4), wireM);
      wire.position.copy(a).add(hook).multiplyScalar(0.5); wire.quaternion.setFromUnitVectors(_Y, hook.clone().sub(a).normalize());
      wire.userData.noInk = true; g.add(wire);
    }
    // a brass picture light over it
    {
      const lw = Math.min(0.9, sz.ow * 0.55);
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.3, 6), brass); arm.position.set(0, top + 0.1, 0.12); arm.rotation.x = 1.1; g.add(arm);
      const hood = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, lw, 14, 1, false, 0, Math.PI), brass);
      hood.rotation.z = Math.PI / 2; hood.rotation.x = 0.5; hood.position.set(0, top + 0.2, 0.25); g.add(hood);
      const bulb = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, lw * 0.9, 8), lampGlow);
      bulb.rotation.z = Math.PI / 2; bulb.position.set(0, top + 0.18, 0.26); bulb.userData.noInk = true; g.add(bulb);
    }
    // its card on the wall beside it
    const card = canvasTex(320, 200, (c, w, h) => {
      c.fillStyle = '#fbf6ea'; c.fillRect(0, 0, w, h);
      c.strokeStyle = INKC; c.lineWidth = 5; c.strokeRect(3, 3, w - 6, h - 6);
      c.fillStyle = INKC; c.textBaseline = 'alphabetic';
      fit(c, work.title, 38, SCRIPT, w - 36, 700); c.fillText(work.title, 18, 52);
      c.font = `400 21px ${HAND}`; c.fillStyle = '#5a4e5e';
      c.fillText(ARTIST.name + (work.year ? ', ' + work.year : ''), 18, 86);
      if (work.medium) c.fillText(work.medium, 18, 112);
      c.fillStyle = '#e8604c'; c.fillRect(18, h - 52, 46, 4);
      c.font = `400 17px ${HAND}`; c.fillStyle = '#8a7e8e'; c.fillText('No. ' + (i + 1) + ' · click to look closer', 18, h - 24);
    });
    const side = sz.ow / 2 + 0.36;
    const cg = new THREE.Group(); cg.position.set(side, 1.4 - HANG_Y, -0.04); g.add(cg);
    const back = new THREE.Mesh(rb(0.34, 0.22, 0.015, 0.004), paint(0xfbf6ea)); cg.add(back);
    const face = new THREE.Mesh(new THREE.PlaneGeometry(0.32, 0.2), paint(0xffffff, { map: card, hatch: 0, unique: true }));
    face.position.z = 0.009; face.userData.noInk = true; face.userData.work = i; cg.add(face);
    const normal = new THREE.Vector3(r.nx, 0, r.nz);
    pieces.push({ i, canvas, card: face, center: new THREE.Vector3(x, HANG_Y, z), normal, size: sz });
  });
  FG.traverse(o => { if (o.isMesh && Math.max(o.scale.x, o.scale.y) < 0.012) o.userData.noInk = true; });   // (beads and pearls: too small to outline)
  ink(FG, 'mid');
  // merge the frames into a few draws, but keep each painting and card its own mesh (they're clicked)
  const keep = [];
  FG.traverse(o => { if (o.isMesh && (o.userData.painting || o.userData.work != null)) keep.push(o); });
  mergeStatic(FG, keep);

  ink(solid, 'mid');
  mergeStatic(solid);

  // ── 4. walking about ──
  const bounds = { x0: -W / 2 + 0.55, x1: W / 2 - 0.55, z0: -D + 0.55, z1: -0.5 };
  const blocked = (x, z) => x < bounds.x0 || x > bounds.x1 || z < bounds.z0 || z > bounds.z1 || cols.some(([a, b, c, d]) => x > a && x < b && z > c && z < d);
  // where to stand to look at painting k: back from it along its normal, clear of everything
  const viewSpot = (p) => {
    for (let d = 2.6; d > 1.2; d -= 0.2) {
      const s = p.center.clone().addScaledVector(p.normal, d);
      if (!blocked(s.x, s.z)) return s.setY(EYE);
    }
    return p.center.clone().addScaledVector(p.normal, 1.2).setY(EYE);
  };
  return { D, W, H, EYE, pieces, blocked, viewSpot, floor, exit: scene.getObjectByName('exit'), start: new THREE.Vector3(0, EYE, -1.6) };
}

// a museum bench: a padded seat on gilt legs
function bench(put, z) {
  const wood = paint(0x6b4a33), pad = paint(0x8e3b3f);
  put(rb(2.0, 0.08, 0.6, 0.03), wood, 0, 0.42, z);
  put(rb(1.9, 0.1, 0.52, 0.05), pad, 0, 0.5, z);
  for (const sx of [-0.85, 0.85]) for (const sz of [-0.22, 0.22]) put(new THREE.CylinderGeometry(0.035, 0.025, 0.4, 10), paint(PAL.gold), sx, 0.2, z + sz);
}
// a potted palm
function palm(put, x, z) {
  const pot = new THREE.LatheGeometry([[0.001, 0], [0.26, 0], [0.32, 0.5], [0.36, 0.55], [0.001, 0.55]].map(([a, b]) => new THREE.Vector2(a, b)), 20);
  put(pot, paint(0xb9764a), x, 0, z);
  put(new THREE.CylinderGeometry(0.04, 0.06, 1.3, 8), paint(PAL.bark), x, 1.1, z);
  const leaf = paint(0x6d9358, { side: THREE.DoubleSide });
  for (let k = 0; k < 7; k++) {
    const a = k / 7 * Math.PI * 2;
    const g = new THREE.SphereGeometry(0.5, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2); g.scale(0.32, 0.12, 1);
    const m = put(g, leaf, x + Math.sin(a) * 0.4, 1.72, z + Math.cos(a) * 0.4, [0.5, a, 0]);
    m.rotation.order = 'YXZ'; m.rotation.set(0.55, a, 0);
  }
}
