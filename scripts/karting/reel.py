"""Reel vertical « État des lieux du kart » pour la chaîne Karting Tinkan (Louis & Marius).

Histoire : le grand frère prête son kart… mais fait d'abord un état des lieux d'entrée
sur son téléphone (interface Oscar). Le frère part à 114 km/h, revient, et le comparatif
entrée / sortie tranche : pneus lisses, retenu sur la caution. Oscar n'apparaît que comme
l'outil utilisé dans la blague, puis en petite signature à la fin.

Montage 100 % programmatique (Pillow + ffmpeg), 1080x1920, 30 i/s, son synthétisé.

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


def pill(text, ok=True):
    fnt = font("Bold", 36)
    tw = int(fnt.getlength(text))
    im = Image.new("RGBA", (tw + 110, 72))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, 71), 36, fill=WHITE)
    im.alpha_composite(check_icon(48, ok, 1), (14, 12))
    d.text((74, 14), text, font=fnt, fill=NAVY)
    return im


def signature_path():
    """Tracé de signature manuscrite (points normalisés 0..1)."""
    pts = []
    for i in range(400):
        u = i / 399
        x = 0.06 + 0.86 * u
        y = 0.55 - 0.28 * math.sin(u * 13.5) * (1 - 0.5 * u) - 0.12 * math.sin(u * 4.2 + 1)
        if u < 0.12:  # grande boucle d'initiale
            a = u / 0.12 * 2 * math.pi
            x = 0.12 + 0.07 * math.sin(a)
            y = 0.48 - 0.32 * math.cos(a) * (1 - u * 3)
        pts.append((x, y))
    pts += [(0.55 + 0.4 * u, 0.82 - 0.03 * u) for u in np.linspace(0, 1, 60)]  # paraphe
    return pts


SIG = signature_path()


def phone_sign(t, signed_at):
    """Téléphone à l'écran Oscar « Signature du locataire »."""
    pw, ph = 700, 1380
    im = Image.new("RGBA", (pw, ph))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), 92, fill=(17, 17, 20))
    sx, sy, sw, sh = 22, 22, pw - 44, ph - 44
    scr = Image.new("RGBA", (sw, sh))
    s = ImageDraw.Draw(scr)
    s.rectangle((0, 0, sw, sh), fill=PAPER)
    s.rectangle((0, 0, sw, 250), fill=ORANGE)
    s.text((44, 30), "9:41", font=font("SemiBold", 28), fill=NAVY)
    s.rounded_rectangle((sw / 2 - 110, 14, sw / 2 + 110, 58), 22, fill=(17, 17, 20))
    s.text((44, 110), "État des lieux", font=font("ExtraBold", 52), fill=NAVY)
    s.text((44, 176), "Entrée · Kart #202", font=font("SemiBold", 32), fill=NAVY)
    y = 290
    for lab in ["Volant", "Plaque 202", "Pneus", "Carénage"]:
        s.rounded_rectangle((30, y, sw - 30, y + 74), 20, fill=WHITE)
        s.text((60, y + 18), lab, font=font("Bold", 32), fill=NAVY)
        scr.alpha_composite(check_icon(46, True, 1), (sw - 30 - 24 - 46, y + 14))
        y += 88
    s.text((44, y + 20), "Signature du locataire", font=font("Bold", 34), fill=NAVY)
    bx0, by0, bx1, by1 = 30, y + 80, sw - 30, y + 380
    s.rounded_rectangle((bx0, by0, bx1, by1), 26, fill=WHITE, outline=(203, 213, 225), width=3)
    n = int(len(SIG) * ease(t / (signed_at - 0.35)))
    if n > 1:
        pts = [(bx0 + 20 + x * (bx1 - bx0 - 40), by0 + 20 + yy * (by1 - by0 - 40)) for x, yy in SIG[:n]]
        s.line(pts, fill=(29, 78, 216), width=7, joint="curve")
    by = by1 + 40
    pressed = t >= signed_at
    col = GREEN if pressed else (148, 163, 184)
    s.rounded_rectangle((30, by, sw - 30, by + 110), 55, fill=col)
    lab = "Signé  ✓" if pressed else "Signer"
    tw = font("Bold", 42).getlength(lab)
    s.text(((sw - tw) / 2, by + 30), lab, font=font("Bold", 42), fill=WHITE)
    mask = Image.new("L", (sw, sh))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw - 1, sh - 1), 72, fill=255)
    im.paste(scr, (sx, sy), mask)
    return im


def stamp(text1, text2):
    f1, f2 = font("Black", 64), font("Black", 44)
    w = int(max(f1.getlength(text1), f2.getlength(text2))) + 80
    im = Image.new("RGBA", (w, 210))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w - 5, 205), 22, outline=RED, width=10)
    d.text(((w - f1.getlength(text1)) / 2, 30), text1, font=f1, fill=RED)
    d.text(((w - f2.getlength(text2)) / 2, 118), text2, font=f2, fill=RED)
    return im.rotate(-9, expand=True, resample=Image.BICUBIC)


def signature_badge():
    """Petite signature de fin : carré orange + mention discrète."""
    f1, f2 = font("Bold", 34), font("Medium", 28)
    l1, l2 = "État des lieux fait avec Oscar", "monassistantoscar.com"
    w = int(max(f1.getlength(l1), f2.getlength(l2))) + 120
    im = Image.new("RGBA", (w, 100))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 8, 84, 92), 22, fill=ORANGE)
    d.ellipse((20, 28, 64, 72), outline=WHITE, width=9)
    d.text((104, 8), l1, font=f1, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((104, 56), l2, font=f2, fill=(226, 232, 240), stroke_width=2, stroke_fill=(0, 0, 0))
    return im


# ---------------------------------------------------------------- montage

def load_frames(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".jpg")]


def build(media, work, out_dir):
    brothers = cover(Image.open(f"{media}/freres.png"), 0.5, 0.0)
    kart_raw = Image.open(f"{media}/kart.webp").convert("RGB")
    # la photo du kart a des bandes noires en haut et en bas : on les retire
    a = np.asarray(kart_raw).mean(axis=(1, 2))
    rows = np.where(a > 20)[0]
    ky0 = rows[0]
    kart_c = kart_raw.crop((0, rows[0], kart_raw.width, rows[-1]))
    kx0 = 190
    kw = int(kart_c.height * W / H)
    kart = kart_c.crop((kx0, 0, kx0 + kw, kart_c.height)).resize((W, H), Image.LANCZOS)
    kscale = W / kw
    sunset = cover(Image.open(f"{media}/sunset.jpg"), 0.38, 0.5)
    sunset = sunset.filter(ImageFilter.GaussianBlur(1.6))
    kart_blur = kart.filter(ImageFilter.GaussianBlur(26))
    kart_blur = Image.blend(kart_blur, Image.new("RGB", (W, H), (0, 0, 0)), 0.45).convert("RGBA")
    yellow = load_frames(f"{work}/yellow")
    speed = load_frames(f"{work}/speed")
    red = load_frames(f"{work}/red")
    vig = vignette()

    # points d'inspection (coordonnées dans la photo du kart, bandes noires retirées)
    insp = [
        ((1020, 1150), "Volant : RAS"),
        ((760, 1300), "Plaque 202 : RAS"),
        ((1480, 1950), "Pneus : neufs"),
        ((470, 2330), "Carénage : 0 rayure"),
    ]
    insp_rows = [("Volant", "RAS"), ("Plaque 202", "RAS"), ("Pneus", "Neufs, 0 tour"),
                 ("Carénage", "Aucune rayure")]
    T_INSP0, T_STEP = 4.0, 1.25

    # chronologie (secondes)
    S = dict(hook=(0.0, 3.0), insp=(3.0, 9.4), sign=(9.4, 12.2), yel=(12.2, 14.0),
             spd=(14.0, 17.8), red=(17.8, 19.5), comp=(19.5, 23.6), end=(23.6, 28.0))
    total = S["end"][1]
    events = []  # (temps, type) pour le son

    cap_hook1 = caption(["J'ai prêté mon kart", "à mon frère…"], 84)
    cap_hook2 = caption(["…mais avant, j'ai fait", "un [o]ÉTAT DES LIEUX[/] 😏"], 84)
    cap_sign = caption(["Signature obligatoire.", "On ne rigole pas."], 70)
    cap_yel = caption(["Le locataire est prêt 🏁"], 68, style="box")
    cap_spd = caption(["…et il me le ramène", "à 114 km/h 💀"], 64, style="box")
    cap_red = caption(["Moi au retour du kart 👀"], 68, style="box")
    cap_comp = caption(["Le comparatif", "ne ment pas 🔍"], 72)
    cap_end1 = caption(["Moralité :", "toujours faire un", "[o]état des lieux[/]."], 84)
    cap_end2 = caption(["Même pour un kart 😉"], 60)
    st = stamp("PNEUS LISSES", "RETENU SUR LA CAUTION")
    badge = signature_badge()
    card_comp_rows = [("Volant", ""), ("Plaque 202", ""), ("Carénage", ""), ("Pneus", "")]
    comp_cols = [("ENTRÉE", [(True, "RAS"), (True, "RAS"), (True, "RAS"), (True, "neufs")]),
                 ("SORTIE", [(True, "RAS"), (True, "RAS"), (True, "RAS"), (False, "lisses")])]

    # événements sonores
    events += [(S["insp"][0], "whoosh"), (S["sign"][0], "whoosh"), (S["yel"][0], "whoosh"),
               (S["spd"][0], "whoosh"), (S["red"][0], "whoosh"), (S["comp"][0], "whoosh"),
               (S["end"][0], "whoosh"), (1.45, "pop")]
    for i in range(len(insp)):
        ti = T_INSP0 + i * T_STEP
        events += [(ti, "shutter"), (ti + 0.35, "ding")]
    events += [(S["sign"][0] + 0.3, "scribble"), (S["sign"][0] + 2.0, "ding")]
    for i in range(4):
        events += [(S["comp"][0] + 0.5 + i * 0.45, "ding" if i < 3 else "buzz")]
    T_STAMP = S["comp"][0] + 2.6
    events += [(T_STAMP, "stamp")]

    os.makedirs(out_dir, exist_ok=True)
    vpath = f"{work}/video.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-pix_fmt", "yuv420p", vpath],
        stdin=subprocess.PIPE,
    )
    nfr = int(round(total * FPS))
    for n in range(nfr):
        t = n / FPS
        if t < S["hook"][1]:
            lt = t
            fr, _ = kenburns(brothers, lt, 1.0, 1.14, 0.5, 0.35, dur=3.0)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            place(fr, cap_hook1, W / 2, 1330, 0.05, lt, 1.4)
            place(fr, cap_hook2, W / 2, 1330, 1.4, lt)
        elif t < S["insp"][1]:
            lt = t - S["insp"][0]
            fr, (x0, y0, z) = kenburns(kart, lt, 1.0, 1.1, 0.5, 0.55, dur=6.4)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            prog = []
            for i, ((px, py), lab) in enumerate(insp):
                ti = T_INSP0 - S["insp"][0] + i * T_STEP
                prog.append(ease((lt - ti - 0.3) / 0.25))
                if ti <= lt < ti + T_STEP:
                    fx = ((px - kx0) * kscale - x0) * z
                    fy = (py * kscale - y0) * z
                    k = back_out((lt - ti) / 0.25)
                    size = int(230 * (1.5 - 0.5 * k))
                    fr.alpha_composite(brackets(size), (int(fx - size / 2), int(fy - size / 2)))
                    p = pill(lab)
                    side = -1 if fx > W * 0.55 else 1
                    place(fr, p, min(max(fx + side * (p.width / 2 + 40), p.width / 2 + 20),
                                     W - p.width / 2 - 20), fy + 160, ti + 0.3, lt)
                    fr = flash(fr, 0.85 * (1 - (lt - ti) / 0.12) if lt - ti < 0.12 else 0)
            card = oscar_card(860, "État des lieux", "Entrée · Kart #202 · Locataire : mon frère",
                              insp_rows, prog)
            k = back_out(lt / 0.35)
            place(fr, drop_shadow(card), W / 2, 40 + card.height / 2 - (1 - k) * 600, 0, lt, pop=False)
        elif t < S["sign"][1]:
            lt = t - S["sign"][0]
            fr = kart_blur.copy()
            ph = phone_sign(lt, 2.0)
            k = back_out(lt / 0.4)
            ph = ph.resize((int(ph.width * 0.92), int(ph.height * 0.92)), Image.LANCZOS)
            place(fr, drop_shadow(ph, 40, 0.6), W / 2, 1110 + (1 - k) * 900, 0, lt, pop=False)
            place(fr, cap_sign, W / 2, 230, 0.15, lt)
        elif t < S["yel"][1]:
            lt = t - S["yel"][0]
            i = min(int(lt * FPS), len(yellow) - 1)
            src = Image.open(yellow[i]).convert("RGBA")
            place(src, cap_yel, W / 2, 1602, 0.0, lt, pop=False)  # masque le texte incrusté d'origine
            fr, _ = kenburns(src.convert("RGB"), lt, 1.0, 1.06, 0.5, 0.4, dur=1.8)
            fr = fr.convert("RGBA")
        elif t < S["spd"][1]:
            lt = t - S["spd"][0]
            i = min(int(lt * FPS), len(speed) - 1)
            fr = Image.open(speed[i]).convert("RGB")
            sh = 1.03 + 0.012 * math.sin(lt * 41)
            fr, _ = kenburns(fr, 0, sh, sh, 0.5 + 0.004 * math.sin(lt * 53), 0.5 + 0.004 * math.cos(lt * 47))
            fr = fr.convert("RGBA")
            place(fr, cap_spd, W / 2, 1520, 0.2, lt)
        elif t < S["red"][1]:
            lt = t - S["red"][0]
            i = min(int(lt * FPS), len(red) - 1)
            src = Image.open(red[i]).convert("RGBA")
            place(src, cap_red, W / 2, 1600, 0.0, lt, pop=False)  # masque le texte incrusté d'origine
            fr, _ = kenburns(src.convert("RGB"), lt, 1.0, 1.12, 0.4, 0.45, dur=1.7)
            fr = fr.convert("RGBA")
        elif t < S["comp"][1]:
            lt = t - S["comp"][0]
            fr = kart_blur.copy()
            prog = [ease((lt - 0.5 - i * 0.45) / 0.3) for i in range(4)]
            card = oscar_card(940, "Comparatif", "Kart #202 · Entrée / Sortie", card_comp_rows, prog,
                              cols=comp_cols)
            k = back_out(lt / 0.35)
            place(fr, drop_shadow(card), W / 2, 980 + (1 - k) * 900, 0, lt, pop=False)
            place(fr, cap_comp, W / 2, 330, 0.1, lt)
            ts = T_STAMP - S["comp"][0]
            if lt >= ts:
                s = 1 + 1.4 * (1 - ease((lt - ts) / 0.14))
                ss = st.resize((int(st.width * s), int(st.height * s)), Image.BILINEAR)
                fr.alpha_composite(ss, (int(W / 2 - ss.width / 2), int(1530 - ss.height / 2)))
                if lt - ts < 0.2:
                    dx = int(14 * math.sin((lt - ts) * 120) * (1 - (lt - ts) / 0.2))
                    fr = Image.fromarray(np.roll(np.asarray(fr), dx, axis=1))
        else:
            lt = t - S["end"][0]
            fr, _ = kenburns(sunset, lt, 1.0, 1.12, 0.45, 0.45, dur=4.4)
            fr = fr.convert("RGBA")
            fr.alpha_composite(vig)
            place(fr, cap_end1, W / 2, 470, 0.15, lt)
            place(fr, cap_end2, W / 2, 760, 1.5, lt)
            place(fr, badge, W / 2, 1770, 2.2, lt, pop=False)
            if lt > 4.0:
                fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), ease((lt - 4.0) / 0.4))
        # micro « punch » de zoom à chaque coupe
        for a, _ in S.values():
            if 0 < a <= t < a + 0.12:
                z = 1.06 - 0.06 * ease((t - a) / 0.12)
                fr, _ = kenburns(fr.convert("RGB"), 0, z, z)
                fr = fr.convert("RGBA")
        fr = grain(fr, 4, n)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    music = render_audio(total, events, S, f"{work}/speed.wav", True)
    dry = render_audio(total, events, S, f"{work}/speed.wav", False)
    for name, path in [("oscar_karting_etat_des_lieux.mp4", music),
                       ("oscar_karting_etat_des_lieux_sans_musique.mp4", dry)]:
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
            drop = t0 >= S["insp"][0]
            # le moteur parle tout seul pendant le passage à 114 km/h
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
