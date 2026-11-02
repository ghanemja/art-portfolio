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
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { paint, ink, mergeStatic, PAL } from './style.js';
import { frameKit } from './museum.js';
import { realTree } from './foliage.js';
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


// ── MOULDINGS: a profile swept straight along a run, the way a joiner's moulding plane cuts it ──
// prof: [[out, up], …] from the wall at the bottom round to the wall at the top; a point given
// twice creases there, everywhere else the shading runs smooth across the curves. Swept along
// local x (len, centred), out is local +z. The open ends get the profile as a cap.
const arc = (cz, cy, r, a0, a1, n = 6) => Array.from({ length: n + 1 }, (_, k) => { const a = a0 + (a1 - a0) * k / n; return [cz + Math.cos(a) * r, cy + Math.sin(a) * r]; });
function sweep(prof, len, mat, off = 0) {
  const pos = [], idx = [];
  for (const [z, y] of prof) pos.push(-len / 2, y, z + off, len / 2, y, z + off);
  for (let j = 0; j < prof.length - 1; j++) { const a = j * 2, b = a + 1, c = a + 2, d = a + 3; idx.push(a, b, c, b, d, c); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat);
  const sh = new THREE.Shape(prof.map(([z, y]) => new THREE.Vector2(z + off, y)));     // the end caps
  for (const sgn of [-1, 1]) {
    const cg = new THREE.ShapeGeometry(sh); cg.rotateY(sgn > 0 ? -Math.PI / 2 : Math.PI / 2);
    if (sgn > 0) cg.scale(1, 1, -1);
    const cap = new THREE.Mesh(cg, mat); cap.position.x = sgn * len / 2; cap.userData.noInk = true; m.add(cap);
  }
  return m;
}
// a ceiling rosette: petals round a boss, lathed
const ROSETTE = (() => { const pts = [[0.001, 0], [0.2, 0], [0.19, -0.015], [0.16, -0.02], [0.15, -0.035], [0.11, -0.04], [0.1, -0.06], [0.05, -0.07], [0.03, -0.09], [0.001, -0.095]].reverse().map(([x, y]) => new THREE.Vector2(x, y));   // (centre first: its faces look down)
  const g = new THREE.LatheGeometry(pts, 24), p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const a = Math.atan2(p.getZ(i), p.getX(i)), r = Math.hypot(p.getX(i), p.getZ(i)), k = 1 + 0.1 * Math.cos(a * 8) * Math.min(1, r / 0.1); p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * k); }
  g.computeVertexNormals(); return g; })();
const SKIRT = [[0, 0], [0.045, 0], [0.045, 0], [0.045, 0.014], [0.038, 0.022], [0.038, 0.022], [0.034, 0.19], [0.034, 0.19],
  [0.04, 0.198], ...arc(0.04, 0.214, 0.016, -Math.PI / 2, Math.PI / 2, 5).slice(1), [0.034, 0.234], [0.034, 0.234],
  ...arc(0.034, 0.262, 0.028, -Math.PI / 2, 0, 4).slice(1).map(([z, y]) => [0.068 - z, y]), [0.012, 0.286], [0.012, 0.3], [0.012, 0.3], [0, 0.3]];
const CHAIR = [[0, 0.95], [0.018, 0.954], [0.028, 0.966], [0.028, 0.966], ...arc(0.03, 0.994, 0.024, -Math.PI / 2, Math.PI / 2, 7),
  [0.028, 1.022], [0.028, 1.022], [0.03, 1.034], [0.02, 1.048], [0, 1.056]];
const RAIL = [[0, 3.19], [0.012, 3.196], [0.026, 3.214], [0.031, 3.236], [0.024, 3.256], [0.012, 3.266], [0, 3.27]];
// the crown: bed moulding, a fascia for the dentils, the corona, a bead, and a deep ogee up to the ceiling
const crown = (H) => {
  const y0 = H - 0.58, P = [[0, y0], [0.014, y0 + 0.004], ...arc(0.016, y0 + 0.022, 0.016, -Math.PI / 2, Math.PI / 2, 5).slice(1), [0.016, y0 + 0.038], [0.016, y0 + 0.038],
    [0.05, y0 + 0.042], [0.05, y0 + 0.042], [0.05, y0 + 0.17], [0.05, y0 + 0.17], [0.13, y0 + 0.174], [0.13, y0 + 0.174], [0.13, y0 + 0.25], [0.13, y0 + 0.25],
    ...arc(0.135, y0 + 0.268, 0.018, -Math.PI / 2, Math.PI / 2, 5).slice(1), [0.15, y0 + 0.288], [0.15, y0 + 0.288]];
  for (let k = 1; k <= 10; k++) { const t = k / 10; P.push([0.15 + 0.3 * t, y0 + 0.29 + (H - y0 - 0.32) * (0.5 - 0.5 * Math.cos(Math.PI * t))]); }
  P.push([0.45, H - 0.03], [0.45, H - 0.03], [0.47, H - 0.01], [0.47, H], [0.47, H], [0, H]);
  return P;
};

export function buildGallery(scene, { textures }) {
  // ── 1. plan the hang: how long must the hall be? ──
  // paintings in a group (collection.js group: '…') hang together as a little 2×2 collage,
  // smaller frames close together, as ONE unit on the wall; everything else is a unit of one
  const sizes = WORKS.map(w => frameSize(w.w / w.h, w.group ? 0.26 : 0.95));
  const units = [], seen = new Set();
  WORKS.forEach((w, i) => {
    if (seen.has(i)) return;
    const members = w.group ? WORKS.map((v, j) => v.group === w.group ? j : -1).filter(j => j >= 0) : [i];
    members.forEach(j => seen.add(j));
    if (members.length === 1) { units.push({ members, ow: sizes[i].ow, oh: sizes[i].oh, offs: [[0, 0]] }); return; }
    const G = 0.1, rows = [];
    for (let k = 0; k < members.length; k += 2) rows.push(members.slice(k, k + 2));
    const rw = rows.map(r => r.reduce((t, j) => t + sizes[j].ow, 0) + G * (r.length - 1)), rh = rows.map(r => Math.max(...r.map(j => sizes[j].oh)));
    const ow = Math.max(...rw), oh = rh.reduce((t, h) => t + h, 0) + G * (rows.length - 1), offs = [];
    let y = oh / 2;
    rows.forEach((r, ri) => {
      let x = -rw[ri] / 2; y -= rh[ri] / 2;
      for (const j of r) { offs.push([x + sizes[j].ow / 2, y]); x += sizes[j].ow + G; }
      y -= rh[ri] / 2 + G;
    });
    units.push({ members, ow, oh, offs, title: w.groupTitle || w.group });
  });
  const need = (n) => units[n].ow + GAP;
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
      while (i < units.length && u + units[i].ow <= r.len - END + 1e-6) { row.push({ n: i, u: u + units[i].ow / 2 }); u += need(i); i++; }
      // spread the row out evenly along the wall
      if (row.length) {
        const used = row.reduce((s, p) => s + units[p.n].ow, 0), spare = r.len - 2 * END - used, g = spare / (row.length + 1);
        let at = END + g;
        for (const p of row) { p.u = at + units[p.n].ow / 2; at += units[p.n].ow + g; out.push({ ...p, r }); }
      }
    }
    return i >= units.length ? out : null;
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
  const ivory = paint(0xfffaf0), ivoryHi = paint(0xf3e6c9);
  const CROWN = crown(H);
  const wall = (cx, cz, len, ry) => {
    const g = new THREE.Group(); g.position.set(cx, 0, cz); g.rotation.y = ry; room.add(g);
    flat(len, H - 1.0, wallMat(len), 0, 1.0 + (H - 1.0) / 2, 0, null, g);
    const sg = new THREE.Group(); g.add(sg);
    put(rb(len, 1.0, 0.06, 0.01), panel, 0, 0.5, 0.03, null, sg);              // the wainscot's ground
    sg.add(sweep(SKIRT, len, ivory, 0.06));                                     // skirting: plinth, a bead, an ogee
    sg.add(sweep(CHAIR, len, ivory, 0.06));                                     // chair rail: a fat bead between fillets
    sg.add(sweep(RAIL, len, gilt));                                             // picture rail, gilt
    sg.add(sweep(CROWN, len, ivory));                                           // the crown cornice
    // dentils under the corona, a row of little blocks the length of the wall
    {
      const dg = [], n = Math.floor((len - 0.1) / 0.08);
      for (let k = 0; k < n; k++) { const b = new THREE.BoxGeometry(0.042, 0.075, 0.05); b.translate(-len / 2 + 0.09 + k * 0.08, H - 0.58 + 0.105, 0.075); dg.push(b); }
      if (dg.length) put(mergeGeometries(dg), ivoryHi, 0, 0, 0, null, sg);
    }
    // raised and fielded panels on the wainscot, each framed in a bolection moulding
    const n = Math.max(1, Math.round(len / 1.3)), pw = len / n;
    for (let k = 0; k < n; k++) {
      const px = -len / 2 + pw * (k + 0.5), fw = pw - 0.3, fy = 0.6, fh = 0.5;
      put(rb(fw, fh, 0.03, 0.012), paint(0x6b5880), px, fy, 0.075, null, sg);                     // the raised field
      put(rb(fw - 0.12, fh - 0.12, 0.012, 0.004), paint(0x75628a), px, fy, 0.094, null, sg);       // its bevel
      for (const sy of [-1, 1]) put(rb(fw + 0.1, 0.05, 0.05, 0.02), ivory, px, fy + sy * (fh / 2 + 0.025), 0.085, null, sg);   // the frame
      for (const sx of [-1, 1]) put(rb(0.05, fh + 0.15, 0.05, 0.02), ivory, px + sx * (fw / 2 + 0.025), fy, 0.085, null, sg);
    }
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
    // (flush behind the jambs and a little bigger than the opening, so the frame overlaps its edges: set back
    // 0.25 outside the wall it left a gap round it where the bare background showed, a white border)
    const doorway = flat(DW + 0.2, DH + 0.15, new THREE.MeshBasicMaterial({ map: out, toneMapped: false }), 0, (DH + 0.15) / 2, 0.035, [0, Math.PI, 0]);
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
    // coffers either side of the skylight: moulded beams across and along, a gilt rosette in each
    const bx0 = SW / 2 + 0.18, bx1 = W / 2 - 0.47, BEAM = 2.6;
    const zs = []; for (let z = -0.6; z > -D + 0.4; z -= BEAM) zs.push(z);
    for (const sx of [-1, 1]) {
      const xm = sx * (bx0 + bx1) / 2, wspan = bx1 - bx0;
      put(rb(0.2, 0.2, D - 1.0, 0.05), ivory, sx * ((bx0 + bx1) / 2), H - 0.1, -D / 2);              // a beam along the middle of the coffers
      for (const z of zs) put(rb(wspan, 0.2, 0.2, 0.05), ivory, xm, H - 0.1, z);                  // beams across
      for (let k = 0; k < zs.length - 1; k++) {
        const zc = (zs[k] + zs[k + 1]) / 2;
        for (const q of [-1, 1]) {
          const cx = xm + q * wspan / 4, cw = wspan / 2 - 0.3, cd = BEAM - 0.3;
          // a little moulded frame inside each coffer, and the rosette at its heart
          for (const sz2 of [-1, 1]) put(rb(cw, 0.045, 0.045, 0.015), ivoryHi, cx, H - 0.03, zc + sz2 * cd / 2);
          for (const sx2 of [-1, 1]) put(rb(0.045, 0.045, cd, 0.015), ivoryHi, cx + sx2 * cw / 2, H - 0.03, zc);
          put(ROSETTE, gilt, cx, H - 0.005, zc);
        }
      }
    }
  }
  // fluted pilasters in the corners and either side of the door: a base, the shaft, a capital
  for (const [x, z, ry] of [[-W / 2, -D, Math.PI / 4], [W / 2, -D, -Math.PI / 4], [-W / 2, 0, 3 * Math.PI / 4], [W / 2, 0, -3 * Math.PI / 4], [-1.55, 0, Math.PI], [1.55, 0, Math.PI]]) {
    const pg = new THREE.Group(); pg.position.set(x, 0, z); pg.rotation.y = ry; solid.add(pg);
    put(rb(0.5, 0.32, 0.16, 0.03), ivory, 0, 0.16, 0.08, null, pg);
    put(rb(0.4, 3.75, 0.1, 0.03), ivory, 0, 0.32 + 1.875, 0.06, null, pg);
    for (let f = -2; f <= 2; f++) put(rb(0.035, 3.45, 0.03, 0.012), ivoryHi, f * 0.07, 0.32 + 1.875, 0.115, null, pg);
    put(rb(0.5, 0.1, 0.16, 0.03), ivory, 0, 4.12, 0.08, null, pg);
    put(rb(0.46, 0.12, 0.14, 0.04), gilt, 0, 4.02, 0.08, null, pg);
    sconce(put, pg, 0, 2.35, 0.11, 0);                                       // and a sconce on each
  }

  // the partitions: free-standing walls down the middle, wallpapered both faces
  const cols = [];      // walk-blockers, [x0, x1, z0, z1]
  for (let i = 0; i < NPART; i++) {
    const zf = PZ0 - i * (PART_L + PART_GAP), zc = zf - PART_L / 2;
    for (const lx of PART_X) {
      put(rb(PART_T, PART_H, PART_L, 0.04), paint(0xc9bbd9), lx, PART_H / 2, zc);
      for (const s of [-1, 1]) flat(PART_L - 0.02, PART_H - 1.1, wallMat(PART_L), lx + s * (PART_T / 2 + 0.003), 1.0 + (PART_H - 1.1) / 2 + 0.05, zc, [0, s * Math.PI / 2, 0]);
      put(rb(PART_T + 0.1, 1.0, PART_L + 0.06, 0.02), panel, lx, 0.5, zc);                  // wainscot
      put(rb(PART_T + 0.2, 0.08, PART_L + 0.2, 0.03), ivory, lx, PART_H + 0.13, zc);        // a cornice cap…
      put(rb(PART_T + 0.12, 0.06, PART_L + 0.12, 0.02), gilt, lx, PART_H + 0.06, zc);       // …on a gilt band
      // the same mouldings as the walls, run along both faces
      for (const sd of [-1, 1]) {
        const fg = new THREE.Group(); fg.position.set(lx + sd * (PART_T / 2 + 0.05), 0, zc); fg.rotation.y = sd * Math.PI / 2; solid.add(fg);
        fg.add(sweep(SKIRT, PART_L + 0.06, ivory, 0.0)); fg.add(sweep(CHAIR, PART_L + 0.06, ivory, 0.0));
        const n = 4, pw = PART_L / n;
        for (let k = 0; k < n; k++) {
          const px = -PART_L / 2 + pw * (k + 0.5), fw = pw - 0.26, fy = 0.6, fh = 0.5;
          put(rb(fw, fh, 0.03, 0.012), paint(0x6b5880), px, fy, 0.015, null, fg);
          for (const sy of [-1, 1]) put(rb(fw + 0.1, 0.05, 0.05, 0.02), ivory, px, fy + sy * (fh / 2 + 0.025), 0.025, null, fg);
          for (const sx of [-1, 1]) put(rb(0.05, fh + 0.15, 0.05, 0.02), ivory, px + sx * (fw / 2 + 0.025), fy, 0.025, null, fg);
        }
      }
      cols.push([lx - PART_T / 2 - 0.45, lx + PART_T / 2 + 0.45, zc - PART_L / 2 - 0.45, zc + PART_L / 2 + 0.45]);
      for (const e of [-1, 1]) sconce(put, solid, lx, 2.25, zc + e * (PART_L / 2 + 0.03), e > 0 ? 0 : Math.PI);   // a sconce on each end
    }
    // a bench in the gap after it (facing the art across the aisle)
    if (i < NPART - 1) {
      const bz = zf - PART_L - PART_GAP / 2;
      bench(put, bz);
      cols.push([-1.1, 1.1, bz - 0.5, bz + 0.5]);
    }
  }
  if (!NPART) { bench(put, -D / 2); cols.push([-1.1, 1.1, -D / 2 - 0.5, -D / 2 + 0.5]); }
  // potted trees in the corners: little indoor trees with real leaves (foliage.js), in glazed urns
  for (const [k, [x, z]] of [[-W / 2 + 0.7, -D + 0.7], [W / 2 - 0.7, -D + 0.7], [-W / 2 + 0.7, -0.8], [W / 2 - 0.7, -0.8]].entries()) {
    pottedTree(put, room, x, z, k);
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
  hang.forEach(({ n, u, r }) => {
    const U = units[n], solo = U.members.length === 1;
    const cy = solo ? HANG_Y : Math.max(HANG_Y, 1.26 + U.oh / 2);          // (a collage sits well clear of the chair rail)
    U.members.forEach((i, mi) => hangOne(i, r, u + U.offs[mi][0], cy + U.offs[mi][1], solo));
    if (!solo) hangGroup(U, r, u, cy);
  });
  // one painting: its frame, and (hung alone) its wires, picture light and card
  function hangOne(i, r, u, y, solo) {
    const work = WORKS[i], sz = sizes[i];
    const x = r.x + r.dx * u + r.nx * 0.07, z = r.z + r.dz * u + r.nz * 0.07;
    const ry = Math.atan2(r.nx, r.nz);
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry; FG.add(g);
    const [style, finish] = frameStyle(i);
    const tex = textures.get(work.file);
    const F = ornateFrame(sz.ow, sz.oh, g, style, { finish, art: tex, shape: work.shape || 'rect' });   // (round canvases: an oval frame)
    const canvas = F.userData.canvas;
    canvas.userData.work = i;
    const normal = new THREE.Vector3(r.nx, 0, r.nz);
    if (!solo) { pieces.push({ i, canvas, card: canvas, center: new THREE.Vector3(x, y, z), normal, size: sz }); return; }
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
      wash(g, Math.max(lw * 1.6, sz.ow * 1.05), sz.oh + 0.3, top + 0.15);       // its light, falling down the canvas
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
    pieces.push({ i, canvas, card: face, center: new THREE.Vector3(x, HANG_Y, z), normal, size: sz });
  }
  // a collage: one picture light over the lot, one card beside it naming the set
  function hangGroup(U, r, u, cy) {
    const x = r.x + r.dx * u + r.nx * 0.07, z = r.z + r.dz * u + r.nz * 0.07;
    const g = new THREE.Group(); g.position.set(x, cy, z); g.rotation.y = Math.atan2(r.nx, r.nz); FG.add(g);
    const top = U.oh / 2, lw = Math.min(1.0, U.ow * 0.6);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.3, 6), brass); arm.position.set(0, top + 0.1, 0.12); arm.rotation.x = 1.1; g.add(arm);
    const hood = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, lw, 14, 1, false, 0, Math.PI), brass);
    hood.rotation.z = Math.PI / 2; hood.rotation.x = 0.5; hood.position.set(0, top + 0.2, 0.25); g.add(hood);
    const bulb = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, lw * 0.9, 8), lampGlow);
    bulb.rotation.z = Math.PI / 2; bulb.position.set(0, top + 0.18, 0.26); bulb.userData.noInk = true; g.add(bulb);
    wash(g, U.ow * 1.05, U.oh + 0.3, top + 0.15);
    const first = U.members[0];
    const card = canvasTex(320, 200, (c, w, h) => {
      c.fillStyle = '#fbf6ea'; c.fillRect(0, 0, w, h);
      c.strokeStyle = INKC; c.lineWidth = 5; c.strokeRect(3, 3, w - 6, h - 6);
      c.fillStyle = INKC; c.textBaseline = 'alphabetic';
      fit(c, U.title, 38, SCRIPT, w - 36, 700); c.fillText(U.title, 18, 52);
      c.font = `400 21px ${HAND}`; c.fillStyle = '#5a4e5e';
      c.fillText(ARTIST.name, 18, 86); c.fillText(`a set of ${U.members.length} small canvases`, 18, 112);
      c.fillStyle = '#e8604c'; c.fillRect(18, h - 52, 46, 4);
      c.font = `400 17px ${HAND}`; c.fillStyle = '#8a7e8e'; c.fillText('click one to look closer', 18, h - 24);
    });
    const cg = new THREE.Group(); cg.position.set(U.ow / 2 + 0.36, 1.4 - cy, -0.04); g.add(cg);
    cg.add(new THREE.Mesh(rb(0.34, 0.22, 0.015, 0.004), paint(0xfbf6ea)));
    const face = new THREE.Mesh(new THREE.PlaneGeometry(0.32, 0.2), paint(0xffffff, { map: card, hatch: 0, unique: true }));
    face.position.z = 0.009; face.userData.noInk = true; face.userData.work = first; cg.add(face);
    for (const p of pieces) if (U.members.includes(p.i)) p.card = face;
  }
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

// ── LIGHT: no real lamps (the toon paint is lit by the room's two lights), but the look of
// light, painted on: a warm wash down each painting from its picture light, and a soft pool on
// the wall round every sconce. Additive, so they brighten whatever they fall on ──
const glowTex = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 128; const c = cv.getContext('2d');
  const g = c.createRadialGradient(64, 64, 2, 64, 64, 64); g.addColorStop(0, 'rgba(255,214,150,0.9)'); g.addColorStop(0.35, 'rgba(255,200,130,0.35)'); g.addColorStop(1, 'rgba(255,190,120,0)');
  c.fillStyle = g; c.fillRect(0, 0, 128, 128); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const washTex = (() => { const cv = document.createElement('canvas'); cv.width = 128; cv.height = 256; const c = cv.getContext('2d');
  const v = c.createLinearGradient(0, 0, 0, 256); v.addColorStop(0, 'rgba(255,226,170,0)'); v.addColorStop(0.07, 'rgba(255,226,170,0.9)'); v.addColorStop(0.32, 'rgba(255,220,160,0.4)'); v.addColorStop(1, 'rgba(255,214,150,0)');
  c.fillStyle = v; c.fillRect(0, 0, 128, 256);
  c.globalCompositeOperation = 'destination-in';                       // and soft at the sides, like a cone of light
  const h = c.createLinearGradient(0, 0, 128, 0); h.addColorStop(0, 'rgba(0,0,0,0)'); h.addColorStop(0.2, 'rgba(0,0,0,1)'); h.addColorStop(0.8, 'rgba(0,0,0,1)'); h.addColorStop(1, 'rgba(0,0,0,0)');
  c.fillStyle = h; c.fillRect(0, 0, 128, 256); const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t; })();
const lightMat = (map, opacity) => new THREE.MeshBasicMaterial({ map, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });
const WASH = lightMat(washTex, 0.5), GLOW = lightMat(glowTex, 0.55);
function wash(parent, w, h, top) {                     // down from a picture light at `top`
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), WASH); m.position.set(0, top - h / 2 + 0.04, 0.14); m.userData.noInk = true; m.renderOrder = 3; m.raycast = () => {}; parent.add(m);
}
// a wall sconce: a brass backplate, two curling arms, a candle cup and a little lit shade on each
function sconce(put, parent, x, y, z, ry) {
  const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry; parent.add(g);
  const brass = paint(0xc89b45), shade = paint(0xfff0d0, { emissive: 0xffd9a0, hatch: 0 });
  const plate = new THREE.LatheGeometry([[0.001, 0.0], [0.05, 0.0], [0.06, 0.012], [0.05, 0.022], [0.001, 0.024]].map(([a, b]) => new THREE.Vector2(a, b)), 20);
  plate.rotateX(Math.PI / 2); plate.scale(0.9, 1.8, 1);
  put(plate, brass, 0, 0, 0, null, g);
  for (const s of [-1, 1]) {
    const arm = new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(0, -0.02, 0.02), new THREE.Vector3(s * 0.06, -0.09, 0.1), new THREE.Vector3(s * 0.16, -0.05, 0.14), new THREE.Vector3(s * 0.19, 0.04, 0.14)]), 16, 0.011, 6);
    put(arm, brass, 0, 0, 0, null, g);
    put(new THREE.CylinderGeometry(0.03, 0.022, 0.035, 12), brass, s * 0.19, 0.055, 0.14, null, g);        // the cup
    put(new THREE.CylinderGeometry(0.012, 0.012, 0.05, 8), paint(0xfffaf0, { hatch: 0 }), s * 0.19, 0.095, 0.14, null, g);
    const sh = put(new THREE.CylinderGeometry(0.045, 0.075, 0.1, 16, 1, true), shade, s * 0.19, 0.15, 0.14, null, g);
    sh.material.side = THREE.DoubleSide;
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), GLOW); glow.position.set(s * 0.19, 0.16, 0.012); glow.userData.noInk = true; glow.renderOrder = 3; glow.raycast = () => {}; g.add(glow);
  }
  put(new THREE.SphereGeometry(0.022, 10, 8), brass, 0, -0.06, 0.03, null, g);                               // a finial below
}

// a museum bench: a padded seat on gilt legs
function bench(put, z) {
  const wood = paint(0x6b4a33), pad = paint(0x8e3b3f);
  put(rb(2.0, 0.08, 0.6, 0.03), wood, 0, 0.42, z);
  put(rb(1.9, 0.1, 0.52, 0.05), pad, 0, 0.5, z);
  for (const sx of [-0.85, 0.85]) for (const sz of [-0.22, 0.22]) put(new THREE.CylinderGeometry(0.035, 0.025, 0.4, 10), paint(PAL.gold), sx, 0.2, z + sz);
}
// a potted tree: a glazed urn on a little foot, dark soil with moss, and an indoor tree
// (a ficus, glossy green) grown from the same kit as the island's trees
function pottedTree(put, parent, x, z, seed) {
  let sd = 1234 + seed * 977; const R = () => ((sd = (sd * 16807) % 2147483647) / 2147483647);
  const urn = new THREE.LatheGeometry([[0.001, 0], [0.2, 0], [0.22, 0.04], [0.17, 0.08], [0.2, 0.14], [0.3, 0.3], [0.34, 0.48], [0.33, 0.58], [0.37, 0.62], [0.37, 0.66], [0.32, 0.67], [0.31, 0.6]]
    .map(([a, b]) => new THREE.Vector2(a, b)), 32);
  urn.computeVertexNormals();
  put(urn, paint([0x2f5d6a, 0x7a3b2e, 0x3d4f3a, 0x2f5d6a][seed % 4], { hatch: 0.3 }), x, 0, z);
  put(new THREE.TorusGeometry(0.345, 0.02, 8, 32), paint(PAL.gold), x, 0.48, z, [Math.PI / 2, 0, 0]);          // a gilt band
  put(new THREE.CircleGeometry(0.31, 24), paint(0x3a2a20, { hatch: 0 }), x, 0.6, z, [-Math.PI / 2, 0, 0]);
  const t = realTree(R, { height: 1.9 + R() * 0.3, palette: [0x4f7a3e, 0x5f8c46, 0x3f6a36, 0x6f9a50], leaves: 0.55 });
  t.scale.setScalar(0.62); t.position.set(x, 0.58, z); t.rotation.y = R() * 6.28; parent.add(t);
  ink(t.userData.inkOnly, 'fine');
}
