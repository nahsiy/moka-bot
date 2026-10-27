# Installation sur un serveur de test

Le développement local ne crée aucune application Discord. Pour une recette
réelle, le propriétaire crée une application dédiée dans le Developer Portal,
idéalement rattachée à une équipe Discord avec des responsables durables.

## Application et accès

1. Créer l'application et son bot avec le compte du responsable.
2. Activer **Server Members Intent** et **Message Content Intent** dans Bot.
   L'XP vocal suit uniquement les états de présence ; aucune connexion audio
   ni dépendance de capture audio n'est nécessaire.
3. Installer l'application dans un serveur de test avec les scopes `bot` et
   `applications.commands`.
4. Accorder les droits nécessaires aux seuls modules essayés. Ne pas demander
   Administrateur.

| Module | Permissions supplémentaires |
| --- | --- |
| Base / cartes | Voir le salon, envoyer des messages, intégrer des liens ; joindre des fichiers pour les taux illustrés |
| Jeux | Ajouter des réactions, lire l'historique |
| Rôles et pénalités | Gérer les rôles ; rôle Moka au-dessus des rôles attribués |
| Tickets | Gérer les salons ; staff des tickets explicitement configuré |
| Vocaux temporaires | Gérer les salons, voir/connecter, déplacer les membres |
| Trombinoscope | Lire le salon, gérer les rôles, créer et utiliser des fils publics |
| Timeout | Exclure temporairement des membres ; hiérarchies staff/bot vérifiées |
| Export personnel | Joindre des fichiers dans les réponses |

Les permissions effectives de chaque salon peuvent restreindre celles du rôle.
`/diagnostic` aide à les contrôler une fois connecté ; il ne peut pas prouver
que les intents privilégiés ont été activés dans le portail.

## Démarrage Python

Depuis le dossier du projet :

```sh
uv sync --locked --extra dev
cp .env.example .env
chmod 600 .env
```

Renseigner `.env` localement : `DISCORD_TOKEN`, `MOKA_GUILD_IDS` (identifiant du
serveur test), `MOKA_CONFIG=config.example.toml`. Ne jamais publier ce fichier.

```sh
uv run --env-file .env moka --config config.example.toml check
```

Pour le premier enregistrement des commandes, mettre `MOKA_SYNC_COMMANDS=1`
dans `.env`, puis :

```sh
uv run --env-file .env moka run
```

Le bot ne synchronise que les serveurs explicitement listés. Une fois les
commandes enregistrées, remettre `MOKA_SYNC_COMMANDS=0` pour les démarrages
ordinaires. Les commandes existantes de cette application dans les serveurs
listés sont remplacées par cet arbre ; utiliser une application de test dédiée.

Le token se renseigne dans l'environnement, jamais dans une conversation ou
dans une commande copiée dans un dépôt. En cas d'erreur au démarrage, vérifier
les logs sans les diffuser tels quels.

## Configuration dans Discord

Avec un compte disposant de Gérer le serveur :

```text
/config salon usage:counting salon:#counting
/config salon usage:words salon:#suite-de-mots
/config salon usage:logs salon:#journal-moka
/config salon usage:goblin salon:#distractions
/config role usage:counting_failure role:@Pas-doué
/config comptage amende:1000
/config suite_mots mode:free
```

Ces noms sont des exemples à créer sur le serveur de test. Ne pas activer deux
bots de counting ou d'XP dans le même salon pendant un essai de transition.
Les montants et délais sont dans `[rules]` du TOML ; ils demandent un redémarrage.
L'amende de counting peut être changée immédiatement par `/config comptage` ;
`amende:0` la désactive. Voir les [règles de counting](COUNTING.md).
Le rôle `counting_failure` est commun aux deux jeux : sa configuration bloque
l'écriture dans leurs deux salons pendant la pause. La durée par défaut est
d'une heure, y compris dans le laboratoire : [détails](GAME-PENALTIES.md).
Les commandes `/config` persistent les choix de salons/rôles/modules dans SQLite
et prennent le dessus sur le TOML pour ces choix.

Pour les menus : `/config role_choix`, puis `/roles publier`. Un nom de groupe
exclusif identique permet un seul choix parmi ses rôles (exemple : MP).

Pour les tickets : configurer `/config equipe_tickets`, éventuellement le
`ticket_category`, puis `/ticket publier`. Les administrateurs Discord peuvent
toujours voir les salons privés selon leurs droits ; Moka ne contourne pas cela.

Pour les vocaux : définir `voice_creator` et `voice_category`. La catégorie doit
déjà porter les droits d'accès souhaités. Moka ne donne pas au propriétaire de
salon des permissions de modération sur le serveur.

Le trombinoscope reste désactivé jusqu'au réglage de `trombi`, `trombi_review`,
`trombi_preaccess` et `trombi_access`. Le salon de validation doit être visible
uniquement par le staff. Les droits du pré-accès et de l'accès complet sont à
configurer explicitement sur les salons. Seuls les membres autorisés par ces
rôles peuvent y soumettre une image. Pas d'accès automatique par simple message.

## Nouveautés et mise à jour

`/taux` et `/duo` utilisent le module `rates`, actif par défaut, et rendent les
images localement avec Pillow. Les illustrations, polices et licences sont
embarquées ; aucun service IA ni clé supplémentaire n'est nécessaire.
`/compliment` et `/insulter` utilisent le module `fun` :
[comportement](AMBIANCE.md). Les commandes peuvent s'utiliser dans un salon de
distractions, sans configuration d'identifiant supplémentaire.

Pour passer de 0.1.0 à 0.2.0, suivre [le guide de mise à jour](../CHANGELOG.md).
Sauvegarder la base et resynchroniser une fois les commandes dans les seuls
serveurs autorisés. Les pauses actives gardent leur échéance.

## Docker

```sh
docker compose build
docker compose up -d
docker compose logs --tail=100 moka
```

Le conteneur ne publie aucun port entrant. Il utilise un utilisateur sans
privilèges, un système de fichiers applicatif en lecture seule et un volume
persistant `/data`. `.env` est lu au démarrage ; le TOML d'exemple est monté en
lecture seule et peut être remplacé par votre configuration.

**Le build Docker n'a pas été exécuté pendant cette livraison : le moteur
Docker local était arrêté.** Valider l'image avant tout hébergement durable.
