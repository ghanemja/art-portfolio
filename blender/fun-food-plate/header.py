"""Adds the "What's for dessert?" header on top of the rendered frames.
It pops in with a bounce at the start, then a crayon underline draws itself.

    python3 header.py frames/ frames_titled/ [--text "What's for dessert?"] [--font Caveat.ttf]

The repo ships Caveat as .woff2; convert it once with fontTools:
    python3 -c "from fontTools.ttLib import TTFont; f=TTFont('../../fonts/caveat-latin-700-normal.woff2'); f.flavor=None; f.save('caveat700.ttf')"
"""
import sys, os, glob, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
text = args[args.index("--text") + 1] if "--text" in args else "What's for dessert?"
font_path = args[args.index("--font") + 1] if "--font" in args else "caveat700.ttf"
os.makedirs(dst, exist_ok=True)
frames = sorted(glob.glob(os.path.join(src, "f_*.png")))
W, H = Image.open(frames[0]).size
k = W / 720

INK = (92, 42, 70)          # deep plum
LINE = (235, 110, 150)      # pink crayon underline
font = ImageFont.truetype(font_path, int(84 * k))

# the title as one RGBA sprite (soft white glow behind so it reads on lavender)
bbox = font.getbbox(text)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
pad = int(30 * k)
sprite = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
glow = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
ImageDraw.Draw(glow).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=(255, 255, 255, 200))
glow = glow.filter(ImageFilter.GaussianBlur(6 * k))
sprite.alpha_composite(glow)
ImageDraw.Draw(sprite).text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=(*INK, 255))

# wobbly crayon underline points
random.seed(4)
ux0, ux1 = W / 2 - tw * 0.42, W / 2 + tw * 0.42
cy = int(118 * k)
uy = cy + th * 0.62
pts = []
for i in range(60):
    t = i / 59
    pts.append((ux0 + (ux1 - ux0) * t, uy + 4 * k * math.sin(t * 9 + 1) + 2 * k * math.sin(t * 23)))

def ease_pop(t):  # 0..1 -> scale with overshoot
    keys = [(0, 0.0), (0.35, 1.15), (0.6, 0.94), (0.8, 1.03), (1, 1.0)]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t <= b:
            u = (t - a) / (b - a); u = u * u * (3 - 2 * u)
            return va + (vb - va) * u
    return 1.0

POP0, POP_LEN = 2, 14            # frames
LINE0, LINE_LEN = 14, 12
for i, fp in enumerate(frames):
    im = Image.open(fp).convert("RGBA")
    f = int(os.path.basename(fp)[2:6])
    t = (f - POP0) / POP_LEN
    if t > 0:
        s = ease_pop(min(1.0, t))
        if s > 0.01:
            sp = sprite.resize((max(1, int(sprite.width * s)), max(1, int(sprite.height * s))), Image.LANCZOS)
            im.alpha_composite(sp, (int(W / 2 - sp.width / 2), int(cy - sp.height / 2)))
    u = (f - LINE0) / LINE_LEN
    if u > 0:
        n = max(2, int(len(pts) * min(1.0, u)))
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).line(pts[:n], fill=(*LINE, 230), width=int(7 * k), joint="curve")
        im.alpha_composite(layer)
    im.convert("RGB").save(os.path.join(dst, os.path.basename(fp)))
print("titled", len(frames), "frames")
