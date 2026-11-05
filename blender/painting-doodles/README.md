# Painting Doodles: Instagram reels

Each reel is 1080×1920 (9:16), 30 fps and about 11 seconds long, with sound. It goes like this:

1. A crayon doodle of the painting is scribbled onto paper. The doodle is made from the painting
   itself: the painting is simplified into a few big colour shapes, and each shape is coloured in
   with zig-zag hatching and outlined in a darker crayon, biggest shapes first. Crayon-scratching
   sounds play while it's drawn.
2. The real painting pops in with a squash-and-bounce and a soft pop sound, and a few crayon-coloured
   dots fly out. Round canvases come in round.
3. The painting comes alive with a slow push-in and a gentle 2.5D parallax. The sky sits further
   back than the foreground, and blue water shimmers a little. A light sweeps across the varnish,
   and a few twinkles catch the brightest spots, each with a tiny bell.
4. A title card (the painting's title and the artist's name from `js/collection.js`) slides in with
   a chime and holds on screen.

A soft kalimba-and-pad tune plays under everything. Each painting gets its own key and melody.

Finished reels are in `out/`.

## Make more

You need Python 3 with numpy, scipy, Pillow and opencv-python-headless, plus ffmpeg.

```bash
pip install numpy scipy pillow opencv-python-headless
```

Pass one or more painting names. They are the `file:` names in `js/collection.js`:

```bash
python3 render_reel.py art_IMG_0658 art_IMG_5557
```

Check one frame quickly before rendering a whole reel. Frame 128 is the finished doodle, frame 300 the title card:

```bash
python3 render_reel.py art_IMG_0658 --res 540 --still 128
```

Other options:
- `--out DIR` sets where the reels go.
- `--seed N` gives a different doodle and tune.
- `--res 720` makes a smaller, faster reel.

A reel takes about a minute or two to render on a laptop CPU.

The timing is set at the top of `build()` in `render_reel.py`: `T_DRAW0`/`T_DRAW1` for the doodle,
`T_POP` for the reveal and `T_TITLE` for the title card. The sound is in `soundtrack.py`.

This doesn't use Blender: the reel is all flat paper and canvas, so a 2D compositor is quicker and
keeps the painting pixel-sharp.
