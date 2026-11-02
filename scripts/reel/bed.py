# The nature bed, by section: birdsong over the island shots, the waterfall (and birds) under the island,
# nothing inside the hall or on the loading screens. Soft fades at each change. Writes bed.wav.
import json, subprocess, numpy as np
from scipy.io import wavfile
SR = 48000; T = json.load(open('timeline.json')); LEN = T['voice_end'] + 1.2; n = int(LEN * SR)
def load(f, skip=0.5):
  a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ss', str(skip), '-ac', '2', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout, np.int16)
  a = a.reshape(-1, 2).astype(float) / 32768; return np.pad(a, ((0, max(0, n - len(a))), (0, 0)))[:n]
db = lambda d: 10 ** (d / 20)
birds = load('nature_birds.webm') * db(float(__import__('os').environ.get('BIRDS_DB', 14)))
fall = load('nature_nowind.webm') * db(float(__import__('os').environ.get('FALL_DB', 13)))
def mask(spans, fade=0.7):
  m = np.zeros(n); t = np.arange(n) / SR
  for a, b in spans: m = np.maximum(m, np.clip(np.minimum((t - a) / fade, (b - t) / fade), 0, 1))
  return m[:, None]
end = LEN
bed = birds * mask([(0, T['l2'] + 0.3), (T['outro'] - 0.3, end)]) + fall * mask([(T['l3'] - 0.2, T['l4'] + 0.4)])
wavfile.write('bed.wav', SR, (np.clip(bed, -1, 1) * 32767).astype(np.int16)); print('bed', round(LEN, 2), 's, peak', round(20 * np.log10(np.abs(bed).max() + 1e-9), 1), 'dBFS')
