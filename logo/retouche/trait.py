"""Version « au trait » de l'assiette du logo La Table des Saisons (filtre XDoG).
Usage : python3 trait.py original.png sortie_prefixe
Les illustrations sont converties en dessin à l'encre fine puis recolorées
en doré ou en vert ; le reste de l'image est conservé tel quel.
"""
import sys
import cv2
import numpy as np

src, prefix = sys.argv[1], sys.argv[2]
img = cv2.imread(src)
SC = 2
RING_C, RING_R = (623.3, 334.8), 169.7
# zones des illustrations, à l'écart des filets dorés de séparation
QUADS = [(470, 192, 615, 331), (632, 180, 760, 333), (478, 350, 615, 474), (633, 348, 760, 478)]

big = cv2.resize(img, None, fx=SC, fy=SC, interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
H, W = big.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
zone = np.zeros((H, W), bool)
for (x0, y0, x1, y1) in QUADS:
    zone[y0 * SC:y1 * SC, x0 * SC:x1 * SC] = True
zone &= (xx / SC - RING_C[0]) ** 2 + (yy / SC - RING_C[1]) ** 2 < (RING_R - 6) ** 2

def xdog(gray, sigma=1.1, k=1.6, tau=0.985, eps=0.0, phi=60.0):
    g1 = cv2.GaussianBlur(gray, (0, 0), sigma)
    g2 = cv2.GaussianBlur(gray, (0, 0), sigma * k)
    d = g1 - tau * g2
    return np.where(d >= eps, 1.0, 1.0 + np.tanh(phi * (d - eps)))   # 1 = papier, <1 = encre

gray = cv2.cvtColor(big.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
# pétales blancs sur fond crème : contraste local renforcé sur le quadrant du printemps
x0, y0, x1, y1 = [v * SC for v in QUADS[0]]
spring = (gray[y0:y1, x0:x1] * 255).astype(np.uint8)
spring = cv2.createCLAHE(clipLimit=6.0, tileGridSize=(4, 4)).apply(spring).astype(np.float32) / 255
gray[y0:y1, x0:x1] = cv2.GaussianBlur(spring, (0, 0), 0.8)
gray = cv2.bilateralFilter(gray, 7, 0.08, 5)
ink = 1 - np.clip(xdog(gray), 0, 1)                 # 0..1, 1 = trait
ink = np.clip((ink - 0.12) / 0.6, 0, 1)             # on supprime le grain et les ombres très douces
ink = cv2.GaussianBlur(ink, (0, 0), 0.6)
ink[~zone] = 0

# fond : on remplace les illustrations par le papier de l'assiette (inpainting)
illus = np.zeros(img.shape[:2], np.uint8)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
bg_local = cv2.cvtColor(cv2.medianBlur(cv2.medianBlur(img, 61), 61), cv2.COLOR_BGR2LAB).astype(np.float32)
diff = np.linalg.norm(lab - bg_local, axis=2) > 4
small_zone = cv2.resize(zone.astype(np.uint8), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
illus[diff & small_zone] = 255
illus = cv2.dilate(illus, np.ones((5, 5), np.uint8))
paper = cv2.inpaint(img, illus, 7, cv2.INPAINT_TELEA)
paper_big = cv2.resize(paper, None, fx=SC, fy=SC, interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
base = np.where(zone[..., None], paper_big, big)

def colour(col):
    a = ink[..., None]
    return np.clip(base * (1 - a) + np.array(col, np.float32) * a, 0, 255).astype(np.uint8)

cv2.imwrite(f'{prefix}-dore.png', colour((48, 132, 182)))     # BGR
cv2.imwrite(f'{prefix}-vert.png', colour((38, 68, 28)))
