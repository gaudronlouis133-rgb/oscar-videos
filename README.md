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

Finition (sous-titres FR, traductions, son, vidéo finale), sur processeur, sans quota :

```
python scripts/finition.py --voice voice/oscar-emmenagement --out sortie \
  [--langues en,es] [--voix <dossier des répliques .mp3>] [--muet vraie3d-emmenagement-muet.mp4]
```

Les sous-titres français viennent des `*.timing.json` (aucun modèle). Les répliques audio restent
hors du dépôt : `--voix` pointe vers un dossier local.

Le plan de site vidéo pour Google (`video-sitemap.xml`) est fabriqué par le site lui-même, à chaque
mise en ligne, à partir des vidéos réellement publiées.
