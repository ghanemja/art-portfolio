// Headless check: the page loads with no console errors, the island renders, you can go in,
// walk to a painting, open the viewer, and come back out. Screenshots go to scripts/shots/.
// Needs a local server at the repo root:  python3 -m http.server 8123   then  node scripts/smoke.mjs
import { createRequire } from 'module';
import { execSync } from 'child_process';
const require = createRequire(import.meta.url);
let pw; try { pw = require('playwright'); } catch { pw = require(execSync('npm root -g').toString().trim() + '/playwright'); }   // (a global install works too)
const { chromium } = pw;
import { mkdirSync } from 'fs';
const URL = process.env.URL || 'http://localhost:8123/';
const OUT = new globalThis.URL('./shots/', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
// THREE_DIR=<unpacked three@0.160.0 package> serves three locally (for machines that can't reach unpkg):
//   npm pack three@0.160.0 && tar xzf three-0.160.0.tgz   → THREE_DIR=./package
if (process.env.THREE_DIR) await page.route('https://unpkg.com/three@0.160.0/**', (r) =>
  r.fulfill({ path: r.request().url().replace('https://unpkg.com/three@0.160.0/', process.env.THREE_DIR.replace(/\/$/, '') + '/'), contentType: 'application/javascript' }));
const errors = [];
const fail = (why) => { console.error('FAIL: ' + why + '\n' + errors.join('\n')); process.exit(1); };
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));
page.on('requestfailed', r => errors.push('failed: ' + r.url()));
page.on('response', r => { if (r.status() >= 400) errors.push(r.status() + ' ' + r.url()); });
const t0 = Date.now();
await page.goto(URL);
await page.waitForFunction(() => window.__portfolio?.mode === 'outside', null, { timeout: 120000 }).catch(() => fail('never got outside'));
console.log('outside after', ((Date.now() - t0) / 1000).toFixed(1), 's');
await page.waitForTimeout(6000);
await page.screenshot({ path: OUT + '1-outside.png' });
const t1 = Date.now();
await page.evaluate(() => window.__portfolio.enter());
await page.waitForFunction(() => window.__portfolio.mode === 'inside', null, { timeout: 120000 }).catch(() => fail('never got inside'));
console.log('inside after', ((Date.now() - t1) / 1000).toFixed(1), 's; hall length', await page.evaluate(() => window.__portfolio.gal.D));
await page.waitForFunction(() => window.__portfolio.visitors?.list.length >= 6, null, { timeout: 60000 }).catch(() => fail('the visitors never arrived'));
console.log('visitors:', await page.evaluate(() => window.__portfolio.visitors.list.length));
await page.waitForTimeout(2500);
await page.screenshot({ path: OUT + '2-inside.png' });
await page.evaluate(() => window.__portfolio.goToWork(1));
await page.waitForTimeout(4000);
await page.screenshot({ path: OUT + '3-painting.png' });
await page.evaluate(() => window.__portfolio.goToWork(30));
await page.waitForTimeout(4500);
await page.screenshot({ path: OUT + '4-painting.png' });
await page.evaluate(() => window.__portfolio.openView(30));
await page.waitForTimeout(2500);
await page.screenshot({ path: OUT + '5-viewer.png' });
await page.evaluate(() => window.__portfolio.openView(2));
await page.waitForTimeout(2500);
await page.screenshot({ path: OUT + '5b-viewer.png' });
await page.keyboard.press('Escape');
await page.evaluate(() => window.__portfolio.leave());
await page.waitForTimeout(3000);
const back = await page.evaluate(() => window.__portfolio.mode);
await page.screenshot({ path: OUT + '6-back-outside.png' });
await browser.close();
if (back !== 'outside') errors.push('did not get back outside: ' + back);
if (errors.length) { console.error('FAIL\n' + errors.join('\n')); process.exit(1); }
console.log('ok');
