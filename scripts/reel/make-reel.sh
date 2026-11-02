#!/usr/bin/env bash
# Makes the Instagram Reel (1080x1920, 30 fps, with a silent track to lay your voiceover on) from the live site.
# Needs: Playwright + Chromium, ffmpeg, and Python with Pillow, fonttools and brotli.
# Run it from anywhere; it works in ./work next to this script. It takes about 30 minutes (software WebGL).
set -euo pipefail
cd "$(dirname "$0")"; HERE=$PWD; ROOT=$(cd ../.. && pwd)
mkdir -p work && cd work
cp "$HERE"/{vclock.js,record.mjs,loading.mjs,captions.py} .
python3 - "$ROOT" <<'PY'
import sys; from fontTools.ttLib import TTFont
for n in ['caveat-latin-700-normal', 'patrick-hand-latin-400-normal']:
  f = TTFont(f'{sys.argv[1]}/fonts/{n}.woff2'); f.flavor = None; f.save(f'{n}.ttf')
PY
(cd "$ROOT" && exec python3 -m http.server 8123 >/dev/null 2>&1) & SRV=$!; trap 'kill $SRV' EXIT; sleep 1
rm -rf frames loadframes seq out
node record.mjs      # the 3D shots -> frames/
node loading.mjs     # the loading screens -> loadframes/
# the cut: hook + lesson 1, then the loading screens (lesson 2), then the rest
python3 - <<'PY'
import os
os.makedirs('seq'); n = 0
for d, p, a, b in [('frames', 'f', 0, 270), ('loadframes', 'u', 0, 165), ('loadframes', 'h', 0, 105), ('frames', 'f', 270, 1038)]:
  for i in range(a, b): os.symlink(os.path.abspath(f'{d}/{p}{i:05d}.jpg'), f'seq/f{n:05d}.jpg'); n += 1
PY
python3 captions.py seq out
ffmpeg -y -loglevel error -framerate 30 -i out/f%05d.jpg -f lavfi -i anullsrc=r=48000:cl=stereo -shortest \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high -movflags +faststart -c:a aac reel.mp4
echo "made $PWD/reel.mp4"
