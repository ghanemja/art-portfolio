#!/usr/bin/env bash
# seq (hook + L1, loading screens, the rest) -> captions -> video with voice over ducked nature
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import os, json, shutil
n = json.load(open('shots.json')); shutil.rmtree('seq', ignore_errors=True); os.makedirs('seq'); k = 0
ab = n['A'] + n['B']; tot = sum(n[x] for x in 'ABCDEFG')
for d, p, a, b in [('frames', 'f', 0, ab), ('loadframes', 'u', 0, n['U']), ('loadframes', 'h', 0, n['H']), ('frames', 'f', ab, tot)]:
  for i in range(a, b): os.symlink(os.path.abspath(f'{d}/{p}{i:05d}.jpg'), f'seq/f{k:05d}.jpg'); k += 1
print('seq', k)
PY
python3 sfx.py
python3 bed.py
rm -rf out && python3 captions.py seq out
LEN=$(python3 -c "import json; T=json.load(open('timeline.json')); print(round(T['voice_end'] + 1.2, 2))")
ffmpeg -y -loglevel error -framerate 30 -i out/f%05d.jpg -i vo/voice_final.wav -i bed.wav -i sfx.wav -filter_complex "\
[2:a]atrim=0:$LEN,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,afade=t=out:st=$(python3 -c "print($LEN-1.8)"):d=1.8[bed];\
[1:a]adelay=0|0,aformat=channel_layouts=stereo,apad=whole_dur=$LEN[vox];[vox]asplit[v1][v2];\
[bed][v2]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=450:makeup=1[duck];\
[3:a]volume=0.45,apad=whole_dur=$LEN[fx];\
[v1][duck][fx]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -profile:v high -movflags +faststart -c:a aac -b:a 192k -shortest reel.mp4
ffprobe -v error -show_entries format=duration -of default=nw=1 reel.mp4
