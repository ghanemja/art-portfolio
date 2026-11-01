// ─── THE CLOSE LOOK: one painting, in its own frame, filling the screen ──────
// The same frame it hangs in on the wall (gallery.js frameStyle: same moulding, same finish),
// built at full detail from art-heist's frame kit, the picture swapped up to the full-size
// image once that's loaded. It turns a little with the pointer so the carving catches the
// light. Drawn by the main renderer in place of the world while it's open.
import * as THREE from 'three';
import { paint, ink, PAL } from './style.js';
import { frameKit } from './museum.js';
import { frameSize, frameStyle } from './gallery.js';
import { WORKS } from './collection.js';

export function createViewer(renderer, textures) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x2b2231);
  scene.add(new THREE.HemisphereLight(0xfff6e8, 0x6a5a70, 1.15));
  const key = new THREE.DirectionalLight(0xfff1dc, 1.5); key.position.set(-2.5, 3.5, 4); scene.add(key);
  const camera = new THREE.PerspectiveCamera(28, innerWidth / innerHeight, 0.05, 50);
  // a soft pool of wall-light behind the frame
  {
    const cv = document.createElement('canvas'); cv.width = cv.height = 256;
    const c = cv.getContext('2d'), g = c.createRadialGradient(128, 128, 10, 128, 128, 128);
    g.addColorStop(0, 'rgba(255,236,200,0.32)'); g.addColorStop(1, 'rgba(255,236,200,0)');
    c.fillStyle = g; c.fillRect(0, 0, 256, 256);
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false }));
    glow.position.z = -0.6; glow.scale.setScalar(6); glow.userData.noInk = true; scene.add(glow);
    scene.userData.glow = glow;
  }
  const { ornateFrame } = frameKit({ S: (col, o = {}) => paint(col, { map: o.map, side: o.side, hatch: o.map ? 0 : 0.35 }), GOLD: paint(PAL.gold), lite: false });
  const loader = new THREE.TextureLoader();
  const holder = new THREE.Group(); scene.add(holder);
  let cur = -1, frame = null, size = null, full = null;
  const tilt = { x: 0, y: 0, tx: 0, ty: 0 };

  function clear() {
    if (!frame) return;
    frame.traverse(o => { if (o.isMesh) { o.geometry.dispose(); if (o.userData.painting) o.material.dispose(); } });
    holder.remove(frame); frame = null;
    if (full) { full.dispose(); full = null; }
  }
  function show(i) {
    if (i === cur && frame) return;
    clear(); cur = i;
    const w = WORKS[i], [style, finish] = frameStyle(i);
    size = frameSize(w.w / w.h);
    frame = new THREE.Group(); holder.add(frame);
    const F = ornateFrame(size.ow, size.oh, frame, style, { finish, art: textures.get(w.file), shape: w.shape || 'rect' });
    F.traverse(o => { if (o.isMesh && Math.max(o.scale.x, o.scale.y) < 0.012) o.userData.noInk = true; });
    ink(frame, 'mid');
    const canvas = F.userData.canvas;
    loader.load(`./artworks/${w.file}.jpg`, (t) => {                 // the full-size picture, once it's here
      if (cur !== i || !frame) { t.dispose(); return; }
      t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
      canvas.material.map = t; canvas.material.needsUpdate = true; full = t;
    });
    scene.userData.glow.scale.set(size.ow * 2.6, size.oh * 2.6, 1);
    fit();
  }
  // fit it in the space the page leaves: under the close button, above the caption, between the arrows
  function fit() {
    if (!size) return;
    const W = innerWidth, H = innerHeight, narrow = W < 640;
    const top = 70, bottom = narrow ? 140 : 160, side = narrow ? 24 : 96;
    camera.aspect = W / H; camera.updateProjectionMatrix();
    const th = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const fh = (H - top - bottom) / H, fw = (W - 2 * side) / W;
    const dist = Math.max(size.oh / (fh * th), size.ow / (fw * th * camera.aspect));
    const viewH = dist * th;
    camera.position.set(0, -((bottom - top) / 2 / H) * viewH, dist);
    camera.lookAt(0, camera.position.y, 0);
  }
  addEventListener('resize', fit);
  function point(x, y) { tilt.ty = (x / innerWidth - 0.5) * 0.35; tilt.tx = (y / innerHeight - 0.5) * 0.22; }
  function render(t, dt) {
    const k = 1 - Math.exp(-dt * 4);
    tilt.x += (tilt.tx - tilt.x) * k; tilt.y += (tilt.ty - tilt.y) * k;
    holder.rotation.set(tilt.x + Math.sin(t * 0.6) * 0.012, tilt.y + Math.sin(t * 0.4) * 0.03, 0);
    renderer.render(scene, camera);
  }
  return { show, render, point, hide: () => { clear(); cur = -1; } };
}
