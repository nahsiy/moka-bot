# Historique des versions

## 0.3.0 — 30 octobre 2026

Le Comptoir prend vie : accueil, personnalisation, outils du staff et musique partagée.

### Fonctions

- Accueil privé sur entretien à partir de 21 ans, charte séparée et validation humaine.
- Rôles au choix par rubriques, paliers XP du Comptoir, suivi des pauses et absences annoncées.
- Profil privé illustré, opérations bancaires directes, récompenses, historique,
  boutique, inventaire, huit badges et quatre titres décoratifs.
- Tableau privé du Barista : modules et règles métier persistées par serveur.
- Tournée de Moka et câlin collectif avec cartes originales et boutons persistants.
- Counting : bonus surprise et corvée de vaisselle après modification d’un nombre validé.
- Compliments et taquineries illustrés en trois éditions ; catalogue bienveillant.
- Juke-box partagé : lecteur, file, votes et vocal d’écoute sans micro ni XP passif.

### Nettoyage avant release

- Chargement des commandes partagé entre le bot et sa vérification hors ligne.
- Écritures de configuration centralisées et lecture des règles dans la transaction métier.
- Tarif du jackpot conservé pour toute la durée des nouvelles animations.
- Gestion commune de la propriété et de l’expiration des écrans privés du profil.
- Guides alignés sur le panneau Barista, les cartes sociales et les prérequis musicaux.
- FFmpeg et Deno embarqués dans Docker ; contrôle du conteneur ajouté à la CI.

### Mise à jour depuis 0.2.0

1. Sauvegarder la base et arrêter l’instance avant de remplacer les sources.
2. Synchroniser les dépendances verrouillées avec `uv sync --locked` ; installer
   FFmpeg et Deno pour le Juke-box en installation Python, ou reconstruire l’image.
3. Conserver la configuration et les données locales. Les tables sont ajoutées
   sans effacer les comptes ; les anciens réglages d’amende/corvée restent lus.
4. Resynchroniser une fois les commandes sur les seuls serveurs autorisés, puis
   remettre `MOKA_SYNC_COMMANDS=0`. Installer accueil et Juke-box explicitement.
5. Les sanctions et événements en cours gardent leur état. Les anciens jackpots
   sans tarif enregistré gardent le comportement historique ; les nouveaux figent leur prix.
   La file musicale repart vide après un redémarrage.

La validation actuelle et ses limites figurent dans [VALIDATION.md](docs/VALIDATION.md).

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
