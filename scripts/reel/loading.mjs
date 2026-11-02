// Films the two loading screens: unwrapping the parcels (U) and the crew hanging a painting (H).
import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require('playwright'); import fs from 'fs';
const PREVIEW = !!process.env.PREVIEW, DT = 1000 / 30;
const UN = +(process.env.UN || 165), HN = +(process.env.HN || 105), WARM = +(process.env.WARM || 90), EVERY = +(process.env.EVERY || 30);
fs.mkdirSync('loadframes', { recursive: true });
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: PREVIEW ? { width: 540, height: 960 } : { width: 1080, height: 1920 } });
await p.addInitScript({ path: 'vclock.js' });
await p.addInitScript(() => addEventListener('DOMContentLoaded', () => window.__freeze()));
p.on('pageerror', e => console.log('ERR', String(e)));
// hold the paintings back and let them in one at a time, so the parcels arrive at an easy pace
const held = [];
await p.route('**/artworks/web/*.webp', (r) => held.push(r));
await p.goto('http://localhost:8123/');
await p.waitForFunction(() => document.querySelector('#load canvas'), null, { timeout: 60000 });
let f = 0;
const release = () => { const r = held.shift(); if (r) r.continue(); };
for (let i = 0; i < 3; i++) release();
const tick = async (cap, name) => {
  if (f % EVERY === 0) release(); f++;
  await p.evaluate((ms) => window.__step(ms, false), DT);
  if (cap) await p.screenshot({ path: name, type: 'jpeg', quality: 92 });
};
for (let i = 0; i < WARM; i++) { await tick(false); if (i % 10 === 0) await new Promise(r => setTimeout(r, 50)); }
let t0 = Date.now();
for (let i = 0; i < UN; i++) {
  if (PREVIEW && i % 40) { await tick(false); continue; }
  await tick(true, `loadframes/u${String(i).padStart(5, '0')}.jpg`);
}
console.log('U', UN, ((Date.now() - t0) / 1000).toFixed(0) + 's');
// the hanging screen: shown over everything, its CSS animations stepped by hand
for (const r of held.splice(0)) await r.continue().catch(() => {}); await p.unroute('**/artworks/web/*.webp');
await p.evaluate(() => {
  const st = document.createElement('style');
  st.textContent = '#fade .crew { transform: scale(2.3); margin: 640px 0 300px; } #fade span { font-size: 80px; }';
  document.head.appendChild(st);
  document.querySelector('#load').style.display = 'none';
  const fade = document.querySelector('#fade');
  fade.querySelector('span').textContent = 'hanging the paintings…';
  fade.querySelector('.pic').setAttribute('href', './artworks/web/art_IMG_0658.webp');
  fade.style.transition = 'none';
  fade.classList.add('on', 'hanging');
  getComputedStyle(fade).opacity;
  window.__anims = document.getAnimations(); for (const a of window.__anims) a.pause();
});
await p.waitForFunction(() => { const i = new Image(); i.src = './artworks/web/art_IMG_0658.webp'; return i.complete; }, null, { timeout: 30000 }).catch(() => {});
await p.waitForTimeout(1500);
t0 = Date.now();
for (let i = 0; i < HN; i++) {
  await p.evaluate((t) => { for (const a of window.__anims) a.currentTime = t; }, i * DT);
  if (PREVIEW && i % 35) continue;
  await p.screenshot({ path: `loadframes/h${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 });
}
console.log('H', HN, ((Date.now() - t0) / 1000).toFixed(0) + 's');
await b.close();
