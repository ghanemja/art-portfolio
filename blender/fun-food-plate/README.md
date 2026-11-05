# Fun Food Plate (Blender)

A top-down plate that fills up one food at a time. Each food is scribbled in crayon first, then
pops into a real 3D food: a sprinkle donut, sushi rolls, a pizza slice, a smiley fried egg,
strawberries, macarons and gummy bears. At the end the plate empties so the clip loops.

`fun-food-plate.mp4` is the rendered clip (720×1280, 30 fps, about 9.5 s).

Everything is built from code in `fun_food_plate.py`, with no models or textures to download.

## Render it again

Needs Blender 4.2 (Cycles on the CPU), ffmpeg, and Python with numpy.

```bash
blender -b -P fun_food_plate.py -- --out frames/ --res 720 --samples 12
python3 soundtrack.py frames/events.json frames/sound.wav
ffmpeg -framerate 30 -i frames/f_%04d.png -i frames/sound.wav -c:v libx264 -pix_fmt yuv420p -crf 20 -af "highpass=f=120,acompressor=threshold=-20dB:ratio=3:makeup=4,loudnorm=I=-14:TP=-1" -ar 48000 -ac 2 -c:a aac -b:a 160k -shortest -movflags +faststart fun-food-plate.mp4
```

`--still N` renders only frame N; `--still 9999` renders the full plate. Raise `--res` and
`--samples` for a sharper, cleaner render.
