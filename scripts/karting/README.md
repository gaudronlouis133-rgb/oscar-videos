# Reel karting « L'état des lieux du kart »

Vidéo verticale (1080x1920, 28 s) pour la chaîne Karting Tinkan (Louis & Marius).
Oscar n'est jamais présenté comme une pub : c'est l'outil qui fait la chute de la blague.

## L'histoire

| Temps | Plan | Texte à l'écran |
|---|---|---|
| 0–3 s | Les deux frères en combinaison (zoom lent) | « J'ai prêté mon kart à mon frère… » → « …mais avant, j'ai fait un **ÉTAT DES LIEUX** 😏 » |
| 3–9,4 s | Kart #202 : 4 « photos » (flash + cadre orange) et la carte Oscar se coche | Volant, Plaque 202, Pneus neufs, Carénage |
| 9,4–12,2 s | Téléphone, écran Oscar, signature qui se trace puis « Signé ✓ » | « Signature obligatoire. On ne rigole pas. » |
| 12,2–14 s | Vidéo : pilote jaune sous l'auvent | « Le locataire est prêt 🏁 » |
| 14–17,8 s | Vidéo : passage, compteur TOP SPEED 0 → 121 KM/H posé sur le bandeau d'origine, son moteur d'origine | « …et il me le ramène à 121 km/h 💀 » |
| 17,8–19,5 s | Vidéo : casque rouge (réaction) | « Moi au retour du kart 👀 » |
| 19,5–23,6 s | Comparatif Oscar entrée / sortie : pneus ✗, tampon rouge | « PNEUS LISSES — RETENU SUR LA CAUTION » |
| 23,6–28 s | Coucher de soleil, casque rouge | « Moralité : toujours faire un état des lieux. Même pour un kart 😉 » + petite mention « État des lieux fait avec Oscar · monassistantoscar.com » |

Pourquoi ça marche : l'accroche tient en une phrase, la rivalité entre frères fait réagir en
commentaire (« et la caution c'était quoi ? »), et la seule mention du produit arrive quand
la blague est déjà comprise.

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
