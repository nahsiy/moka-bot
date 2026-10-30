# Moka 0.3.0 — Le Comptoir prend vie

Moka devient un compagnon de café plus complet : accueillir les nouveaux membres,
personnaliser son profil, partager une animation et choisir la musique ensemble.
La monnaie reste fictive et l’humour bienveillant.

## Un premier café pour les nouveaux membres

- Accueil réservé aux 21 ans et plus : salon privé avec le staff, charte séparée
  et mot de lecture, entretien écrit par défaut ou vocal sur demande.
- Validation humaine avant les accès communautaires ; aucun document d’identité demandé.
- Rôles au choix dans huit rubriques, listes directes et confirmations privées.
- Paliers XP du Comptoir, absences annoncées et suivi des pauses sans exclusion automatique.

## Un profil où tout se retrouve

- Carte privée lisible, dépôt/retrait et agrandissement de banque directement accessibles.
- Récompenses quotidiennes et hebdomadaires, historique des cœurs, boutique et inventaire.
- Huit badges à obtenir à son rythme et quatre titres décoratifs pour son profil.
- Prix visibles avant achat ; aucune permission Discord vendue ; cadeaux annoncés publiquement.

## Des pauses à partager

- Tournée de Moka et câlin collectif, avec illustrations originales et inscriptions.
- Bonus surprise au counting ; corvée de vaisselle après modification d’un nombre validé.
- Compliments et taquineries illustrés en trois éditions, avec anti-répétition.
- Le Juke-box : lecteur partagé, ajout d’un titre ou d’un lien YouTube, file et votes.
  Commandes dans le salon textuel dédié, écoute dans le vocal sans micros ni XP passif.

## Un tableau pour le Barista

`/barista` rassemble les fonctions actives et les réglages par serveur dans un
panneau privé. Formulaires préremplis, unités lisibles, enregistrement atomique
et permissions vérifiées au clic. Les événements engagés gardent leurs règles ;
les nouveaux jackpots conservent leur tarif annoncé à l’ouverture.

Le nettoyage regroupe les logiques communes et corrige l’expiration des écrans
privés. Les anciens identifiants de boutons, réglages et événements sont conservés.

## Installer ou mettre à jour

1. Sauvegarder la base et arrêter l’ancienne instance.
2. Mettre à jour les sources puis exécuter `uv sync --locked`. Pour la musique
   en installation Python, prévoir FFmpeg et Deno ; le Dockerfile les embarque.
3. Conserver la configuration et le dossier de données : les tables sont
   ajoutées sans effacer les comptes. Les réglages existants gardent leur priorité.
4. Resynchroniser une fois les commandes dans les seuls serveurs autorisés avec
   `MOKA_SYNC_COMMANDS=1`, puis revenir à `0` pour les démarrages ordinaires.
5. L’accueil et les espaces musicaux demandent une installation explicite :
   [accueil](ACCUEIL.md), `/config jukebox` pour la musique.

Les sanctions en cours gardent leur échéance. Les anciens jackpots sans tarif
mémorisé gardent leur comportement historique. La file musicale repart vide
après un redémarrage ; aucun audio n’est enregistré.

## Validation et limites

- 430 tests sous Python 3.12 et 430 sous Python 3.13, Ruff, formatage, commandes
  sérialisées, démo hors ligne, wheel et archive source vérifiés localement.
- Paquet installé hors dépôt, polices et illustrations présentes, trois cartes rendues.
- Image Docker Linux ARM64 construite et exécutée sans privilèges, racine en
  lecture seule ; commandes, démo, cartes et décodage YouTube vérifiés.
- Plusieurs parcours réellement essayés dans Discord, dont une lecture vocale,
  pause/reprise et file musicale. Les essais avec plusieurs humains simultanés
  et la recette complète restent décrits séparément dans [VALIDATION.md](VALIDATION.md).

Les fichiers de configuration privés, bases, sauvegardes et captures de membres
restent hors de la distribution. Aucun hébergement permanent n’est fourni.

[Guide d’installation](INSTALLATION.md) · [Changelog](../CHANGELOG.md) ·
[Revue du nettoyage](NETTOYAGE.md) · [Matrice des fonctions](FONCTIONS.md)
