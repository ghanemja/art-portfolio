// virtual clock: real time until __freeze(); then time only moves on __step(ms)
(() => {
  const realNow = performance.now.bind(performance), realRAF = window.requestAnimationFrame.bind(window), realDate = Date.now;
  let frozen = false, vt = 0, off = 0, q = [];
  performance.now = () => frozen ? vt : realNow();
  Date.now = () => frozen ? off + vt : realDate();
  window.requestAnimationFrame = (cb) => { if (!frozen) return realRAF((t) => cb(frozen ? vt : t)); q.push(cb); return q.length; };
  window.__freeze = () => { vt = realNow(); off = realDate() - vt; frozen = true; };
  window.__step = (ms, cap = true) => { vt += ms; const cbs = q; q = []; for (const cb of cbs) cb(vt); if (!cap) return null;
    return document.querySelector('canvas').toDataURL('image/jpeg', 0.93); };
})();
