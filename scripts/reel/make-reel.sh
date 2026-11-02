#!/usr/bin/env bash
# Makes the Instagram Reel from the live site, timed to a voiceover recording.
#   ./make-reel.sh path/to/voiceover.m4a
# Steps: transcribe the voice (word timings) -> cut long pauses -> time each shot and card to it ->
# film the shots and the loading screens -> clean up the voice -> mix it over birdsong/waterfall + sound effects.
# Needs: Playwright + Chromium, ffmpeg, Python with Pillow, numpy, scipy, fonttools, brotli and faster-whisper.
# FAST=1 films the 3D shots at 720x1280 (about twice as fast; upscaled to 1080x1920).
set -euo pipefail
VO_IN=$(realpath "$1")
cd "$(dirname "$0")"; HERE=$PWD; ROOT=$(cd ../.. && pwd)
mkdir -p work/vo && cd work
cp "$HERE"/{vclock.js,record.mjs,loading.mjs,audio.mjs,captions.py,sfx.py,bed.py,voedit.py,words.py,finish.sh} .
python3 - "$ROOT" <<'PY'
import sys; from fontTools.ttLib import TTFont
for n in ['caveat-latin-700-normal', 'patrick-hand-latin-400-normal']:
  f = TTFont(f'{sys.argv[1]}/fonts/{n}.woff2'); f.flavor = None; f.save(f'{n}.ttf')
PY
[ -f vo/sh.rnnn ] || curl -sSL -o vo/sh.rnnn https://raw.githubusercontent.com/richardpl/arnndn-models/master/sh.rnnn
ffmpeg -y -v error -i "$VO_IN" vo/take.wav
python3 words.py vo/take.wav                      # -> words.json
VO=vo/take.wav python3 voedit.py                  # -> vo/voice_edit.wav, timeline.json
python3 - <<'PY'
import json
T = json.load(open('timeline.json')); F = lambda k: round(T[k] * 30); end = round((T['voice_end'] + 1.2) * 30)
n = {'A': F('l1'), 'B': F('l2') - F('l1'), 'U': F('crew') - F('l2'), 'H': F('l3') - F('crew'), 'C': F('l4') - F('l3'),
     'D': F('l5') - F('l4'), 'E': F('l6') - F('l5'), 'F': F('outro') - F('l6'), 'G': end - F('outro')}
json.dump(n, open('shots.json', 'w')); print('shots', n)
PY
ffmpeg -y -v error -i vo/voice_edit.wav -af "$(sed 's#sh.rnnn#vo/sh.rnnn#' "$HERE/voice-chain.txt")" -ar 48000 vo/voice_final.wav
(cd "$ROOT" && exec python3 -m http.server 8123 >/dev/null 2>&1) & SRV=$!; trap 'kill $SRV' EXIT; sleep 1
rm -rf frames loadframes
node record.mjs & node loading.mjs & wait          # the 3D shots and the loading screens, side by side
ROOT="$ROOT/" LEN=62 OUT=nature_nowind.webm node audio.mjs             # waterfall + birds
ROOT="$ROOT/" LEN=62 OUT=nature_birds.webm NO_FALL=1 node audio.mjs    # birds only
./finish.sh                                        # cards, sound effects, nature bed, mix -> reel.mp4
echo "made $PWD/reel.mp4"
