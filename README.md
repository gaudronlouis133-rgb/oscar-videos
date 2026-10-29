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

Plan de site vidéo pour Google et les autres moteurs (`video-sitemap.xml`), sans modèle ni dépendance :

```
python scripts/plan_de_site.py --site https://<adresse du site> --out sortie \
  [--voice voice/oscar-emmenagement] [--videos <dossier des vidéos finales .mp4>]
```

L'adresse du site est donnée au lancement, jamais écrite dans le dépôt. Titre et description :
`voice/<vidéo>/fiche.json`. Avec `--videos`, la durée est mesurée et l'image d'aperçu `<nom>.jpg`
est produite. Adresses par défaut : `{site}/videos/{nom}`, `.mp4` et `.jpg` (options `--page`,
`--fichier`, `--miniature`).

Sans PC : onglet **Actions** → « Plan de site vidéo » → **Run workflow**, saisir l'adresse du site
(masquée dans le journal) ; le fichier est dans les « Artifacts » de l'exécution.
