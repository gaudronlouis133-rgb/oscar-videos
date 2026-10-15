"""Montage TEAMKTC « Nouveau kart Praga » — vidéo verticale 9:16, 15 s, muette.

Anime deux photos (travellings, zooms, lumière, particules, textes) sans jamais les redessiner :
le kart, les visages et les logos restent exactement ceux des photos.

Usage :
    python3 scripts/teamktc/montage.py KART.jpg EQUIPE.jpg SORTIE.mp4 [--preview DOSSIER]

Les photos ne sont pas dans ce dépôt (public) : elles sont passées en argument.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS, DUREE = 1080, 1920, 30, 15.0
N = int(DUREE * FPS)

POLICE = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
POLICE_FINE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BLEU = (40, 110, 255)
NBSP = "\u00a0"
LARGEUR_TEXTE = 900


# ---------------------------------------------------------------- outils
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def etalonne(img):
    """Contraste léger, bleus un peu plus électriques."""
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.12)
    a = np.asarray(img).astype(np.float32)
    a[..., 2] = np.clip(a[..., 2] * 1.04 + 4, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def cadre(src, cx, cy, zoom, angle=0.0):
    """Vue W×H centrée sur (cx, cy) en coordonnées normalisées ; zoom 1 = l'image couvre l'écran."""
    sw, sh = src.size
    echelle = max(W / sw, H / sh) * zoom
    a = math.radians(angle)
    ca, sa = math.cos(a) / echelle, math.sin(a) / echelle
    px, py = cx * sw, cy * sh
    # sortie (x, y) -> source : centre + R(angle) * (x - W/2, y - H/2) / échelle
    c = px - ca * W / 2 + sa * H / 2
    f = py - sa * W / 2 - ca * H / 2
    return src.transform((W, H), Image.AFFINE, (ca, -sa, c, sa, ca, f),
                         resample=Image.BICUBIC, fillcolor=(8, 14, 40))


def flou_horizontal(img, rayon):
    if rayon < 1:
        return img
    a = np.asarray(img).astype(np.float32)
    k = int(rayon) * 2 + 1
    pad = np.pad(a, ((0, 0), (k, k), (0, 0)), mode="edge")
    cs = np.cumsum(pad, axis=1)
    out = (cs[:, k + k // 2: k + k // 2 + W] - cs[:, k // 2: k // 2 + W]) / k
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def ajoute(base, couche, force=1.0):
    """Mélange « écran » (lumière)."""
    b = np.asarray(base).astype(np.float32) / 255
    c = np.asarray(couche).astype(np.float32) / 255 * force
    return Image.fromarray((255 * (1 - (1 - b) * (1 - c))).astype(np.uint8))


def melange(a, b, t):
    return Image.blend(a, b, min(1.0, max(0.0, t)))


# ------------------------------------------------------------- couches fixes
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
VIGNETTE = np.clip(1.0 - 0.55 * np.clip(_r - 0.35, 0, None) ** 1.4, 0.35, 1.0)[..., None]


def vignette(img):
    a = np.asarray(img).astype(np.float32) * VIGNETTE
    return Image.fromarray(a.astype(np.uint8))


def lueur_bleue(cx, cy, rayon, force):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rayon
    m = np.exp(-d * d)[..., None] * force
    return Image.fromarray((m * np.array(BLEU, np.float32)).astype(np.uint8))


def reflet(t, angle_deg=25, largeur=170, force=0.35):
    """Bande de lumière diagonale qui balaie l'écran (t de 0 à 1)."""
    a = math.radians(angle_deg)
    pos = lerp(-700, W + 700, t)
    d = (xx - W / 2) * math.cos(a) + (yy - H / 2) * math.sin(a) - (pos - W / 2)
    m = np.exp(-(d / largeur) ** 2)[..., None] * force * 255
    return Image.fromarray(np.repeat(m, 3, axis=2).astype(np.uint8))


random.seed(239)
PARTICULES = [dict(x=random.uniform(0, W), y=random.uniform(0, H), v=random.uniform(60, 260),
                   r=random.uniform(2, 6), p=random.uniform(0, 6.28)) for _ in range(90)]


def particules(t, force):
    calque = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(calque)
    for p in PARTICULES:
        y = (p["y"] - p["v"] * t) % H
        x = p["x"] + 18 * math.sin(t * 1.7 + p["p"])
        lum = 0.5 + 0.5 * math.sin(t * 5 + p["p"])
        c = tuple(int(v * force * (0.45 + 0.55 * lum)) for v in (150, 200, 255))
        d.ellipse((x - p["r"], y - p["r"], x + p["r"], y + p["r"]), fill=c)
    return calque.filter(ImageFilter.GaussianBlur(2))


# -------------------------------------------------------------------- textes
_EMOJI_FONT = ImageFont.truetype(EMOJI, 109)


def emoji(car, hauteur):
    im = Image.new("RGBA", (160, 160))
    ImageDraw.Draw(im).text((10, 10), car, font=_EMOJI_FONT, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * hauteur / im.height), hauteur), Image.LANCZOS)


def ligne(texte, taille, police=POLICE, emo=None, couleur=(255, 255, 255), espacement=0.02):
    """Une ligne de texte (avec emoji final facultatif), ombre portée comprise."""
    f = ImageFont.truetype(police, taille)
    esp = int(taille * espacement)
    largeurs = [f.getlength(c) + esp for c in texte]
    lt = int(sum(largeurs))
    em = emoji(emo, int(taille * 0.95)) if emo else None
    lw = lt + (em.width + int(taille * 0.3) if em else 0)
    hh = int(taille * 1.35)
    marge = 40
    txt = Image.new("RGBA", (lw + 2 * marge, hh + 2 * marge))
    d = ImageDraw.Draw(txt)
    x = marge
    for c, l in zip(texte, largeurs):
        d.text((x, marge), c, font=f, fill=couleur + (255,))
        x += l
    ombre = Image.new("RGBA", txt.size, (0, 0, 0, 0))
    ombre.putalpha(txt.getchannel("A").point(lambda v: int(v * 0.85)))
    ombre = ombre.filter(ImageFilter.GaussianBlur(12))
    out = Image.new("RGBA", txt.size)
    out.alpha_composite(ombre, (0, 6))
    out.alpha_composite(txt)
    if em:
        out.alpha_composite(em, (marge + lt + int(taille * 0.3), marge + int(taille * 0.08)))
    if lw > LARGEUR_TEXTE:  # reste dans la zone sûre des réseaux sociaux
        k = LARGEUR_TEXTE / lw
        out = out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)
    return out


def colle_texte(img, calque, cy, t, entree, sortie, decal=60):
    """Apparition (glisse vers le haut + fondu) puis disparition (fondu)."""
    a = ease_out((t - entree) / 0.45) * (1 - ease((t - (sortie - 0.3)) / 0.3))
    if a <= 0:
        return img
    dy = int((1 - ease_out((t - entree) / 0.45)) * decal)
    c = calque.copy()
    c.putalpha(c.getchannel("A").point(lambda v: int(v * a)))
    base = img.convert("RGBA")
    base.alpha_composite(c, ((W - c.width) // 2, int(cy - c.height / 2 + dy)))
    return base.convert("RGB")


def bandeau(img, cy, hauteur, force):
    """Dégradé sombre derrière le texte pour la lisibilité."""
    d = np.abs(yy - cy) / (hauteur / 2)
    m = np.clip(1 - d ** 2, 0, 1)[..., None] * force
    a = np.asarray(img).astype(np.float32) * (1 - m) + np.array((4, 10, 30), np.float32) * m
    return Image.fromarray(a.astype(np.uint8))


# ----------------------------------------------------------------- montage
def main():
    kart_p, equipe_p, sortie = sys.argv[1:4]
    apercu = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None

    kart = etalonne(Image.open(kart_p).convert("RGB"))
    eq = Image.open(equipe_p).convert("RGB")
    eq = etalonne(eq.resize((int(eq.width * 2134 / eq.height), 2134), Image.LANCZOS))

    # fond flou + kart entier, pour le plan final
    fond = cadre(kart, 0.5, 0.5, 1.15).filter(ImageFilter.GaussianBlur(40))
    fond = Image.fromarray((np.asarray(fond).astype(np.float32) * 0.45).astype(np.uint8))
    lk = W - 40
    kart_entier = kart.resize((lk, int(kart.height * lk / kart.width)), Image.LANCZOS)
    kart_entier = kart_entier.filter(ImageFilter.UnsharpMask(2, 60, 2))

    T1 = [ligne("UNE NOUVELLE AVENTURE", 84), ligne("COMMENCE…", 110, emo="🔥")]
    T2 = [ligne("TEAMKTC", 150, espacement=0.08),
          ligne("DEUX FRÈRES, UNE PASSION", 64, police=POLICE_FINE, emo="❤️")]
    T3 = [ligne("L'AVENTURE CONTINUE.", 84),
          ligne(f"OBJECTIF{NBSP}: LA PERFORMANCE.", 70, couleur=(150, 200, 255), emo="🏁")]
    LOGO = ligne("TEAMKTC", 190, espacement=0.1)
    MERCI = [ligne("MERCI À CEUX QUI", 66, police=POLICE_FINE),
             ligne("NOUS FONT AVANCER", 66, police=POLICE_FINE, emo="❤️")]

    def scene1(t):  # 0–4 s : travelling de l'avant vers le côté
        u = ease(t / 4.2)
        img = cadre(kart, lerp(0.62, 0.36, u), lerp(0.66, 0.50, u), lerp(1.30, 1.06, u), lerp(1.5, -1.0, u))
        img = img.filter(ImageFilter.UnsharpMask(2, 50, 2))
        img = ajoute(img, reflet(ease((t - 0.6) / 2.4)), 1.0)
        img = ajoute(img, lueur_bleue(W * 0.85, H * 0.15, 700, 0.35))
        img = vignette(img)
        img = bandeau(img, 1430, 420, 0.55 * ease(t / 0.6))
        for i, c in enumerate(T1):
            img = colle_texte(img, c, 1360 + i * 125, t, 0.5 + i * 0.25, 4.0)
        return img

    def scene2(t):  # 4–8 s : l'équipe, zoom lent
        u = ease(t / 4.0)
        img = cadre(eq, lerp(0.50, 0.505, u), lerp(0.52, 0.50, u), lerp(1.0, 1.28, u))
        img = img.filter(ImageFilter.UnsharpMask(2, 40, 2))
        chaud = Image.new("RGB", (W, H), (255, 170, 90))
        img = Image.blend(img, ajoute(img, chaud, 0.10), 0.6)
        img = vignette(img)
        img = bandeau(img, 360, 520, 0.45 * ease(t / 0.6))
        img = colle_texte(img, T2[0], 300, t, 0.35, 4.0, decal=90)
        img = colle_texte(img, T2[1], 430, t, 0.7, 4.0)
        return img

    def scene3(t):  # 8–12 s : la caméra tourne autour du kart
        u = ease(t / 4.0)
        orbite = math.sin(u * math.pi)
        img = cadre(kart, lerp(0.30, 0.70, u), 0.55 - 0.05 * orbite, 1.12 + 0.22 * orbite, lerp(-5, 5, u))
        img = img.filter(ImageFilter.UnsharpMask(2, 60, 2))
        pouls = 0.5 + 0.5 * math.sin(t * math.pi * 2 * 2.0)  # pulsation 120 bpm
        img = ajoute(img, lueur_bleue(lerp(0, W, u), H * 0.35, 800, 0.22 + 0.18 * pouls))
        img = ajoute(img, lueur_bleue(lerp(W, 0, u), H * 0.85, 700, 0.2))
        img = ajoute(img, particules(t, 0.9))
        img = ajoute(img, reflet(ease((t - 1.6) / 1.6), angle_deg=-30, largeur=120, force=0.3))
        img = vignette(img)
        img = bandeau(img, 1450, 380, 0.55 * ease(t / 0.5))
        img = colle_texte(img, T3[0], 1400, t, 0.3, 4.0)
        img = colle_texte(img, T3[1], 1510, t, 0.65, 4.0)
        return img

    def scene4(t):  # 12–15 s : plan final + TEAMKTC
        z = lerp(1.0, 1.06, ease(t / 3))
        k = kart_entier.resize((int(kart_entier.width * z), int(kart_entier.height * z)), Image.BICUBIC)
        img = fond.copy()
        halo = lueur_bleue(W / 2, H * 0.52, 650, 0.55)
        img = ajoute(img, halo)
        img.paste(k, ((W - k.width) // 2, int(H * 0.52 - k.height / 2)))
        img = ajoute(img, particules(t + 4, 0.6))
        img = ajoute(img, reflet(ease((t - 0.2) / 1.8), largeur=200, force=0.25))
        img = vignette(img)
        # TEAMKTC avec halo bleu
        a = ease_out((t - 0.35) / 0.6)
        if a > 0:
            g = LOGO.copy()
            glow = Image.new("RGBA", g.size, BLEU + (0,))
            glow.putalpha(g.getchannel("A").filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(min(255, v * 2) * a)))
            g.putalpha(g.getchannel("A").point(lambda v: int(v * a)))
            s = lerp(1.25, 1.0, a)
            g = g.resize((int(g.width * s), int(g.height * s)), Image.LANCZOS)
            glow = glow.resize(g.size, Image.LANCZOS)
            base = img.convert("RGBA")
            pos = ((W - g.width) // 2, int(H * 0.2 - g.height / 2))
            base.alpha_composite(glow, pos)
            base.alpha_composite(g, pos)
            img = base.convert("RGB")
        img = colle_texte(img, MERCI[0], H * 0.80, t, 1.0, 99)
        img = colle_texte(img, MERCI[1], H * 0.80 + 95, t, 1.2, 99)
        return img

    def image(i):
        t = i / FPS
        if t < 4:
            img = scene1(t)
        elif t < 8:
            img = scene2(t - 4)
        elif t < 12:
            img = scene3(t - 8)
        else:
            img = scene4(t - 12)
        blanc = Image.new("RGB", (W, H), (255, 255, 255))
        bleu = Image.new("RGB", (W, H), (120, 170, 255))
        # 4 s : filé horizontal + flash blanc
        d = t - 4
        if -0.25 < d < 0.25:
            img = flou_horizontal(img, 70 * (1 - abs(d) / 0.25))
            img = melange(img, blanc, 0.85 * (1 - abs(d) / 0.25))
        # 8 s : flash bleu
        d = t - 8
        if -0.2 < d < 0.3:
            img = flou_horizontal(img, 40 * (1 - abs(d) / 0.3))
            img = melange(img, bleu, 0.75 * (1 - abs(d) / (0.2 if d < 0 else 0.3)))
        # 12 s : transition lumineuse
        d = t - 12
        if -0.35 < d < 0.45:
            img = melange(img, blanc, 0.95 * (1 - abs(d) / (0.35 if d < 0 else 0.45)))
        # ouverture / fin
        if t < 0.3:
            img = melange(Image.new("RGB", (W, H)), img, t / 0.3)
        if t > DUREE - 0.35:
            img = melange(img, Image.new("RGB", (W, H)), (t - (DUREE - 0.35)) / 0.35)
        return img

    if apercu:
        apercu.mkdir(parents=True, exist_ok=True)
        for s in (1.8, 3.5, 4.0, 6.0, 7.5, 9.0, 11.0, 12.1, 13.8):
            image(int(s * FPS)).save(apercu / f"t{s:04.1f}.jpg", quality=85)
        return

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-movflags", "+faststart", sortie,
    ], stdin=subprocess.PIPE)
    for i in range(N):
        ff.stdin.write(image(i).tobytes())
        if i % 30 == 0:
            print(f"{i / FPS:4.1f} s", flush=True)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
