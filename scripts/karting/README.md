# Reel KTC « POV : t'es le team manager de KTC »

Vidéo verticale (1080x1920, 20 s) pour la chaîne KTC (Karting Teamcamp, Louis & Marius).
C'est d'abord une vidéo karting. Oscar n'apparaît qu'en notification sur le téléphone du
team manager, tenu devant la piste ; aucun texte ne le nomme.

## L'histoire

| Temps | Plan | Texte (petit, discret) |
|---|---|---|
| 0–3,8 s | Passage en piste, compteur TOP SPEED 0 → 121 km/h, son moteur | « POV : t'es le team manager de KTC » |
| 3,8–5,5 s | Les deux pilotes | « les pilotes ✓ » |
| 5,5–6,9 s | Gros plan pneu, kart #202 | « les pneus ✓ » |
| 6,9–8,3 s | Moteur et radiateur, kart #239 | « le moteur ✓ » |
| 8,3–10,1 s | Vidéo : pilote jaune sous l'auvent | « le chrono ✓ » |
| 10,1–14,8 s | Vue subjective : main + téléphone devant la piste floue, moteur au loin. Notifications OSCAR « Loyer reçu ✓ 850 € » puis « Quittance envoyée » | « et le reste ✓ » |
| 14,8–16,4 s | Vidéo : casque rouge | « 👀 » |
| 16,4–20 s | Coucher de soleil, fondu au noir | « KTC 🏁 » |

La main qui tient le téléphone est détourée automatiquement (`key_hand`) ; les notifications
sont projetées sur l'écran en perspective (`homography`). Les textes incrustés des vidéos
d'origine sont sortis du cadre par un léger zoom.

## Rendu

```bash
# 1. extraire les plans vidéo retenus
ffmpeg -ss 0   -t 1.7 -i karting_reel_v2.mp4  -q:v 2 work/red/%04d.jpg
ffmpeg -ss 9.9 -t 1.8 -i karting_reel_v2.mp4  -q:v 2 work/yellow/%04d.jpg
ffmpeg -ss 5.4 -t 3.8 -i karting_topspeed.mp4 -q:v 2 work/speed/%04d.jpg
ffmpeg -ss 5.4 -t 3.8 -i karting_topspeed.mp4 -vn work/speed.wav
# 2. monter
python3 reel.py --media media/ --work work/ --out out/
```

`media/` contient `freres.png`, `kart.webp`, `kart239.jpg`, `sunset.jpg`, `main.jpg`. Deux fichiers sortent : avec
musique synthétisée, et **sans musique** (bruitages + moteur seulement), à utiliser pour
poser un son tendance directement dans TikTok / Instagram.

Les photos et vidéos des enfants ne sont pas versionnées dans ce dépôt.

## Plans animés par l'IA (LTX-Video, open source)

1. `python3 kaggle_ltx.py --media media/ --out ktc_video_ia.ipynb` (les photos sont
   embarquées dans le carnet).
2. Sur Kaggle : **Create → New Notebook → File → Import Notebook**, choisir le fichier.
   Dans le panneau de droite : **Accelerator = GPU T4 x2**, **Internet = On**. **Run All**.
   Compter 5 à 10 min par plan sur GPU.
3. Télécharger `freres.mp4`, `kart.mp4`, `kart239.mp4`, `sunset.mp4` (onglet Output) et les
   poser dans `work/ia/`. `reel.py` les utilise à la place des photos fixes.
