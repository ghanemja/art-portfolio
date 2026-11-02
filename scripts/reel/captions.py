# Lays the lesson cards over the filmed frames: frames/fNNNNN.jpg -> out/fNNNNN.jpg
import os, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC, DST = (sys.argv[1] if len(sys.argv) > 1 else 'frames'), (sys.argv[2] if len(sys.argv) > 2 else 'out')
os.makedirs(DST, exist_ok=True)
W, H = 1080, 1920
CAV = 'caveat-latin-700-normal.ttf'; PH = 'patrick-hand-latin-400-normal.ttf'
INK, PAPER, RED = (43, 33, 30), (247, 238, 218), (178, 52, 38)
# (start frame, end frame, label, headline, sub)
CARDS = [
  (0,    120,  '6 things I learned', 'I turned my paintings into\na museum that floats', ''),
  (120,  270,  'LESSON 1', "Start before you're ready.", ''),
  (270,  540,  'LESSON 2', 'Make the wait part of the show.', ''),
  (540,  690,  'LESSON 3', 'Details make it feel alive.', ''),
  (690,  855,  'LESSON 4', 'Presentation is part of the art.', ''),
  (855,  1023, 'LESSON 5', 'Done beats perfect. Then fix it.', ''),
  (1023, 1158, 'LESSON 6', 'Make room for people.', ''),
  (1158, 1308, 'JanGogh Art', 'Come walk through it · link in bio', ''),
]
def font(p, s): return ImageFont.truetype(p, s)
def card(label, head, sub):
  fl, fh, fs = font(PH, 30), font(CAV, 64), font(PH, 36)
  d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
  bb = lambda t, f, sp: tuple(int(round(v)) for v in d0.multiline_textbbox((0, 0), t, font=f, spacing=sp, align='center'))
  hw = bb(head, fh, 0); sw = bb(sub, fs, 8) if sub else (0, 0, 0, 0); lw = bb(label, fl, 0)
  w = max(hw[2], sw[2], lw[2]) + 70; h = 24 + (lw[3] + 12) + hw[3] + (sw[3] + 16 if sub else 0) + 30
  im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
  sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((26, 30, w + 26, h + 30), 28, fill=(0, 0, 0, 90))
  im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(im)
  d.rounded_rectangle((20, 20, w + 20, h + 20), 20, fill=PAPER, outline=INK, width=4)
  y = 20 + 24
  # the label as a little red stamp
  lx = 20 + (w - lw[2]) // 2
  d.rounded_rectangle((lx - 14, y - 5, lx + lw[2] + 14, y + lw[3] + 9), 11, fill=RED)
  d.text((lx, y - 4), label, font=fl, fill=PAPER); y += lw[3] + 12 + 8
  d.multiline_text((20 + w // 2, y), head, font=fh, fill=INK, anchor='ma', align='center', spacing=0); y += hw[3] + 26
  if sub: d.multiline_text((20 + w // 2, y), sub, font=fs, fill=(95, 75, 62), anchor='ma', align='center', spacing=8)
  return im
cards = [(a, b, card(l, h, s)) for a, b, l, h, s in CARDS]
files = sorted(f for f in os.listdir(SRC) if f.endswith('.jpg'))
for f in files:
  n = int(f[1:6]); src = Image.open(os.path.join(SRC, f)).convert('RGB')
  if src.width == W and src.height < H:          # a short frame (the unwrapping): pad the top with its own paper colour
    pad = Image.new('RGB', (W, H), src.getpixel((W // 2, 4))); pad.paste(src, (0, H - src.height)); src = pad
  fr = src.resize((W, H), Image.LANCZOS).convert('RGBA')
  for i, (a, b, c) in enumerate(cards):
    if not (a <= n < b): continue
    tin, tout = n - a, b - 1 - n
    k = min(1, tin / 9); ko = min(1, tout / 6)
    pop = 1 - (1 - k) ** 3; s = (0.82 + 0.18 * pop + 0.04 * math.sin(k * math.pi)) * (0.92 + 0.08 * ko)
    tilt = (-1.0 if i % 2 else 0.9)
    cc = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS).rotate(tilt, resample=Image.BICUBIC, expand=True)
    alpha = min(pop, ko); cc.putalpha(cc.getchannel('A').point(lambda v: int(v * alpha)))
    cy = int(H * 0.125)
    fr.alpha_composite(cc, (W // 2 - cc.width // 2, cy - cc.height // 2 + int((1 - pop) * 40)))
  fr.convert('RGB').save(os.path.join(DST, f), quality=94)
print('captioned', len(files))
