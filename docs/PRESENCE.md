# Présence et pauses du Comptoir

Ce repère sert à prendre des nouvelles. Il ne mesure ni l'attachement au serveur,
ni la qualité des personnes. Aucun bannissement, retrait d'accès, amende, perte
d'XP ou message privé automatique.

## Règles

- Après **21 jours** sans participation observée : rôle **🌙 En pause café**,
  sans permission. Le staff décide humainement de la suite.
- À l'activation, chaque membre admis commence avec 21 jours de grâce. Un nouvel
  admis dispose du même délai. Aucun ancien message n'est parcouru ni importé.
- Écrit : deux auteurs humains alternent dans le même salon autorisé à moins de
  30 minutes d'intervalle. Chacun écrit au moins quatre mots et vingt lettres.
  Le second message qualifie les deux personnes. Les salutations trop courtes,
  liens seuls, mentions, commandes, bots et webhooks ne comptent pas.
- Les salons de counting et d'association de mots sont toujours exclus, même
  s'ils figurent par erreur dans la liste autorisée. Les commandes et clics de
  jeux ne valident aucune présence. Une conversation ordinaire dans le salon
  de distractions peut compter.
- Vocal : cinq minutes continues observées avec au moins deux humains admis,
  hors AFK, ni muets ni sourds ni supprimés de scène. Les changements d'état
  interrompent le compteur individuel. Un retard de boucle ou une déconnexion
  ne produit aucun rattrapage. Ce suivi fonctionne indépendamment du module XP.
- Un échange qualifiant retire le rôle ; en cas d'échec Discord, la maintenance
  réessaie chaque minute. Les dates restent persistées après redémarrage.

Ce filtre syntaxique est imparfait : une conversation courte peut lui échapper,
une phrase artificielle peut le satisfaire. Il ne prétend pas comprendre les
messages. Moka ne voit pas les échanges pendant son arrêt ; le staff doit tenir
compte de ces périodes. La grâce reste une durée calendaire, pas un chronomètre
du temps de disponibilité du bot.

## Absences annoncées

`/absence jours:14` enregistre uniquement la date de fin prévue (1 à 365 jours,
7 par défaut). Aucun motif n'est demandé. La confirmation est privée ; le staff
voit la date dans son bilan. Aucun rôle d'inactivité pendant cette absence.
À son expiration, un nouveau délai de 21 jours commence.

`/retour` termine une absence et ouvre 21 jours de grâce, sans inventer une
participation écrite ou vocale. Un échange qualifiant termine aussi l'absence.
Les commandes agissent seulement sur leur auteur admis.

## Bilan et permissions

Un encart est maintenu dans le journal privé du staff, sans notifications.
`/activite bilan page:1` fournit une réponse privée, vingt membres par page.
Le contrôle staff est renouvelé à l'exécution avec le membre relu sur Discord :
propriétaire, Gérer le serveur ou rôle explicitement configuré pour l'accueil
ou les tickets. Aucun droit d'administration supplémentaire n'est accordé.

Le rôle doit être dédié, non géré, sans permission, sous le rôle de Moka et
distinct des rôles d'accès, XP, staff, sanction, photo et propriétaire. Il est
exclu des préférences que les membres peuvent choisir. Son groupe dans la liste
des membres dépend du rôle affiché séparément le plus haut ; un titre staff ou
un palier XP de priorité supérieure peut continuer à y apparaître.

Le journal est vérifié avant chaque publication : aucun rôle non staff ni
exception individuelle non staff ne doit pouvoir le lire. Les administrateurs
et bots sont les exceptions techniques habituelles. Si ces droits changent,
Moka refuse de publier et tente de retirer son encart existant, puis réessaie
après correction des droits. Il ne modifie pas les permissions du salon.

## Installation explicite

Le suivi est **désactivé par défaut**, sans création de rôle ni de salon à
l'arrivée de Moka. Un exploitant configure en SQLite, via `Service.set_setting`,
les clés suivantes pour le serveur autorisé :

| Clé | Valeur |
| --- | --- |
| `presence:role` | Identifiant du rôle dédié, zéro permission |
| `presence:channels` | Liste des salons de discussion autorisés ; les fils ne sont pas inclus implicitement |
| `presence:journal` | Identifiant d'un salon strictement réservé au staff |
| `presence:enabled` | `true` après validation des trois paramètres |

Synchroniser les commandes uniquement dans les serveurs autorisés après
installation. Ne pas activer le suivi avec un rôle existant utilisé ailleurs.
Pour désactiver, retirer d'abord le rôle de pause des membres puis passer
`presence:enabled` à `false` ; aucune suppression de rôle n'est implicite.

## Données et limites de recette

La table `presence` contient serveur, membre, début du délai, dernière
participation, type écrit/vocal et fin d'absence. Aucun texte, empreinte de
message, motif médical/personnel ni enregistrement audio n'est stocké. Les
candidats d'échange et durées vocales intermédiaires restent en mémoire et sont
vidés à la déconnexion.

`/mes_donnees` inclut ces dates ; `/oublier` les efface avec le profil. Une activité
ou un contrôle ultérieur peut créer un nouveau suivi avec une grâce complète,
comme pour un nouvel admis. Un départ du serveur efface le suivi de présence.
Les sauvegardes et l'encart déjà publié sur Discord suivent leur propre
rétention ; l'encart est actualisé au prochain contrôle.

Les tests sur horloge injectée vérifient le passage à 21 jours ; ils ne prouvent
pas une observation réelle de trois semaines. La recette Discord et les tests
simulés doivent rester distingués dans VALIDATION.md.
