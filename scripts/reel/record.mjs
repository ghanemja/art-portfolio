// Films the Reel's shots from the live site, frame by frame on a virtual clock.
// PREVIEW=1: 540x960, first/last frame of each shot only.
import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require('playwright'); import fs from 'fs';
const PREVIEW = !!process.env.PREVIEW, FPS = 30, DT = 1000 / FPS;
// each shot's length in frames, timed to the voiceover (shots.json: written by voedit/plan)
const N = JSON.parse(fs.readFileSync(process.env.SHOTS || 'shots.json', 'utf8'));
const OUT = PREVIEW ? 'preview/' : 'frames/'; fs.mkdirSync(OUT, { recursive: true });
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: PREVIEW ? { width: 540, height: 960 } : process.env.FAST ? { width: 720, height: 1280 } : { width: 1080, height: 1920 } });
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
await shot('A', N.A, orbitCam(1.25, 0.35, 46, 32, 16, 8.5, 0));
// B — lesson 1: close on the museum front, leaves everywhere
await shot('B', N.B, orbitCam(-0.75, 0.45, 20, 15.5, 3.4, 4.4, 3.2));
// C — lesson 2: low, under the island: the waterfall, the woods, the birds
await shot('C', N.C, orbitCam(-0.45, 0.6, 58, 48, -6, 1.5, -7));
// go in (off camera) and let the visitors arrive
p.evaluate(() => window.__portfolio.enter());
for (let i = 0; i < 400; i++) {
  await p.evaluate(() => window.__step(50, false));
  if (await p.evaluate(() => window.__portfolio.mode === 'inside' && !!window.__portfolio.visitors)) break;
  await real(150);
}
await idle(60);   // let them stroll off the doorstep
// D — lesson 3: walk down the hall to the horses under their picture light
await shot('D', N.D, `
  const kw = Math.min(1, k / 0.55), e = kw * kw * (3 - 2 * kw), push = Math.max(0, (k - 0.55) / 0.45);
  const g = P.gal, pc = g.pieces.find(q => q.i === arg.w), to = g.viewSpot(pc), look = pc.center.clone().setY(pc.center.y - 0.05);
  const from = g.start.clone();
  P.me.pos.lerpVectors(from, to, e);
  P.me.pos.lerp(look, push * 0.14);
  const d = look.clone().sub(to), yaw1 = Math.atan2(-d.x, -d.z), pitch1 = Math.atan2(d.y, Math.hypot(d.x, d.z));
  const yaw1w = Math.atan2(Math.sin(yaw1), Math.cos(yaw1));
  P.me.yaw = yaw1w * Math.min(1, e * 1.25); P.me.pitch = pitch1 * e;`, { w: 5 });
// E — lesson 4: quick cuts, painting after painting, close up
{ const L = [10, 7, 24, 0, 21, 13, 5, 1, 2, 26, 30, 36, 41, 47, 16, 19].slice(0, Math.max(1, Math.round(N.E / 28))), each = Math.floor(N.E / L.length);   // (about a second each)
  for (const [j, w] of L.entries()) {
    await p.evaluate((w) => window.__portfolio.openView(w), w);
    await shot('E' + j, j === L.length - 1 ? N.E - each * (L.length - 1) : each, '');
  } }
await p.evaluate(() => document.querySelector('#vx').click());
// F — lesson 5: over a visitor's shoulder, looking at the painting with them
await shot('F', N.F, ease + `
  const g = P.gal;
  if (!window.__fv) {
    const vs = P.visitors.list.filter(v => v.state !== 'walk' && v.target != null).sort((a, b) => b.wait - a.wait);
    const v = vs[0] || P.visitors.list[0]; v.wait = 99;                 // (they stay put for the shot)
    window.__fv = { v, pc: g.pieces.find(q => q.i === v.target) || g.pieces[0], r: v.root.position.clone() };
  }
  const { pc, r: r0 } = window.__fv, c = pc.center.clone(), r = r0.clone();
  const back = r.clone().sub(c).setY(0).normalize(), side = new P.camera.position.constructor(-back.z, 0, back.x);
  P.me.pos.copy(r).addScaledVector(back, 2.3 - 0.5 * e).addScaledVector(side, 0.9 - 1.4 * e).setY(g.EYE + 0.15);
  const look = c.clone().lerp(r.clone().setY(1.3), 0.35), d = look.sub(P.me.pos);
  P.me.yaw = Math.atan2(-d.x, -d.z); P.me.pitch = Math.atan2(d.y, Math.hypot(d.x, d.z));`);
// G — the call: back out, and rise away from the island
p.evaluate(() => window.__portfolio.leave());
await real(800); await idle(50);
await p.evaluate(() => { const P = window.__portfolio; P.orbit.enabled = false; });
await shot('G', N.G, orbitCam(0.05, -1.1, 14, 38, 3, 12, 1.5));
await b.close();
console.log('done', fno);
