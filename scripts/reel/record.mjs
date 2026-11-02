// Films the Reel's shots from the live site, frame by frame on a virtual clock.
// PREVIEW=1: 540x960, first/last frame of each shot only.
import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require('playwright'); import fs from 'fs';
const PREVIEW = !!process.env.PREVIEW, FPS = 30, DT = 1000 / FPS;
const OUT = PREVIEW ? 'preview/' : 'frames/'; fs.mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: PREVIEW ? { width: 540, height: 960 } : { width: 1080, height: 1920 } });
await p.addInitScript({ path: 'vclock.js' });
p.on('pageerror', e => console.log('ERR', String(e)));
await p.goto('http://localhost:8123/');
await p.waitForFunction(() => window.__portfolio?.mode === 'outside', null, { timeout: 300000 });
await p.evaluate(() => window.__freeze());
const real = (ms) => new Promise(r => setTimeout(r, ms));
const idle = async (n, ms = 50) => { for (let i = 0; i < n; i++) await p.evaluate(([ms]) => window.__step(ms, false), [ms]); };
let fno = 0;
// a shot: n frames; setup(k in 0..1) runs in the page before each frame
async function shot(name, n, fn, arg = {}) {
  const t0 = Date.now();
  for (const i of PREVIEW ? [0, n - 1] : [...Array(n).keys()]) {
    const keep = true;
    await p.evaluate(([src, k, arg]) => { new Function('k', 'P', 'arg', src)(k, window.__portfolio, arg); }, [fn, n > 1 ? i / (n - 1) : 0, arg]);
    const d = await p.evaluate(([ms, cap]) => window.__step(ms, cap), [DT, keep]);
    if (keep) fs.writeFileSync(PREVIEW ? `${OUT}${name}_${i === 0 ? 'a' : 'b'}.jpg` : `${OUT}f${String(fno).padStart(5, '0')}.jpg`, Buffer.from(d.split(',')[1], 'base64'));
    if (!PREVIEW) fno++;
  }
  console.log(name, n, 'frames', ((Date.now() - t0) / 1000).toFixed(0) + 's');
}
// finish the intro swoop off-camera, then take the camera over
await idle(90);
await p.evaluate(() => { const P = window.__portfolio; P.orbit.enabled = false; P.orbit.autoRotate = false; });
const ease = 'const e = k * k * (3 - 2 * k);';
const orbitCam = (a0, a1, r0, r1, h0, h1, ty = 2.2) => ease + `
  const a = ${a0} + (${a1} - ${a0}) * e, r = ${r0} + (${r1} - ${r0}) * e, h = ${h0} + (${h1} - ${h0}) * e;
  P.camera.position.set(Math.sin(a) * r, h, Math.cos(a) * r); P.camera.lookAt(0, ${ty}, 0);`;
// A — the hook: sweep round the floating island
await shot('A', 120, orbitCam(1.15, 0.45, 46, 34, 16, 9, 0));
// B — lesson 1: close on the museum front, leaves everywhere
await shot('B', 150, orbitCam(-0.5, 0.25, 19, 16, 3.5, 4.2, 3.2));
// C — lesson 2: low, under the island: the waterfall, the woods, the birds
await shot('C', 150, orbitCam(-0.15, 0.4, 58, 50, -5, 1, -7));
// go in (off camera) and let the visitors arrive
p.evaluate(() => window.__portfolio.enter());
for (let i = 0; i < 400; i++) {
  await p.evaluate(() => window.__step(50, false));
  if (await p.evaluate(() => window.__portfolio.mode === 'inside' && !!window.__portfolio.visitors)) break;
  await real(150);
}
await idle(60);   // let them stroll off the doorstep
// D — lesson 3: walk down the hall to the horses under their picture light
await shot('D', 165, ease + `
  const g = P.gal, pc = g.pieces.find(q => q.i === arg.w), to = g.viewSpot(pc), look = pc.center.clone().setY(pc.center.y - 0.05);
  const from = g.start.clone();
  P.me.pos.lerpVectors(from, to, e);
  const d = look.clone().sub(to), yaw1 = Math.atan2(-d.x, -d.z), pitch1 = Math.atan2(d.y, Math.hypot(d.x, d.z));
  const yaw1w = Math.atan2(Math.sin(yaw1), Math.cos(yaw1));
  P.me.yaw = yaw1w * Math.min(1, e * 1.25); P.me.pitch = pitch1 * e;`, { w: 5 });
// E — lesson 4: quick cuts, painting after painting, close up
for (const [j, w] of [10, 7, 24, 0, 21, 13].entries()) {
  await p.evaluate((w) => window.__portfolio.openView(w), w);
  await shot('E' + j, 28, '');
}
await p.evaluate(() => document.querySelector('#vx').click());
// F — lesson 5: over a visitor's shoulder, looking at the painting with them
await shot('F', 135, ease + `
  const g = P.gal;
  if (!window.__fv) { window.__fv = P.visitors.list.find(v => v.state !== 'walk' && v.target != null) || P.visitors.list[0]; }
  const v = window.__fv, pc = g.pieces.find(q => q.i === v.target) || g.pieces[0];
  const c = pc.center.clone(), r = v.root.position.clone();
  const back = r.clone().sub(c).setY(0).normalize(), side = new P.camera.position.constructor(-back.z, 0, back.x);
  P.me.pos.copy(r).addScaledVector(back, 2.3 - 0.5 * e).addScaledVector(side, 0.9 - 1.4 * e).setY(g.EYE + 0.15);
  const look = c.clone().lerp(r.clone().setY(1.3), 0.35), d = look.sub(P.me.pos);
  P.me.yaw = Math.atan2(-d.x, -d.z); P.me.pitch = Math.atan2(d.y, Math.hypot(d.x, d.z));`);
// G — the call: back out, and rise away from the island
p.evaluate(() => window.__portfolio.leave());
await real(800); await idle(50);
await p.evaluate(() => { const P = window.__portfolio; P.orbit.enabled = false; });
await shot('G', 150, orbitCam(0.05, -0.35, 14, 40, 3, 14, 1.5));
await b.close();
console.log('done', fno);
