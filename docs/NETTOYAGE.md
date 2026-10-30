# Revue avant la release 0.3.0

Revue du 30 octobre 2026, intégrée à la version 0.3.0 après 0.2.0. Le nettoyage
ne change pas les données du serveur.

## Changements retenus

| Zone | Nettoyage ou correction |
| --- | --- |
| Commandes Discord | Le bot et la commande `check` partagent le même chargement des cogs, pour éviter un écart entre validation et exécution. |
| Réglages | Une seule écriture JSON/SQL commune ; lecture des règles sur la connexion de la transaction métier, plutôt que par des connexions répétées. |
| Compatibilité | Les anciens réglages amende/corvée sont résolus dans un seul endroit ; les boutons déjà publiés et leurs identifiants sont conservés. |
| Jackpot | Les nouvelles animations gardent le tarif annoncé à leur ouverture, même si le staff modifie les règles avant une inscription. |
| Profil privé | Propriété et expiration réunies dans `profile_controls.py` ; un écran remplacé est arrêté, les commandes expirées sont retirées et un formulaire bancaire expiré refuse le prélèvement. |
| Historique | Huit mouvements par page et une seule ligne supplémentaire pour détecter la page suivante. |
| Documentation | README, matrice, guides d’installation/banque/ambiance et changelog distinguent la version publiée de la branche en préparation. |
| Conteneur | Deno officiel fixé par digest complète FFmpeg ; cache temporaire borné et job de vérification hors ligne du conteneur en CI. |

## Code ancien conservé volontairement

La recherche de blocs identiques et de fonctions apparemment isolées n’a pas
établi de module source entièrement mort à supprimer. Les méthodes décorées de
Discord sont appelées par le framework : leur absence d’appel Python explicite
n’indique pas du code mort.

`CategoryRoleButton`, les anciens panneaux, les clés historiques et le nom
interne `goblin` servent encore à reprendre les messages/configurations/événements
existants. Ils sont conservés pour éviter de casser ces états à la mise à jour.
Les preuves de recette, sauvegardes et environnements temporaires restent dans
les répertoires locaux ignorés par Git.

## Vérifications effectuées

- **430 tests sous Python 3.12 et 430 sous Python 3.13**, avec environnement
  distinct pour la seconde version ; Ruff, formatage et diff sans erreur.
- Configuration et sérialisation des 36 commandes racines, démo hors ligne et
  construction du wheel et de l’archive source.
- Installation du wheel dans un environnement neuf avec dépendances issues du
  verrou, puis exécution depuis un répertoire extérieur au dépôt : commandes,
  démo, intégrité SQLite et rendu de trois cartes.
- Contrôle des ressources embarquées : polices/licences, quatorze illustrations
  des taux et nouvelles images des petites attentions/Juke-box.
- Contrôle des fichiers distribués et des liens locaux de la documentation :
  aucun lien cassé, fichier de données, secret détecté, chemin personnel ou
  métadonnée EXIF détectée dans les PNG publics inspectés.

Les dépréciations signalées par discord.py sont conservées visibles ; elles ne
sont pas masquées pour obtenir un journal silencieux.

## Conteneur et limites de recette

Docker Desktop a été démarré pour lever le dernier point de vérification local.
Le build et l’exécution de l’image Linux ARM64 sont validés : utilisateur 10001,
racine en lecture seule, toutes les capacités retirées, privilèges supplémentaires
interdits et `/tmp` temporaire de 64 Mio. Commandes et démo passent ; trois cartes
sont rendues ; une source YouTube est résolue avec Deno 2.9.7 et cinq paquets Opus
sont décodés, sans conserver d’audio ni connecter de bot à Discord.

Le job conteneur de la CI reprend les contrôles hors ligne. Son exécution sur
le runner Linux AMD64 et une nouvelle recette vocale Discord complète restent
distinctes de cette vérification locale. Les essais Discord précédents sont
conservés dans [VALIDATION.md](VALIDATION.md).

Les changements et les consignes de mise à jour sont détaillés dans les
[notes de version 0.3.0](RELEASE-0.3.0.md).
