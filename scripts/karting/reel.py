"""Reel vertical karting pour la chaîne Karting Tinkan (Louis & Marius).

Une vraie vidéo karting d'abord : passage à 121 km/h, les deux pilotes, la check-list
avant roulage, le départ en piste, le coucher de soleil. Oscar n'apparaît qu'à l'écran du
téléphone pendant la check-list du kart (« État des lieux · Kart #202 »), sans slogan :
ceux qui le remarquent le remarquent.

Textes courts et discrets, montage Pillow + ffmpeg, 1080x1920, 30 i/s.

Usage :
    python3 reel.py --media DOSSIER --work DOSSIER --out DOSSIER

--media : freres.png  kart.webp  sunset.jpg
--work  : red/ yellow/ speed/ (images extraites des vidéos) et speed.wav, voir README
"""

import argparse
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
TOP_KMH = 121
SR = 44100

ORANGE = (247, 148, 29)
NAVY = (15, 23, 42)
SLATE = (71, 85, 105)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
PAPER = (248, 250, 252)
WHITE = (255, 255, 255)

INTER = "/usr/share/fonts/opentype/inter/"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJIS = set("😏🏁💀👀😉🔍🧽")


def font(weight, size):
    return ImageFont.truetype(f"{INTER}Inter-{weight}.otf", size)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def back_out(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------------------------------------------------------- texte riche

_emoji_cache = {}


def emoji(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (160, 160))
        ImageDraw.Draw(im).text((8, 8), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        _emoji_cache[key] = im.resize((size, int(size * im.height / im.width)), Image.LANCZOS)
    return _emoji_cache[key]


def segments(line, color):
    """'texte [orange]mot[/] 😏' -> [(texte, couleur), ...] ; emoji isolés."""
    out, cur = [], color
    i = 0
    while i < len(line):
        if line.startswith("[o]", i):
            cur = ORANGE
            i += 3
            continue
        if line.startswith("[r]", i):
            cur = RED
            i += 3
            continue
        if line.startswith("[/]", i):
            cur = color
            i += 3
            continue
        ch = line[i]
        if ch in EMOJIS:
            out.append((ch, None))
        elif out and out[-1][1] == cur:
            out[-1] = (out[-1][0] + ch, cur)
        else:
            out.append((ch, cur))
        i += 1
    return out


def rich_line(line, fnt, color, stroke=0, stroke_fill=(0, 0, 0)):
    segs = segments(line, color)
    asc, desc = fnt.getmetrics()
    lh = asc + desc
    esz = int(fnt.size * 1.05)
    widths = []
    for s, c in segs:
        widths.append(esz + 8 if c is None else int(fnt.getlength(s)))
    pad = stroke + 4
    im = Image.new("RGBA", (sum(widths) + 2 * pad, lh + 2 * pad))
    d = ImageDraw.Draw(im)
    x = pad
    for (s, c), w in zip(segs, widths):
        if c is None:
            e = emoji(s, esz)
            im.alpha_composite(e, (x + 4, pad + (lh - e.height) // 2 - 4))
        else:
            d.text((x, pad), s, font=fnt, fill=c, stroke_width=stroke, stroke_fill=stroke_fill)
        x += w
    return im


def caption(lines, size=78, style="stroke", color=WHITE):
    """Bloc de légende centré (RGBA). style : stroke (contour noir) ou box (bandeau blanc)."""
    fnt = font("Black", size)
    ims = []
    for ln in lines:
        if style == "box":
            t = rich_line(ln, fnt, NAVY if color == WHITE else color)
            b = Image.new("RGBA", (t.width + 44, t.height + 30))
            ImageDraw.Draw(b).rounded_rectangle((0, 0, b.width - 1, b.height - 1), 18, fill=WHITE)
            b.alpha_composite(t, (22, 12))
            ims.append(b)
        else:
            ims.append(rich_line(ln, fnt, color, stroke=8))
    gap = 6 if style == "box" else -6
    w = max(i.width for i in ims)
    h = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new("RGBA", (w, h))
    y = 0
    for i in ims:
        out.alpha_composite(i, ((w - i.width) // 2, y))
        y += i.height + gap
    if style == "stroke":
        sh = out.copy().filter(ImageFilter.GaussianBlur(10))
        a = np.asarray(sh).copy()
        a[..., :3] = 0
        a[..., 3] = (a[..., 3] * 0.55).astype(np.uint8)
        base = Image.fromarray(a)
        base.alpha_composite(out)
        out = base
    return out


def place(frame, layer, cx, cy, t_in, t, t_out=None, pop=True):
    """Pose un calque centré en (cx, cy) avec apparition « pop » et sortie en fondu."""
    if t < t_in or (t_out is not None and t >= t_out):
        return
    k = back_out((t - t_in) / 0.18) if pop else 1.0
    alpha = ease((t - t_in) / 0.08)
    if t_out is not None:
        alpha *= ease((t_out - t) / 0.08)
    lay = layer
    if abs(k - 1) > 1e-3:
        s = max(0.3, 0.6 + 0.4 * k)
        lay = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.BILINEAR)
    if alpha < 0.999:
        a = np.asarray(lay).copy()
        a[..., 3] = (a[..., 3] * alpha).astype(np.uint8)
        lay = Image.fromarray(a)
    frame.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


# ---------------------------------------------------------------- images

def cover(im, cx_frac=0.5, cy_frac=0.5):
    """Recadre en 9:16 (centre réglable) et met à 1080x1920."""
    im = im.convert("RGB")
    r = W / H
    if im.width / im.height > r:
        nw = int(im.height * r)
        x0 = int((im.width - nw) * cx_frac)
        im = im.crop((x0, 0, x0 + nw, im.height))
    else:
        nh = int(im.width / r)
        y0 = int((im.height - nh) * cy_frac)
        im = im.crop((0, y0, im.width, y0 + nh))
    return im.resize((W, H), Image.LANCZOS)


def kenburns(img, t, z0, z1, fx=0.5, fy=0.5, dur=1.0):
    """Zoom lent de z0 à z1 vers le point (fx, fy) (fractions de l'image)."""
    z = z0 + (z1 - z0) * ease(t / dur)
    cw, ch = img.width / z, img.height / z
    x0 = min(max(fx * img.width - cw / 2, 0), img.width - cw)
    y0 = min(max(fy * img.height - ch / 2, 0), img.height - ch)
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)), (x0, y0, z)


def grain(frame, amount=5, seed=0):
    rng = np.random.default_rng(seed)
    a = np.asarray(frame.convert("RGB")).astype(np.int16)
    a += rng.integers(-amount, amount + 1, size=(H // 4, W // 4, 1)).repeat(4, 0).repeat(4, 1)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def flash(frame, strength):
    if strength <= 0:
        return frame
    return Image.blend(frame, Image.new("RGBA", frame.size, (255, 255, 255, 255)), min(strength, 1))


def vignette():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.75)) ** 2)
    a = (np.clip(d - 0.45, 0, 1) * 330).clip(0, 150).astype(np.uint8)
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = a
    return Image.fromarray(v)


# ---------------------------------------------------------------- UI Oscar

def check_icon(size, ok=True, t=1.0):
    im = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(im)
    if t <= 0:
        d.ellipse((3, 3, size - 4, size - 4), outline=(203, 213, 225), width=max(3, size // 14))
        return im
    s = 0.4 + 0.6 * back_out(t)
    r = size / 2 * s
    c = size / 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=GREEN if ok else RED)
    lw = max(4, size // 9)
    if ok:
        pts = [(c - r * 0.45, c + r * 0.02), (c - r * 0.1, c + r * 0.36), (c + r * 0.48, c - r * 0.3)]
        d.line(pts, fill=WHITE, width=lw, joint="curve")
    else:
        q = r * 0.38
        d.line((c - q, c - q, c + q, c + q), fill=WHITE, width=lw)
        d.line((c - q, c + q, c + q, c - q), fill=WHITE, width=lw)
    return im


def oscar_card(width, title, subtitle, rows, progress, cols=None):
    """Carte au style de l'app Oscar : bandeau orange + lignes à cocher.

    rows : [(libellé, détail)] ; progress[i] in [0..1] = avancement de la coche i.
    cols : None (une colonne) ou [(entete, [(ok, detail), ...]), ...] pour le comparatif.
    """
    hdr = 132
    rh = 88
    pad = 26
    h = hdr + pad + len(rows) * (rh + 16) + pad - 16 + (60 if cols else 0)
    im = Image.new("RGBA", (width, h))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, width - 1, h - 1), 38, fill=PAPER)
    d.rounded_rectangle((0, 0, width - 1, hdr + 40), 38, fill=ORANGE)
    d.rectangle((0, hdr, width - 1, hdr + 40), fill=PAPER)
    d.text((36, 24), title, font=font("ExtraBold", 48), fill=NAVY)
    d.text((36, 82), subtitle, font=font("SemiBold", 29), fill=NAVY)
    y = hdr + pad
    if cols:
        for j, (head, _) in enumerate(cols):
            cx = width - 70 - (len(cols) - 1 - j) * 150
            tw = font("Bold", 26).getlength(head)
            d.text((cx - tw / 2, y + 4), head, font=font("Bold", 26), fill=SLATE)
        y += 60
    for i, (label, detail) in enumerate(rows):
        d.rounded_rectangle((pad, y, width - pad, y + rh), 24, fill=WHITE)
        d.text((pad + 30, y + 10), label, font=font("Bold", 36), fill=NAVY)
        p = progress[i] if i < len(progress) else 0
        if cols:
            for j, (_, vals) in enumerate(cols):
                ok, det = vals[i]
                cx = width - 70 - (len(cols) - 1 - j) * 150
                pj = min(max(p * len(cols) - j, 0), 1)
                ic = check_icon(58, ok, pj)
                im.alpha_composite(ic, (int(cx - 29), y + 4))
                if pj > 0:
                    col = GREEN if ok else RED
                    tw = font("SemiBold", 22).getlength(det)
                    d.text((cx - tw / 2, y + 62), det, font=font("SemiBold", 22), fill=col)
            d.text((pad + 30, y + 52), detail, font=font("Medium", 24), fill=SLATE)
        else:
            if p > 0:
                d.text((pad + 30, y + 52), detail, font=font("Medium", 24), fill=SLATE)
            im.alpha_composite(check_icon(60, True, p), (width - pad - 30 - 60, y + 14))
        y += rh + 16
    return im


def drop_shadow(layer, radius=30, alpha=0.45, off=(0, 18)):
    a = np.zeros((layer.height + 4 * radius, layer.width + 4 * radius, 4), np.uint8)
    a[2 * radius:2 * radius + layer.height, 2 * radius:2 * radius + layer.width, 3] = (
        np.asarray(layer)[..., 3] * alpha
    ).astype(np.uint8)
    sh = Image.fromarray(a).filter(ImageFilter.GaussianBlur(radius))
    sh.alpha_composite(layer, (2 * radius - off[0], 2 * radius - off[1]))
    return sh


def brackets(size, color=ORANGE, lw=9):
    im = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(im)
    L = size // 4
    s = size - 1
    for (x, y, dx, dy) in [(0, 0, 1, 1), (s, 0, -1, 1), (0, s, 1, -1), (s, s, -1, -1)]:
        d.line((x, y, x + dx * L, y), fill=color, width=lw)
        d.line((x, y, x, y + dy * L), fill=color, width=lw)
    return im


def soft_caption(text, size=52, color=WHITE):
    """Légende discrète : graisse moyenne, ombre douce, pas de contour."""
    t = rich_line(text, font("SemiBold", size), color)
    a = np.asarray(t).copy()
    sh = a.copy()
    sh[..., :3] = 0
    sh[..., 3] = (sh[..., 3] * 0.7).astype(np.uint8)
    sh = Image.fromarray(sh).filter(ImageFilter.GaussianBlur(8))
    out = Image.new("RGBA", (t.width + 20, t.height + 20))
    out.alpha_composite(sh, (10, 14))
    out.alpha_composite(t, (10, 10))
    return out


def speed_readout(kmh):
    """Compteur de vitesse sobre (sans bandeau)."""
    f1, f2 = font("Bold", 38), font("Black", 132)
    t1, t2 = "TOP SPEED", f"{kmh} km/h"
    w = int(max(f1.getlength(t1), f2.getlength(t2))) + 60
    im = Image.new("RGBA", (w, 230))
    d = ImageDraw.Draw(im)
    d.text(((w - f1.getlength(t1)) / 2, 10), t1, font=f1, fill=WHITE)
    d.text(((w - f2.getlength(t2)) / 2, 52), t2, font=f2, fill=(255, 226, 0))
    a = np.asarray(im).copy()
    a[..., :3] = 0
    sh = Image.fromarray(a).filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", im.size)
    out.alpha_composite(sh, (0, 4))
    out.alpha_composite(sh, (0, 4))
    out.alpha_composite(im)
    return out


def phone_check(rows, progress):
    """Petit téléphone tenu dans le coin : écran Oscar, check-list du kart."""
    pw, ph = 640, 1200
    im = Image.new("RGBA", (pw, ph))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), 84, fill=(17, 17, 20))
    sw, sh = pw - 40, ph - 40
    scr = Image.new("RGBA", (sw, sh), PAPER)
    card = oscar_card(sw, "État des lieux", "Kart #202", rows, progress)
    s = ImageDraw.Draw(scr)
    s.rectangle((0, 0, sw, 90), fill=ORANGE)  # barre d'état au-dessus de la carte
    scr.alpha_composite(card, (0, 70))
    s.rounded_rectangle((sw / 2 - 100, 14, sw / 2 + 100, 54), 20, fill=(17, 17, 20))
    # bouton photo en bas de l'écran, comme dans l'app
    s.rounded_rectangle((sw / 2 - 90, sh - 240, sw / 2 + 90, sh - 90), 30, fill=NAVY)
    s.ellipse((sw / 2 - 42, sh - 207, sw / 2 + 42, sh - 123), fill=WHITE)
    s.ellipse((sw / 2 - 26, sh - 191, sw / 2 + 26, sh - 139), fill=ORANGE)
    mask = Image.new("L", (sw, sh))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, sh - 1), 66, fill=255)
    im.paste(scr, (20, 20), mask)
    return im


# ---------------------------------------------------------------- montage

def load_frames(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".jpg")]


def clip_frame(frames, lt, z, anchor):
    """Image de clip zoomée pour sortir du cadre le texte incrusté d'origine.

    anchor = "top" garde le haut (texte en bas), "bottom" garde le bas (texte en haut).
    """
    fr = Image.open(frames[min(int(lt * FPS), len(frames) - 1)]).convert("RGB")
    fy = 1 / (2 * z) if anchor == "top" else 1 - 1 / (2 * z)
    out, _ = kenburns(fr, 0, z, z, 0.5, fy)
    return out


def build(media, work, out_dir):
    brothers = cover(Image.open(f"{media}/freres.png"), 0.5, 0.0)
    kart_raw = Image.open(f"{media}/kart.webp").convert("RGB")
    # la photo du kart a des bandes noires en haut et en bas : on les retire
    rows = np.where(np.asarray(kart_raw).mean(axis=(1, 2)) > 20)[0]
    kart_c = kart_raw.crop((0, rows[0], kart_raw.width, rows[-1]))
    kx0 = 190
    kw = int(kart_c.height * W / H)
    kart = kart_c.crop((kx0, 0, kx0 + kw, kart_c.height)).resize((W, H), Image.LANCZOS)
    kscale = W / kw
    sunset = cover(Image.open(f"{media}/sunset.jpg"), 0.38, 0.5).filter(ImageFilter.GaussianBlur(1.6))
    yellow = load_frames(f"{work}/yellow")
    speed = load_frames(f"{work}/speed")
    red = load_frames(f"{work}/red")
    vig = vignette()

    # chronologie (secondes)
    S = dict(spd=(0.0, 3.8), freres=(3.8, 6.4), check=(6.4, 10.9), yel=(10.9, 12.7),
             red=(12.7, 14.4), end=(14.4, 18.6))
    total = S["end"][1]

    # points contrôlés sur la photo du kart (coordonnées source, bandes noires retirées)
    insp = [(1020, 1150), (760, 1300), (1480, 1950), (470, 2330)]
    rows_ui = [("Volant", "RAS"), ("Plaque 202", "RAS"), ("Pneus", "Neufs"), ("Carénage", "RAS")]
    T0, STEP = 0.6, 0.85

    cap_spd = soft_caption("pas mal pour un samedi")
    cap_freres = soft_caption("Louis & Marius 🏁")
    cap_check = soft_caption("check avant de rouler")
    cap_yel = soft_caption("à toi")
    cap_red = soft_caption("👀")
    cap_end = soft_caption("prochain roulage bientôt")

    events = [(a, "whoosh") for a, _ in list(S.values())[1:]]
    for i in range(len(insp)):
        events += [(S["check"][0] + T0 + i * STEP, "shutter")]

    os.makedirs(out_dir, exist_ok=True)
    vpath = f"{work}/video.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-pix_fmt", "yuv420p", vpath],
        stdin=subprocess.PIPE,
    )
    for n in range(int(round(total * FPS))):
        t = n / FPS
        if t < S["spd"][1]:
            lt = t - S["spd"][0]
            # zoom qui sort du cadre le bandeau « 114 KM/H » incrusté en haut
            z = 1.36 + 0.01 * math.sin(lt * 41)
            fr = clip_frame(speed, lt, z, "bottom").convert("RGBA")
            kmh = int(round(TOP_KMH * ease(lt / 1.6)))
            place(fr, speed_readout(kmh), W / 2, 300, 0.0, lt, pop=False)
            place(fr, cap_spd, W / 2, 1660, 1.9, lt)
        elif t < S["freres"][1]:
            lt = t - S["freres"][0]
            fr, _ = kenburns(brothers, lt, 1.0, 1.1, 0.5, 0.35, dur=2.6)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            place(fr, cap_freres, W / 2, 1660, 0.3, lt)
        elif t < S["check"][1]:
            lt = t - S["check"][0]
            fr, (x0, y0, z) = kenburns(kart, lt, 1.0, 1.08, 0.5, 0.5, dur=4.5)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            prog = []
            for i, (px, py) in enumerate(insp):
                ti = T0 + i * STEP
                prog.append(ease((lt - ti - 0.2) / 0.2))
                if ti <= lt < ti + STEP:
                    fx = ((px - kx0) * kscale - x0) * z
                    fy = (py * kscale - y0) * z
                    k = back_out((lt - ti) / 0.25)
                    size = int(170 * (1.4 - 0.4 * k))
                    fr.alpha_composite(brackets(size, (255, 255, 255), 5),
                                       (int(fx - size / 2), int(fy - size / 2)))
                    if lt - ti < 0.1:
                        fr = flash(fr, 0.5 * (1 - (lt - ti) / 0.1))
            ph = phone_check(rows_ui, prog)
            ph = ph.resize((int(ph.width * 0.52), int(ph.height * 0.52)), Image.LANCZOS)
            ph = drop_shadow(ph, 24, 0.55).rotate(-6, expand=True, resample=Image.BICUBIC)
            k = back_out(lt / 0.4)
            place(fr, ph, W - 230, 1430 + (1 - k) * 700, 0, lt, pop=False)
            place(fr, cap_check, W / 2 - 150, 1780, 0.2, lt)
        elif t < S["yel"][1]:
            lt = t - S["yel"][0]
            # zoom qui sort du cadre le texte incrusté en bas
            fr = clip_frame(yellow, lt, 1.26 + 0.03 * lt, "top").convert("RGBA")
            place(fr, cap_yel, W / 2, 1660, 0.2, lt)
        elif t < S["red"][1]:
            lt = t - S["red"][0]
            fr = clip_frame(red, lt, 1.26 + 0.05 * lt, "top").convert("RGBA")
            place(fr, cap_red, W / 2, 1660, 0.3, lt)
        else:
            lt = t - S["end"][0]
            fr, _ = kenburns(sunset, lt, 1.0, 1.12, 0.45, 0.45, dur=4.2)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            place(fr, cap_end, W / 2, 1660, 0.6, lt)
            if lt > 3.7:
                fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), ease((lt - 3.7) / 0.5))
        for a, _ in list(S.values())[1:]:
            if a <= t < a + 0.12:
                zz = 1.05 - 0.05 * ease((t - a) / 0.12)
                fr, _ = kenburns(fr.convert("RGB"), 0, zz, zz)
                fr = fr.convert("RGBA")
        fr = grain(fr, 4, n)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    music = render_audio(total, events, S, f"{work}/speed.wav", True)
    dry = render_audio(total, events, S, f"{work}/speed.wav", False)
    for name, path in [("karting_tinkan_121.mp4", music),
                       ("karting_tinkan_121_sans_musique.mp4", dry)]:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vpath, "-i", path, "-c:v", "copy",
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR),
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                        f"{out_dir}/{name}"], check=True)


# ---------------------------------------------------------------- son

def read_wav(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).reshape(-1, 2)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t / decay)


def sfx(kind, rng):
    if kind == "kick":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        f = 45 + 110 * np.exp(-t * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.12)
    if kind == "hat":
        n = int(0.06 * SR)
        x = rng.standard_normal(n)
        x = np.diff(x, prepend=0)
        return 0.25 * x * env(n, 0.001, 0.015)
    if kind == "snare":
        n = int(0.2 * SR)
        t = np.arange(n) / SR
        return (0.5 * rng.standard_normal(n) * env(n, 0.001, 0.05)
                + 0.4 * np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 0.06))
    if kind == "whoosh":
        n = int(0.4 * SR)
        x = rng.standard_normal(n)
        k = np.hanning(n) ** 2
        y = np.convolve(x, np.ones(18) / 18, "same") * k
        return 0.9 * y
    if kind == "shutter":
        n = int(0.12 * SR)
        x = rng.standard_normal(n)
        e = env(n, 0.0005, 0.008) + 0.7 * np.roll(env(n, 0.0005, 0.012), int(0.06 * SR))
        return 0.6 * np.diff(x, prepend=0) * e
    if kind in ("ding", "pop"):
        n = int(0.6 * SR)
        t = np.arange(n) / SR
        f = 1320 if kind == "ding" else 880
        return 0.28 * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t)) * env(n, 0.002, 0.12)
    if kind == "buzz":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        return 0.22 * np.sign(np.sin(2 * np.pi * 150 * t)) * env(n, 0.005, 0.2)
    if kind == "stamp":
        n = int(0.7 * SR)
        t = np.arange(n) / SR
        f = 40 + 90 * np.exp(-t * 25)
        return (1.0 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.18)
                + 0.5 * rng.standard_normal(n) * env(n, 0.001, 0.03))
    if kind == "scribble":
        n = int(1.6 * SR)
        t = np.arange(n) / SR
        x = np.diff(rng.standard_normal(n), prepend=0)
        m = 0.5 + 0.5 * np.sin(2 * np.pi * 7 * t) ** 2
        return 0.12 * x * m * np.hanning(n)
    raise ValueError(kind)


def render_audio(total, events, S, engine_wav, with_music):
    rng = np.random.default_rng(7)
    n = int(total * SR) + SR
    mix = np.zeros((n, 2), np.float32)

    def add(sig, t0, gain=1.0, pan=0.0):
        i = int(t0 * SR)
        sig = sig[: max(0, n - i)]
        mix[i:i + len(sig), 0] += sig * gain * (1 - pan)
        mix[i:i + len(sig), 1] += sig * gain * (1 + pan)

    if with_music:
        bpm = 124
        beat = 60 / bpm
        nb = int(total / beat) + 1
        bass_notes = [55.0, 55.0, 65.41, 49.0]
        for b in range(nb):
            t0 = b * beat
            if t0 >= total - 0.3:
                break
            drop = t0 >= S["freres"][0]
            # le moteur parle tout seul pendant le passage à 121 km/h
            duck = 0.35 if S["spd"][0] <= t0 < S["spd"][1] else 1.0
            if drop or b % 2 == 0:
                add(sfx("kick", rng), t0, 0.75 * duck)
            if drop:
                add(sfx("hat", rng), t0 + beat / 2, 0.8 * duck, 0.3)
                if b % 2 == 1:
                    add(sfx("snare", rng), t0, 0.55 * duck)
                f = bass_notes[(b // 4) % 4]
                m = int(beat * SR)
                tt = np.arange(m) / SR
                bass = 0.22 * np.tanh(3 * np.sin(2 * np.pi * f * tt)) * env(m, 0.005, 0.25)
                add(bass, t0, duck)
            else:
                add(sfx("hat", rng), t0 + beat / 2, 0.4, -0.3)
    for t0, kind in events:
        add(sfx(kind, rng), t0, 0.9)

    eng = read_wav(engine_wav)
    a, b = S["spd"]
    m = min(len(eng), int((b - a) * SR))
    fade = np.ones(m, np.float32)
    k = int(0.15 * SR)
    fade[:k] = np.linspace(0, 1, k)
    fade[-k:] = np.linspace(1, 0, k)
    mix[int(a * SR):int(a * SR) + m] += eng[:m] * fade[:, None] * 1.1

    end = int((total - 0.5) * SR)
    mix[end:end + int(0.5 * SR)] *= np.linspace(1, 0, int(0.5 * SR))[:, None][: len(mix) - end]
    mix = mix[: int(total * SR)]
    peak = np.abs(mix).max()
    mix = np.tanh(mix / peak * 1.4) * 0.89
    path = f"{os.path.dirname(engine_wav)}/_mix_{'music' if with_music else 'dry'}.wav"
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--media", required=True, help="dossier des photos et vidéos sources")
    ap.add_argument("--work", required=True, help="dossier des images extraites (red/, yellow/, speed/, speed.wav)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build(args.media, args.work, args.out)
