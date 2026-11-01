# Janelle Ghanem: paintings in a floating museum

A hand-drawn 3D portfolio. My paintings hang in a museum that floats on an island high above a
painted landscape. Fly round the island, walk in through the open door, and browse the hall
alongside the other visitors. Click any painting to see it close up in its frame.

Built with three.js r160 (plain ES modules from unpkg, no build step). The museum building, the
frame kit and the paint-and-ink style come from [art-heist](https://github.com/ghanemja/art-heist).
The visitors are people made in [Citizen Maker](https://github.com/ghanemja/citizen-maker).

## Run locally

```bash
python3 -m http.server 8123
# → http://localhost:8123
```

## Host on GitHub Pages

Settings → Pages → *Deploy from a branch* → pick the branch and `/ (root)`. Everything is static.

## Add or edit paintings

- `js/collection.js` lists every work in hanging order: title, year, medium, and an optional note. It also holds the artist
  name, the name carved over the portico, and links.
- Put the photo in `artworks/originals/` and add its row to `collection.js`, then run
  `python3 scripts/prep-art.py` (needs Pillow and numpy). It crops away the wall or backdrop
  around the canvas, turns sideways photos upright (its `ROTATE` list), spots round canvases
  so they hang in oval frames, writes `artworks/<name>.jpg` and `artworks/web/<name>.webp`, and
  updates the size and shape in `collection.js`. You can fix a bad crop by hand in its `CROP` list.
  The hall gets longer to fit the collection.
- `TOUR` in `collection.js` lists the stops of the guided tour.

## Layout

- `index.html`: the page, its UI, and the import map.
- `js/main.js`: loading, the outside and inside modes, the controls, the close-up viewer, and the index of all works.
- `js/island.js`: the floating island, the museum on it, the waterfall, the islets, the clouds and the landscape.
- `js/museum.js`: art-heist's museum and frame kit, with the crime scene turned off (`heist: false`)
  and `ornateFrame(..., { art })` to hang a painting in a frame.
- `js/gallery.js`: the hall. It works out how to hang the paintings, then builds the walls, partitions,
  frames, wall cards and picture lights.
- `js/viewer.js`: the close-up, which shows a painting in its own frame at full size.
- `js/music.js`: the soundtrack. It's all made live in the browser: a pad, a bass, a kalimba melody and chimes, with wind, the waterfall and birds underneath. It starts on the first click, and the sound button or M mutes it.
- `js/loading.js`: the loading screen, where you unwrap the paintings.
- `js/visitors.js`: the other visitors. They are Citizen Maker models that walk between paintings on a grid path.
- `js/style.js`: art-heist's gouache paint and boiling ink lines.
- `scripts/bump-cache.py`: run it after changing anything in `js/`. It gives every module a new version tag in `index.html`, so visitors' browsers don't keep the old files.
- `scripts/smoke.mjs`: a headless test with Playwright. It fails on any console error and saves screenshots to `scripts/shots/`.

## License

© 2026 Janelle Ghanem. **All rights reserved.** That covers the paintings, the images of them,
the models and the code. You may not copy, reuse, sell, or use any of it for AI training without
written permission. See [LICENSE](LICENSE). The fonts (Caveat, Patrick Hand) are under the SIL
Open Font License.
