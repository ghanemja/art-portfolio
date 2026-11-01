// ─── THE PORTFOLIO: a floating museum you can walk into ──────────────────────
// Outside: orbit the island (drag, scroll/pinch to zoom); click the open door or "Enter".
// Inside: drag to look, WASD / arrows to walk, click the floor to walk there, click a
// painting (or its card) to see it up close. "All works" lists everything at once.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { styleTick } from './style.js';
import { buildIsland, MUSEUM_Z, DOOR_Z } from './island.js';
import { buildGallery } from './gallery.js';
import { createViewer } from './viewer.js';
import { createVisitors } from './visitors.js';
import { createUnwrap } from './loading.js';
import { ARTIST, WORKS, TOUR } from './collection.js';

const $ = (s) => document.querySelector(s);
const coarse = matchMedia('(pointer: coarse)').matches;

// ── the page's words ──
$('#card h1').textContent = ARTIST.name;
$('#card p').innerHTML = `${ARTIST.tagline} · © ${ARTIST.name}, all rights reserved` + (ARTIST.links?.length ? ' · ' + ARTIST.links.map(([t, u]) => `<a href="${u}" target="_blank" rel="noopener">${t}</a>`).join(' · ') : '');
const HINT_OUT = coarse ? 'drag to fly round · pinch to zoom · tap the door to go in' : 'drag to fly round · scroll to zoom · click the open door to go in';
const HINT_IN = coarse ? 'drag to look · tap the floor to walk · tap a painting' : 'drag to look · WASD / arrows or click the floor to walk · click a painting';

// ── renderer ──
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, coarse ? 1.5 : 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;          // gouache: colours as painted
document.body.prepend(renderer.domElement);
const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.08, 1400);
addEventListener('resize', () => {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
});

// ── load: the fonts the canvases letter with, then every painting's small copy ──
const fill = $('#load .fill');
const unwrap = createUnwrap($('#load'), WORKS.length);   // the parcels (loading.js)
await Promise.all(['700 40px Caveat', '600 40px Caveat', '400 20px "Patrick Hand"'].map(f => document.fonts.load(f).catch(() => {})));
const textures = new Map();
{
  const loader = new THREE.TextureLoader();
  const maxAniso = renderer.capabilities.getMaxAnisotropy();
  let done = 0;
  await Promise.all(WORKS.map(w => new Promise((res) => {
    const ok = (t) => {
      t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = Math.min(8, maxAniso);
      textures.set(w.file, t); fill.style.width = (++done / WORKS.length * 100) + '%'; unwrap.add(t.image, w.title); res();
    };
    loader.load(`./artworks/web/${w.file}.webp`, ok, undefined, () => loader.load(`./artworks/${w.file}.jpg`, ok, undefined, () => {
      // a missing picture: a blank canvas, so the hang still works
      const cv = document.createElement('canvas'); cv.width = cv.height = 4; const c = cv.getContext('2d'); c.fillStyle = '#efe4cc'; c.fillRect(0, 0, 4, 4);
      console.warn('missing painting', w.file); ok(new THREE.CanvasTexture(cv));
    }));
  })));
}

const viewer = createViewer(renderer, textures);
let visitors = null;

await unwrap.finish();                        // let the last parcel land

// ── outside ──
const outside = new THREE.Scene();
const island = buildIsland(outside, { textures });
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.target.set(0, 2.2, MUSEUM_Z - 4);
orbit.enableDamping = true; orbit.dampingFactor = 0.08;
orbit.minDistance = 9; orbit.maxDistance = 80; orbit.maxPolarAngle = 2.05;
orbit.autoRotate = true; orbit.autoRotateSpeed = 0.35;
orbit.enablePan = false;
orbit.addEventListener('start', () => { orbit.autoRotate = false; clearTimeout(orbit._idle); });
orbit.addEventListener('end', () => { clearTimeout(orbit._idle); orbit._idle = setTimeout(() => { if (mode === 'outside') orbit.autoRotate = true; }, 9000); });

// ── inside (built the first time you go in) ──
let inside = null, gal = null;
const me = { pos: new THREE.Vector3(), yaw: 0, pitch: 0 };
let auto = null;          // a glide: { from, to, yaw0, yaw1, pitch0, pitch1, t, dur, done }
let tour = null;          // the guided tour: { k, wait }

// ── the modes ──
let mode = 'loading';
const fade = $('#fade');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function fadeOut(text = '') { fade.querySelector('span').textContent = text; fade.classList.add('on'); await sleep(470); }
function fadeIn() { fade.classList.remove('on'); }

function setUI() {
  const inn = mode === 'inside';
  $('#enter').style.display = inn ? 'none' : '';
  $('#out').style.display = inn ? '' : 'none';
  $('#tour').style.display = inn ? '' : 'none';
  $('#tour').classList.toggle('hide', !inn);
  $('#tour').textContent = tour ? 'Stop the tour ■' : 'Guided tour ▶';
  $('#hint').textContent = inn ? HINT_IN : HINT_OUT;
  document.body.classList.toggle('pad', inn && PAD);
}

// the intro: swoop in from far out over the landscape
const intro = { t: 0, dur: 4.2, from: new THREE.Vector3(70, 34, 120), to: new THREE.Vector3(15, 6.5, 23) };
camera.position.copy(intro.from); camera.lookAt(orbit.target);

async function enter() {
  if (mode !== 'outside') return;
  mode = 'going';
  orbit.enabled = false; orbit.autoRotate = false;
  closeAll();
  // glide up the walk to the door
  const p0 = camera.position.clone(), t0 = orbit.target.clone();
  const p1 = new THREE.Vector3(0, 2.0, DOOR_Z + 7.5), p2 = new THREE.Vector3(0, 1.6, DOOR_Z + 0.4), look = new THREE.Vector3(0, 1.5, DOOR_Z - 6);
  const curve = new THREE.QuadraticBezierCurve3(p0, p1, p2);
  const T = 1.9, start = performance.now();
  await new Promise((res) => {
    const step = () => {
      const k = Math.min(1, (performance.now() - start) / 1000 / T), e = k * k * (3 - 2 * k);
      camera.position.copy(curve.getPoint(e)).add(new THREE.Vector3(0, island.isle.position.y * (1 - e), 0));
      camera.lookAt(new THREE.Vector3().lerpVectors(t0, look, Math.min(1, e * 1.4)));
      if (k > 0.78 && !fade.classList.contains('on')) fade.classList.add('on');
      if (k < 1) requestAnimationFrame(step); else res();
    };
    step();
  });
  fade.querySelector('span').textContent = inside ? '' : 'hanging the paintings…';
  fade.classList.add('on');
  await sleep(480);
  if (!inside) {
    await sleep(30);
    inside = new THREE.Scene();
    gal = buildGallery(inside, { textures });
    createVisitors(inside, gal, { me }).then(v => { visitors = v; }, (e) => console.warn('no visitors', e));   // (they stroll in while you look about)
  }
  me.pos.copy(gal.start); me.yaw = 0; me.pitch = 0; auto = null;
  camera.fov = 62; camera.updateProjectionMatrix();
  mode = 'inside'; setUI();
  applyLook();
  fadeIn();
}

async function leave() {
  if (mode !== 'inside') return;
  mode = 'going'; tour = null; auto = null; closeAll();
  await fadeOut();
  camera.fov = 45; camera.updateProjectionMatrix();
  camera.position.set(0, 2.4, DOOR_Z + 9); camera.lookAt(0, 1.8, DOOR_Z);
  orbit.target.set(0, 2.2, MUSEUM_Z - 4);
  // back off to the usual view
  const from = camera.position.clone(), to = new THREE.Vector3(10, 6, 26), start = performance.now();
  mode = 'outside'; setUI(); orbit.enabled = false;
  fadeIn();
  const step = () => {
    const k = Math.min(1, (performance.now() - start) / 1600), e = k * k * (3 - 2 * k);
    camera.position.lerpVectors(from, to, e);
    camera.lookAt(orbit.target);
    if (k < 1 && mode === 'outside') requestAnimationFrame(step); else { orbit.enabled = true; orbit.update(); }
  };
  step();
}

// ── looking about inside ──
function applyLook() {
  camera.position.copy(me.pos);
  camera.rotation.order = 'YXZ';
  camera.rotation.set(me.pitch, me.yaw, 0);
}
const wrapA = (a) => Math.atan2(Math.sin(a), Math.cos(a));
// glide to a spot, turning to face a point
function glide(to, lookAt, dur = null) {
  const d = lookAt.clone().sub(to);
  const yaw1 = Math.atan2(-d.x, -d.z), pitch1 = Math.atan2(d.y, Math.hypot(d.x, d.z));
  const dist = to.distanceTo(me.pos);
  auto = { from: me.pos.clone(), to: to.clone(), yaw0: me.yaw, yaw1: me.yaw + wrapA(yaw1 - me.yaw), pitch0: me.pitch, pitch1, t: 0,
    dur: dur ?? Math.max(0.6, Math.min(3.2, dist / 2.6 + Math.abs(wrapA(yaw1 - me.yaw)) * 0.25)) };
}
function goToWork(i) {
  if (!gal) return;
  const p = gal.pieces.find(q => q.i === i); if (!p) return;
  glide(gal.viewSpot(p), p.center.clone().setY(p.center.y - 0.05));
}

// keys
const keys = new Set();
// phones: the on-screen D-pad (inside only) holds down the same keys the arrows do
const PAD = coarse || navigator.maxTouchPoints > 0 || new URLSearchParams(location.search).has('pad');
for (const b of document.querySelectorAll('#pad button')) {
  const k = b.dataset.k;
  const down = (e) => { e.preventDefault(); keys.add(k); b.classList.add('on'); auto = null; stopTour(); try { b.setPointerCapture(e.pointerId); } catch { /* (no capture: pointerup still ends it) */ } };
  const up = () => { keys.delete(k); b.classList.remove('on'); };
  b.addEventListener('pointerdown', down);
  for (const ev of ['pointerup', 'pointercancel', 'lostpointercapture']) b.addEventListener(ev, up);
  b.addEventListener('contextmenu', (e) => e.preventDefault());
}
addEventListener('keydown', (e) => {
  if (e.target.closest?.('input, textarea')) return;
  const k = e.key.toLowerCase();
  if (!$('#view').classList.contains('hide')) {
    if (k === 'arrowleft') step(-1); else if (k === 'arrowright') step(1); else if (k === 'escape') closeView();
    return;
  }
  if (k === 'escape') { closeAll(); return; }
  if (mode === 'outside' && k === 'enter') enter();
  keys.add(k);
  if (mode === 'inside' && ['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(k)) { auto = null; stopTour(); e.preventDefault(); }
});
addEventListener('keyup', (e) => keys.delete(e.key.toLowerCase()));
addEventListener('blur', () => keys.clear());

// pointer: drag to look; a click (no real drag) picks what's under it
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
const cv = renderer.domElement;
let drag = null;
const pickAt = (x, y, objs) => { ndc.set(x / innerWidth * 2 - 1, -(y / innerHeight) * 2 + 1); ray.setFromCamera(ndc, camera); return ray.intersectObjects(objs, false)[0] || null; };
const clickables = () => gal ? [...gal.pieces.flatMap(p => [p.canvas, p.card]), gal.floor, gal.exit] : [];
cv.addEventListener('pointerdown', (e) => {
  drag = { x: e.clientX, y: e.clientY, moved: 0, id: e.pointerId };
  if (mode === 'inside') cv.setPointerCapture(e.pointerId);
});
cv.addEventListener('pointermove', (e) => {
  if (drag && drag.id === e.pointerId) {
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY;
    if (mode === 'inside' && drag.moved > 4) {
      auto = null; stopTour();
      const s = coarse ? 0.006 : 0.0042;
      me.yaw += dx * s; me.pitch = THREE.MathUtils.clamp(me.pitch + dy * s, -1.0, 1.0);
    }
  } else if (!coarse) hover(e.clientX, e.clientY);
});
cv.addEventListener('pointerup', (e) => {
  if (!drag || drag.id !== e.pointerId) return;
  const click = drag.moved < 8; drag = null;
  if (!click) return;
  if (mode === 'outside') {
    if (pickAt(e.clientX, e.clientY, [island.door])) enter();
  } else if (mode === 'inside') {
    const hit = pickAt(e.clientX, e.clientY, clickables()); if (!hit) return;
    const o = hit.object;
    if (o.userData.work != null) { stopTour(); goToWork(o.userData.work); openView(o.userData.work); }
    else if (o === gal.exit) leave();
    else if (o === gal.floor) {
      stopTour();
      const p = hit.point; if (gal.blocked(p.x, p.z)) return;
      const to = new THREE.Vector3(p.x, gal.EYE, p.z), d = to.clone().sub(me.pos);
      glide(to, to.clone().add(d.setY(0).normalize()).setY(gal.EYE + me.pitch * 0.5 * 0), null);
    }
  }
});
cv.addEventListener('pointercancel', () => { drag = null; });
const label = $('#label');
function hover(x, y) {
  let over = null, cursor = '';
  if (mode === 'outside') { if (pickAt(x, y, [island.door])) { cursor = 'pointer'; over = 'step inside'; } }
  else if (mode === 'inside') {
    const hit = pickAt(x, y, clickables());
    if (hit?.object.userData.work != null) { cursor = 'pointer'; over = WORKS[hit.object.userData.work].title; }
    else if (hit?.object === gal.exit) { cursor = 'pointer'; over = 'back out to the island'; }
    else if (hit?.object === gal.floor) cursor = 'crosshair';
  }
  cv.style.cursor = cursor;
  if (over) { label.textContent = over; label.classList.remove('hide'); } else if (!tour) label.classList.add('hide');   // (the tour keeps its caption)
}

// ── the close look ──
const view = $('#view');
view.addEventListener('pointermove', (e) => viewer.point(e.clientX, e.clientY));
let viewing = -1;
function openView(i) {
  viewing = (i + WORKS.length) % WORKS.length;
  const w = WORKS[viewing];
  viewer.show(viewing);                                      // the painting in its own frame, full size (viewer.js)
  view.querySelector('.info b').textContent = w.title;
  view.querySelector('.info span').textContent = [ARTIST.name, w.year, w.medium, `${viewing + 1} / ${WORKS.length}`].filter(Boolean).join(' · ') + (w.note ? ' — ' + w.note : '');
  view.classList.remove('hide'); document.body.classList.add('viewing');
  label.classList.add('hide');
}
function closeView() { view.classList.add('hide'); document.body.classList.remove('viewing'); viewing = -1; viewer.hide(); }
function step(d) { const i = (viewing + d + WORKS.length) % WORKS.length; if (mode === 'inside') goToWork(i); openView(i); }
$('#vx').onclick = closeView;
$('#prev').onclick = () => step(-1);
$('#next').onclick = () => step(1);
view.addEventListener('click', (e) => { if (e.target === view) closeView(); });

// ── every work at once ──
const index = $('#index');
{
  const grid = index.querySelector('.grid');
  WORKS.forEach((w, i) => {
    const f = document.createElement('figure');
    f.innerHTML = `<img loading="lazy" src="./artworks/web/${w.file}.webp" alt=""><figcaption></figcaption>`;
    f.querySelector('img').alt = w.title; f.querySelector('figcaption').textContent = w.title;
    f.onclick = () => { index.classList.add('hide'); if (mode === 'inside') { stopTour(); goToWork(i); } openView(i); };
    grid.appendChild(f);
  });
}
$('#all').onclick = () => index.classList.remove('hide');
$('#ix').onclick = () => index.classList.add('hide');
function closeAll() { closeView(); index.classList.add('hide'); }

// ── the guided tour: from painting to painting, a pause at each ──
function stopTour() { if (tour) { tour = null; setUI(); label.classList.add('hide'); } }
$('#tour').onclick = () => {
  if (tour) { stopTour(); return; }
  closeAll();
  tour = { k: 0, wait: 0 }; tourStop(); setUI();
};
// the tour visits just the featured paintings (collection.js TOUR), round and round
const tourList = () => { const l = TOUR.map(f => WORKS.findIndex(w => w.file === f)).filter(i => i >= 0); return l.length ? l : WORKS.map((_, i) => i); };
function tourStop() {
  const l = tourList(), i = l[tour.k % l.length];
  goToWork(i);
  label.textContent = `${WORKS[i].title} · ${tour.k % l.length + 1} of ${l.length}`; label.classList.remove('hide');
}
$('#enter').onclick = enter;
$('#out').onclick = leave;

// ── the loop ──
const clock = new THREE.Clock();
const fwd = new THREE.Vector3(), rgt = new THREE.Vector3();
function frame() {
  const dt = Math.min(0.05, clock.getDelta()), t = clock.elapsedTime;
  styleTick(t, renderer.domElement.width, renderer.domElement.height);
  if (mode === 'outside' || mode === 'going' && !inside?.visible) island.tick(t);
  if (intro.t < intro.dur && mode === 'outside') {
    intro.t += dt; const k = Math.min(1, intro.t / intro.dur), e = 1 - Math.pow(1 - k, 3);
    camera.position.lerpVectors(intro.from, intro.to, e); camera.lookAt(orbit.target);
    if (k >= 1) orbit.update();
  } else if (mode === 'outside' && orbit.enabled) orbit.update();

  if (mode === 'inside') {
    // walking by keys
    const k = (a, b) => keys.has(a) || keys.has(b);
    const mv = (k('w', 'arrowup') ? 1 : 0) - (k('s', 'arrowdown') ? 1 : 0);
    const st = (k('d', '') ? 1 : 0) - (k('a', '') ? 1 : 0);
    const turn = (keys.has('arrowleft') ? 1 : 0) - (keys.has('arrowright') ? 1 : 0);
    me.yaw += turn * 1.8 * dt;
    if (mv || st) {
      const sp = (keys.has('shift') ? 4.6 : 2.6) * dt;
      fwd.set(-Math.sin(me.yaw), 0, -Math.cos(me.yaw)); rgt.set(Math.cos(me.yaw), 0, -Math.sin(me.yaw));
      const dx = (fwd.x * mv + rgt.x * st) * sp, dz = (fwd.z * mv + rgt.z * st) * sp;
      if (!gal.blocked(me.pos.x + dx, me.pos.z)) me.pos.x += dx;          // (slide along walls)
      if (!gal.blocked(me.pos.x, me.pos.z + dz)) me.pos.z += dz;
      if (me.pos.z > -0.55 && Math.abs(me.pos.x) < 0.9 && mv > 0 && Math.abs(wrapA(me.yaw)) > 2.4) leave();   // walked back out of the door
    }
    if (auto) {
      auto.t += dt; const a = Math.min(1, auto.t / auto.dur), e = a * a * (3 - 2 * a);
      me.pos.lerpVectors(auto.from, auto.to, e);
      me.yaw = auto.yaw0 + (auto.yaw1 - auto.yaw0) * e; me.pitch = auto.pitch0 + (auto.pitch1 - auto.pitch0) * e;
      if (a >= 1) auto = null;
    }
    if (tour && !auto && viewing < 0) {
      tour.wait += dt;
      if (tour.wait > 7) { tour.wait = 0; tour.k++; tourStop(); }
    }
    me.pos.y = gal.EYE + Math.sin(t * 1.3) * 0.004;
    applyLook();
    visitors?.update(dt);
    if (viewing < 0) renderer.render(inside, camera);
  } else if (viewing < 0) {
    renderer.render(outside, camera);
  }
  if (viewing >= 0) viewer.render(t, dt);
  requestAnimationFrame(frame);
}

// go
mode = 'outside'; setUI();
requestAnimationFrame(frame);
$('#load').classList.add('hide');
setTimeout(() => unwrap.stop(), 700);
window.__portfolio = { enter, leave, openView, goToWork, get mode() { return mode; }, get gal() { return gal; }, get visitors() { return visitors; }, me };   // (for the smoke test)
