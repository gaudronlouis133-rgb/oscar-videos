# oscar-videos

Rendus 3D (Blender) des vidéos de démonstration d'OSCAR, calculés sur les machines gratuites
de GitHub Actions.

Ce dépôt ne contient que des scripts de rendu et des éléments libres :

- scripts Blender (`scripts/`) ;
- images d'écran factices affichées sur le téléphone (`scripts/humans/screens/`) ;
- durées des phrases et mouvements de bouche (`voice/*/manifest.json`, `*.timing.json`).

Les éléments 3D sont téléchargés au moment du rendu : Blender (GPL), MPFB / MakeHuman (GPL,
CC0), Poly Haven (CC0).

Il ne contient ni code d'application, ni données, ni secret, ni fichier audio. Le rendu
produit une vidéo **muette** ; le son est ajouté ailleurs.

Lancement : onglet **Actions** → « Rendu 3D » → **Run workflow**.

## Montage TEAMKTC (photos → vidéo 9:16)

`scripts/teamktc/montage.py` anime deux photos (kart + équipe) en une vidéo verticale de 15 s
pour TikTok / Reels. Une carte de profondeur (MiDaS v2.1, MIT, téléchargée au premier lancement)
permet une vraie caméra virtuelle en 2,5D : parallaxe, orbite, mise au point, flou de mouvement,
rayons de soleil, grain et étalonnage cinéma. Les pixels restent ceux des photos (visages, logos).
Dépendances : `numpy pillow opencv-python-headless onnxruntime` et ffmpeg. Les photos ne sont pas
versionnées ici (dépôt public) :

    python3 scripts/teamktc/montage.py kart.jpg equipe.jpg sortie.mp4
