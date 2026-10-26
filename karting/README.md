# Karting #202 — photos animées par l'IA

Vidéo verticale (1080×1920, 20 s, TikTok / Reels / Shorts) au format « ces photos étaient
figées… jusqu'à ce que l'IA les réveille » : chaque plan démarre sur la vraie photo, puis la même
image se met en mouvement. Les coupes tombent sur le tempo et la fin reboucle sur le début.

Les photos ne sont pas dans ce dépôt public : elles sont dans le dataset Kaggle privé
`ericbouhfna/karting-202-photos`.

## Outils (tous open source)

| Étape | Outil | Licence |
| --- | --- | --- |
| Image → vidéo | Wan 2.2 I2V-A14B (Alibaba), 81 images à 16 i/s | Apache-2.0 |
| Tenir sur une T4 de 16 Go | quantification GGUF Q4_K_M (QuantStack) | Apache-2.0 |
| 10× plus rapide | LoRA « Lightning » de lightx2v (4 pas, sans CFG) | Apache-2.0 |
| Agrandissement | Real-ESRGAN x4plus, chargé par spandrel | BSD-3 / MIT |
| 16 → 30 i/s | `minterpolate` de FFmpeg (interpolation par mouvement) | LGPL |
| Montage, textes, effets | Python (OpenCV, Pillow), polices Inter et Noto Color Emoji | OFL |
| Musique et bruitages | synthétisés dans `montage.py` (aucun son sous droits) | — |

## Lancement

1. `kaggle_anime.py` : script Kaggle (GPU T4, Internet activé, dataset branché). Il produit
   `out/<plan>.mp4` (480p) et `out/<plan>_hd.mp4` (agrandi), plus `rapport.json`.
2. `python montage.py <dossier_photos> <dossier_clips> karting202.mp4` : écrit
   `karting202.mp4` (avec musique) et `karting202_sans_son.mp4`. Si un clip manque, la photo est
   remplacée par un zoom lent, ce qui permet de tester le montage sans GPU.

Les textes, l'ordre des plans et le minutage sont dans `TIMELINE`, en haut de `montage.py`.
