# Validation de Moka 0.2.0

État au 27 octobre 2026 ; les sections historiques précisent la version essayée.
Première recette réelle effectuée sur un serveur de test dédié, avec un seul
compte humain. La recette complète reste à terminer.

## Évolution counting — 27 octobre 2026

- **114 tests locaux passent** après intégration des calculs, amendes et pile
  ou face ; Ruff, formatage, installation verrouillée, contrôle des commandes
  et démo hors ligne réussis.
- Évaluation exacte et bornée : calculs usuels et fractions, refus des appels,
  attributs, divisions par zéro et puissances hors limites.
- Les deux résultats de la pièce sont forcés dans les tests. Vérifications
  du portefeuille non négatif, banque intacte, économie désactivée, amende
  configurable, concurrence, message ancien et reçu rejoué après redémarrage.
- Frontière Discord simulée : réaction et réponse avec amende et prochain
  nombre, pas de double réponse ; contrôle réel des permissions de la nouvelle
  commande staff à travers son callback. 49 commandes sous 27 entrées principales.
- Ces tests ne constituent pas une recette du nouveau counting entre deux
  comptes humains. Les captures du 25 octobre montrent les anciennes règles.
- Après redémarrage du laboratoire : connexion Gateway confirmée sans erreur
  dans le nouveau log, `/config comptage` relu dans l'API Discord avec son
  option d'amende bornée, intégrité SQLite vérifiée. État préservé au
  redémarrage : prochain nombre 1, record 0, amende 1 000 cœurs. Le sujet du
  salon affiche les nouvelles règles.

Les règles actuelles et l'origine Silvers sont détaillées dans [COUNTING.md](COUNTING.md).

## Vérifié localement

### Catalogue bienveillant — 27 octobre 2026

- 50 compliments et 50 taquineries originales, relus pour rester chaleureux
  ou absurdes, sans attaque sur le physique, les identités ou sujets sensibles.
- Les cinq dernières phrases de chaque catégorie sont exclues du tirage dans
  chaque serveur. Historique de textes persisté sans identifiant de cible,
  repris après redémarrage ; reçu rejoué sans nouveau tirage.
- Délai partagé de 15 secondes par auteur pour les deux commandes ; module,
  serveurs, absence de mutation économique et absence de mentions testés.
- **188 tests locaux passent** ; installation verrouillée, Ruff, formatage,
  configuration, démo et construction du wheel réussis.
- Recette réelle après redémarrage dans #distractions : `/compliment` et
  `/insulter` répondent avec deux phrases du nouveau catalogue ; présentation
  publique et historique persisté relus. Aucun autre serveur connecté.

### Taux du jour et duos illustrés — 27 octobre 2026

- **174 tests locaux passent**, Ruff et formatage conformes. Couverture des
  huit taux solo et six duos, stabilité quotidienne, minuit à Paris et changements
  d'heure, symétrie, validation des cibles, absence d'écritures économiques et
  rendu des quatorze illustrations transparentes.
- Régression du pseudo mêlant latin, grec et cyrillique : chaque caractère
  possède un glyphe dans Noto Sans. Les pseudos et initiales utilisent cette
  police embarquée ; l'interface conserve Nunito.
- Laboratoire redémarré et connecté. L'API Discord expose `/taux` avec huit
  choix et `/duo` avec six choix, dans le seul serveur autorisé.
- Recette réelle dans **#distractions** : choupitude du testeur à 54 %, puis
  amitié entre le testeur et Moka à 12 %. Les deux PNG sont affichés dans Discord,
  avec avatars et pseudo corrigé. Le sujet du salon explique les commandes.
  Cette recette ne constitue pas une vérification manuelle des quatorze types.
- Wheel construit et ressources contrôlées : quatorze illustrations, polices
  et licences embarquées. Pack d'images portable préparé dans
  `dist/moka-taux-images.zip` ; aucun envoi à un tiers effectué.

Les règles, illustrations et sources sont décrites dans [RATES.md](RATES.md).

Correction suivante : les emojis des pseudos utilisent Noto Color Emoji v2.047
en couleur, avec conservation des séquences jointes, variantes et drapeaux.
Un pseudo fictif entouré de feuilles reproduit le carré avant correction ; un nouveau
`/taux` dans #distractions affiche les deux feuilles vertes (choupitude 36 %).
**180 tests passent** après ajout des régressions ; Ruff, formatage et wheel
vérifiés, dont la présence de la police emoji et de sa licence dans le paquet.

### Pause commune aux jeux — évolution du 27 octobre 2026

- **127 tests locaux passent**, avec lint, formatage, configuration et démo
  hors ligne vérifiés.
- Erreurs de counting et de mots : rôle immédiatement demandé, échéance de
  3 600 secondes, blocage des deux jeux sans nouvelle amende, sans prolongation
  au rejeu et après redémarrage. Autres personnes et autres serveurs isolés.
- Horloge simulée : jeu autorisé à nouveau à l'échéance et rôle retiré par
  l'adaptateur. Cache membre absent, rôle supprimé et permissions restreintes
  aux seuls salons de jeux couverts par les tests.
- Dans le laboratoire Discord : rôle existant repris sous le nom `Pas-doué`,
  interdictions d'écriture relues par API dans counting et suite-de-mots,
  descriptions mises à jour et durée configurée à une heure.
- Après une erreur réelle du propriétaire à 17 h 07, rôle attribué et pause
  active relus par API. L'affichage séparé, initialement désactivé, a été
  activé puis contrôlé dans le client Discord : le propriétaire apparaît sous
  le groupe Pas-doué. Les 16 tests ciblés du laboratoire et des pénalités passent.
- Aucun cycle complet d'une heure ni retrait sur une personne réelle n'a
  encore été observé. Les tests de reprise et d'expiration utilisent une
  horloge injectée et des adaptateurs Discord simulés.

Voir [GAME-PENALTIES.md](GAME-PENALTIES.md) pour le comportement et ses limites.

### Levée manuelle de sanction — 27 octobre 2026

- **134 tests passent** : levée commune aux deux jeux, préservation des soldes,
  des autres rôles et serveurs, rejeu ne levant pas une nouvelle sanction,
  retrait Discord échoué réessayé par maintenance, concurrence avec une
  attribution en cours et contrôle des permissions staff.
- `/debloquer membre` relu dans les commandes du laboratoire par l'API :
  permission Gérer le serveur et membre obligatoire. Bot reconnecté sans
  erreur ; intégrité SQLite vérifiée.
- Déblocage réel du propriétaire effectué avec le moteur de levée de sanction :
  retrait du rôle et absence de pause active relus après redémarrage dans
  Discord et SQLite. Le callback de commande est testé avec un adaptateur simulé.

### Vérifications initiales du 25 octobre

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
- Dépôt public publié sous `nahsiy/moka-bot`. Le premier workflow
  [GitHub Actions](https://github.com/nahsiy/moka-bot/actions/runs/40228508445)
  réussit sous Python 3.12 et 3.13 : installation verrouillée, lint, formatage,
  tests, vérification des commandes et démonstration CLI. Il ne se connecte pas
  à Discord.

Un avertissement de dépréciation `audioop` provient de discord.py sous Python
3.12. Aucun audio n'est capturé ou lu par ce projet.

## Vérifié dans Discord — laboratoire uniquement

- Installation de Moka Test dans le seul serveur explicitement autorisé,
  sans Administrateur ; salons et rôles préparés par l'API officielle du bot.
- Recette initiale du 25 octobre : intents membres et contenu activés, connexion
  Gateway réussie, 27 entrées
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
  puis retiré à échéance (30 secondes dans la configuration de cette recette du 25 octobre).
- Suite de mots : `café` validé en mode libre. XP écrit persisté après message.
- Intégrité SQLite vérifiée ; aucune erreur dans les logs après correction.

Le premier démarrage a révélé l'utilisation de `Guild.afk_channel_id`, absent
de discord.py. Le suivi vocal utilise désormais la propriété publique
`Guild.afk_channel`. Un test de régression avec un vrai objet Guild reproduit
l'exception avant correction et passe après celle-ci.

Le laboratoire tourne localement avec `.env` et `config.test.toml` ; ce n'est
pas encore un hébergement permanent. Les données et logs ne sont pas versionnés.
Les captures du client restent privées. Le README présente uniquement des
aperçus générés avec des noms fictifs et la mascotte, sans données de membres.

## Non vérifié ou non exécuté

- Ensemble des cartes et permissions de tous les modules ; la première recette
  ci-dessus couvre uniquement les parcours explicitement décrits.
- Tickets avec un second compte ordinaire, vocaux temporaires, trombinoscope,
  timeouts, banque, transferts et autres jeux en conditions réelles.
- XP vocal : adaptateur écrit, recette à deux humains nécessaire.
- Build/exécution Docker : moteur local arrêté, `docker info` a échoué.
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

Les aperçus publics sont des exemples hors ligne avec des noms fictifs ; ils
ne prouvent pas l'exécution de la recette Discord restante.
