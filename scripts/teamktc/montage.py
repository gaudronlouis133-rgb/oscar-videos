"""Montage TEAMKTC « Nouveau kart Praga » — vidéo verticale 9:16, 15 s, muette.

Animation cinématographique en 2,5D : une carte de profondeur (MiDaS v2.1, licence MIT, calculée
sur place avec onnxruntime) permet de déplacer une vraie caméra virtuelle dans chaque photo
(parallaxe, travelling, orbite, mise au point). Les pixels restent ceux des photos : le kart,
les visages et les logos ne sont jamais redessinés.

Usage :
    python3 scripts/teamktc/montage.py KART.jpg EQUIPE.jpg SORTIE.mp4 [--preview DOSSIER]

Les photos ne sont pas dans ce dépôt (public) : elles sont passées en argument.
"""
import math
import random
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUREE = 1080, 1920, 30, 15.0
N = int(DUREE * FPS)
SOUS_IMAGES = 3  # flou de mouvement (obturateur à 180°)

POLICE = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
POLICE_FINE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
BLEU = np.array((40, 110, 255), np.float32) / 255
NBSP = " "
LARGEUR_TEXTE = 900

MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v2_1/model-f6b98070.onnx"
MIDAS = Path.home() / ".cache" / "teamktc" / "midas_v21_384.onnx"

# Visage à éclaircir (personne de gauche, photo d'équipe), en fraction de l'image :
# centre x, centre y, demi-largeur, demi-hauteur, gain de luminosité.
VISAGE = (0.3817, 0.4430, 0.028, 0.030, 0.34)


# ---------------------------------------------------------------- outils
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def ecran(a, b):
    return 1 - (1 - a) * (1 - b)


# ------------------------------------------------------------- profondeur
def profondeur(img):
    """Profondeur inverse normalisée (1 = proche), même taille que l'image."""
    if not MIDAS.exists():
        MIDAS.parent.mkdir(parents=True, exist_ok=True)
        print("Téléchargement de MiDaS v2.1…", flush=True)
        urllib.request.urlretrieve(MIDAS_URL, MIDAS)
    s = ort.InferenceSession(str(MIDAS), providers=["CPUExecutionProvider"])
    x = cv2.resize(img, (384, 384), interpolation=cv2.INTER_AREA)
    x = (x - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)
    d = s.run(None, {s.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    lo, hi = np.percentile(d, (2, 99.5))
    d = np.clip((d - lo) / (hi - lo), 0, 1)
    d = cv2.resize(d, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(d, (0, 0), max(img.shape[:2]) / 300).astype(np.float32)


# ---------------------------------------------------------------- caméra
class Plan:
    """Une photo + sa profondeur, filmée par une caméra virtuelle."""

    def __init__(self, img, dep):
        self.img, self.dep = img, dep
        self.h, self.w = dep.shape

    def filme(self, cx, cy, zoom, tx=0.0, ty=0.0, dolly=0.0, angle=0.0, focus=0.5, ow=W, oh=H):
        """tx/ty : parallaxe (pixels de sortie par unité de profondeur) ; dolly : les plans proches
        grossissent plus que le fond ; focus : profondeur qui reste immobile (mise au point)."""
        s = max(ow / self.w, oh / self.h) * zoom
        v, u = np.mgrid[0:oh, 0:ow].astype(np.float32)
        u -= ow / 2
        v -= oh / 2
        a = math.radians(angle)
        ur = u * math.cos(a) + v * math.sin(a)
        vr = -u * math.sin(a) + v * math.cos(a)
        px, py = cx * self.w, cy * self.h
        mx, my = px + ur / s, py + vr / s
        for _ in range(3):  # point fixe : la profondeur est lue là où l'on échantillonne
            d = cv2.remap(self.dep, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) - focus
            k = s * (1 + dolly * d)
            mx = px + (ur - tx * d) / k
            my = py + (vr - ty * d) / k
        img = cv2.remap(self.img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        dep = cv2.remap(self.dep, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return np.clip(img, 0, 1), dep


def flou_profondeur(img, dep, focus, force):
    """Profondeur de champ : flou croissant loin du plan de mise au point."""
    if force <= 0:
        return img
    flou = cv2.GaussianBlur(img, (0, 0), 9)
    m = np.clip(np.abs(dep - focus) * 2.2 * force, 0, 1)[..., None]
    return img * (1 - m) + flou * m


# ------------------------------------------------------------- étalonnage
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
VIGNETTE = np.clip(1.0 - 0.6 * np.clip(_r - 0.35, 0, None) ** 1.4, 0.3, 1.0)[..., None]
_x = np.linspace(0, 1, 256, dtype=np.float32)
COURBE_S = np.clip(_x - 0.3 * np.sin(2 * math.pi * _x) / (2 * math.pi), 0, 1)


def etalonne(img):
    """Look cinéma : courbe en S, ombres bleutées, hautes lumières légèrement chaudes."""
    x = COURBE_S[(np.clip(img, 0, 1) * 255).astype(np.uint8)]
    lum = x.mean(axis=2, keepdims=True)
    x = x + (1 - lum) ** 2 * np.array((-0.025, 0.0, 0.045), np.float32) \
          + lum ** 3 * np.array((0.03, 0.01, -0.02), np.float32)
    gris = x.mean(axis=2, keepdims=True)
    x = gris + (x - gris) * 1.12
    return np.clip(x * VIGNETTE, 0, 1)


def grain(img, rng):
    n = rng.standard_normal((H // 2, W // 2), dtype=np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return np.clip(img + n * 0.018, 0, 1)


def eclaircit_visage(img, cx, cy, rx, ry, gain):
    """Relève l'exposition du visage (luminance seule, la teinte ne bouge pas)."""
    h, w = img.shape[:2]
    m = np.zeros((h, w), np.float32)
    cv2.ellipse(m, (int(cx * w), int(cy * h)), (int(rx * w), int(ry * w * 1.3)), 0, 0, 360, 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), rx * w * 0.45)[..., None]
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2Lab)
    L = lab[..., :1]
    L2 = np.clip(L * (1 + gain) + 20 * gain, 0, 100)
    lab = np.concatenate([L * (1 - m) + L2 * m, lab[..., 1:]], axis=2)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_Lab2RGB), 0, 1)


# ---------------------------------------------------------------- lumières
def lueur(cx, cy, rayon, force, couleur=BLEU):
    d = ((xx - cx) ** 2 + (yy - cy) ** 2) / (rayon * rayon)
    return np.exp(-d)[..., None] * force * couleur


def reflet(t, angle_deg=25, largeur=170, force=0.3):
    a = math.radians(angle_deg)
    pos = lerp(-700, W + 700, t)
    d = (xx - W / 2) * math.cos(a) + (yy - H / 2) * math.sin(a) - (pos - W / 2)
    return (np.exp(-(d / largeur) ** 2) * force)[..., None] * np.ones(3, np.float32)


def rayons(img, cx, cy, force):
    """Rayons de soleil : flou radial des hautes lumières depuis la source."""
    hl = np.clip(img.mean(axis=2) - 0.72, 0, 1) * 3
    hl = cv2.resize(hl, (W // 4, H // 4))
    acc = np.zeros_like(hl)
    for i in range(24):
        k = 1 - i * 0.03
        M = np.float32([[k, 0, (1 - k) * cx / 4], [0, k, (1 - k) * cy / 4]])
        acc += cv2.warpAffine(hl, M, (W // 4, H // 4)) * (1 - i / 24)
    acc = cv2.resize(acc / 12, (W, H))[..., None]
    return ecran(img, np.clip(acc * force * np.array((1.0, 0.85, 0.6), np.float32), 0, 1))


def flare(img, x, y, force):
    """Reflet anamorphique horizontal (trait bleu + halo)."""
    if force <= 0.01:
        return img
    trait = np.exp(-((yy - y) / 5) ** 2 - ((xx - x) / 520) ** 2)[..., None] * np.array((0.45, 0.65, 1.0), np.float32)
    halo = lueur(x, y, 90, 1.0, np.array((0.8, 0.9, 1.0), np.float32))
    return ecran(img, np.clip((trait + halo) * force, 0, 1))


random.seed(239)
PARTICULES = [dict(x=random.uniform(0, W), y=random.uniform(0, H), v=random.uniform(60, 260),
                   r=random.uniform(2, 6), p=random.uniform(0, 6.28), z=random.uniform(0.3, 1))
              for _ in range(110)]


def particules(t, force, derive=0.0):
    c = np.zeros((H, W), np.float32)
    for p in PARTICULES:
        y = (p["y"] - p["v"] * t) % H
        x = (p["x"] + 18 * math.sin(t * 1.7 + p["p"]) + derive * p["z"]) % W
        lum = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 5 + p["p"]))
        cv2.circle(c, (int(x), int(y)), int(p["r"] * p["z"] + 1), lum * p["z"], -1, cv2.LINE_AA)
    c = cv2.GaussianBlur(c, (0, 0), 2.2)[..., None]
    return c * force * np.array((0.6, 0.8, 1.0), np.float32)


# -------------------------------------------------------------------- textes
_EMOJI_FONT = ImageFont.truetype(EMOJI, 109)


def emoji(car, hauteur):
    im = Image.new("RGBA", (160, 160))
    ImageDraw.Draw(im).text((10, 10), car, font=_EMOJI_FONT, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * hauteur / im.height), hauteur), Image.LANCZOS)


def ligne(texte, taille, police=POLICE, emo=None, couleur=(255, 255, 255), espacement=0.02, lueur_bleue=False):
    """Une ligne de texte (emoji final facultatif) avec ombre portée, en RGBA float."""
    f = ImageFont.truetype(police, taille)
    esp = int(taille * espacement)
    largeurs = [f.getlength(c) + esp for c in texte]
    lt = int(sum(largeurs))
    em = emoji(emo, int(taille * 0.95)) if emo else None
    lw = lt + (em.width + int(taille * 0.3) if em else 0)
    marge = 50
    txt = Image.new("RGBA", (lw + 2 * marge, int(taille * 1.35) + 2 * marge))
    d = ImageDraw.Draw(txt)
    x = marge
    for c, l in zip(texte, largeurs):
        d.text((x, marge), c, font=f, fill=couleur + (255,))
        x += l
    a = txt.getchannel("A")
    out = Image.new("RGBA", txt.size)
    if lueur_bleue:
        g = Image.new("RGBA", txt.size, (40, 110, 255, 0))
        g.putalpha(a.filter(ImageFilter.GaussianBlur(26)).point(lambda v: min(255, v * 2)))
        out.alpha_composite(g)
    ombre = Image.new("RGBA", txt.size)
    ombre.putalpha(a.point(lambda v: int(v * 0.8)).filter(ImageFilter.GaussianBlur(12)))
    out.alpha_composite(ombre, (0, 6))
    out.alpha_composite(txt)
    if em:
        out.alpha_composite(em, (marge + lt + int(taille * 0.3), marge + int(taille * 0.08)))
    if lw > LARGEUR_TEXTE:  # reste dans la zone sûre des réseaux sociaux
        k = LARGEUR_TEXTE / lw
        out = out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)
    return np.asarray(out).astype(np.float32) / 255


def colle(img, calque, cx, cy, alpha, echelle=1.0, flou=0.0):
    if alpha <= 0.01:
        return img
    c = calque
    if echelle != 1.0:
        c = cv2.resize(c, (int(c.shape[1] * echelle), int(c.shape[0] * echelle)), interpolation=cv2.INTER_AREA)
    if flou > 0.5:
        c = cv2.GaussianBlur(c, (0, 0), flou)
    h, w = c.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xa >= xb or ya >= yb:
        return img
    zone = c[ya - y0:yb - y0, xa - x0:xb - x0]
    a = zone[..., 3:] * alpha
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + zone[..., :3] * a
    return img


def texte_anime(img, calque, cy, t, entree, sortie, decal=60):
    """Entrée : glisse vers le haut et se met au point ; sortie : fondu."""
    e = ease_out((t - entree) / 0.5)
    a = e * (1 - ease((t - (sortie - 0.3)) / 0.3))
    return colle(img, calque, W / 2, cy + (1 - e) * decal, a, flou=(1 - e) * 8)


def bandeau(img, cy, hauteur, force):
    m = (np.clip(1 - (np.abs(yy - cy) / (hauteur / 2)) ** 2, 0, 1) * force)[..., None]
    return img * (1 - m) + np.array((0.015, 0.04, 0.12), np.float32) * m


# ----------------------------------------------------------------- montage
def main():
    kart_p, equipe_p, sortie = sys.argv[1:4]
    apercu = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None

    k = cv2.cvtColor(cv2.imread(kart_p), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    k = cv2.resize(k, (k.shape[1] * 2, k.shape[0] * 2), interpolation=cv2.INTER_LANCZOS4)
    k = np.clip(k + (k - cv2.GaussianBlur(k, (0, 0), 2.0)) * 0.6, 0, 1)
    e = cv2.cvtColor(cv2.imread(equipe_p), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    e = eclaircit_visage(e, *VISAGE)
    e = cv2.resize(e, (1800, 2400), interpolation=cv2.INTER_AREA)
    print("Profondeur…", flush=True)
    KART, EQ = Plan(k, profondeur(k)), Plan(e, profondeur(e))
    f_kart = float(KART.dep[int(0.57 * KART.h), int(0.62 * KART.w)])  # mise au point sur la carrosserie
    f_eq = float(EQ.dep[int(0.47 * EQ.h), int(0.5 * EQ.w)])  # mise au point sur l'équipe

    # fond du plan final : la photo du kart, floue et sombre
    fond, _ = KART.filme(0.5, 0.5, 1.2)
    fond = cv2.GaussianBlur(fond, (0, 0), 30) * 0.4
    kh = int(W * KART.h / KART.w)

    T1 = [ligne("UNE NOUVELLE AVENTURE", 84), ligne("COMMENCE…", 110, emo="🔥")]
    T2 = [ligne("TEAMKTC", 150, espacement=0.08), ligne("DEUX FRÈRES, UNE PASSION", 64, police=POLICE_FINE, emo="❤️")]
    T3 = [ligne("L'AVENTURE CONTINUE.", 84),
          ligne(f"OBJECTIF{NBSP}: LA PERFORMANCE.", 70, couleur=(150, 200, 255), emo="🏁")]
    LOGO = ligne("TEAMKTC", 190, espacement=0.1, lueur_bleue=True)
    MERCI = [ligne("MERCI À CEUX QUI", 66, police=POLICE_FINE), ligne("NOUS FONT AVANCER", 66, police=POLICE_FINE, emo="❤️")]

    def camera(t):
        """Caméra seule (rendue plusieurs fois par image pour le flou de mouvement)."""
        if t < 4:  # travelling bas, de l'avant vers le côté, parallaxe marquée
            u = ease(t / 4.2)
            img, dep = KART.filme(lerp(0.62, 0.38, u), lerp(0.64, 0.52, u), lerp(1.38, 1.10, u),
                                  tx=lerp(110, -110, u), ty=lerp(30, -10, u), dolly=0.18,
                                  angle=lerp(2.0, -1.5, u), focus=f_kart)
            return flou_profondeur(img, dep, f_kart, 0.45)
        if t < 8:  # lent travelling avant vers l'équipe
            u = ease((t - 4) / 4.0)
            img, dep = EQ.filme(0.5, lerp(0.53, 0.50, u), lerp(1.02, 1.30, u),
                                tx=lerp(25, -35, u), ty=lerp(-10, 10, u), dolly=lerp(0.0, 0.35, u), focus=f_eq)
            return flou_profondeur(img, dep, f_eq, 0.5)
        if t < 12:  # orbite énergique autour du kart
            u = ease((t - 8) / 4.0)
            o = math.sin(u * math.pi)
            img, dep = KART.filme(lerp(0.28, 0.72, u), 0.56 - 0.05 * o, 1.14 + 0.24 * o,
                                  tx=lerp(-200, 200, u), ty=-30 * o, dolly=0.25,
                                  angle=lerp(-6, 6, u), focus=f_kart)
            return flou_profondeur(img, dep, f_kart, 0.55)
        u = ease((t - 12) / 3)  # plan final : kart entier, léger travelling avant
        kimg, _ = KART.filme(0.5, 0.5, lerp(1.0, 1.08, u), tx=lerp(-40, 40, u), dolly=0.15,
                             focus=f_kart, ow=W, oh=kh)
        img = ecran(fond, lueur(W / 2, H * 0.52, 650, 0.5))
        y0 = int(H * 0.52 - kh / 2)
        bord = np.clip(np.minimum(np.arange(kh), kh - 1 - np.arange(kh)) / 60, 0, 1)[:, None, None]
        img[y0:y0 + kh] = img[y0:y0 + kh] * (1 - bord) + kimg * bord
        return img

    def image(i, rng):
        t = i / FPS
        img = sum(camera(t + (j / SOUS_IMAGES - 0.5) * 0.5 / FPS) for j in range(SOUS_IMAGES)) / SOUS_IMAGES
        img = img.astype(np.float32)

        if t < 4:
            img = ecran(img, reflet(ease((t - 0.6) / 2.4)))
            img = ecran(img, lueur(W * 0.85, H * 0.12, 700, 0.3))
        elif t < 8:
            img = rayons(img, W * 0.92, H * 0.05, 0.55 + 0.25 * ease((t - 4) / 4))
            img = ecran(img, lueur(W * 0.95, 0, 900, 0.25, np.array((1.0, 0.7, 0.4), np.float32)))
        elif t < 12:
            u = (t - 8) / 4
            pouls = 0.5 + 0.5 * math.sin(t * math.pi * 4)
            img = ecran(img, lueur(lerp(0, W, ease(u)), H * 0.35, 800, 0.2 + 0.15 * pouls))
            img = ecran(img, lueur(lerp(W, 0, ease(u)), H * 0.85, 700, 0.18))
            img = ecran(img, particules(t, 0.9, derive=lerp(200, -200, ease(u))))
            img = flare(img, lerp(W * 0.1, W * 0.9, ease(u)), H * 0.30, 0.55 * math.sin(math.pi * u))
        else:
            img = ecran(img, particules(t + 4, 0.6))
            img = ecran(img, reflet(ease((t - 12.2) / 1.8), largeur=200, force=0.22))
            img = flare(img, W / 2, H * 0.2, 0.5 * ease_out((t - 12.35) / 0.6))
        img = etalonne(img)

        if t < 4:
            img = bandeau(img, 1430, 420, 0.55 * ease(t / 0.6))
            img = texte_anime(img, T1[0], 1360, t, 0.5, 4.0)
            img = texte_anime(img, T1[1], 1485, t, 0.75, 4.0)
        elif t < 8:
            img = bandeau(img, 360, 520, 0.45 * ease((t - 4) / 0.6))
            img = texte_anime(img, T2[0], 300, t - 4, 0.35, 4.0, decal=90)
            img = texte_anime(img, T2[1], 430, t - 4, 0.7, 4.0)
        elif t < 12:
            img = bandeau(img, 1450, 380, 0.55 * ease((t - 8) / 0.5))
            img = texte_anime(img, T3[0], 1400, t - 8, 0.3, 4.0)
            img = texte_anime(img, T3[1], 1510, t - 8, 0.65, 4.0)
        else:
            a = ease_out((t - 12.35) / 0.6)
            img = colle(img, LOGO, W / 2, H * 0.2, a, echelle=lerp(1.25, 1.0, a), flou=(1 - a) * 10)
            img = texte_anime(img, MERCI[0], H * 0.80, t - 12, 1.0, 99)
            img = texte_anime(img, MERCI[1], H * 0.80 + 95, t - 12, 1.2, 99)

        # transitions
        blanc = np.ones(3, np.float32)
        d = t - 4  # filé + flash blanc
        if -0.25 < d < 0.25:
            r = int(70 * (1 - abs(d) / 0.25)) * 2 + 1
            img = lerp(cv2.blur(img, (r, 1)), blanc, 0.85 * (1 - abs(d) / 0.25))
        d = t - 8  # flash bleu
        if -0.2 < d < 0.3:
            r = int(40 * (1 - abs(d) / 0.3)) * 2 + 1
            img = lerp(cv2.blur(img, (r, 1)), np.array((0.47, 0.67, 1.0), np.float32),
                       0.75 * (1 - abs(d) / (0.2 if d < 0 else 0.3)))
        d = t - 12  # transition lumineuse
        if -0.35 < d < 0.45:
            img = lerp(img, blanc, 0.95 * (1 - abs(d) / (0.35 if d < 0 else 0.45)))
        if t < 0.3:
            img = img * (t / 0.3)
        if t > DUREE - 0.35:
            img = img * (1 - (t - (DUREE - 0.35)) / 0.35)
        img = grain(img, rng)
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)

    rng = np.random.default_rng(239)
    if apercu:
        apercu.mkdir(parents=True, exist_ok=True)
        for s in (1.8, 3.5, 5.0, 7.5, 9.0, 10.5, 12.1, 13.8):
            Image.fromarray(image(int(s * FPS), rng)).save(apercu / f"c{s:04.1f}.jpg", quality=85)
        return

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-movflags", "+faststart", sortie,
    ], stdin=subprocess.PIPE)
    for i in range(N):
        ff.stdin.write(image(i, rng).tobytes())
        if i % 30 == 0:
            print(f"{i / FPS:4.1f} s", flush=True)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
