# Word timings for a voiceover (faster-whisper): words.json
import sys, json, numpy as np, subprocess
from faster_whisper import WhisperModel
m = WhisperModel('small.en', device='cpu', compute_type='int8')
out = {}
for f in sys.argv[1:]:
  a = np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout, np.int16).astype(np.float32)/32768
  segs, _ = m.transcribe(a, word_timestamps=True)
  out[f] = [(w.word.strip(), round(w.start, 2), round(w.end, 2)) for s in segs for w in s.words]
json.dump(out, open('words.json', 'w'))
