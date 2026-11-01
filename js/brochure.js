// ─── THE BROCHURE: handed to you at the door ─────────────────────────────────
// The first time you step into the gallery a hand slides in from the side, holding out a folded
// brochure. Take it and it opens out: two panels, the artist in her own words on the left (her
// background, medium and inspiration), the collections on the right, each with a "Take me
// there!" that walks you round just those paintings. The Brochure button opens it again.
import { ABOUT, COLLECTIONS, ARTIST, WORKS } from './collection.js';

const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

export function createBrochure({ onTour }) {
  // the hand at the door, holding it out
  const offer = document.createElement('div');
  offer.id = 'offer'; offer.className = 'ui';
  offer.innerHTML = `
    <div class="bubble sk">Welcome in! Here's a brochure ✦</div>
    <button class="take" aria-label="take the brochure">
      <svg viewBox="0 0 220 150" width="220" height="150" aria-hidden="true">
        <g stroke="#2a2230" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">
          <path d="M120 150 L150 96 Q160 84 176 86 L220 92 L220 150 Z" fill="#2f3b52" />
          <path d="M150 96 L142 92" fill="none" />
          <g transform="rotate(-14 90 70)">
            <rect x="36" y="22" width="108" height="92" rx="3" fill="#f6efdf" />
            <path d="M90 22 L90 114" stroke-width="2" />
            <rect x="44" y="30" width="38" height="28" fill="#8fc3c9" stroke-width="2" />
            <path d="M98 34 h36 M98 42 h30 M98 50 h34 M44 68 h38 M44 76 h30 M98 64 h36 M98 72 h28 M98 80 h34" stroke-width="2" />
            <text x="48" y="104" font-family="Caveat, cursive" font-size="17" font-weight="700" fill="#e8604c" stroke="none">${esc(ABOUT.brand)}</text>
          </g>
          <path d="M112 92 Q104 84 112 76 L140 80 Q150 82 152 92 L150 104 Q140 110 126 106 Z" fill="#e0b48a" />
          <path d="M112 76 Q100 70 104 62 Q110 58 120 66 M110 86 Q98 84 100 76" fill="#e0b48a" />
        </g>
      </svg>
    </button>
    <button class="no" aria-label="no thanks">no thanks</button>`;
  document.body.appendChild(offer);

  // the brochure itself
  const work = (f) => WORKS.find(w => w.file === f);
  const sheet = document.createElement('div');
  sheet.id = 'brochure'; sheet.className = 'ui hide fade';
  sheet.innerHTML = `
    <div class="paper">
      <button class="sk x" aria-label="close the brochure">close ✕</button>
      <section class="panel left">
        <h2>${esc(ABOUT.brand)}</h2>
        <p class="by">${esc(ARTIST.name)} · welcome to the gallery</p>
        ${ABOUT.sections.map(s => `
          <div class="about">
            ${work(s.art) ? `<img src="./artworks/web/${s.art}.webp" alt="${esc(work(s.art).title)}">` : ''}
            <div><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p></div>
          </div>`).join('')}
      </section>
      <section class="panel right">
        <h2>The Collections</h2>
        ${COLLECTIONS.map((c, k) => {
          const n = c.files.filter(work).length;
          return `<div class="coll"><h3>${esc(c.name)}</h3><p>${esc(c.blurb)}</p>
            <button class="go" data-k="${k}">Take me there!</button> <span class="n">${n} painting${n === 1 ? '' : 's'}</span></div>`;
        }).join('')}
      </section>
    </div>`;
  document.body.appendChild(sheet);

  const hideOffer = () => offer.classList.remove('in');
  const open = () => { hideOffer(); sheet.classList.remove('hide'); sheet.classList.add('open'); document.body.classList.add('reading'); };
  const close = () => { sheet.classList.add('hide'); sheet.classList.remove('open'); document.body.classList.remove('reading'); };
  offer.querySelector('.take').onclick = open;
  offer.querySelector('.no').onclick = hideOffer;
  sheet.querySelector('.x').onclick = close;
  sheet.addEventListener('click', (e) => { if (e.target === sheet) close(); });
  for (const b of sheet.querySelectorAll('.go')) b.onclick = () => {
    const c = COLLECTIONS[+b.dataset.k];
    close();
    onTour(c.files.map(f => WORKS.findIndex(w => w.file === f)).filter(i => i >= 0), c.name);
  };
  let offered = false;
  return {
    // hold it out (once): when you first come in
    offer() { if (offered) return; offered = true; setTimeout(() => offer.classList.add('in'), 900); setTimeout(hideOffer, 20000); },
    open, close, hideOffer,
    get isOpen() { return !sheet.classList.contains('hide'); },
  };
}
