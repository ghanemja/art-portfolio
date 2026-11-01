// ─── VISITORS: other people browsing the gallery ─────────────────────────────
// The townsfolk from art-heist (made in Citizen Maker, github.com/ghanemja/citizen-maker:
// rigged GLBs with baked idle / walk / read / phone clips, models/people/), restyled into
// gouache paint and inked the way art-heist's citizens.js does it. Each one picks a painting,
// strolls over to it (round the partitions, on a grid path), stands and looks a while (one
// reads the gallery guide, one takes a photo on her phone), then wanders to another. They keep
// out of each other's spots and step around you; you can walk through them if you must.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { paint, ink, blobShadow } from './style.js';

const SCALE = 1.0;          // the models are in metres; so is the hall
const CAST = [
  { id: 'wren' }, { id: 'kai' }, { id: 'ada' }, { id: 'teo' }, { id: 'yara' },
  { id: 'lev', act: 'read' }, { id: 'iris', act: 'phone' }, { id: 'june' }, { id: 'dev' }, { id: 'zara' },
];
const WALK = 0.75;          // the walk clip's time scale (an unhurried gallery stroll)
const SPEED = 1.27 * WALK;  // metres a second at that pace (the clip's own speed is ~1.27 m/s)

// ── art-heist citizens.js: drop skin hidden under clothes (it pokes through on a bent knee) ──
function cullHiddenSkin(root) {
  const cloth = [], skin = [];
  root.traverse((o) => { if (o.isSkinnedMesh) (o.userData.role === 'cloth' ? cloth : o.userData.role === 'skin' ? skin : []).push(o); });
  if (!cloth.length || !skin.length) return;
  const CELL = 0.08, R2 = 0.08 * 0.08, grid = new Map(), v = new THREE.Vector3();
  const key = (x, y, z) => `${Math.floor(x / CELL)},${Math.floor(y / CELL)},${Math.floor(z / CELL)}`;
  for (const m of cloth) {
    const P = m.geometry.attributes.position;
    for (let i = 0; i < P.count; i++) {
      v.fromBufferAttribute(P, i).applyMatrix4(m.bindMatrix);
      const k = key(v.x, v.y, v.z); let a = grid.get(k); if (!a) grid.set(k, a = []); a.push(v.x, v.y, v.z);
    }
  }
  const covered = (x, y, z) => {
    const cx = Math.floor(x / CELL), cy = Math.floor(y / CELL), cz = Math.floor(z / CELL);
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) for (let k = -1; k <= 1; k++) {
      const a = grid.get(`${cx + i},${cy + j},${cz + k}`); if (!a) continue;
      for (let n = 0; n < a.length; n += 3) { const dx = a[n] - x, dy = a[n + 1] - y, dz = a[n + 2] - z; if (dx * dx + dy * dy + dz * dz < R2) return true; }
    }
    return false;
  };
  const TRUNK = /spine|pelvis|root|upperleg|lowerleg|breast|clavicle/i;
  for (const m of skin) {
    const g = m.geometry, P = g.attributes.position, idx = g.index; if (!idx) continue;
    const SI = g.attributes.skinIndex, SW = g.attributes.skinWeight, bones = m.skeleton.bones;
    const hid = new Uint8Array(P.count);
    for (let i = 0; i < P.count; i++) {
      let best = 0, bw = -1; if (SI) for (let k = 0; k < 4; k++) { const w = SW.getComponent(i, k); if (w > bw) { bw = w; best = SI.getComponent(i, k); } }
      if (!SI || !TRUNK.test(bones[best]?.name || '')) continue;
      v.fromBufferAttribute(P, i).applyMatrix4(m.bindMatrix); hid[i] = covered(v.x, v.y, v.z) ? 1 : 0;
    }
    const keep = [];
    for (let t = 0; t < idx.count; t += 3) { const a = idx.getX(t), b = idx.getX(t + 1), c = idx.getX(t + 2); if (!(hid[a] && hid[b] && hid[c])) keep.push(a, b, c); }
    if (keep.length < idx.count) g.setIndex(keep);
  }
}
// ── and its materials: gouache paint by the part's role, a fine ink line ──
function restyle(root) {
  cullHiddenSkin(root);
  root.traverse((o) => {
    if (!o.isMesh) return;
    const role = o.userData.role, m = o.material;
    const vc = !!o.geometry.getAttribute('color');
    o.material = paint(vc ? 0xffffff : m.color.getHex(), { vertexColors: vc, soft: role === 'skin' || role === 'hair' || role === 'eye', hatch: role === 'cloth' ? 1 : 0, side: m.side === THREE.DoubleSide ? THREE.DoubleSide : undefined });
    if (role === 'eye' || role === 'brow') o.userData.noInk = true;
    if (o.isSkinnedMesh) { o.geometry.computeBoundingSphere(); o.geometry.boundingSphere.radius *= 1.6; }
    o.raycast = () => {};                       // (never in the way of a click on a painting)
  });
  ink(root, 'fine');
  // their skinned bounds are the rest pose's, so up close the body was culled as off-screen
  // while its ink hull (never culled) still drew: a black figure. Ten people: just draw them.
  root.traverse((o) => { if (o.isMesh) o.frustumCulled = false; });
  return root;
}

// ── paths: A* on a 0.4 m grid over the hall's walkable floor, then straightened ──
function makeNav(gal) {
  const C = 0.4, x0 = -gal.W / 2, z0 = -gal.D, nx = Math.ceil(gal.W / C), nz = Math.ceil(gal.D / C);
  const PAD = 0.15;     // a little extra clearance on top of what blocks the visitor's camera
  const free = new Uint8Array(nx * nz);
  const ok = (x, z) => !gal.blocked(x, z) && !gal.blocked(x + PAD, z) && !gal.blocked(x - PAD, z) && !gal.blocked(x, z + PAD) && !gal.blocked(x, z - PAD);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) free[j * nx + i] = ok(x0 + (i + 0.5) * C, z0 + (j + 0.5) * C) ? 1 : 0;
  const cell = (x, z) => [Math.max(0, Math.min(nx - 1, Math.floor((x - x0) / C))), Math.max(0, Math.min(nz - 1, Math.floor((z - z0) / C)))];
  const centre = (i, j) => new THREE.Vector3(x0 + (i + 0.5) * C, 0, z0 + (j + 0.5) * C);
  const clear = (a, b) => {                                   // a straight walk from a to b stays on free floor
    const n = Math.ceil(a.distanceTo(b) / (C * 0.5));
    for (let k = 1; k < n; k++) { const t = k / n; if (!ok(a.x + (b.x - a.x) * t, a.z + (b.z - a.z) * t)) return false; }
    return true;
  };
  const nearestFree = (i, j) => {
    if (free[j * nx + i]) return [i, j];
    for (let r = 1; r < 8; r++) for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
      const a = i + di, b = j + dj; if (a >= 0 && b >= 0 && a < nx && b < nz && free[b * nx + a]) return [a, b];
    }
    return [i, j];
  };
  function path(from, to) {
    const [si, sj] = nearestFree(...cell(from.x, from.z)), [ti, tj] = nearestFree(...cell(to.x, to.z));
    const N = nx * nz, g = new Float32Array(N).fill(Infinity), came = new Int32Array(N).fill(-1), shut = new Uint8Array(N);
    const open = [[0, sj * nx + si]]; g[sj * nx + si] = 0;
    const h = (k) => Math.hypot(k % nx - ti, Math.floor(k / nx) - tj);
    const goal = tj * nx + ti;
    while (open.length) {
      let bi = 0; for (let q = 1; q < open.length; q++) if (open[q][0] < open[bi][0]) bi = q;
      const [, k] = open.splice(bi, 1)[0];
      if (k === goal) break;
      if (shut[k]) continue; shut[k] = 1;
      const i = k % nx, j = Math.floor(k / nx);
      for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
        const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= nx || b >= nz) continue;
        const n = b * nx + a; if (!free[n] || shut[n]) continue;
        if (di && dj && (!free[j * nx + a] || !free[b * nx + i])) continue;   // no cutting corners
        const ng = g[k] + (di && dj ? 1.414 : 1);
        if (ng < g[n]) { g[n] = ng; came[n] = k; open.push([ng + h(n), n]); }
      }
    }
    if (came[goal] < 0 && goal !== sj * nx + si) return [to.clone()];
    const pts = [];
    for (let k = goal; k >= 0 && k !== sj * nx + si; k = came[k]) pts.push(centre(k % nx, Math.floor(k / nx)));
    pts.reverse(); pts[pts.length - 1] = to.clone().setY(0);
    // pull the string tight: skip every corner you can see past
    const out = []; let a = from.clone().setY(0), k = 0;
    while (k < pts.length) {
      let far = k; for (let q = pts.length - 1; q > k; q--) if (clear(a, pts[q])) { far = q; break; }
      out.push(pts[far]); a = pts[far]; k = far + 1;
    }
    return out;
  }
  return { path, ok };
}

export async function createVisitors(scene, gal, { me } = {}) {
  const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
  const load = (url) => loader.loadAsync(url).then((g) => { restyle(g.scene); return g; });
  const nav = makeNav(gal);
  const list = [];
  const taken = new Map();                          // painting → visitor looking at it
  const rnd = Math.random;

  // a place to stand before painting p: back from it, a little to one side
  const standFor = (p, side) => {
    const lat = new THREE.Vector3(-p.normal.z, 0, p.normal.x);
    for (const d of [1.9, 1.6, 2.3, 1.4]) {
      const s = p.center.clone().addScaledVector(p.normal, d).addScaledVector(lat, side * (0.45 + rnd() * 0.35)).setY(0);
      if (nav.ok(s.x, s.z)) return s;
    }
    return null;
  };
  function choose(v) {
    // somewhere not too far, not already being looked at, not the one just seen
    const near = gal.pieces.filter(p => !taken.has(p.i) && p.i !== v.last)
      .map(p => ({ p, d: p.center.distanceTo(v.root.position) + rnd() * 9 })).sort((a, b) => a.d - b.d);
    for (const { p } of near.slice(0, 6)) {
      const spot = standFor(p, rnd() < 0.5 ? -1 : 1); if (!spot) continue;
      if (v.target != null) taken.delete(v.target);
      taken.set(p.i, v); v.target = p.i; v.last = p.i;
      v.look = p.center.clone().setY(0);
      v.route = nav.path(v.root.position, spot);
      v.state = 'walk'; v.play('walk');
      return;
    }
    v.state = 'look'; v.wait = 3;
  }

  for (const [n, C] of CAST.entries()) {
    let g;
    try { g = await load(`./models/people/${C.id}.glb`); } catch (e) { console.warn('visitor', C.id, e); continue; }
    const root = new THREE.Group();
    const body = g.scene; body.scale.setScalar(SCALE); root.add(body); root.add(blobShadow(0.32));
    const mixer = new THREE.AnimationMixer(body);
    const clips = Object.fromEntries(g.animations.map((a) => [a.name, mixer.clipAction(a)]));
    if (clips.walk) clips.walk.timeScale = WALK;
    const v = { ...C, root, body, mixer, clips, cur: null, state: 'look', wait: 1 + rnd() * 4, route: [], target: null, last: -1, look: null, prop: null };
    v.play = (name, fade = 0.35) => {
      const clip = name === 'idle' && v.act ? v.act : name;           // the reader keeps reading, the photographer keeps her phone up
      if (v.cur === clip || !clips[clip]) return;
      const next = clips[clip].reset().play();
      if (v.cur) clips[v.cur].crossFadeTo(next, fade, false);
      v.cur = clip;
      if (v.prop) v.prop.visible = clip === v.act;
    };
    if (C.act) {
      try {
        const prop = await load(`./models/people/${C.id}-${C.act}.glb`);
        prop.scene.scale.setScalar(SCALE); root.add(prop.scene);
        v.prop = prop.scene; v.propMixer = new THREE.AnimationMixer(prop.scene);
        if (prop.animations[0]) v.propMixer.clipAction(prop.animations[0]).play();
      } catch { /* no prop: they just look */ }
    }
    // start in front of a painting, already looking, spread down the hall
    const p = gal.pieces[Math.floor((n + 0.5) / CAST.length * gal.pieces.length)];
    const spot = p && !taken.has(p.i) && standFor(p, n % 2 ? 1 : -1);
    if (spot) {
      root.position.copy(spot); taken.set(p.i, v); v.target = v.last = p.i; v.look = p.center.clone().setY(0);
      root.rotation.y = Math.atan2(v.look.x - spot.x, v.look.z - spot.z);
    } else root.position.set((rnd() - 0.5) * 4, 0, -gal.D / 2);
    v.play('idle', 0);
    mixer.setTime(rnd() * 3);
    scene.add(root);
    list.push(v);
  }

  const tmp = new THREE.Vector3();
  function update(dt) {
    for (const v of list) {
      v.mixer.update(dt); v.propMixer?.update(dt);
      const P = v.root.position;
      if (v.state === 'walk') {
        const tgt = v.route[0];
        if (!tgt) { v.state = 'look'; v.wait = 7 + rnd() * 12; v.play('idle'); continue; }
        tmp.subVectors(tgt, P).setY(0);
        const d = tmp.length();
        // give way: someone (or you) right ahead → wait a beat
        let blockedBy = false;
        if (me && me.pos.distanceTo(tmp.set(P.x, me.pos.y, P.z)) < 0.75) blockedBy = true;
        tmp.subVectors(tgt, P).setY(0);
        for (const o of list) if (o !== v && o.state === 'walk' && o.root.position.distanceTo(P) < 0.6 && tmp.dot(o.root.position.clone().sub(P)) > 0) blockedBy = true;
        if (blockedBy) { v.hold = (v.hold || 0) + dt; if (v.hold < 1.5) { v.play('idle'); continue; } }   // (then on round them)
        else v.hold = 0;
        v.play('walk');
        const step = Math.min(d, SPEED * dt);
        if (d > 1e-4) {
          P.addScaledVector(tmp.normalize(), step);
          const want = Math.atan2(tmp.x, tmp.z);
          v.root.rotation.y += Math.atan2(Math.sin(want - v.root.rotation.y), Math.cos(want - v.root.rotation.y)) * Math.min(1, dt * 8);
        }
        if (d - step < 0.02) v.route.shift();
      } else {
        // looking: turn to face the painting, then stand a while
        if (v.look) {
          const want = Math.atan2(v.look.x - P.x, v.look.z - P.z);
          v.root.rotation.y += Math.atan2(Math.sin(want - v.root.rotation.y), Math.cos(want - v.root.rotation.y)) * Math.min(1, dt * 3);
        }
        v.wait -= dt;
        if (v.wait <= 0) choose(v);
      }
    }
  }
  return { update, list };
}
