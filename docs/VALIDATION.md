# Validation de Moka 0.4.0 — état courant et historique

## État courant — 30 octobre 2026

**524 tests passent sous Python 3.12 et sous Python 3.13.** Ruff, formatage,
38 commandes racines, démo hors ligne et intégrité SQLite sont vérifiés.
La [revue 0.4.0](NETTOYAGE-0.4.0.md) décrit les corrections, compatibilités et
contrôles de confidentialité ; les notes [0.4.0](RELEASE-0.4.0.md) expliquent la mise à jour.

Recettes réelles distinctes des tests : administration privée, menus d'intérêts,
notification de charte, clôture d'un entretien déjà validé et cycle de suppression
sur un salon temporaire avec horloge séparée. Horoscope : douze éditions du jour
relues à la source, sélection dans Discord, réponse privée et menu réinitialisé.
Les captures, bases et identifiants de recette restent locaux et hors distribution.

Les droits d'un nouvel arrivant sont vérifiés par profils synthétiques ; cela
ne remplace pas une recette de bout en bout avec un nouveau compte humain.
La garde sur vocal occupé et les échéances à sept jours sont testées hors ligne.
Les votes musicaux avec plusieurs humains et la musique depuis le futur hôte
restent à recetter. La validation Docker locale est consignée ci-dessous ; les
résultats distants restent visibles dans [le workflow CI](https://github.com/nahsiy/moka-bot/actions/workflows/ci.yml).

## Distribution et conteneur 0.4.0

Wheel et archive source construits, dépendances verrouillées et paquet installé
dans un environnement neuf. Depuis un répertoire extérieur au dépôt : version
0.4.0, 38 commandes, démo et intégrité SQLite validées. Trois cartes sont rendues
avec noms fictifs ; la nouvelle bannière et les polices sont présentes.

Image Docker Linux ARM64 construite et exécutée : utilisateur 10001, racine en
lecture seule, capacités retirées, privilèges supplémentaires interdits, temporaire
de 64 Mio, deux CPU, 1 Gio et 256 processus. Même scénario de commandes, démo et
rendu de trois cartes réussi ; bannière chargée, FFmpeg, Deno et yt-dlp disponibles.
Ce test ne fournit ni token ni connexion Discord et ne relance pas YouTube.

Le job CI construit et teste le conteneur sur son runner Linux, avec ces mêmes
protections. La recette YouTube depuis le futur VPS reste distincte. Les paquets
publics sont inspectés pour les fichiers privés, identifiants réels, chemins
personnels, métadonnées d'image et liens locaux cassés.

## Historique de la recette

État au 28 octobre 2026 ; les sections historiques précisent la version essayée.
Première recette réelle effectuée sur un serveur de test dédié, avec un seul
compte humain. La recette complète reste à terminer.

## Évolutions locales après 0.2.0

Ces changements sont en cours dans le laboratoire, hors du tag publié 0.2.0.

- Cartes de taux et duos en 1 200 × 900, envoyées seules en pièce jointe avec
  description accessible et repli texte. Solo et duo observés dans Discord.
- Profil privé illustré avec boutons déposer, retirer, acheter de la capacité
  au prix affiché et actualiser. Les profils d'autres membres restent en lecture
  seule ; la confidentialité est vérifiée avant tout rendu.
- **261 tests locaux passent** : montants, auteur et serveur, modules désactivés
  après ouverture, achats et formulaires rejoués, devis de palier périmé,
  conservation des fonds et repli texte. Ruff, formatage, CLI et démo conformes.
- Recette réelle depuis le profil : dépôt d'un cœur puis retrait du même cœur,
  mise à jour de la carte et des boutons, soldes initiaux restaurés et intégrité
  SQLite relue. Le bouton d'achat est grisé si les fonds sont insuffisants.
  L'achat de capacité est vérifié localement ; aucun achat de capacité n'a été
  effectué sur le compte pendant la recette Discord.

La capacité et les coûts initiaux sont conservés : [règles de banque](BANQUE.md).

Le 28 octobre, `/offrir` annonce publiquement l'auteur, l'objet et le destinataire
dans un encart « Un cadeau ! », avec un déterminant et sans ping. `/acheter`
reste privé. Les callbacks sont testés avec une vraie base
jetable, y compris l'absence d'annonce de succès si l'objet manque ; aucun cadeau
supplémentaire n'a été envoyé à un membre pour cette vérification.

L'harmonisation des réponses utilise le même encart café pour les confirmations,
avertissements, erreurs, jeux et outils communautaires. L'audit des appels
d'envoi ne trouve plus de réponse textuelle hors cadre. Les cartes illustrées
gardent leur cadre intégré ; les confirmations du profil sont rendues dans
l'image et sa description accessible. Les régressions testent aussi le rendu
d'une erreur avant ou après acquittement et la confidentialité de l'export JSON.
Voir [la charte visuelle](DIRECTION-ARTISTIQUE.md).

Recette Discord de cette harmonisation : consultation de `/config comptage`
sans modifier l'amende, puis dépôt refusé pour capacité insuffisante. Les deux
réponses privées affichent le cadre attendu ; aucun mouvement bancaire n'est
effectué par ce refus. Les autres parcours gardent le périmètre de recette
décrit dans leurs sections respectives.

### Tournée de Moka — 28 octobre 2026

Le jeu collectif devient une pause café illustrée : carte 1 200 × 900, compteur
d'inscriptions, objectif, temps restant et bouton « Je prends un café ». Les
réglages, références persistées et récompenses économiques restent compatibles
avec les événements antérieurs. Aucun identifiant technique n'est affiché sur
la nouvelle carte ; le bouton contient sa référence et vérifie le message,
son auteur, le salon et le serveur.

Les tests couvrent les trois états illustrés, l'absence de temps négatif, une
récompense nulle avec groupe réuni, la transparence de l'illustration embarquée,
le repli texte avec bouton, sa reconstruction et les doubles inscriptions.
Ruff, formatage, configuration, démonstration et construction wheel/source passent.
Le wheel contient l'illustration et son prompt, sans donnée de membre.

Recette réelle dans #distractions : lancement avec le nouveau choix, une tasse
réservée, redémarrage pendant les 30 secondes, puis second clic refusé comme
participation déjà enregistrée. La carte finale « La tournée est servie ! »
remplace l'attente, sans bouton ; un seul crédit de 100 cœurs et aucune écriture
bancaire sont relus dans le journal. L'annonce est marquée effectuée et l'intégrité
SQLite est conforme. La fin sans groupe suffisant est testée hors ligne.

Cette évolution tourne uniquement dans le laboratoire ; aucune nouvelle
publication ni nouvelle version GitHub n'est créée pour cette recette.

### Rôle Café renversé — 28 octobre 2026

Le rôle de pause est renommé **☕ Café renversé**, en caramel café. Les clés
`counting_failure` et les références des sanctions restent inchangées ; les
messages de première erreur et de pause sont adaptés au comptoir, avec leur
échéance réelle. Les anciens noms restent pris en charge par la préparation
idempotente, sans duplication du rôle ni reprise de permissions privilégiées.
Les durées, amendes et règles de déblocage sont conservées.

**233 tests locaux passent**, dont la reprise des deux anciens noms et d'un rôle
configuré sous un autre nom, l'absence de doublon à la relance et le refus de
renommer un rôle privilégié. Installation verrouillée, Ruff, formatage, contrôle
des commandes et démo hors ligne passent.

Sur le serveur autorisé, nom et couleur relus par API : même identifiant,
même position et affichage séparé, mêmes permissions globales et interdictions
dans les deux salons, mêmes références et échéances de sanctions. Les sujets
des salons reprennent le nouveau nom. Aucune sanction de membre n'a été
provoquée pour cette vérification ; les parcours de pause et de déblocage
sont couverts par les tests existants.

### Paliers XP du Comptoir — 28 octobre 2026

Les six paliers de [rôles XP](ROLES-XP.md) sont créés et activés en mode exclusif.
Les membres présents reçoivent automatiquement le rôle correspondant à leur
niveau ; les bots sont ignorés. Un seul palier est conservé, indépendamment
du titre du propriétaire, du staff et du rôle de pause.

**261 tests locaux passent** : paliers 0/3/7 et au-delà, rôle unique, concurrence,
préservation du compte et des rôles indépendants, refus d'un rôle privilégié,
absence de retrait si l'ajout échoue, reprise par maintenance, nouveaux membres,
module désactivé, serveur interdit et compatibilité cumulative. Ruff, formatage,
contrôle des commandes, démonstration et construction des paquets passent.

Après redémarrage, l'attribution automatique est relue par API pour les membres
humains présents : un seul palier chacun, rôles antérieurs préservés et titre
Le Barista toujours prioritaire pour le propriétaire. Comparaison SQLite avec
la sauvegarde : XP, portefeuilles, banques et améliorations inchangés. Aucun
message ni gain artificiel n'est utilisé pour déclencher le rattrapage.
Le parcours d'arrivée d'un nouveau membre et les échecs Discord sont testés
avec l'adaptateur simulé ; aucun compte supplémentaire n'est invité.

### Accès du staff au journal — 28 octobre 2026

Un salon journal existant avait des permissions propres sans autorisation de
lecture pour le rôle du staff, malgré l'autorisation de sa catégorie. L'accès
au salon et à l'historique est rétabli explicitement pour ce rôle ; le refus
pour everyone et les autres dérogations sont conservés et relus par API.

La préparation répare désormais aussi cet accès sur un salon existant. La
régression reproduit une dérogation staff sans droit de voir le journal, puis
vérifie la réparation en préservant un refus d'écriture et les dérogations des
autres rôles. Le test échoue avant correction et passe après ; **243 tests passent**.

### Préférences à choisir — 28 octobre 2026

Huit panneaux Moka sont publiés dans le salon rôles, ouvert en lecture aux
membres et fermé à l'écriture ordinaire. Le catalogue propose 51 choix
facultatifs par rubrique. Les menus sont privés, les rôles choisis sont publics.
Le staff, Le Barista, les paliers XP et la pause ne font pas partie du catalogue.
Voir [les rôles à choisir](ROLES-A-CHOISIR.md).

**261 tests locaux passent** : installation idempotente avec reprise des rôles
existants, droits sûrs, préservation des autres rubriques et des comptes,
exclusivité, ancien menu et droits relus après ouverture, rôles réservés,
bouton reconstruit et publication actualisée sans doublons. La permission staff
est contrôlée à l'exécution de la commande installer. Ruff, formatage, contrôle
des commandes, démo et construction des paquets passent.

Recette réelle : panneau des centres d'intérêt, ouverture du menu privé,
sélection de Lecteur puis réouverture avec l'option cochée, retrait et confirmation.
L'attribution et le retrait sont relus par API ; tous les rôles initiaux sont
restaurés. Les huit panneaux et la nouvelle commande sont relus dans Discord.
Les autres rubriques sont couvertes par le filtrage et les tests locaux ; aucune
information d'identité, de localisation ou de préférence personnelle n'est
déduite ni attribuée à un membre pendant la préparation.

### Menus directs de rôles — 28 octobre 2026

Le bouton intermédiaire est remplacé par un menu déroulant sous chaque rubrique.
Le choix est appliqué au membre qui clique, avec une confirmation privée donnant
ses rôles retenus ; le panneau public n'est pas personnalisé avec ses choix.
Un bouton secondaire retire tous ses choix de cette seule rubrique.

**261 tests passent**, dont sélection et retrait après reconstruction des
composants, confirmation privée sans modification du message public, refus
d'un panneau forgé et attribution au seul membre qui clique. Les anciens boutons
restent reconnus ; `/roles choisir` conserve son menu privé pré-coché.

Recette des menus directs : ouverture de la liste publique des centres d'intérêt
sans bouton intermédiaire, choix de Lecteur et confirmation privée ; retrait
par le bouton dédié. Attribution, retrait et restauration de tous les rôles
initiaux relus par API. Les huit messages sont actualisés en place, avec le même
identifiant et sans défaut personnel dans les options publiques.

## Validation Linux de la version 0.2.0

Le workflow [GitHub Actions](https://github.com/nahsiy/moka-bot/actions/runs/40549716197)
réussit sous Python **3.12 et 3.13** : installation verrouillée, Ruff, formatage,
188 tests, sérialisation des commandes, démonstration hors ligne et construction
des paquets source et wheel. Ce contrôle ne se connecte pas à Discord.

Les paquets de publication sont contrôlés séparément : illustrations et
licences embarquées, absence de base, token, capture du client, chemin local
et identifiant réel dans les fichiers distribués. Les aperçus utilisent la
mascotte et des noms fictifs. Les sommes SHA-256 accompagnent les téléchargements.

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
Aucune capture du client n'est incluse dans cette version. Le README présente des
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

## Accueil sur entretien — validation du 28 octobre 2026

- 276 tests locaux réussis, dont 15 nouveaux contrôles d'accueil : isolement des
  serveurs, lecture avant décision, délai de nouvel essai, refus/reprise,
  permissions réelles de discord.py pour texte/vocal, contrôles staff renouvelés,
  doubles arrivées concurrentes, reprise d'un salon créé avant interruption,
  décision conservée après une panne d'application des rôles et commandes
  présentes dans l'arbre hors ligne.
- Installation explicite sur le serveur autorisé : quinze salons/catégories
  protégés, charte séparée en lecture seule et deux membres existants conservant
  leurs accès. Rôles d'accès distincts des rôles XP ; aucun changement aux soldes
  ou à l'XP lors de l'installation.
- Permissions relues depuis l'API Discord : simulation d'un candidat sans rôle,
  avec attente, ou avec tous les rôles XP/préférences ; seule la charte est visible
  avant création de son entretien. Un membre validé sans rôle staff n'accède pas
  au journal staff. Les droits effectifs des membres présents et de Moka sur les
  salons préexistants sont conservés.
- Commandes synchronisées, bot reconnecté et maintenance sans erreur observée.
  Rendu de la charte et aperçu à boutons désactivés vérifiés dans Discord.
- **Pas de vraie arrivée d'un autre compte humain effectuée à ce stade.** La
  simulation utilise les permissions relues du serveur ; elle ne constitue pas
  une recette réelle du parcours complet, des modales ou du vocal.

Les sauvegardes des sources, de la base et des permissions précédentes ainsi que
les preuves contenant des identifiants restent locales, ignorées par Git. Aucun
transcript d'entretien ni donnée personnelle n'est ajouté à cette documentation.

## Câlin collectif — validation du 28 octobre 2026

- 291 tests locaux réussis, dont 15 nouveaux cas pour le câlin : formule de gain,
  paiement unique après reprise, isolement des serveurs, places concurrentes,
  paramètres figés au lancement, modules désactivés après lancement, plafonds,
  contrôle staff, bouton reconstruit après redémarrage, repli texte et rendu des
  trois états sans donnée de membre.
- Choix **Câlin collectif** synchronisé dans `/animation lancer` sur le seul
  serveur autorisé. Recette réelle dans le salon de distractions : lancement par
  commande, clic, confirmation privée, deuxième clic rejeté, clôture automatique
  et versement de 200 cœurs pour un participant. Rejouer le règlement n'ajoute
  aucun paiement. Le gain du compte de recette a été annulé par une écriture
  compensatrice dans le journal, avec solde initial rétabli.
- Carte finale relue via l'API Discord et vérifiée visuellement : une illustration
  seule, sans texte public en double, bouton retiré après clôture. Les états
  sans participant et à plusieurs participants ont été vérifiés hors ligne ;
  la recette réelle décrite ici comporte un seul participant.
- Installation verrouillée, lint, format, configuration d'exemple, démonstration,
  sdist et wheel validés. La nouvelle illustration transparente est bien dans
  le wheel. Aucun identifiant ou avatar de membre n'est dans les nouveaux
  textes, illustrations ou exemples publiables.

Les preuves de recette, les soldes et les sauvegardes restent locaux et ignorés
par Git. Aucun nouveau tag de release ni publication n'a été effectué.

## Bonus surprise du counting — validation du 28 octobre 2026

- 308 tests locaux réussis, dont 17 nouveaux cas : frontière des 5 %, montant
  borné, absence de tirage sur erreur/pause/message ancien, désactivation,
  cumul avec un palier, plafonds, concurrence, reçu conservé au redémarrage,
  isolement des serveurs et rollback de toute la transaction en cas d'échec.
- Le tirage à pile ou face après une erreur garde son fonctionnement ; son test
  de reprise utilise à nouveau un générateur pour le nouveau nombre valide,
  qui peut maintenant déclencher un bonus distinct du reçu d'erreur rejoué.
- Reconnexion du bot avec les paramètres 500 points de base et 10–50 cœurs,
  explication du salon counting mise à jour et relue via Discord. Aperçu de
  l'encart publié dans les distractions, explicitement sans gain versé.
  Compteur conservé et aucun crédit de recette injecté ; les variations de
  solde observées sont expliquées par l’activité normale dans le journal.
- Les gains et leur annonce ont été exercés sur des données isolées avec tirages
  contrôlés. **Aucun gain aléatoire réel n'est revendiqué pour cette recette** :
  le tirage réel reste à 5 %, sans forcer une victoire sur les comptes du serveur.

Installation verrouillée, lint, format, vérification de la configuration et
démonstration hors ligne réussis. Les réglages des paliers restent conservés.
Les preuves et sauvegardes contenant l'état du serveur sont locales, ignorées
par Git. Aucune publication ni nouvelle release n'est effectuée.

## Réinitialisation visuelle des listes de rôles — 28 octobre 2026

- Défaut reproduit dans Discord : après sélection puis retrait, le rôle était
  réellement supprimé mais le client continuait d'afficher le choix précédent.
  Le test de non-régression échouait avant correction faute de rafraîchissement.
- Le menu de la rubrique reçoit maintenant une nouvelle référence après une
  action réussie, avec toutes les options publiques sans pré-sélection. Seuls
  les composants du message partagé sont renouvelés ; le détail des choix reste
  dans une confirmation privée. Les anciens identifiants restent reconnus.
- 311 tests réussis, dont les contrôles de retrait/réinitialisation, compatibilité
  des anciennes listes, absence de succès mensonger après refus Discord et
  confirmation du retrait réel même si le rafraîchissement échoue.
- Recette réelle dans les distractions avant et après redémarrage : sélection,
  retrait confirmé par l'API, cases décochées, nouvelle sélection avec les
  nouveaux identifiants puis retrait. Les préférences du compte de recette sont
  rétablies. Les modifications des autres membres pendant leur activité sont
  conservées, sans restauration de leurs préférences par le test.
- Les huit panneaux de rôles sont actualisés sur leurs messages existants,
  avec leurs listes directes et sans choix personnels précochés publiquement.
  Le panneau d'essai est désactivé après recette pour éviter un menu en double.

Installation verrouillée, lint, format, contrôle de configuration et démo hors
ligne réussis. Les preuves et sauvegardes restent locales et ignorées par Git.

## Boutons de rôles simplifiés — 28 octobre 2026

Les six rubriques à choix unique n'affichent plus de bouton de retrait : une
option **Aucun choix** permet d'enlever le rôle directement depuis leur liste.
**Tout retirer** reste sous les centres d'intérêt et les notifications.

312 tests passent, dont le retrait par l'option vide en conservant les autres
rubriques. Installation verrouillée, lint, format, contrôle de configuration et
démo réussis. Après redémarrage, les huit messages existants sont actualisés ;
la relecture API confirme les six listes sans bouton, les deux boutons multiples
et l'absence de choix personnels précochés. Aucun rôle de membre n'est modifié
par cette publication. La preuve détaillée reste locale et ignorée par Git.

## Présence et pauses — 28 octobre 2026

- Vérifications locales : dépendances verrouillées, Ruff, format, **349 tests**,
  CLI hors ligne (34 racines slash), démonstration et intégrité SQLite réussis.
- 37 cas dédiés : seuil exact à 21 jours, persistance après redémarrage,
  séparation des serveurs, grâce initiale et au retour, absences et expiration,
  suppression/export, messages courts/commandes/liens/jeux exclus, échange à
  deux, vocal cinq minutes/solo/muet/AFK/déconnexion, reprise des rôles,
  relecture après attente réseau, rôles réservés et bilan privé contrôlé.
- Discord : rôle dédié créé sans permission et affiché séparément si sa
  priorité le permet ; ajout puis retrait réels sur le propriétaire uniquement,
  avec une base et une horloge isolées. Les autres rôles ont été préservés.
- Activation sur le seul serveur autorisé, deux membres admis initialisés avec
  grâce complète. Aucun historique de conversation parcouru ; aucun membre
  signalé inactif à l'activation.
- Les 34 commandes du serveur sont relues via l'API officielle ; bilan publié
  puis relu dans le journal vérifié réservé au staff, sans notification.
- `/absence` exécuté réellement dans le salon de distractions : confirmation
  privée vue, date persistée, date affichée dans le bilan. L'absence de recette
  a été terminée directement via le service ; `/retour` et `/activite bilan`
  ont été testés par leurs callbacks hors ligne, sans revendiquer une exécution
  interactive réelle de ces deux commandes. Navigation Discord partagée avec
  l'utilisateur : aucune action supplémentaire forcée sur son interface.
- Pas de recette vocale réelle à deux pendant cinq minutes, ni d'observation
  réelle de trois semaines : ces durées sont couvertes par horloge injectée.
- Processus connecté après déploiement, aucun ERROR/Traceback dans son nouveau
  journal lors du contrôle. L'exécution reste locale, dépendante du Mac.
- Preuve privée ignorée par Git : `data/private-previews/presence-live.json`.

## Corvée de vaisselle — 30 octobre 2026

- Dépendances verrouillées, Ruff, format, CLI hors ligne (34 racines slash),
  démonstration et **384 tests** réussis, dont 35 cas dédiés à l'intégrité du
  counting et à la corvée. Diff vérifié sans erreur d'espacement.
- Tests sur nombres équivalents, valeur altérée/invalide, messages non validés,
  auteurs et serveurs distincts, rétention, effacement, rollback transactionnel,
  éditions concurrentes/rejouées, redémarrage et expiration exacte. Vérification
  du refus des jeux et anciens boutons, de l'abandon et des règlements déjà
  promis, du déblocage et des rôles devenus privilégiés après configuration.
- Déploiement : table ajoutée à la base existante, rôle dédié zéro permission,
  distinct du Café renversé, écriture interdite uniquement dans les deux salons
  textuels de jeux. Configuration et commandes relues par API officielle.
  Redémarrage avec le LaunchAgent existant, synchronisation ordinaire à zéro.
- Recette réelle dans le salon de distractions, avec le propriétaire uniquement :
  nouveau message humain « 1 », validation par le service sur un compteur de
  recette séparé, puis vraie édition Discord en « 2 ». Le Gateway a détecté
  l'édition sans injection d'événement ; rôle réellement attribué, sanction
  persistée et annonce encadrée envoyée une seule fois.
- Le salon de counting configuré n'a pas été déplacé ; son compteur n'a pas été
  modifié par la validation de recette. Le premier message n'a donc pas traversé
  le routage automatique du salon habituel : cette étape a été appelée par le
  service pour garder toute la recette dans le salon de distractions.
- `/hack` exécuté pendant la sanction : refus privé vu. `/debloquer` exécuté
  ensuite sur le compte de recette : confirmation privée vue, rôle retiré,
  contrôle métier à nouveau autorisé et autres rôles préservés.
- Nettoyage idempotent : compteur et trace de recette retirés, 15 XP et 3 cœurs
  du message annulés, avec mouvement de remboursement identifié dans le journal.
  Portefeuille, banque, XP et nombre de messages relus identiques à la baseline.
  Les reçus protègent contre un second remboursement. L'annonce de recette est
  devenue un encart « Corvée de vaisselle vérifiée ».
- Après reprise de la session interrompue : Moka connecté, service actif, aucun
  ERROR/Traceback observé depuis le début de la recette. La corvée du propriétaire
  est levée ; la fonctionnalité reste active pour les prochains nombres validés.
- L'expiration à une heure et la rétention à trente jours sont testées sur
  horloge injectée, sans prétendre les avoir attendues sur Discord.
- Preuves privées ignorées par Git : `data/private-previews/corvee-live.json`
  et `data/private-previews/corvee-recette-terminee.png`. Aucun nom, avatar ou
  identifiant réel ajouté à la documentation publique ou aux exemples de tests.

## Suite café — panneau, profil, souvenirs, petites attentions et musique

Validation du 30 octobre 2026, code de travail après la version 0.2.0 :

- **419 tests locaux passent**, Ruff et formatage passent, configuration et
  sérialisation de 36 commandes racines validées, démo hors ligne et intégrité
  SQLite vérifiées. Dépendances verrouillées synchronisées.
- Règles par serveur : gains/XP/capacité réellement appliqués, isolement des
  serveurs, rejet atomique d’un formulaire invalide, révision concurrente,
  compatibilité des anciens réglages, refus de réduire une banque sous un solde.
- Profil : banque conservée, navigation privée et contrôle de propriétaire,
  historique séparé par membre, achat unique de titres, équipement réservé aux
  titres acquis, export/effacement des nouvelles données, badges sans création
  de monnaie. Le catalogue montre les prix avant achat.
- Petites attentions : trois éditions, répartition 60/30/10, répertoires de phrases
  distincts, anti-répétition et reçus conservés ; carte publique sans texte recopié
  au-dessus et sans notification de mention. Trois images originales intégrées ;
  huit variantes de cartes rendues ; formats principaux inspectés.
- Musique : URL bornée à YouTube HTTPS ou recherche, timeout du résolveur avec
  arrêt du processus, file bornée et contrôles de propriétaire, vote unique,
  permissions de salon/accueil, autorisations relues, boutons cohérents avec l’état,
  refus de réécrire les accès d’un salon préexistant et limite des recherches.

Recette réelle Discord, dans le salon de distractions et les deux espaces du
Juke-box du serveur autorisé : profil privé, badges fondés sur l’état existant,
boutique privée ; panneau staff privé, formulaire prérempli et enregistrement des
valeurs inchangées ; compliment public illustré dans une édition rare au tirage.
Les huit contrôles d’accès musicaux ont été relus par l’API officielle : accueil
fermé aux arrivants, vue/commandes pour les membres accueillis, écriture libre
interdite, connexion vocale permise et parole/partage interdits, parole du bot permise.

La source YouTube a été résolue et cinq paquets Opus décodés localement. Dans
Discord, le bot s’est connecté au vocal, a lancé un extrait court, puis a suivi
les actions de pause, ajout d’un second morceau, consultation privée de la file,
retrait de ce morceau et reprise. Les captures et identifiants de recette restent
privés et ignorés par Git. Une nouvelle lecture complète après correction du traitement de stderr FFmpeg a lu 953 paquets Opus, avec sortie FFmpeg à zéro et aucune nouvelle erreur. L’écoute n’a pas été évaluée subjectivement par l’agent.

Limites : la majorité des votes avec plusieurs humains simultanés est testée
localement, sans mobiliser des membres pour une recette. L’hébergement Docker
nécessite encore sa recette YouTube propre ; la validation musicale ci-dessus
concerne le service supervisé du poste de recette. La file reste volontairement
en mémoire et revient au repos après redémarrage. Les restrictions de salons
ne neutralisent pas le propriétaire ou Administrateur de Discord.


## Nettoyage avant la prochaine release — 30 octobre 2026

430 tests passent sous Python 3.12 et 3.13. Onze vérifications supplémentaires
couvrent la durée de vie des écrans privés, le refus d’un formulaire bancaire
expiré, le prix du jackpot conservé après changement des règles/redémarrage,
et huit opérations métier sans seconde connexion de lecture des réglages.

Build et installation isolée du wheel validés ; 70 fichiers de ressources et
de code du paquet installé sont identiques à ceux du wheel reconstruit. Les
polices, licences et illustrations sont présentes, avec un rendu réel de trois cartes.
Les liens locaux sont valides. L’inspection du contenu destiné à la distribution
ne détecte ni données privées ni cache, sauvegarde ou base embarquée.

Docker : image Linux ARM64 construite et essayée avec utilisateur 10001, racine
en lecture seule, toutes les capacités retirées et `/tmp` borné. Configuration et
démo passent ; trois cartes sont rendues ; YouTube est résolu avec le binaire Deno
officiel, puis cinq paquets Opus sont décodés sans audio enregistré. Aucun token
ni connexion Discord dans cette vérification. Le workflow CI inclut maintenant
un job de construction/exécution hors ligne du conteneur ; son exécution distante
ne fait pas partie de cette preuve locale.

La revue [NETTOYAGE.md](NETTOYAGE.md) précise les compatibilités conservées et le
périmètre exact. Les résultats datés plus haut restent ceux des étapes précédentes.


## Café des astres — intégré à 0.4.0

516 tests hors ligne validés, dont 28 sur les horoscopes : dates Paris et passage
de minuit, édition absente ou incomplète, réseau et redirections, cache et concurrence,
permissions au clic, rôle facultatif et menus persistants. Ruff et contrôle de
configuration passent ; le wheel contient le module et la nouvelle illustration.

Lecture réseau réelle des douze signes vérifiée sur la même édition : aperçu RSS
court, date et cinq notes cohérentes, liens vers les pages de l’éditeur. Salon
créé dans La Pause Café, accès relus avec profils synthétiques en attente et
accepté ; panneau illustré et douze options relus via l’API Discord. Ces profils
ne remplacent pas une recette avec un nouveau compte humain.

Recette via le client Discord : la liste des douze signes s’ouvre directement ;
une sélection produit la lecture privée datée, les cinq notes et le lien complet.
Le menu commun retrouve son état initial. Vérification depuis le compte responsable,
sans attribuer ni retirer de rôle. Capture conservée uniquement dans les preuves
locales ignorées par Git. Moka reconnecté après installation et synchronisation.
