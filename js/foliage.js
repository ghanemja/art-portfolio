// ─── FOLIAGE: trees with real branches and real leaves, and a floor of fallen ones ───
// Trees: a tapered trunk that forks into boughs and twigs (smooth, inked like everything else),
// and a crown made of thousands of single leaves gathered in clusters at the twig ends, each
// leaf a little folded card in its own shade of the tree's autumn colour, darker deep inside
// the crown and toward its underside (light doesn't get in there). The leaves flutter in the
// breeze (a vertex shader, one draw per tree); the whole crown sways from the trunk.
// The ground: leaf litter in the manner of art-heist's meadow (meadow.js): ONE mesh, colours
// per vertex, thousands of real leaf outlines (oak, maple, elm, curled a little at the tips)
// lying in drifts that thicken under the trees, along the path's edges and into heaps.
import * as THREE from 'three';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { paint, inkUniforms } from './style.js';

export const AUTUMN = [0xd9773a, 0xc8503a, 0xe3ad45, 0xb8642e, 0xe08f4a, 0xcf6a3c, 0xd99a3c];
const LITTER_COLS = [0xc8732e, 0xb5562a, 0xd99a3c, 0x9a5a2e, 0xe0a046, 0x8a4e2a, 0xc98a52, 0xa8452e, 0xd6b06a].map(h => new THREE.Color(h));

// ── leaf outlines, in the xz plane, stem toward −z, about 1 long ──
function outline(kind) {
  const P = [];
  if (kind === 'oak') {                     // rounded lobes down each side
    const lobes = 4;
    for (let i = 0; i <= 9; i++) { const t = i / 9, z = -0.5 + t, w = 0.22 * Math.sin(Math.PI * Math.min(1, t * 1.05)) * (0.75 + 0.35 * Math.abs(Math.sin(t * Math.PI * lobes))); P.push([w, z]); }
    for (let i = 9; i >= 0; i--) { const t = i / 9, z = -0.5 + t, w = 0.22 * Math.sin(Math.PI * Math.min(1, t * 1.05)) * (0.75 + 0.35 * Math.abs(Math.sin(t * Math.PI * lobes))); P.push([-w, z]); }
  } else if (kind === 'maple') {            // five pointed lobes
    const N = 20;
    for (let i = 0; i < N; i++) {
      const a = i / N * Math.PI * 2, lobe = Math.pow(Math.abs(Math.cos(a * 2.5)), 3), r = 0.22 + 0.3 * lobe * (a > Math.PI * 0.75 && a < Math.PI * 1.25 ? 0.2 : 1);
      P.push([Math.sin(a) * r, Math.cos(a) * r * 0.95 + 0.05]);
    }
  } else {                                   // elm / birch: a plain pointed oval
    for (let i = 0; i < 8; i++) { const a = i / 8 * Math.PI * 2; P.push([Math.sin(a) * 0.22 * (1 - 0.25 * Math.cos(a)), -Math.cos(a) * 0.5]); }
  }
  return P;
}
// a flat leaf geometry from an outline, curled up a little toward its tips
function leafGeo(kind) {
  const sh = new THREE.Shape(outline(kind).map(([x, z]) => new THREE.Vector2(x, z)));
  const g = new THREE.ShapeGeometry(sh, 1); g.rotateX(Math.PI / 2);   // shape xy → lying in xz (y up)
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i); p.setY(i, (x * x * 1.6 + z * z * 0.5)); }   // curled
  g.deleteAttribute('uv'); g.deleteAttribute('normal');
  return g;
}
// for crowns: a leaf as a folded card, stem to tip, the halves lifted along the midrib (2 triangles:
// thousands of these make a crown; up close the detailed outlines are on the ground, in the litter)
function cardGeo() {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, -0.5, -0.26, 0.09, 0.02, 0, 0, 0.5, 0.26, 0.09, 0.02], 3));
  g.setIndex([0, 1, 2, 0, 2, 3]); return g;
}
const LEAVES = { oak: leafGeo('oak'), maple: leafGeo('maple'), elm: leafGeo('elm'), card: cardGeo() };
const KINDS = ['oak', 'maple', 'elm'];
export const leafShape = (kind = 'maple') => LEAVES[kind].clone();

// stamp copies of a small geometry into big position/colour arrays (no per-leaf objects)
function stamper() {
  const pos = [], col = [], ph = [], idx = [];
  const m4 = new THREE.Matrix4(), v = new THREE.Vector3();
  return {
    add(geo, matrix, color, phase = 0) {
      const p = geo.attributes.position, base = pos.length / 3;
      for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i).applyMatrix4(matrix); pos.push(v.x, v.y, v.z); col.push(color.r, color.g, color.b); ph.push(phase); }
      const I = geo.index; if (I) for (let k = 0; k < I.count; k++) idx.push(base + I.getX(k)); else for (let k = 0; k < p.count; k++) idx.push(base + k);
    },
    build() {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      g.setAttribute('aPh', new THREE.Float32BufferAttribute(ph, 1));
      g.setIndex(idx); g.computeVertexNormals();
      return g;
    },
    m4,
  };
}

// leaves that flutter: each vertex nudged along its normal by a little wave, out of step leaf to leaf
function flutterMat(base) {
  const m = paint(0xffffff, { vertexColors: true, side: THREE.DoubleSide, hatch: 0.25, unique: true, ...base });
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (sh, r) => {
    prev(sh, r);
    sh.uniforms.uTime = inkUniforms.uTime;
    sh.vertexShader = 'uniform float uTime;\nattribute float aPh;\n' + sh.vertexShader.replace('#include <begin_vertex>',
      '#include <begin_vertex>\ntransformed += objectNormal * sin(uTime * 4.5 + aPh) * 0.018 + vec3(sin(uTime * 1.7 + aPh * 0.7), 0.0, cos(uTime * 1.3 + aPh)) * 0.01;');
  };
  m.customProgramCacheKey = () => 'flutter';
  return m;
}

// a tapered tube along a curve (bark): radius r0 at the start to r1 at the end, smooth
function limb(points, r0, r1, seg = 7) {
  const curve = new THREE.CatmullRomCurve3(points), n = Math.max(4, points.length * 3);
  const g = new THREE.TubeGeometry(curve, n, 1, seg, false), p = g.attributes.position;
  // TubeGeometry is radius 1 round the curve: pull each ring in to its tapered radius
  for (let i = 0; i <= n; i++) {
    const t = i / n, c = curve.getPointAt(t), r = r0 + (r1 - r0) * t;
    for (let j = 0; j <= seg; j++) { const k = i * (seg + 1) + j; const x = p.getX(k) - c.x, y = p.getY(k) - c.y, z = p.getZ(k) - c.z; p.setXYZ(k, c.x + x * r, c.y + y * r, c.z + z * r); }
  }
  g.deleteAttribute('uv'); g.computeVertexNormals();
  return g;
}

// ── a broadleaf tree: trunk, forking boughs, twigs, and leaf clusters at the ends ──
// returns a group with userData.crown (the part that sways), leafCol, crownH
export function realTree(R, { height = 2.4 + R() * 1.2, cols = null, leaves = 1, palette: pal = null } = {}) {
  const g = new THREE.Group();
  const base = pal ? pal[0] : cols || AUTUMN[Math.floor(R() * AUTUMN.length)];
  const palette = (pal || [base, base, AUTUMN[Math.floor(R() * AUTUMN.length)], R() < 0.3 ? 0x9aa84a : base]).map(h => new THREE.Color(h));
  const lean = new THREE.Vector3((R() - 0.5) * 0.25, 0, (R() - 0.5) * 0.25);
  const pivotY = height * 0.42;
  // the trunk, up to where it forks (below the pivot it stays put; above, it sways with the crown)
  const T = (t) => new THREE.Vector3(lean.x * t * t + Math.sin(t * 3 + R()) * 0.04, height * 0.62 * t, lean.z * t * t);
  const trunkPts = [0, 0.25, 0.5, 0.75, 1].map(T);
  const bark = [limb(trunkPts.map(p => p.clone()), 0.14 + R() * 0.04, 0.09, 9)];
  // root flare: three little buttresses
  for (let k = 0; k < 3; k++) { const a = k / 3 * Math.PI * 2 + R(); bark.push(limb([new THREE.Vector3(Math.cos(a) * 0.26, 0.0, Math.sin(a) * 0.26), new THREE.Vector3(Math.cos(a) * 0.1, 0.12, Math.sin(a) * 0.1), new THREE.Vector3(0, 0.35, 0)], 0.035, 0.08, 6)); }
  const top = trunkPts[4];
  const tips = [];
  const NB = 5 + Math.floor(R() * 3);
  for (let b = 0; b < NB; b++) {
    const a = b / NB * Math.PI * 2 + R() * 0.6, up = 0.55 + R() * 0.5, len = height * (0.32 + R() * 0.18);
    const start = T(0.7 + R() * 0.3);
    const dir = new THREE.Vector3(Math.cos(a) * (1 - up * 0.5), up, Math.sin(a) * (1 - up * 0.5)).normalize();
    const mid = start.clone().addScaledVector(dir, len * 0.5).add(new THREE.Vector3(0, len * 0.08, 0));
    const end = start.clone().addScaledVector(dir, len);
    bark.push(limb([start, mid, end], 0.065, 0.025, 6));
    tips.push(end);
    // twigs off each bough
    const nt = 2 + Math.floor(R() * 2);
    for (let k = 0; k < nt; k++) {
      const from = start.clone().lerp(end, 0.45 + R() * 0.4);
      const td = dir.clone().add(new THREE.Vector3((R() - 0.5) * 1.2, R() * 0.5, (R() - 0.5) * 1.2)).normalize();
      const tend = from.clone().addScaledVector(td, len * (0.3 + R() * 0.25));
      bark.push(limb([from, from.clone().lerp(tend, 0.5).add(new THREE.Vector3(0, 0.05, 0)), tend], 0.025, 0.01, 5));
      tips.push(tend);
    }
  }
  tips.push(top.clone().add(new THREE.Vector3(0, height * 0.3, 0)));                   // a leader at the top
  // split the bark at the pivot: what's below stays, the rest goes in the crown
  const barkGeo = mergeGeometries(bark);
  const crown = new THREE.Group(); crown.position.y = pivotY; g.add(crown);
  const barkMat = paint(0x6e5240);
  const trunkMesh = new THREE.Mesh(barkGeo, barkMat); trunkMesh.position.y = -pivotY; crown.add(trunkMesh);
  // the leaves: a cluster round every tip, denser and bigger toward the crown's outside
  const S = stamper(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), pos = new THREE.Vector3(), c = new THREE.Color();
  const centre = tips.reduce((a, t) => a.add(t), new THREE.Vector3()).multiplyScalar(1 / tips.length);
  const crownR = Math.max(...tips.map(t => t.distanceTo(centre))) + 0.6;
  const kind = KINDS[Math.floor(R() * KINDS.length)];
  for (const tip of tips) {
    const cr = 0.75 + R() * 0.45, n = Math.round((150 + R() * 50) * leaves);
    for (let i = 0; i < n; i++) {
      // a point in the cluster, biased to its surface
      const u = R() * 2 - 1, th = R() * Math.PI * 2, rr = cr * (0.45 + 0.55 * Math.cbrt(R()));
      pos.set(Math.sqrt(1 - u * u) * Math.cos(th) * rr, u * rr * 0.8, Math.sqrt(1 - u * u) * Math.sin(th) * rr).add(tip);
      const out = pos.clone().sub(centre), d = out.length() / crownR;
      e.set(-0.9 + (R() - 0.5) * 1.6, Math.atan2(out.x, out.z) + (R() - 0.5) * 1.8, (R() - 0.5) * 1.2);
      const s = 0.24 + R() * 0.1;
      S.m4.compose(pos.clone().setY(pos.y - pivotY), q.setFromEuler(e), sc.set(s, s, s));
      // colour: the tree's own, varied leaf to leaf; darker inside the crown and underneath
      c.copy(palette[Math.floor(R() * palette.length)]);
      c.offsetHSL((R() - 0.5) * 0.03, (R() - 0.5) * 0.1, (R() - 0.5) * 0.12);
      const shade = 0.55 + 0.45 * Math.min(1, d * 1.1) * (0.75 + 0.25 * Math.min(1, (pos.y - centre.y + crownR) / (crownR * 1.4)));
      c.multiplyScalar(shade);
      S.add(LEAVES.card, S.m4, c, R() * 6.28);
    }
  }
  void kind;
  const leavesMesh = new THREE.Mesh(S.build(), flutterMat());
  leavesMesh.userData.noInk = true; crown.add(leavesMesh);
  g.userData.crown = crown; g.userData.sway = 0.035; g.userData.leafCol = base;
  g.userData.crownH = centre.y + crownR * 0.6; g.userData.crownR = crownR;
  g.userData.inkOnly = trunkMesh;           // (ink the bark; the leaves are too many to outline)
  return g;
}

// ── an Italian cypress: a tight green flame of tiny scale-leaves round a hidden spindle ──
export function realCypress(R) {
  const g = new THREE.Group(), h = 2.6 + R() * 0.8, w = 0.42 + R() * 0.1;
  const crown = new THREE.Group(); crown.position.y = 0.3; g.add(crown);
  const trunk = new THREE.Mesh(limb([new THREE.Vector3(0, -0.3, 0), new THREE.Vector3(0, 0.4, 0), new THREE.Vector3(0, h * 0.8, 0)], 0.07, 0.03, 7), paint(0x6e5240));
  crown.add(trunk);
  const S = stamper(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), pos = new THREE.Vector3(), c = new THREE.Color();
  const greens = [0x4f7a46, 0x5d8a4e, 0x47703f, 0x6b9455].map(x => new THREE.Color(x));
  for (let i = 0; i < 1400; i++) {
    const t = R(), y = 0.1 + t * h, prof = Math.sin(Math.PI * Math.min(1, t * 1.1 + 0.05)) * (1 - t * 0.35), r = w * prof * (0.55 + 0.45 * Math.sqrt(R())), a = R() * Math.PI * 2;
    pos.set(Math.cos(a) * r, y, Math.sin(a) * r);
    e.set(-1.2 + (R() - 0.5), a + Math.PI / 2 + (R() - 0.5), (R() - 0.5));
    const s = 0.16 + R() * 0.07; S.m4.compose(pos, q.setFromEuler(e), sc.set(s, s, s * 1.4));
    c.copy(greens[Math.floor(R() * greens.length)]).multiplyScalar(0.65 + 0.35 * (r / (w * prof + 1e-3)));
    S.add(LEAVES.card, S.m4, c, R() * 6.28);
  }
  const m = new THREE.Mesh(S.build(), flutterMat()); m.userData.noInk = true; crown.add(m);
  g.userData.crown = crown; g.userData.sway = 0.015; g.userData.inkOnly = trunk;
  return g;
}

// ── a shrub: a low mound of leaves on a few hidden stems, autumn red, orange or still green ──
export function realBush(R) {
  const g = new THREE.Group();
  const base = new THREE.Color([0xc0453a, 0xd9773a, 0xe3ad45, 0xa8452e, 0x7d9a52][Math.floor(R() * 5)]);
  const S = stamper(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), pos = new THREE.Vector3(), c = new THREE.Color();
  const w = 0.55 + R() * 0.3, h = 0.45 + R() * 0.2;
  for (let i = 0; i < 380; i++) {
    const u = R(), th = R() * Math.PI * 2, rr = Math.sqrt(R()) * 0.5 + 0.5;
    pos.set(Math.cos(th) * Math.sqrt(1 - u * u) * w * rr, u * h * rr + 0.04, Math.sin(th) * Math.sqrt(1 - u * u) * w * rr);
    e.set(-0.9 + (R() - 0.5) * 1.4, th + Math.PI / 2 + (R() - 0.5), (R() - 0.5));
    const s = 0.17 + R() * 0.07; S.m4.compose(pos, q.setFromEuler(e), sc.set(s, s, s));
    c.copy(base).offsetHSL((R() - 0.5) * 0.04, (R() - 0.5) * 0.1, (R() - 0.5) * 0.12).multiplyScalar(0.6 + 0.4 * rr * (0.6 + 0.4 * u));
    S.add(LEAVES.card, S.m4, c, R() * 6.28);
  }
  const m = new THREE.Mesh(S.build(), flutterMat()); m.userData.noInk = true; g.add(m);
  return g;
}

// ── the leaf litter: drifts of fallen leaves over the ground ──
// heightAt(x, z) → ground y; density(x, z) → 0…1 how thick the leaves lie there (0: none)
export function leafLitter(R, { count, heightAt, density, area }) {
  const S = stamper(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), pos = new THREE.Vector3(), c = new THREE.Color();
  let placed = 0, tries = 0;
  const layer = new Map();                     // a coarse grid of how many leaves already lie there (so they stack, not z-fight)
  while (placed < count && tries < count * 6) {
    tries++;
    const x = area.x0 + R() * (area.x1 - area.x0), z = area.z0 + R() * (area.z1 - area.z0);
    const d = density(x, z); if (d <= 0 || R() > d) continue;
    const key = Math.round(x * 6) + ',' + Math.round(z * 6), n = layer.get(key) || 0; layer.set(key, n + 1);
    const y = heightAt(x, z); if (y == null) continue;
    pos.set(x, y + 0.008 + n * 0.006, z);
    e.set((R() - 0.5) * 0.35, R() * Math.PI * 2, (R() - 0.5) * 0.35);
    const s = 0.1 + R() * 0.09; S.m4.compose(pos, q.setFromEuler(e), sc.set(s, s, s));
    c.copy(LITTER_COLS[Math.floor(R() * LITTER_COLS.length)]).offsetHSL((R() - 0.5) * 0.02, (R() - 0.5) * 0.1, (R() - 0.5) * 0.1);
    if (R() < 0.25) c.lerp(new THREE.Color(0xc9b28a), 0.45);            // some faded, dry and pale
    c.multiplyScalar(0.85 + Math.min(n, 4) * 0.04);                     // the top of a heap catches more light
    const lr = R(); S.add(LEAVES[lr < 0.3 ? 'oak' : lr < 0.55 ? 'maple' : 'elm'], S.m4, c, R() * 6.28);
    placed++;
  }
  const m = new THREE.Mesh(S.build(), paint(0xffffff, { vertexColors: true, side: THREE.DoubleSide, hatch: 0.2, unique: true }));
  m.userData.noInk = true;
  return m;
}

// ── FRAMING: maple branches reaching in from the top corners of the view, as in a photo taken
// from under a tree. Built in "view units" (1 = half the view's height, origin at the corner,
// +x inward, −y down); main.js keeps them pinned to the camera. Red, scarlet and orange leaves,
// thick at the ends, fluttering; the bark is inked like everything else ──
export function framingBranch(R) {
  const g = new THREE.Group();
  const bark = [];
  const main = [new THREE.Vector3(-0.2, 0.05, 0), new THREE.Vector3(0.2, -0.22, 0.05), new THREE.Vector3(0.55, -0.4, 0.1), new THREE.Vector3(0.9, -0.62, 0.12)];
  bark.push(limb(main, 0.035, 0.008, 7));
  const tips = [main[3]];
  const curve = new THREE.CatmullRomCurve3(main);
  // side shoots: some droop down, some reach up and in
  for (let k = 0; k < 13; k++) {
    const t = 0.1 + k / 13 * 0.85, p = curve.getPointAt(t);
    const down = k % 3 !== 1, len = 0.2 + R() * 0.3;
    const end = p.clone().add(new THREE.Vector3((R() - 0.2) * len * 0.8, down ? -len : len * 0.4, (R() - 0.5) * 0.15));
    bark.push(limb([p, p.clone().lerp(end, 0.5).add(new THREE.Vector3(0.03, down ? 0.02 : 0.0, 0)), end], 0.012, 0.004, 5));
    tips.push(end);
  }
  const barkMesh = new THREE.Mesh(mergeGeometries(bark), paint(0x4a3428));
  g.add(barkMesh);
  const S = stamper(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3(), pos = new THREE.Vector3(), c = new THREE.Color();
  const reds = [0xd8321e, 0xc4241c, 0xe8522a, 0xf07a2a, 0xb81e1e, 0xf0a030].map(h => new THREE.Color(h));
  for (const tip of tips) {
    const n = 90 + Math.floor(R() * 50), cr = 0.16 + R() * 0.08;
    for (let i = 0; i < n; i++) {
      const u = R() * 2 - 1, th = R() * Math.PI * 2, rr = cr * Math.cbrt(R());
      pos.set(Math.sqrt(1 - u * u) * Math.cos(th) * rr * 1.4, u * rr, Math.sqrt(1 - u * u) * Math.sin(th) * rr * 0.6).add(tip);
      e.set(Math.PI / 2 + (R() - 0.5) * 1.1, (R() - 0.5) * 0.9, R() * Math.PI * 2);    // facing the viewer, turned every way
      const s = 0.085 + R() * 0.04; S.m4.compose(pos, q.setFromEuler(e), sc.set(s, s, s));
      c.copy(reds[Math.floor(R() * reds.length)]).offsetHSL((R() - 0.5) * 0.02, 0, (R() - 0.5) * 0.12);
      c.multiplyScalar(0.8 + 0.3 * Math.min(1, rr / cr));
      S.add(LEAVES.maple, S.m4, c, R() * 6.28);
    }
  }
  const leaves = new THREE.Mesh(S.build(), flutterMat({ hatch: 0.15 }));
  leaves.material.fog = false; barkMesh.material.fog = false;
  leaves.userData.noInk = true; g.add(leaves);
  return g;
}
