# Painting Doodles: Instagram reels

Each reel is 1080×1920 (9:16), 30 fps and about 12 seconds long, with sound. It goes like this:

1. A crayon doodle of the painting is scribbled onto paper, sitting exactly where the painting will
   be. The doodle is made from the painting itself: the painting is simplified into a few big colour
   shapes, and each shape is coloured in with zig-zag hatching and outlined in a darker crayon,
   biggest shapes first. Crayon-scratching sounds play while it's drawn.
2. The doodle comes to life. Real paint floods into each crayon shape in the order the shapes were
   drawn, about 0.13 s apart, bleeding outwards from the hatch lines like wet paint with a soft
   watercolour edge. The hatching vanishes under the paint. A final flood fills the last gaps, then
   the crayon outlines wash away with a wet shimmer. Each flood plays a soft bloop, each one a little
   higher than the last, and the wash plays a sparkle.
3. The finished painting gives one gentle settle bounce with a soft pop. Round canvases stay round.
4. The painting stays put, and things inside it start to move for about 4.5 s: water rolls,
   a waterfall flows, trees sway, clouds drift, petals fall. Each motion comes from the painting's
   own pixels, warped gently inside a hand-drawn mask, and comes with its own ambient sound
   (waves, the rush of falling water, rustling leaves, wind, an airy pad).
5. Meanwhile the handle `@janelle.builds` fades in, small and centred, about 280 px above the
   bottom edge, so Instagram's caption doesn't cover it. It stays until the end.

A soft kalimba-and-pad tune plays under everything. Each painting gets its own key and melody.

The audio is mastered for phones: -14 LUFS integrated, true peak below -1 dBTP (two-pass ffmpeg
`loudnorm` plus a gain top-up), stereo AAC at 48 kHz, 160 kbit/s. The sound effects keep their energy between 500 Hz
and 4 kHz so they come through small speakers.

Finished reels are in `out/`.

## What moves in each painting

| Painting | Motion | Sound |
|---|---|---|
| Wild Horses at the Falls (`art_IMG_0658`) | waterfall flowing down, river waves rolling, trees swaying | rushing water, waves, leaves |
| Lavender Peaks Harbour (`art_IMG_2256`) | clouds drifting, harbour waves, the boat bobbing | wind, waves |
| Castle Above the Valley (`art_IMG_5264`) | clouds drifting, the lakes rippling, the forest swaying | wind, water, leaves |
| Winter Sun, Spinning (`art_IMG_7165`) | the sky swirling round the sun, snow shimmering, branches swaying | airy pad, wind |
| Aurora Over the Sea (`art_IMG_5557`) | the aurora waving, waves rolling, the flowering bushes swaying | airy pad, waves |
| Sun-Melted Sea (`art_IMG_9615`) | sun glints sliding on the water, waves rolling, the sky drifting | waves, airy pad |
| Banana Treats for the Astronaut (`art_banana_treats_astronaut`) | the speed streaks streaming outwards, the treat stack floating | wind, airy pad |
| Cherry Blossom Road (`art_IMG_7158`) | blossom trees swaying with fluttering leaves, petals falling, clouds drifting | leaves, wind |

The masks and effects for each painting are in `EFFECTS` in `animate.py`: polygons in 0–1 image
coordinates, optionally narrowed by colour, and feathered. A painting without an entry gets a slow
drift in its top third.

## Make more

You need Python 3 with numpy, scipy, Pillow and opencv-python-headless, plus ffmpeg.

```bash
pip install numpy scipy pillow opencv-python-headless
```

Pass one or more painting names. They are the `file:` names in `js/collection.js`:

```bash
python3 render_reel.py art_IMG_0658 art_IMG_5557
```

Check one frame quickly before rendering a whole reel. Frame 128 is the finished doodle, frame 145 is mid-flood, and frame 300 is mid-animation:

```bash
python3 render_reel.py art_IMG_0658 --res 540 --still 128
```

Other options:
- `--out DIR` sets where the reels go.
- `--seed N` gives a different doodle and tune.
- `--res 720` makes a smaller, faster reel.
- `--handle @name` changes the handle, and `--handle ''` leaves it out.

A reel takes about a minute or two to render on a laptop CPU.

The timing is set at the top of `build()` in `render_reel.py`: `T_DRAW0`/`T_DRAW1` for the doodle,
`T_FLOOD`, `STAG` and `FDUR` for the paint flood, `T_ANIM` for when the painting starts moving, and
`T_HANDLE` for when the handle fades in. The sound is in `soundtrack.py`.

This doesn't use Blender: the reel is all flat paper and canvas, so a 2D compositor is quicker and
keeps the painting pixel-sharp.
