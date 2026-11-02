// Records the site's own soundtrack (js/music.js) in real time: outside, then inside for the hall shots, then outside.
import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require('playwright'); import fs from 'fs';
const LEN = +(process.env.LEN || 46), IN_AT = +(process.env.IN_AT || 23), OUT_AT = +(process.env.OUT_AT || 38.5);
const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage();
p.on('pageerror', e => console.log('ERR', String(e)));
// no glassy chimes in the Reel (they ring on): serve music.js with the chime call taken out
const ROOT = process.env.ROOT || new URL('../../', import.meta.url).pathname;
await p.route('http://localhost:8123/js/music.js', r => r.fulfill({ contentType: 'application/javascript',
  body: fs.readFileSync(ROOT + '/js/music.js', 'utf8').replace(/\bchime\(C\.mel/, 'void (C.mel') }));
await p.route('http://localhost:8123/__rec.html', r => r.fulfill({ contentType: 'text/html', body: `<!doctype html><script type="module">
  const conn = AudioNode.prototype.connect;
  AudioNode.prototype.connect = function (to, ...a) {
    if (to instanceof AudioDestinationNode) {
      const c = this.context;
      if (!c.__tap) { c.__tap = c.createMediaStreamDestination(); window.__tap = c.__tap; }
      conn.call(this, c.__tap);
    }
    return conn.call(this, to, ...a);
  };
  const { music } = await import('./js/music.js');
  window.__music = music;
</script>` }));
await p.goto('http://localhost:8123/__rec.html');
await p.waitForFunction(() => window.__music);
const b64 = await p.evaluate(async ([LEN, IN_AT, OUT_AT]) => {
  const m = window.__music; if (m.muted) m.toggle(); m.start(); m.setPlace('outside');
  const rec = new MediaRecorder(window.__tap.stream, { mimeType: 'audio/webm;codecs=opus', audioBitsPerSecond: 256000 });
  const chunks = []; rec.ondataavailable = e => chunks.push(e.data);
  rec.start(1000);
  setTimeout(() => m.setPlace('inside'), IN_AT * 1000);
  setTimeout(() => m.setPlace('outside'), OUT_AT * 1000);
  await new Promise(r => setTimeout(r, LEN * 1000)); rec.stop();
  await new Promise(r => rec.onstop = r);
  const buf = await new Blob(chunks).arrayBuffer(); let s = ''; const u = new Uint8Array(buf);
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
  return btoa(s);
}, [LEN, IN_AT, OUT_AT]);
fs.writeFileSync('nature.webm', Buffer.from(b64, 'base64'));
await b.close(); console.log('recorded');
