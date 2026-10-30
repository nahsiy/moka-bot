# Moka ☕

Un compagnon Discord francophone : discussions, progression et petites
animations pour faire vivre une communauté. Python 3.12+, SQLite, modules
activables séparément. Aucun service payant ni modèle IA requis.

**Moka 0.3.0 — Le Comptoir prend vie.** Accueil sur entretien, rôles au choix,
profil et banque, badges et titres, panneau du Barista, cartes originales et
Juke-box partagé. Les [notes de version](docs/RELEASE-0.3.0.md) présentent les
nouveautés et la mise à jour depuis 0.2.0.
Les tests locaux et les parcours réellement essayés dans Discord sont détaillés
séparément dans [VALIDATION.md](docs/VALIDATION.md).

Moka peut servir de base commune : code Python modifiable, licence MIT et
hébergement au choix de l'équipe. Chaque module peut être activé séparément,
notamment pour conserver les fonctions déjà assurées par un autre bot.

## Les cartes de Moka

Ces exemples sont générés par le véritable moteur de cartes, avec la mascotte
Moka et des noms fictifs. Les pourcentages sont illustratifs : ce sont des
aperçus, pas des captures du client Discord. Aucun avatar humain, identifiant
de membre ni conversation privée n'est inclus dans ces visuels.

![Exemple de carte de choupitude avec la mascotte Moka](docs/images/taux-choupitude.png)

![Exemple de duo d'amitié avec deux noms fictifs](docs/images/duo-amitie.png)

`/taux type:choupitude` découvre ton taux du jour ; `/duo type:amitie
membre:@quelqu’un` mesure un duo pour rire. Huit types individuels et six duos,
fixes jusqu'à minuit à Paris, avec avatars et illustrations partiellement
colorées. Les pseudos grecs, cyrilliques et les emojis sont pris en charge.

Le counting accepte les calculs et tire à pile ou face après une erreur, avec
une amende configurable : [règles](docs/COUNTING.md). Le rôle **☕ Café renversé** impose
une pause d'une heure dans les deux jeux ; le staff la lève avec
`/debloquer membre` : [détails](docs/GAME-PENALTIES.md).

Un [parcours de démonstration de cinq minutes](docs/DEMO.md) permet de présenter
le bot au staff. Une démonstration locale sans compte Discord est aussi disponible
ci-dessous.

## Ce qui est développé

| Module | Fonctions |
| --- | --- |
| Progression | XP écrit et vocal, niveaux, profils, classement, [six paliers de rôles](docs/ROLES-XP.md) avec rattrapage automatique |
| Économie | Cœurs fictifs, récompenses 24 h / 7 j, cadeaux, portefeuille |
| Banque | Dépôts, retraits, capacité, intérêts, amélioration de la protection |
| Distractions | Paris, jackpot collectif, vol de portefeuille, mini-jeu de hack |
| [Tournée de Moka](docs/TOURNEE.md) | Pause café illustrée, inscriptions, compte à rebours et récompense collective |
| Jeux de salon | Counting avec calculs, amende et pile ou face, record, rôle d'erreur temporaire ; suite de mots avec deux modes |
| Ambiance | 50 compliments et 50 taquineries illustrés, trois éditions, cinq dernières phrases évitées, horoscope fictif |
| Taux du jour | 8 taux individuels et 6 duos, cartes illustrées avec avatars, résultats fixes jusqu'à minuit |
| Boutique et souvenirs | Objets à offrir, 8 badges et 4 titres décoratifs ; achats privés, aucune gemme |
| [Le Juke-box](docs/JUKEBOX.md) | File partagée, lecteur illustré, commandes dans un salon dédié et écoute vocale sans micros |
| Communauté | Accueil privé sur entretien, rôles à choisir, pauses annoncées, tickets et vocaux temporaires |
| Trombinoscope | Pré-accès, niveau minimum, approbation du staff, retrait d'accès après suppression |
| Administration | Panneau privé du Barista, règles par serveur, diagnostic, correction journalisée des cœurs, timeout manuel |
| Données | Profil privé, export personnel, effacement confirmé, sauvegarde cohérente |

Le catalogue et les textes sont originaux. Les montants, probabilités et règles
par défaut sont des propositions, **pas une copie vérifiée de l'équilibrage de
Sylhbot**. Le vol bancaire, les immunités par rôle et les fonctionnalités de
modération non inventoriées ne sont pas implémentés à ce stade. La matrice
[fonction par fonction](docs/FONCTIONS.md) sépare le livré du reste à préciser.

## Essayer immédiatement, sans Discord

Avec [uv](https://docs.astral.sh/uv/getting-started/installation/) installé :

```sh
uv sync --locked --extra dev
uv run moka --config config.example.toml check
uv run moka demo
uv run pytest -q
```

`check` construit et sérialise réellement l'arbre des commandes Discord, sans
token ni requête réseau. `demo` joue un scénario dans une base SQLite jetable :
récompenses, banque, achat, cadeau, counting, tournée collective et sauvegarde. Ce scénario
ne charge aucun membre Discord et ne crée aucun salon.

## Installer sur un serveur de test

Suivre [INSTALLATION.md](docs/INSTALLATION.md) : application Discord dédiée,
serveur de test explicitement autorisé, permissions limitées, configuration des
salons, puis synchronisation des commandes sur ce seul serveur.

Ne jamais copier le token dans le code, un ticket ou le README. `.env`, bases et
sauvegardes sont exclus de Git. Le bot refuse de démarrer sans token et sans
liste de serveurs autorisés.

## Organisation

```text
src/moka/
  base.py          Comptes, reçus, XP et transactions
  settings.py      Règles et activation des modules par serveur
  economy.py       Banque, boutique, cadeaux, paris et vols
  games.py         Counting, mots, événements et règlements
  community.py     Tickets, photos et tirages des phrases d'ambiance
  admission*.py    Accueil privé, charte et accès sur entretien
  presence.py      Participation observée et absences annoncées
  collection.py    Badges, titres et historique des cœurs
  profile_*.py     Cartes, navigation privée et durée de vie des écrans
  music*.py        Sources, file, lecteur et installation du Juke-box
  social_catalog.py  50 compliments et 50 taquineries originales
  rates.py         Pourcentages quotidiens individuels et en duo
  rate_cards.py    Rendu local des cartes, avatars et emojis
  assets/          Illustrations et polices avec leurs licences
  bot.py           Connexion, événements Discord et tâches de reprise
  discord_ui.py    Cartes et boutons persistants
  cogs/            Commandes membres, staff et communauté
tests/             Tests métier, concurrence et frontière Discord
```

- [Exploitation et sauvegardes](docs/EXPLOITATION.md)
- [Identité visuelle et présentation des réponses](docs/DIRECTION-ARTISTIQUE.md)
- [État de validation et recette Discord](docs/VALIDATION.md)
- [Revue de nettoyage avant release](docs/NETTOYAGE.md)
- [Taux du jour, duos et illustrations](docs/RATES.md)
- [Compliments et taquineries](docs/AMBIANCE.md)
- [Changements et mise à jour](CHANGELOG.md)
- [Crédits et licences des ressources](THIRD_PARTY_NOTICES.md)
- [Périmètre et inconnues](PLAN.md)
- [Sécurité](SECURITY.md)

## Indépendance de la communauté

Le code est distribué sous [licence MIT](LICENSE). Chaque équipe peut reprendre
le dépôt, modifier le bot et choisir son hébergement. Une équipe Discord peut
gérer l'application indépendamment du compte qui héberge ce dépôt. Les tokens
et données des membres restent privés : ils ne font pas partie de la diffusion
open source.

Une seule instance de Moka par base. SQLite suffit à cette première version ;
aucun dashboard web, port entrant, Redis ou PostgreSQL n'est nécessaire.

## Sources techniques

- [discord.py : installation et événements](https://discordpy.readthedocs.io/en/stable/intro.html)
- [discord.py : commandes et composants](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [Discord : équipes de développement](https://docs.discord.com/developers/topics/teams)
- [uv dans Docker](https://docs.astral.sh/uv/guides/integration/docker/)

Les aperçus et la démonstration CLI sont produits hors ligne. Ils ne prouvent
pas le fonctionnement de tous les modules dans Discord. Les essais réels sont
décrits séparément dans [VALIDATION.md](docs/VALIDATION.md).

Le [premier café](docs/ACCUEIL.md) propose un accueil privé sur entretien, avec
charte et validation humaine avant les accès communautaires. Il reste désactivé
par défaut et demande une installation explicite.

Le [câlin collectif](docs/CALIN-COLLECTIF.md) rejoint les choix de
`/animation lancer` : une pause facultative, illustrée et gratuite, avec des
cœurs fictifs selon le nombre de participants.

Le [tableau du Barista](docs/BARISTA.md) regroupe les réglages du serveur. Le
[profil et les souvenirs](docs/PROFIL-ET-SOUVENIRS.md) donnent accès à la banque,
aux récompenses, à la boutique et aux badges. [Le Juke-box](docs/JUKEBOX.md) propose
une écoute partagée, avec son lecteur et sa file, dans deux espaces dédiés.
