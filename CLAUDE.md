# Règles pour Claude — dépôt public des vidéos

- **Dépôt public** : seulement ce qui ne présente aucun risque de sécurité (scripts de rendu et
  de finition des vidéos, éléments libres). Jamais de code de l'application, de données, de
  secret, d'adresse de serveur ou de nom de service interne.
- **0 €** : rien de payant. Les Actions de ce dépôt public sont gratuites ; les workflows
  restent en lancement manuel (`workflow_dispatch`) avec un `timeout-minutes` sur chaque job.
  Kaggle : processeur de préférence, GPU seulement si nécessaire et annoncé avant.
- **Pas de régression, que du mieux** (26/10/2026) : chaque changement ne fait qu'améliorer
  l'existant ; rien de ce qui marche ne doit cesser de marcher. Chercher d'abord si la
  fonction existe déjà (ici ou dans la chaîne vidéo existante) pour la réutiliser plutôt que
  la refaire ; vérifier avant et après ; ne rien supprimer ni remplacer de ce qui sert sans
  l'accord de Louis ; en cas de doute, demander avant ; une régression se corrige en priorité.
