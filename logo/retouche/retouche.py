"""Retouche « fraîcheur » de l'assiette du logo La Table des Saisons.
Usage : python3 retouche.py original.png sortie.png
Éclaircit et rafraîchit les verts, passe la feuille de chêne en or clair,
les baies sombres en groseilles et allège la pomme de pin.
"""
import sys
import numpy as np
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
rgb = Image.open(src).convert('RGB')
hsv = np.asarray(rgb.convert('HSV')).astype(float) / 255.0
H, S, V = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
h, w = V.shape
yy, xx = np.mgrid[0:h, 0:w]

def box(x0, y0, x1, y1):
    return (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)

def disc(cx, cy, r):
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r

quads = box(475, 200, 612, 330) | box(635, 185, 756, 335) | box(483, 352, 612, 466) | box(638, 350, 752, 470)
autumn = box(483, 352, 612, 466)
berries = disc(562, 445, 11) | disc(592, 426, 10)
cone = disc(680, 436, 24) & box(638, 350, 752, 470)

H2, S2, V2 = H.copy(), S.copy(), V.copy()

# 1. Verts plus lumineux et plus tendres (masque progressif, sans effet de contour)
hue_w = np.clip(1 - np.abs(H - 105) / 55, 0, 1)
sat_w = np.clip((S - 0.04) / 0.16, 0, 1)
gw = np.where(quads & ~berries, hue_w * sat_w, 0)
V2 = V2 + (1 - V2) * 0.36 * gw
H2 = H2 + 4 * gw
S2 = np.clip(S2 * (1 + 0.12 * gw), 0, 1)
# contours sombres adoucis pour suivre l'éclaircissement
dw = np.where(quads & ~berries & ~cone, np.clip((0.55 - V) / 0.35, 0, 1), 0)
V2 = V2 + (1 - V2) * 0.28 * dw

# 2. Feuille de chêne : du brun orangé vers un or clair et frais
oak = autumn & (H >= 15) & (H <= 65) & (S > 0.25) & ~berries
H2[oak] = 44 + (H[oak] - 38) * 0.4
S2[oak] = S[oak] * 0.75
V2[oak] = V[oak] + (1 - V[oak]) * 0.45

# 3. Baies sombres → groseilles rouge corail
dark = berries & (V < 0.6) & (S > 0.08)
H2[dark] = 352
S2[dark] = 0.62
V2[dark] = np.clip(0.55 + V[dark] * 0.75, 0, 0.97)

# 4. Pomme de pin plus claire, tons miel
pc = cone & (H >= 10) & (H <= 55) & (S > 0.2)
V2[pc] = V[pc] + (1 - V[pc]) * 0.4
S2[pc] = S[pc] * 0.8
H2[pc] = H[pc] + 6

# 5. Tiges brunes un peu adoucies
stem = quads & (H >= 10) & (H < 40) & (V < 0.45) & ~berries & ~pc
V2[stem] = V[stem] + (1 - V[stem]) * 0.25

out = np.stack([(H2 % 360) / 360, np.clip(S2, 0, 1), np.clip(V2, 0, 1)], -1)
img = Image.fromarray((out * 255).round().astype('uint8'), 'HSV').convert('RGB')
img.save(dst)
