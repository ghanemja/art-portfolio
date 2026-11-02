# Cuts the voiceover (trims long pauses) and writes the timeline the shots and cards follow.
import json, subprocess
W = json.load(open('words.json'))
idx = lambda ws, word, after=0: next(i for i, (w, s, e) in enumerate(ws) if s >= after and w.lower().strip('.,%') == word)
import os
SRC = os.environ.get('VO', 'vo/rec96.wav')
pieces = [(SRC, W[SRC])]
MAXGAP, KEEP, LEAD, TAIL = 0.75, 0.5, 0.25, 0.35
segs = []   # (file, src_start, src_end)
wordmap = []   # (piece, word, new_start)
t = 0.0
for pi, (f, ws) in enumerate(pieces):
  start = max(0, ws[0][1] - LEAD); cur = start
  for k in range(len(ws)):
    w, s, e = ws[k]
    wordmap.append((pi, w, t + (s - cur)))
    if k + 1 < len(ws) and ws[k + 1][1] - e > MAXGAP:   # a long pause: cut it down
      cut_from = e + KEEP / 2; cut_to = ws[k + 1][1] - KEEP / 2
      segs.append((f, cur, cut_from)); t += cut_from - cur; cur = cut_to
  end = ws[-1][2] + TAIL
  segs.append((f, cur, end)); t += end - cur
  if pi < len(pieces) - 1: segs.append(('gap', 0, 0.25)); t += 0.25
total = t
# the cut list for ffmpeg (10 ms fades at every join so nothing clicks)
inputs = [SRC]; parts = []; fc = []
for j, (f, a, b) in enumerate(segs):
  if f == 'gap': fc.append(f'anullsrc=r=48000:cl=mono,atrim=0:{b - a:.3f}[s{j}]')
  else: fc.append(f'[{inputs.index(f)}:a]aformat=channel_layouts=mono,atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={b - a - 0.01:.3f}:d=0.01[s{j}]')
  parts.append(f'[s{j}]')
fc.append(''.join(parts) + f'concat=n={len(parts)}:v=0:a=1[out]')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', inputs[0], '-filter_complex', ';'.join(fc), '-map', '[out]', '-ar', '48000', 'vo/voice_edit.wav'], check=True)
# when each section starts (seconds into the voice)
def at(pi, word, nth=0):
  hits = [s for p, w, s in wordmap if p == pi and w.lower().strip('.,%') == word]; return hits[nth]
T = {'hook': 0.0, 'l1': at(0, 'first'), 'l2': at(0, 'second'), 'l3': at(0, 'third'), 'l4': at(0, 'fourth'),
     'l5': at(0, 'fifth'), 'l6': at(0, 'last'), 'outro': at(0, 'remember'), 'bio': at(0, 'links'), 'voice_end': total}
T['crew'] = T['l2'] + 0.6 * (T['l3'] - T['l2'])      # (the unwrapping, then the crew hanging one)
T = {k: round(v, 3) for k, v in T.items()}
json.dump(T, open('timeline.json', 'w'), indent=1); print(json.dumps(T)); print('voice length', round(total, 2))
