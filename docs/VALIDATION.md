# Validation du prototype 0.1.0

État au 25 octobre 2026. Aucune recette réelle Discord n'est encore effectuée.

## Vérifié localement

- Installation du projet avec uv, environnement Python 3.12.3.
- discord.py 2.7.1 résolu dans uv.lock depuis PyPI.
- **57 tests passent**, dont concurrence des transferts/récompenses et tickets,
  idempotence, rollback monétaire, cooldowns, plafonds, isolement des serveurs,
  profils privés, sauvegarde/restauration de lecture, effacement et rejeu,
  counting, suite de mots, jackpot/gobelin/hack après redémarrage.
- Construction/sérialisation de **48 commandes** dans **27 entrées principales**,
  sans token et sans connexion Discord.
- Boutons persistants reconnus par discord.py ; contrôles d'auteur, allowlist de
  rôles relue au clic, refus des rôles privilégiés et hiérarchie du bot testés.
- Création simulée de ticket avec visibilité refusée à everyone et staff choisi
  explicitement. Retrait simulé d'une pénalité expirée après redémarrage.
- Démonstration CLI dans une vraie base SQLite jetable, avec contrôle d'intégrité
  et sauvegarde cohérente. Pas de faux résultat réseau.
- Lint Ruff et formatage passent ; lockfile cohérent.

Un avertissement de dépréciation `audioop` provient de discord.py sous Python
3.12. Aucun audio n'est capturé ou lu par ce projet.

## Non vérifié ou non exécuté

- Connexion Gateway et intents réellement activés dans le Developer Portal.
- Installation, permissions effectives, hiérarchies et rendu des cartes Discord.
- Flux réels de rôles, tickets, vocaux temporaires, trombinoscope et timeouts.
- XP vocal : adaptateur écrit, recette à deux humains nécessaire.
- Build/exécution Docker : moteur local arrêté, `docker info` a échoué.
- Workflow GitHub Actions : fichier préparé, pas de dépôt distant ni de run CI.
- Python 3.13 : prévu par la matrice CI, pas testé dans cette livraison locale.
- Anciennes règles précises, équilibrage, catalogue et fonctionnalités cachées
  de Sylhbot. Pas d'affirmation de parité complète à ce stade.

## Recette à faire sur un serveur de test

| Scénario | Attendu |
| --- | --- |
| Commande dans un serveur non autorisé | Refus sans mutation locale |
| Deux messages dans le délai XP | Une seule attribution |
| Deux humains en vocal, non muets/non sourds, plus d'une minute | XP compté sans audio ; sortie/rentrée et déconnexion sans rattrapage |
| Double clic participer / jackpot | Une participation, un débit au plus |
| Redémarrage pendant un gobelin | Bouton encore utilisable puis un seul règlement |
| Erreur counting puis redémarrage | Pénalité conservée puis retirée à échéance |
| Choix d'un rôle retiré de l'allowlist depuis l'ouverture du menu | Refus |
| Rôle plus haut que Moka ou porteur de droits staff | Refus d'attribution |
| Ticket d'un membre | Invisible pour un membre ordinaire, accessible au staff choisi |
| Redémarrage juste après création d'un ticket | Pas de seconde création ; rattachement par référence |
| Vocal temporaire | Droits hérités correctement ; salon vide supprimé après la grâce |
| Photo sans pré-accès ou niveau minimum | Aucun accès accordé |
| Photo validée puis supprimée/éditée | Accès retiré si plus aucune photo approuvée |
| Export et effacement | Réponse privée, confirmation, prise en compte des engagements actifs |
| Droits Discord retirés en cours d'événement | Erreur visible/loggée ; pas de second paiement au retour des droits |
| Deux bots dans le serveur | Désactiver les modules qui feraient doublon avec DraftBot |

Les captures GitHub devront être réalisées après cette recette et être
présentées avec des comptes et données de démonstration consentis.
