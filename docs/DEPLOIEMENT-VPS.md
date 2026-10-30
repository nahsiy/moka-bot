# Préparer un hébergement permanent

Ce guide décrit une bascule à décider et exécuter explicitement. Le dépôt ne
contient ni adresse de serveur, ni compte SSH, ni token, ni identifiant de communauté.
L'installation Docker ne publie aucun port entrant et ne demande pas de proxy web.

## Préparer sans connecter une seconde instance

1. Réserver un dossier d'exploitation, par exemple `/opt/moka`, et un nom de
   projet Compose dédié. Vérifier l'espace disque et la mémoire disponibles.
2. Déployer les sources du tag choisi et construire l'image. Valider les commandes,
   la démo, les polices et les images sans fournir de token ni démarrer `moka run`.
3. Préparer un TOML de production et un fichier d'environnement privé (`0600`).
   Reprendre les réglages actuels plutôt que réinitialiser la base. Examiner les
   valeurs accélérées du laboratoire avant de les conserver en usage durable.
4. Préparer le volume persistant `/data`, accessible à l'utilisateur **10001**.
   Vérifier aussi les permissions de traversée des dossiers lors d'un montage hôte.
5. Prévoir la copie chiffrée hors de l'hôte et la rétention des sauvegardes.
   Une copie dans le même volume Docker ne protège pas de la perte du VPS.

Le Compose fourni limite le conteneur à deux CPU, 1 Gio de mémoire et 256 processus,
avec un processus d'initialisation pour les enfants, racine en lecture seule,
capacités retirées et temporaire de 64 Mio. Ces valeurs sont un point de départ
à surveiller selon le nombre de serveurs et les rendus simultanés.

Le TOML monté par Compose reste `config.example.toml` dans le dépôt. Le remplacer
par une copie d'exploitation adaptée ou modifier le montage dans un fichier
d'override privé ; ne pas publier une configuration réelle dans Git. Les variables
Compose imposent `MOKA_DATA_DIR=/data` et `MOKA_CONFIG=/app/config.toml` dans le conteneur.

## Bascule

1. Vérifier qu'aucun nettoyage de messages ou entretien vocal n'est en cours.
   Prévenir que la musique s'arrête et que la file sera perdue au redémarrage.
2. **Arrêter la supervision de l'ancienne instance**, pas seulement son processus
   enfant. Confirmer qu'elle ne se relance plus.
3. Faire une dernière sauvegarde SQLite cohérente avec `moka backup`. Copier cette
   sauvegarde, le TOML et le fichier d'environnement par un canal chiffré ciblé.
   Ne jamais copier seulement un fichier SQLite pendant que des écritures continuent.
4. Restaurer cette sauvegarde dans le volume préparé et vérifier son intégrité.
   Le verrou de fichier protège un dossier local ; **il ne coordonne pas deux machines**.
5. Démarrer uniquement l'instance du VPS. Synchroniser une fois les commandes si
   nécessaire, puis conserver `MOKA_SYNC_COMMANDS=0`.
6. Relire l'état du conteneur et la connexion Gateway dans les journaux. Vérifier
   un profil, les soldes, les pauses de jeux, les décisions d'accueil, les échéances
   et les panneaux persistants. Tester les commandes dans les salons prévus.
7. Essayer le Juke-box depuis le VPS : son accès à YouTube peut différer de celui
   d'un poste personnel. Une vérification locale ne suffit pas à le garantir.

Le bot utilise des connexions sortantes HTTPS, le Gateway et, pour la musique,
les échanges vocaux de Discord. Une politique réseau restrictive doit les autoriser
sans exposer de service entrant supplémentaire.

## Retour arrière

Arrêter d'abord l'instance du VPS. Si elle a accepté des actions, reprendre une
nouvelle sauvegarde cohérente de sa base avant de déplacer le service à nouveau :
revenir aveuglément à la copie d'avant bascule perdrait les dernières opérations.
Vérifier la compatibilité du code et du schéma avant restauration. Ne pas supprimer
le volume ou utiliser `docker compose down -v` comme méthode de retour arrière.

## Suivi

- Rotation des journaux Docker déjà bornée dans Compose ; ne pas diffuser les logs bruts.
- Sauvegarde SQLite locale quotidienne contrôlée chaque heure ; organiser sa copie
  hors de l'hôte, sa durée de conservation et une recette de restauration.
- Surveiller redémarrages, place disque, mémoire, disponibilité des sources externes
  et connexion Gateway. Un processus actif ne prouve pas que le bot est connecté.
- Conserver une image précédente et la sauvegarde vérifiée avant chaque mise à jour.

[Exploitation](EXPLOITATION.md) · [Installation](INSTALLATION.md) ·
[Version 0.4.0](RELEASE-0.4.0.md)
