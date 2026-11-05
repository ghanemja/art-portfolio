"""An animated Instagram carousel about how the Wild Horses reel was made.

Seven 1080×1350 (4:5) video panels, each a short clip cut from the finished reel
with a hand-lettered heading, callouts that draw themselves in and point at what
is happening, a lesson learned along the bottom, and the reel's own sound for
that moment. The last panel lists the lessons.

    python3 carousel.py [out/art_IMG_0658.mp4] [--out out/carousel] [--still PANEL T]

Needs Pillow, opencv-python-headless, numpy and ffmpeg.
"""
import argparse, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
W, H, FPS = 1080, 1350, 30
WIN = (90, 250, 900)                       # the video window: x, y, size
PAPER = np.array([247, 243, 236], np.float32)
INK = (64, 54, 50)
ACCENT = (178, 92, 52)
HANDLE = "@janelle.builds"

PANELS = [
    dict(slug="01_cover", title="My horses ran out of the painting",
         sub="how this reel was made, all in code", clip=(11.7, 16.7), crop_y=330,
         callouts=[dict(text="swipe to see how  →", at=None, label=(540, 1060), t=1.2)],
         lesson=None),
    dict(slug="02_unwrap", title="1 · Paper that falls, not burns", clip=(0.25, 4.15), crop_y=380,
         callouts=[dict(text="a curl rolls across a 22×22 mesh", at=(540, 640), label=(330, 300), t=0.5),
                   dict(text="lit per pixel: highlight, creases, shadow", at=(760, 760), label=(560, 520), t=1.3),
                   dict(text="then each sheet drops, sways and tilts", at=(560, 1330), label=(540, 800), t=2.3)],
         lesson="Torn brown edges read as burnt. Pale, thin edges read as paper."),
    dict(slug="03_doodle", title="2 · Doodle, then paint", clip=(4.0, 10.4), speed=1.45, crop_y=330,
         callouts=[dict(text="the doodle is the painting, cut into big colour shapes", at=(380, 800),
                        label=(540, 300), t=0.4),
                   dict(text="paint bleeds out from the crayon hatching", at=(620, 940), label=(500, 720), t=2.6),
                   dict(text="each fill: a 60 ms lip-pop sound", at=(780, 660), label=(640, 520), t=3.2)],
         lesson="No music needed: every sound is shaped noise and tiny chirps."),
    dict(slug="04_gallop", title="3 · Only its own pixels move", clip=(10.5, 12.1), speed=0.5, crop_y=330,
         callouts=[dict(text="a mask per horse: bob, rock, legs, mane", at=(300, 820), label=(330, 330), t=0.3),
                   dict(text="each hoof landing = spray + ripple + hoofbeat", at=(450, 935), label=(500, 760), t=1.1),
                   dict(text="trees toss in gusts, mist drifts off the falls", at=(840, 640), label=(620, 520), t=1.9)],
         lesson="One list of hoof landings drives picture and sound, so they never drift apart."),
    dict(slug="05_breakout", title="4 · Paint turns into animation", clip=(12.0, 15.3), crop_y=330,
         callouts=[dict(text="each horse cut out of the painting (GrabCut)", at=(700, 850), label=(420, 300), t=0.2),
                   dict(text="it charges at you in perspective", at=(760, 930), label=(560, 760), t=0.7),
                   dict(text="then dissolves into a hand-built rig with a real 4-beat gallop", at=(900, 800),
                        label=(500, 520), t=1.5)],
         lesson="A ragged, painterly dissolve hides the jump from paint to cartoon."),
    dict(slug="06_pour", title="5 · The river leaves the frame", clip=(14.0, 17.3), crop_y=840,
         callouts=[dict(text="the painting's own river, recoloured to blue and foam", at=(720, 1180),
                        label=(470, 300), t=0.3),
                   dict(text="falls with gravity and frays into streaks", at=(720, 1620), label=(420, 640), t=1.1),
                   dict(text="a second stream arcs out of the side", at=(1035, 1300), label=(640, 470), t=1.9)],
         lesson="Textures must repeat seamlessly: one wrap seam and the eye finds it instantly."),
    dict(slug="07_lessons", title="Lessons learned", clip=(13.6, 17.3), crop_y=330, lessons=[
        "Look at stills before rendering the whole thing",
        "Say what it looks like: \"it looks burnt\" was the best note",
        "Drive picture and sound from the same events",
        "Grids and seams always show: wobble, blur and wrap them",
        "Master audio with headroom: AAC adds ~1 dB of peak",
        "Breaking the frame is the moment people remember",
    ], callouts=[], lesson=None),
]


def font(name, size):
    return ImageFont.truetype(os.path.join(REPO, "fonts", name), size)


F_TITLE = lambda s: font("caveat-latin-700-normal.woff2", s)
F_BODY = lambda s: font("patrick-hand-latin-400-normal.woff2", s)


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def read_clip(src, t0, t1, crop_y, speed=1.0):
    """Frames of the reel between t0 and t1 (reel seconds), cropped square at crop_y and scaled to
    the window, retimed by speed (frame-blended when slowed)."""
    cs = 1080
    size = WIN[2]
    vf = f"crop={cs}:{cs}:0:{crop_y},scale={size}:{size}:flags=area,setpts={1 / speed:.4f}*PTS"
    if speed < 1:
        vf += f",minterpolate=fps={FPS}:mi_mode=blend"
    else:
        vf += f",fps={FPS}"
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", src, "-vf", vf,
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, size, size, 3)
    return fr


def paper_bg(rng):
    g = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.2)
    f = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 9)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vign = 1 - 0.08 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return np.clip(PAPER * (vign * (1 + 0.02 * g + 0.03 * f))[..., None], 0, 255)


def window_mask():
    x, y, s = WIN
    m = np.zeros((H, W), np.float32)
    r = 30
    cv2.rectangle(m, (x + r, y), (x + s - r, y + s), 1.0, -1)
    cv2.rectangle(m, (x, y + r), (x + s, y + s - r), 1.0, -1)
    for cx_, cy_ in ((x + r, y + r), (x + s - r, y + r), (x + r, y + s - r), (x + s - r, y + s - r)):
        cv2.circle(m, (cx_, cy_), r, 1.0, -1, cv2.LINE_AA)
    return m


def static_layer(panel, idx, n):
    """Heading, counter, lesson and handle: drawn once."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ft = F_TITLE(84)
    lines = wrap(d, panel["title"], ft, 940)
    y = 120 - 42 * (len(lines) - 1)
    for ln in lines:
        d.text((W / 2, y), ln, font=ft, fill=(*INK, 255), anchor="mm")
        y += 84
    if panel.get("sub"):
        d.text((W / 2, 205), panel["sub"], font=F_BODY(40), fill=(*ACCENT, 255), anchor="mm")
    d.text((W - 48, 44), f"{idx + 1}/{n}", font=F_BODY(34), fill=(*INK, 150), anchor="rm")
    if panel.get("lesson"):
        fb = F_BODY(40)
        lines = wrap(d, "Lesson: " + panel["lesson"], fb, 900)
        y = 1222 - 22 * (len(lines) - 1)
        for i, ln in enumerate(lines):
            if i == 0:
                d.text((W / 2 - d.textlength(ln, font=fb) / 2, y), "Lesson:", font=fb, fill=(*ACCENT, 255), anchor="lm")
                rest = ln[len("Lesson:"):]
                d.text((W / 2 - d.textlength(ln, font=fb) / 2 + d.textlength("Lesson:", font=fb), y), rest, font=fb,
                       fill=(*INK, 255), anchor="lm")
            else:
                d.text((W / 2, y), ln, font=fb, fill=(*INK, 255), anchor="mm")
            y += 46
    else:
        d.text((W / 2, 1222), HANDLE, font=F_BODY(44), fill=(*INK, 230), anchor="mm")
    a = np.asarray(img).astype(np.float32)
    return a[..., :3], a[..., 3] / 255


def pill(text, fsize=36):
    """A callout label: hand-lettered on a cream pill with a soft shadow."""
    fb = F_BODY(fsize)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = wrap(tmp, text, fb, 560)
    tw = max(tmp.textlength(ln, font=fb) for ln in lines)
    pw, ph = int(tw + 44), int(len(lines) * (fsize + 6) + 26)
    img = Image.new("RGBA", (pw + 16, ph + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 9, pw + 6, ph + 9), radius=ph // 2 if len(lines) == 1 else 22, fill=(40, 30, 20, 60))
    d.rounded_rectangle((2, 2, pw + 2, ph + 2), radius=ph // 2 if len(lines) == 1 else 22,
                        fill=(252, 248, 240, 240), outline=(*ACCENT, 255), width=3)
    y = 2 + 13 + (fsize + 6) / 2
    for ln in lines:
        d.text((2 + pw / 2, y), ln, font=fb, fill=(*INK, 255), anchor="mm")
        y += fsize + 6
    return np.asarray(img).astype(np.float32)


def to_panel(pt, crop_y):
    x, y, s = WIN
    return x + pt[0] * s / 1080, y + (pt[1] - crop_y) * s / 1080


def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def comp(frame, rgba, x, y, alpha):
    """Alpha-composite an RGBA float image (0..255) at (x, y)."""
    h_, w_ = rgba.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w_), min(H, y + h_)
    if x1 <= x0 or y1 <= y0:
        return
    sub = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4] / 255 * alpha
    frame[y0:y1, x0:x1] = frame[y0:y1, x0:x1] * (1 - a) + sub[..., :3] * a


def draw_callout(frame, c, img, t, crop_y):
    u = ease((t - c["t"]) / 0.45)
    if u <= 0:
        return
    lx, ly = c["label"]
    if c["at"] is not None:
        tx, ty = to_panel(c["at"], crop_y)
        # a hand-drawn line from the label to the thing, drawing itself, ending in a pulsing dot
        n = 24
        pts = []
        for i in range(n + 1):
            s = i / n * u
            bend = math.sin(math.pi * s) * 26
            px = lx + (tx - lx) * s
            py = ly + (ty - ly) * s
            dx, dy = ty - ly, -(tx - lx)
            L = math.hypot(dx, dy) + 1e-6
            pts.append((px + dx / L * bend, py + dy / L * bend))
        ov = frame.copy()
        p = np.round(np.array(pts) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(ov, [p], False, (252, 248, 240), 9, cv2.LINE_AA, shift=2)
        cv2.polylines(ov, [p], False, ACCENT, 4, cv2.LINE_AA, shift=2)
        if u > 0.95:
            r = 9 + 3 * math.sin((t - c["t"]) * 6)
            cv2.circle(ov, (int(tx), int(ty)), int(r + 5), (252, 248, 240), -1, cv2.LINE_AA)
            cv2.circle(ov, (int(tx), int(ty)), int(r), ACCENT, -1, cv2.LINE_AA)
        frame[:] = ov
    h_, w_ = img.shape[:2]
    comp(frame, img, lx - w_ / 2, ly - h_ / 2 + 14 * (1 - u), u)


def build_panel(src, panel, idx, n, out_dir, still=None):
    rng = np.random.default_rng(idx)
    t0, t1 = panel["clip"]
    speed = panel.get("speed", 1.0)
    clip = read_clip(src, t0, t1, panel["crop_y"], speed)
    bg = paper_bg(rng)
    wm = window_mask()
    sh = cv2.GaussianBlur(np.roll(wm, (14, 6), (0, 1)), (0, 0), 14)
    bg = bg * (1 - 0.28 * sh * (1 - wm))[..., None]
    srgb, sa = static_layer(panel, idx, n)
    pills = [pill(c["text"]) for c in panel["callouts"]]
    lessons = panel.get("lessons")
    if lessons:
        litems = [pill(f"{i + 1}.  {ln}", 38) for i, ln in enumerate(lessons)]
    x, y, s = WIN
    nf = len(clip)
    frames = range(nf) if still is None else [min(nf - 1, int(still * FPS))]
    path = os.path.join(out_dir, panel["slug"] + ".mp4")
    vid = path + ".v.mp4"
    proc = None
    for fi in frames:
        t = fi / FPS
        frame = bg.copy()
        v = clip[fi].astype(np.float32)
        if lessons:                                          # the reel softly behind the list
            v = cv2.GaussianBlur(v, (0, 0), 6) * 0.55 + PAPER * 0.45
        # fade the clip in and out so each panel loops gently
        fade = min(1.0, (t + 0.5 / FPS) / 0.25, (nf / FPS - t) / 0.25)
        v = v * fade + PAPER * (1 - fade)
        win = frame[y:y + s, x:x + s]
        m = wm[y:y + s, x:x + s, None]
        win[:] = win * (1 - m) + v * m
        frame = frame * (1 - sa[..., None]) + srgb * sa[..., None]
        for c, img in zip(panel["callouts"], pills):
            draw_callout(frame, c, img, t, panel["crop_y"])
        if lessons:
            for i, img in enumerate(litems):
                u = ease((t - 0.3 - 0.45 * i) / 0.4)
                if u > 0:
                    h_, w_ = img.shape[:2]
                    comp(frame, img, W / 2 - w_ / 2 - 30 * (1 - u), 300 + i * 132, u)
        out = np.clip(frame, 0, 255).astype(np.uint8)
        if still is not None:
            return out
        if proc is None:
            proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
                                     "medium", "-crf", "19", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
        proc.stdin.write(out.tobytes())
    proc.stdin.close(); proc.wait()
    # the reel's own sound for this moment, retimed with the picture, faded at the ends
    dur = nf / FPS
    af = []
    sp = speed
    while sp > 2.0:
        af.append("atempo=2.0"); sp /= 2.0
    while sp < 0.5:
        af.append("atempo=0.5"); sp /= 0.5
    af.append(f"atempo={sp:.4f}")
    vol = 0.55 if lessons else 1.0
    af += [f"volume={vol}", f"afade=t=in:d=0.25", f"afade=t=out:st={max(0, dur - 0.35):.2f}:d=0.35"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-ss", f"{t0}", "-t", f"{t1 - t0}", "-i", src,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", ",".join(af), "-c:a", "aac", "-b:a", "160k",
                    "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", path], check=True)
    os.remove(vid)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=os.path.join(HERE, "out", "art_IMG_0658.mp4"))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "carousel"))
    ap.add_argument("--still", nargs=2, type=float, default=None, metavar=("PANEL", "T"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.still:
        i = int(a.still[0])
        img = build_panel(a.src, PANELS[i], i, len(PANELS), a.out, still=a.still[1])
        p = os.path.join(a.out, f".still_{i}.png")
        Image.fromarray(img).save(p)
        print(p)
        return
    for i, p in enumerate(PANELS):
        print(build_panel(a.src, p, i, len(PANELS), a.out))


if __name__ == "__main__":
    main()
