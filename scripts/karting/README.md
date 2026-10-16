# Reel karting « 121 km/h »

Vidéo verticale (1080x1920, 18,6 s) pour la chaîne Karting Tinkan (Louis & Marius).
C'est d'abord une vidéo karting. Oscar n'apparaît qu'à l'écran du téléphone pendant la
check-list du kart, sans slogan ni texte qui le nomme.

## L'histoire

| Temps | Plan | Texte à l'écran (petit, discret) |
|---|---|---|
| 0–3,8 s | Vidéo : passage en piste, compteur TOP SPEED 0 → 121 km/h, son moteur d'origine | « pas mal pour un samedi » |
| 3,8–6,4 s | Les deux pilotes en combinaison | « Louis & Marius 🏁 » |
| 6,4–10,9 s | Kart #202, 4 petits flashs photo ; un téléphone dans le coin montre l'écran Oscar « État des lieux · Kart #202 » qui se coche | « check avant de rouler » |
| 10,9–12,7 s | Vidéo : pilote jaune sous l'auvent | « à toi » |
| 12,7–14,4 s | Vidéo : casque rouge | « 👀 » |
| 14,4–18,6 s | Coucher de soleil, casque rouge, fondu au noir | « prochain roulage bientôt » |

Les textes incrustés des vidéos d'origine (« 114 KM/H », « JOURNEE KARTING »…) sont sortis
du cadre par un léger zoom.

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

`media/` contient `freres.png`, `kart.webp`, `sunset.jpg`. Deux fichiers sortent : avec
musique synthétisée, et **sans musique** (bruitages + moteur seulement), à utiliser pour
poser un son tendance directement dans TikTok / Instagram.

Les photos et vidéos des enfants ne sont pas versionnées dans ce dépôt.
