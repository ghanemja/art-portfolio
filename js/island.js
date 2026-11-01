// ─── OUTSIDE: the museum on a floating island, high over a painted landscape ───
// The museum is art-heist's (museum.js, built with heist: false), restyled into the drawn
// world the way art-heist's town.js does it: every material becomes gouache paint (style.js)
// and the whole building is inked. Around it: a grassy island with a rocky underside hanging
// in the air, a waterfall pouring off its edge, a few little islets bobbing nearby, puffy
// clouds drifting past, and far below, fields, a river, forests and a ring of mountains.
//
// Frame: +Y up. The museum's doorway is at (0, 0.66, DOOR_Z) facing +Z.
import * as THREE from 'three';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { paint, ink, PAL } from './style.js';
import { buildMuseum } from './museum.js';
import { ARTIST, WORKS } from './collection.js';

export const MUSEUM_Z = 4;                  // the museum's origin (its forecourt) on the island
export const DOOR_Z = MUSEUM_Z - 3.9;       // the front wall, where the open door is
const ISLAND_R = 15.5;                       // the island's mean radius
const GROUND_Y = -70;                        // the landscape far below

// a repeatable little random
const rng = (s) => () => ((s = (s * 16807) % 2147483647) / 2147483647);
// smooth value noise, 2D, for terrain and rock
const _h = (x, y) => { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); };
function noise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = _h(xi, yi), b = _h(xi + 1, yi), c = _h(xi, yi + 1), d = _h(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
const fbm = (x, y, o = 4) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * noise(x * f, y * f); f *= 2; a *= 0.5; } return s; };

// the island's rim: a lumpy circle, never closer in than the museum needs
const rimR = (a) => ISLAND_R + 1.3 * Math.sin(3 * a + 1.1) + 0.8 * Math.sin(5 * a + 0.3) + 0.5 * Math.sin(9 * a + 2.0);
// where the museum stands (and its forecourt): kept flat, nothing planted
const inMuseum = (x, z, pad = 0) => Math.abs(x) < 7.9 + pad && z < MUSEUM_Z + 3.6 + pad && z > MUSEUM_Z - 11.8 - pad;
// the front walk: from the forecourt out to the rim at +z
const onWalk = (x, z, pad = 0) => Math.abs(x) < 1.1 + pad && z > MUSEUM_Z && z < 20;

function colorGeo(geo, fn) {
  const p = geo.attributes.position, col = new Float32Array(p.count * 3), c = new THREE.Color();
  for (let i = 0; i < p.count; i++) { fn(c, p.getX(i), p.getY(i), p.getZ(i)); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return geo;
}
const VC = () => paint(0xffffff, { vertexColors: true, hatch: 0.6 });

// ── the island: a grassy top on a rocky, hanging underside ──
function islandBody({ rim = rimR, depth = 16, lump = 1, seed = 0, flat = inMuseum, rings = 22, segs = 120 } = {}) {
  const g = new THREE.Group();
  // the top: rings out from the middle to the rim, rolling gently outside the museum's ground,
  // falling away in a soft lip at the edge
  const top = [], idx = [];
  const topY = (x, z, k) => {
    const lipK = THREE.MathUtils.smoothstep(k, 0.84, 1.0);
    const roll = flat(x, z, 1.2) ? 0 : (fbm(x * 0.12 + seed, z * 0.12) - 0.45) * 0.9 * THREE.MathUtils.smoothstep(k, 0.2, 0.6);
    return roll * (1 - lipK) - 0.45 * lipK * lipK;
  };
  top.push(0, topY(0, 0, 0), 0);
  for (let r = 1; r <= rings; r++) {
    const k = r / rings;
    for (let s = 0; s < segs; s++) {
      const a = s / segs * Math.PI * 2, R = rim(a) * Math.pow(k, 0.9);
      const x = Math.sin(a) * R, z = Math.cos(a) * R;
      top.push(x, topY(x, z, k), z);
    }
  }
  const ring = (r, s) => r === 0 ? 0 : 1 + (r - 1) * segs + (s % segs);
  for (let s = 0; s < segs; s++) idx.push(0, ring(1, s), ring(1, s + 1));
  for (let r = 1; r < rings; r++) for (let s = 0; s < segs; s++) {
    const a = ring(r, s), b = ring(r, s + 1), c = ring(r + 1, s), d = ring(r + 1, s + 1);
    idx.push(a, c, b, b, c, d);
  }
  const tg = new THREE.BufferGeometry();
  tg.setAttribute('position', new THREE.Float32BufferAttribute(top, 3)); tg.setIndex(idx); tg.computeVertexNormals();
  colorGeo(tg, (c, x, y, z) => {
    const n = fbm(x * 0.3 + 7 + seed, z * 0.3);
    c.setHex(PAL.grass).lerp(new THREE.Color(PAL.grassDeep), n * 0.8).lerp(new THREE.Color(PAL.meadow), Math.max(0, y) * 0.6);
  });
  const topM = new THREE.Mesh(tg, VC()); topM.name = 'islandTop'; g.add(topM);

  // the underside: the rim's ring dropped down to a craggy point, bulging, lumpy, banded
  const rows = 26, pos = [], ui = [];
  for (let j = 0; j <= rows; j++) {
    const t = j / rows;                                  // 0 at the rim … 1 at the tip
    for (let s = 0; s < segs; s++) {
      const a = s / segs * Math.PI * 2;
      const lumpN = fbm(Math.cos(a) * 2.2 + seed, Math.sin(a) * 2.2 + t * 4.5, 4);
      const shape = Math.pow(1 - t, 0.75) * (1 + 0.18 * Math.sin(Math.PI * t)) * (0.92 + 0.32 * lumpN * lump);
      const R = rim(a) * shape + (t === 1 ? 0 : 0.0);
      const y = -0.45 - t * depth * (0.85 + 0.3 * fbm(Math.cos(a) * 1.3 + 3, Math.sin(a) * 1.3 + seed)) - (t > 0 ? 0.25 * Math.sin(a * 7 + j) * lump : 0);
      pos.push(Math.sin(a) * R, y, Math.cos(a) * R);
    }
  }
  for (let j = 0; j < rows; j++) for (let s = 0; s < segs; s++) {
    const a = j * segs + s, b = j * segs + (s + 1) % segs, c = (j + 1) * segs + s, d = (j + 1) * segs + (s + 1) % segs;
    ui.push(a, c, b, b, c, d);
  }
  const ug = new THREE.BufferGeometry();
  ug.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); ug.setIndex(ui); ug.computeVertexNormals();
  const earth = new THREE.Color(0xb08a62), rockA = new THREE.Color(PAL.rock), rockB = new THREE.Color(0x9a8c7c), root = new THREE.Color(0x8a6a4a);
  colorGeo(ug, (c, x, y, z) => {
    const band = Math.sin(y * 1.6 + fbm(x * 0.4, z * 0.4) * 3);
    if (y > -1.4) c.copy(earth).lerp(root, THREE.MathUtils.smoothstep(-y, 0.4, 1.4) * 0.5);
    else c.copy(band > 0.2 ? rockA : rockB).lerp(earth, 0.15 * fbm(x, z));
  });
  const um = new THREE.Mesh(ug, VC()); um.name = 'islandRock'; g.add(um);
  return g;
}

// ── a lollipop tree, a bush, a cypress: paint, inked later with the rest ──
function tree(R, kind = 'round') {
  const g = new THREE.Group();
  const leaf = [PAL.leaf, PAL.leafLight, 0x7a9e5e, 0x93b56f][Math.floor(R() * 4)];
  if (kind === 'cypress') {
    const tr = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 0.5, 8), paint(PAL.bark)); tr.position.y = 0.25; g.add(tr);
    const c = new THREE.Mesh(new THREE.SphereGeometry(0.5, 16, 12), paint(0x6d9358));
    c.scale.set(0.85, 3.0, 0.85); c.position.y = 1.7; g.add(c);
    return g;
  }
  const h = 1.0 + R() * 0.9;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.14, h, 10), paint(PAL.bark));
  trunk.position.y = h / 2; g.add(trunk);
  const n = 2 + Math.floor(R() * 2);
  for (let i = 0; i < n; i++) {
    const r = 0.75 + R() * 0.5, s = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), paint(i ? leaf : PAL.leaf));
    s.position.set((R() - 0.5) * 0.8, h + r * 0.6 + i * 0.35, (R() - 0.5) * 0.8); g.add(s);
  }
  return g;
}
function bush(R) {
  const g = new THREE.Group(), col = [PAL.leaf, 0x7a9e5e, PAL.sage][Math.floor(R() * 3)];
  for (let i = 0; i < 3; i++) {
    const r = 0.35 + R() * 0.25, s = new THREE.Mesh(new THREE.SphereGeometry(r, 14, 10), paint(col));
    s.position.set((i - 1) * 0.35, r * 0.75, (R() - 0.5) * 0.3); s.scale.y = 0.85; g.add(s);
  }
  // a few flowers on it
  const fc = [PAL.rose, PAL.mustard, 0xffffff, PAL.lilac][Math.floor(R() * 4)];
  for (let i = 0; i < 6; i++) {
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), paint(fc, { hatch: 0 }));
    const a = R() * 6.28; f.position.set(Math.cos(a) * 0.45, 0.45 + R() * 0.25, Math.sin(a) * 0.35); f.userData.noInk = true; g.add(f);
  }
  return g;
}

// ── the sky: art-heist's painted gradient with paper tooth ──
function sky() {
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: new THREE.Color(0xa9c8d8) }, mid: { value: new THREE.Color(0xf6e7cc) }, low: { value: new THREE.Color(0xf3d2b6) } },
    vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: `uniform vec3 top, mid, low; varying vec3 vP;
      void main(){
        float y = vP.y + 0.12;
        vec3 c = y > 0.0 ? mix(mid, top, smoothstep(0.0, 0.75, y)) : mix(mid, low, smoothstep(0.0, -0.5, y));
        vec2 fc = gl_FragCoord.xy;
        float g = fract(sin(dot(floor(fc / 2.0), vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
        gl_FragColor = vec4(c * (1.0 + g * 0.03), 1.0);
        #include <colorspace_fragment>
      }`,
  });
  const m = new THREE.Mesh(new THREE.SphereGeometry(600, 32, 16), mat);
  m.userData.noInk = true; m.frustumCulled = false; m.renderOrder = -10;
  return m;
}

// ── a puffy cloud: a cluster of squashed balls, soft paint, a fine line ──
function cloud(R, s = 1) {
  const parts = [];
  const n = 5 + Math.floor(R() * 4);
  for (let i = 0; i < n; i++) {
    const r = (1.2 + R() * 1.4) * s, b = new THREE.SphereGeometry(r, 16, 12);
    b.scale(1, 0.72, 1);
    b.translate((i - n / 2) * 1.5 * s + (R() - 0.5) * s, (R() * 0.8 + (i % 2) * 0.5) * s, (R() - 0.5) * 1.6 * s);
    b.deleteAttribute('uv'); parts.push(b);
  }
  const geo = mergeVertices(mergeGeometries(parts)); geo.computeVertexNormals();
  return new THREE.Mesh(geo, paint(0xffffff, { soft: true, hatch: 0 }));
}

// ── far below: fields, a river, woods, mountains round the horizon ──
function landscape(R) {
  const g = new THREE.Group(); g.position.y = GROUND_Y;
  const SIZE = 900, N = 140;
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, N, N); geo.rotateX(-Math.PI / 2);
  const p = geo.attributes.position;
  const river = (x) => Math.sin(x * 0.012) * 60 + Math.sin(x * 0.031 + 1) * 18 + 40;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i);
    const d = Math.abs(z - river(x));
    let y = (fbm(x * 0.006, z * 0.006) - 0.5) * 26 + (fbm(x * 0.02 + 5, z * 0.02) - 0.5) * 6;
    y -= 7 * Math.exp(-d * d / 300);                   // the river's valley
    const far = Math.hypot(x, z);
    y += THREE.MathUtils.smoothstep(far, 260, 420) * 30;   // the land rises toward the mountains
    p.setY(i, y);
  }
  geo.computeVertexNormals();
  const fieldCols = [PAL.meadow, PAL.grass, PAL.mustard, PAL.sage, 0xc9b98a, PAL.grassDeep, 0xd8c98e].map(h => new THREE.Color(h));
  colorGeo(geo, (c, x, y, z) => {
    // a patchwork of fields, wobbly edges, greener in the low ground
    const fx = Math.floor((x + fbm(x * 0.02, z * 0.02) * 30) / 38), fz = Math.floor((z + fbm(z * 0.02, x * 0.02) * 30) / 30);
    c.copy(fieldCols[Math.floor(_h(fx, fz) * fieldCols.length)]);
    c.lerp(new THREE.Color(PAL.grassDeep), THREE.MathUtils.smoothstep(-y, 2, 10) * 0.6);
    const d = Math.abs(z - river(x)); if (d < 12) c.lerp(new THREE.Color(PAL.sand), (1 - d / 12) * 0.5);
  });
  const land = new THREE.Mesh(geo, VC()); land.userData.noInk = true; g.add(land);
  // the river: a ribbon following its valley
  {
    const pts = [], ix = [];
    for (let i = 0; i <= 160; i++) {
      const x = -SIZE / 2 + i / 160 * SIZE, z = river(x), w = 7 + 2 * Math.sin(i * 0.3);
      pts.push(x, -5.2, z - w, x, -5.2, z + w);
      if (i < 160) { const a = i * 2; ix.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    }
    const rg = new THREE.BufferGeometry(); rg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); rg.setIndex(ix); rg.computeVertexNormals();
    const rm = new THREE.Mesh(rg, paint(PAL.water, { hatch: 0 })); rm.userData.noInk = true; g.add(rm);
  }
  // woods: little cone trees in clumps (instanced: one draw)
  {
    const tg = new THREE.ConeGeometry(2.4, 7, 7); tg.translate(0, 3.5, 0);
    const COUNT = 900, im = new THREE.InstancedMesh(tg, paint(0x6f9a64, { hatch: 0.4 }), COUNT);
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), v = new THREE.Vector3();
    const ray = new THREE.Raycaster(), down = new THREE.Vector3(0, -1, 0);
    land.updateMatrixWorld(true);
    let k = 0;
    for (let c = 0; c < 60 && k < COUNT; c++) {
      const cx = (R() - 0.5) * 640, cz = (R() - 0.5) * 640;
      if (Math.abs(cz - river(cx)) < 18 || Math.hypot(cx, cz) < 30) continue;
      for (let t = 0; t < 15 && k < COUNT; t++) {
        const x = cx + (R() - 0.5) * 50, z = cz + (R() - 0.5) * 50;
        ray.set(v.set(x, 200 + GROUND_Y, z), down);
        const hit = ray.intersectObject(land)[0]; if (!hit) continue;
        const s = 0.7 + R() * 0.7;
        m4.compose(v.set(x, hit.point.y - GROUND_Y, z), q, sc.set(s, s * (0.8 + R() * 0.5), s));
        im.setMatrixAt(k++, m4);
      }
    }
    im.count = k; im.userData.noInk = true; g.add(im);
  }
  // mountains round the horizon, snow on the tall ones
  {
    const mg = [], sg = [];
    for (let i = 0; i < 26; i++) {
      const a = i / 26 * Math.PI * 2 + R() * 0.15, d = 380 + R() * 60, h = 60 + R() * 70, r = 55 + R() * 40;
      const cone = new THREE.ConeGeometry(r, h, 9, 4); cone.translate(0, h / 2, 0);
      const cp = cone.attributes.position;
      for (let j = 0; j < cp.count; j++) { const y = cp.getY(j); if (y > 0.5 && y < h - 0.5) { const k = 1 + (_h(j, i) - 0.5) * 0.25; cp.setX(j, cp.getX(j) * k); cp.setZ(j, cp.getZ(j) * k); } }
      cone.deleteAttribute('uv');
      const cm = mergeVertices(cone); cm.computeVertexNormals();
      cm.translate(Math.sin(a) * d, 20, Math.cos(a) * d);
      mg.push(cm);
      if (h > 95) {
        const sh = 0.28 * h, snow = new THREE.ConeGeometry(r * 0.28 * 1.04, sh, 9, 1); snow.translate(Math.sin(a) * d, 20 + h - sh / 2 + 0.3, Math.cos(a) * d); snow.deleteAttribute('uv'); sg.push(snow);
      }
    }
    const M = new THREE.Mesh(mergeGeometries(mg), paint(0x9aa6b8, { hatch: 0.5 }));
    g.add(M);
    if (sg.length) g.add(new THREE.Mesh(mergeGeometries(sg), paint(PAL.snow, { hatch: 0 })));
    ink(M, 'heavy');
  }
  return g;
}

// ── the waterfall: a ribbon off the rim, stripes scrolling down, fading into mist ──
function waterfall(a) {
  const R0 = rimR(a) - 0.2, x0 = Math.sin(a) * R0, z0 = Math.cos(a) * R0;
  const W = 1.5, LEN = 34, N = 40, pts = [], uv = [], ix = [];
  const out = new THREE.Vector3(Math.sin(a), 0, Math.cos(a)), side = new THREE.Vector3(Math.cos(a), 0, -Math.sin(a));
  for (let i = 0; i <= N; i++) {
    const t = i / N, drop = t * LEN, push = 1.2 * Math.sqrt(t) + 0.3 * t;   // it arcs out, then falls
    const c = new THREE.Vector3(x0, -0.3 - drop, z0).addScaledVector(out, push), w = W * (1 + t * 0.9);
    pts.push(...c.clone().addScaledVector(side, -w / 2).toArray(), ...c.clone().addScaledVector(side, w / 2).toArray());
    uv.push(0, t, 1, t);
    if (i < N) { const k = i * 2; ix.push(k, k + 2, k + 1, k + 1, k + 2, k + 3); }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); geo.setIndex(ix);
  const mat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uT: { value: 0 } },
    vertexShader: 'varying vec2 vU; void main(){ vU = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: `uniform float uT; varying vec2 vU;
      void main(){
        float s = fract(vU.y * 9.0 - uT * 1.6 + sin(vU.x * 9.0) * 0.12);
        float streak = step(0.72, fract(vU.x * 5.0 + sin(vU.y * 20.0 - uT * 3.0) * 0.08));
        vec3 c = mix(vec3(0.62, 0.82, 0.86), vec3(0.96, 0.99, 1.0), max(step(0.8, s), streak * 0.7));
        float edge = smoothstep(0.0, 0.12, vU.x) * smoothstep(1.0, 0.88, vU.x);
        float a = edge * (1.0 - smoothstep(0.45, 1.0, vU.y)) * 0.9;
        gl_FragColor = vec4(c, a);
        #include <colorspace_fragment>
      }`,
  });
  const m = new THREE.Mesh(geo, mat); m.userData.noInk = true; m.renderOrder = 3;
  // the stream that feeds it: across the grass from a little spring-fed pond
  const g = new THREE.Group(); g.add(m);
  const pondAt = new THREE.Vector3(Math.sin(a) * (R0 - 4.2), 0, Math.cos(a) * (R0 - 4.2));
  const pond = new THREE.Mesh(new THREE.CircleGeometry(1.7, 40).rotateX(-Math.PI / 2), paint(PAL.water, { hatch: 0 }));
  pond.position.copy(pondAt).setY(0.06); pond.scale.set(1, 1, 0.75); pond.rotation.y = a; pond.userData.noInk = true; g.add(pond);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(1.72, 0.12, 8, 40).rotateX(Math.PI / 2), paint(PAL.rock));
  rim.position.copy(pondAt).setY(0.05); rim.scale.set(1, 1, 0.75); rim.rotation.y = a; g.add(rim);
  const sl = R0 - 4.2 - 1.2, stream = new THREE.Mesh(new THREE.PlaneGeometry(1.0, R0 - (R0 - 4.2) + 0.3).rotateX(-Math.PI / 2), paint(PAL.water, { hatch: 0 }));
  stream.position.set(Math.sin(a) * (R0 - 2.0), 0.05, Math.cos(a) * (R0 - 2.0)); stream.rotation.y = a; stream.userData.noInk = true; g.add(stream);
  void sl;
  // mist where it gives out, and spray at the lip
  const puffM = paint(0xffffff, { soft: true, hatch: 0, opacity: 0.55 });
  for (let i = 0; i < 6; i++) {
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.5 + i * 0.12, 12, 8), puffM);
    p.position.set(x0, -0.4, z0).addScaledVector(out, 0.5 + (i % 3) * 0.3).addScaledVector(side, (i - 2.5) * 0.35); p.userData.noInk = true; g.add(p);
  }
  return { group: g, mat };
}

// ── a little islet: a grass cap on a rocky drip, perhaps a tree ──
function islet(R, r) {
  const rim = (a) => r * (1 + 0.15 * Math.sin(3 * a + R() * 6) + 0.08 * Math.sin(5 * a));
  const g = islandBody({ rim, depth: r * 2.2, lump: 0.8, seed: R() * 50, flat: () => false, rings: 6, segs: 40 });
  if (r > 1.6 && R() < 0.8) { const t = tree(R, R() < 0.3 ? 'cypress' : 'round'); t.scale.setScalar(0.7); g.add(t); }
  else if (r > 1.0) { const b = bush(R); g.add(b); }
  return g;
}

export function buildIsland(scene, { textures }) {
  const R = rng(11);
  scene.add(sky());
  scene.fog = new THREE.Fog(0xf3e3c8, 120, 520);
  scene.add(new THREE.HemisphereLight(0xfff6e8, 0xb7a9a0, 1.35));
  const sun = new THREE.DirectionalLight(0xfff1dc, 1.6); sun.position.set(40, 70, 50); scene.add(sun);

  const world = new THREE.Group(); scene.add(world);
  const isle = new THREE.Group(); world.add(isle);            // everything that floats together

  // ── the island ──
  const body = islandBody();
  isle.add(body);

  // ── the museum ──
  const pick = (f) => WORKS.find(w => w.file === f) || WORKS[0];
  const bannerA = pick('art_cows_in_storm'), bannerB = pick('art_banana_treats_astronaut');
  const easel = WORKS.find(w => w.file === 'art_sunset_swell') || WORKS[1] || WORKS[0];
  const mus = buildMuseum({
    lite: false, openDoor: true, heist: false, spin: 0.22,
    name: ARTIST.museum, shortName: ARTIST.short,
    banners: [[bannerA.file + '.jpg', bannerA.title.toUpperCase()], [bannerB.file + '.jpg', bannerB.title.toUpperCase()]],
    bannerSub: `${WORKS.length} paintings · always open`, bannerFoot: 'NOW SHOWING',
    easelArt: textures.get(easel.file),
  });
  restyle(mus.group);
  ink(mus.group, 'mid', { merge: true });
  mus.group.position.z = MUSEUM_Z;
  isle.add(mus.group);

  // ── the front walk: flagstones from the forecourt to the rim, then stepping stones off into the air ──
  {
    const stone = paint(0xe6d6b8), parts = [];
    for (let z = MUSEUM_Z + 3.7; z < rimR(0) - 0.6; z += 0.75) {
      for (const x of [-0.45, 0.45]) {
        const s = new THREE.CylinderGeometry(0.34 + _h(x, z) * 0.06, 0.36, 0.08, 10); s.scale(1, 1, 0.8);
        s.translate(x + (_h(z, x) - 0.5) * 0.12, 0.03, z); s.deleteAttribute('uv'); parts.push(s);
      }
    }
    const m = new THREE.Mesh(mergeGeometries(parts), stone); isle.add(m);
  }
  const steps = [];
  for (let i = 0; i < 7; i++) {
    const r = 0.75 - i * 0.04, s = islet(rng(100 + i), r);
    s.position.set(Math.sin(i * 0.7) * 1.4, -0.9 - i * 1.25, rimR(0) + 1.4 + i * 1.6);
    isle.add(s); steps.push({ o: s, y: s.position.y, ph: i * 0.9 });
  }

  // ── planting round the museum ──
  {
    const spots = [];
    const ok = (x, z, r) => {
      if (inMuseum(x, z, r) || onWalk(x, z, r)) return false;
      const a = Math.atan2(x, z); if (Math.hypot(x, z) > rimR(a) - 1.2 - r) return false;
      return spots.every(([sx, sz, sr]) => Math.hypot(sx - x, sz - z) > sr + r + 0.2);
    };
    const place = (o, r, tries = 60, band = [8, 15]) => {
      for (let t = 0; t < tries; t++) {
        const a = R() * Math.PI * 2, d = band[0] + R() * (band[1] - band[0]), x = Math.sin(a) * d, z = Math.cos(a) * d;
        if (!ok(x, z, r)) continue;
        o.position.set(x, 0, z); o.rotation.y = R() * 6.28; isle.add(o); spots.push([x, z, r]); return true;
      }
      return false;
    };
    // cypresses flanking the walk, like a formal garden
    for (const z of [MUSEUM_Z + 5.2, MUSEUM_Z + 7.6, MUSEUM_Z + 10]) for (const s of [-1, 1]) {
      const t = tree(R, 'cypress'); t.position.set(s * 2.0, 0, z); isle.add(t); spots.push([s * 2.0, z, 0.6]);
    }
    for (let i = 0; i < 16; i++) place(tree(R), 1.3);
    for (let i = 0; i < 22; i++) place(bush(R), 0.7, 40, [6, 15]);
    // flowers scattered in the grass
    const fl = [], cols = [PAL.rose, PAL.mustard, 0xffffff, PAL.lilac, PAL.accent];
    const flowerMats = cols.map(c => paint(c, { hatch: 0 }));
    const byCol = cols.map(() => []);
    for (let i = 0; i < 260; i++) {
      const a = R() * Math.PI * 2, d = 5 + R() * 10, x = Math.sin(a) * d, z = Math.cos(a) * d;
      if (inMuseum(x, z, 0.3) || onWalk(x, z, 0.2) || d > rimR(a) - 1.0) continue;
      const f = new THREE.SphereGeometry(0.07, 6, 5); f.translate(x, 0.12, z); f.deleteAttribute('uv'); byCol[i % cols.length].push(f);
    }
    byCol.forEach((list, i) => { if (list.length) { const m = new THREE.Mesh(mergeGeometries(list), flowerMats[i]); m.userData.noInk = true; isle.add(m); } });
    void fl;
  }

  // ── the waterfall, off the island's west side ──
  const fall = waterfall(-2.2);
  isle.add(fall.group);

  // ink the island and its planting (the museum and the steps already have theirs)
  const toInk = isle.children.filter(o => o !== mus.group);
  for (const o of toInk) ink(o, o === body ? 'heavy' : 'mid');

  // ── little islets drifting round it ──
  const islets = [];
  for (let i = 0; i < 8; i++) {
    const r = 1.0 + R() * 1.8, s = islet(rng(300 + i * 7), r);
    const a = i / 8 * Math.PI * 2 + R() * 0.4, d = 24 + R() * 14;
    s.position.set(Math.sin(a) * d, -4 + R() * 10, Math.cos(a) * d);
    ink(s, 'mid');
    world.add(s); islets.push({ o: s, y: s.position.y, ph: R() * 6, sp: 0.3 + R() * 0.4 });
  }

  // ── clouds, at every height, drifting slowly round ──
  const clouds = [];
  for (let i = 0; i < 26; i++) {
    const c = cloud(R, 0.8 + R() * 1.6);
    // (clear of the island and the usual view of it: far out, or well below)
    const a = R() * Math.PI * 2, low = R() < 0.45, d = low ? 26 + R() * 90 : 55 + R() * 90, y = low ? -38 + R() * 20 : -12 + R() * 26;
    c.position.set(Math.sin(a) * d, y, Math.cos(a) * d);
    ink(c, 'fine');
    world.add(c); clouds.push({ o: c, a, d, sp: (0.004 + R() * 0.006) * (R() < 0.5 ? 1 : 1) });
  }

  world.add(landscape(R));

  // a click target over the open door (museum-local: the doorway at FRONT, 1.3 wide, 2 high)
  const door = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2.1, 0.9), new THREE.MeshBasicMaterial({ visible: false }));
  door.position.set(0, 0.66 + 1.05, DOOR_Z + 0.2); door.userData.noInk = true; isle.add(door);

  const tick = (t) => {
    isle.position.y = Math.sin(t * 0.35) * 0.35;                       // the whole island breathes up and down
    isle.rotation.z = Math.sin(t * 0.21) * 0.006;
    for (const s of steps) s.o.position.y = s.y + Math.sin(t * 0.8 + s.ph) * 0.12;
    for (const s of islets) { s.o.position.y = s.y + Math.sin(t * s.sp + s.ph) * 0.6; s.o.rotation.y = t * 0.03 * s.sp; }
    for (const c of clouds) { const a = c.a + t * c.sp; c.o.position.x = Math.sin(a) * c.d; c.o.position.z = Math.cos(a) * c.d; }
    fall.mat.uniforms.uT.value = t;
    mus.tick(t, 1);
  };
  return { tick, door, isle, museum: mus };
}

// art-heist's town.js restyle: every material to gouache paint (light beams and shaders stay)
function restyle(root) {
  root.traverse(o => {
    if (!o.isMesh) return;
    const conv = (m) => {
      if (!m || m.isShaderMaterial || m.isMeshBasicMaterial || m.userData?.keep) return m;
      if (m.blending === THREE.AdditiveBlending) return m;
      const col = m.color ? m.color.getHex() : 0xffffff;
      const emiss = m.emissive && m.emissive.getHex() !== 0 && m.emissiveIntensity > 0 ? m.emissive.getHex() : undefined;
      return paint(col, { map: m.map || undefined, opacity: m.transparent ? Math.max(0.35, m.opacity) : 1,
        side: m.side, emissive: emiss, hatch: m.map ? 0 : 1 });
    };
    o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material);
  });
}
