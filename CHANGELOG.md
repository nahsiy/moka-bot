# Historique des versions

## 0.2.0 — 27 octobre 2026

### Nouveautés

- Counting : calculs arithmétiques bornés, amende configurable sur le portefeuille,
  pile ou face après une erreur ; record et récompenses de paliers conservés.
- Pause d'une heure commune au counting et à la suite de mots, rôle Pas-doué
  affiché séparément, restrictions d'écriture et reprise après redémarrage.
- `/debloquer membre` pour lever la pause et retirer le rôle, avec permissions
  staff vérifiées et nouvelle tentative automatique si Discord refuse le retrait.
- `/taux` et `/duo` : huit taux individuels, six duos symétriques, résultats
  stables jusqu'à minuit à Paris, quatorze illustrations originales et avatars.
- Polices embarquées pour les caractères grecs, cyrilliques et emojis en couleur.
- Cinquante compliments et cinquante taquineries bienveillantes ; exclusion des
  cinq dernières phrases de chaque catégorie et délai commun de quinze secondes.
- Icônes de Moka et du laboratoire, documentation et exemples visuels fictifs.

### Mise à jour depuis 0.1.0

1. Sauvegarder la base avec `moka backup`, puis arrêter le bot.
2. Mettre à jour les sources et lancer `uv sync --locked`.
3. Adapter le TOML si nécessaire : le défaut `counting_failure_seconds` passe
   de 10 800 à 3 600 secondes ; une
   valeur déjà explicite dans votre TOML reste prioritaire. Les pauses actives
   gardent leur échéance. L'amende par défaut est de 1 000 cœurs ; la banque
   n'est jamais prélevée.
4. Pour enregistrer les nouvelles commandes, démarrer une fois avec
   `MOKA_SYNC_COMMANDS=1`, puis revenir à `0`. La synchronisation reste limitée
   aux serveurs explicitement autorisés.
5. Dans Discord, configurer les deux salons de jeu si nécessaire, puis le rôle
   avec `/config role usage:counting_failure` : cette action applique les
   restrictions aux deux salons. Le rôle doit être dédié, sans permissions
   globales et sous celui du bot. `/config comptage amende:0` désactive l'amende.

Les tables SQLite existantes sont réutilisées. Les données restent locales.
Les cartes se rendent avec Pillow, sans appel IA à l'exécution. Les exemples
visuels de cette version utilisent uniquement des noms fictifs et la mascotte.

### Validation

188 tests locaux, lint et formatage, configuration, démo hors ligne et paquet
Python vérifiés. Plusieurs parcours sont aussi essayés dans Discord ; voir
[le périmètre exact](docs/VALIDATION.md). La recette complète, l'XP vocal à deux
personnes et l'exécution Docker restent à valider. Aucun hébergement permanent
n'est fourni.

## 0.1.0 — 25 octobre 2026

Premier prototype public : progression, économie fictive, banque, boutique,
jeux, rôles, tickets, vocaux temporaires et outils communautaires. Première
recette dans un serveur Discord dédié et 61 tests locaux.
