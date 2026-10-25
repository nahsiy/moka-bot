# Validation du prototype 0.1.0

État au 25 octobre 2026. Première recette réelle effectuée sur un serveur
de test dédié, avec un seul compte humain. La recette complète reste à terminer.

## Vérifié localement

- Installation du projet avec uv, environnement Python 3.12.3.
- discord.py 2.7.1 résolu dans uv.lock depuis PyPI.
- **61 tests passent**, dont concurrence des transferts/récompenses et tickets,
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

## Vérifié dans Discord — laboratoire uniquement

- Installation de Moka Test dans le seul serveur explicitement autorisé,
  sans Administrateur ; salons et rôles préparés par l'API officielle du bot.
- Intents membres et contenu activés, connexion Gateway réussie, 27 entrées
  principales de commandes enregistrées dans ce serveur uniquement.
- `/aide`, `/argent journalier` (+200 cœurs), `/profile` : réponses privées
  rendues dans le client Discord.
- `/roles publier`, bouton et sélection Lecteur : attribution confirmée par
  relecture de l'API Discord.
- `/ticket ouvrir` : un salon créé ; overwrite de visibilité everyone refusé
  vérifié par API. Visibilité depuis un second compte ordinaire encore à tester.
- Gobelin lancé par commande, participation par bouton, redémarrage pendant
  l'événement, puis nouveau clic : participation déjà enregistrée reconnue.
  Événement terminé et annoncé ; un seul crédit de 100 cœurs dans le journal.
- Counting : `1` validé, `3` refusé avec remise à zéro ; rôle de pénalité observé
  puis retiré à échéance (30 secondes dans config.test.toml).
- Suite de mots : `café` validé en mode libre. XP écrit persisté après message.
- Intégrité SQLite vérifiée ; aucune erreur dans les logs après correction.

Le premier démarrage a révélé l'utilisation de `Guild.afk_channel_id`, absent
de discord.py. Le suivi vocal utilise désormais la propriété publique
`Guild.afk_channel`. Un test de régression avec un vrai objet Guild reproduit
l'exception avant correction et passe après celle-ci.

Le bot tourne localement sur le Mac avec `.env` et `config.test.toml` ; ce n'est
pas encore un hébergement permanent. Les données et logs ne sont pas versionnés.
Deux captures du laboratoire personnel sont sélectionnées dans la
[présentation publique](../README.md#voir-moka-dans-discord). Aucun déploiement
dans le QG n'a été effectué.

## Non vérifié ou non exécuté

- Ensemble des cartes et permissions de tous les modules ; la première recette
  ci-dessus couvre uniquement les parcours explicitement décrits.
- Tickets avec un second compte ordinaire, vocaux temporaires, trombinoscope,
  timeouts, banque, transferts et autres jeux en conditions réelles.
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

Les captures publiques montrent les essais explicitement vérifiés ci-dessus,
avec le compte du testeur et le bot. Elles ne montrent aucun échange de membres
du serveur cible et ne prouvent pas l'exécution de toute la recette restante.
