# Un coup de propre

Évolution après la publication de la 0.3.0. Commandes manuelles réservées aux
personnes ayant **Gérer les messages** dans le salon visé. La permission doit
aussi être accordée à Moka, avec **Voir le salon** et **Lire l'historique**.
Le module `moderation` doit être actif.

| Commande | Sélection |
| --- | --- |
| `/messages vider` | Messages du salon au moment de la demande |
| `/messages avant date:2026-01-01` | Messages antérieurs au 1er janvier à minuit, heure de Paris |
| `/messages anciens jours:7` | Messages de plus de sept jours au moment de la demande |
| `/messages depuis identifiant:…` | Message indiqué et suivants, jusqu'à la demande |
| `/messages supprimer identifiant:…` | Un message précis |

`salon` est facultatif : le salon courant est utilisé par défaut. Les messages
épinglés sont conservés sauf avec `garder_epingles:false`. Les panneaux Moka avec
des composants (rôles, accueil, lecteur, événements…) restent toujours protégés.
Leurs messages de conversation ordinaires sont concernés comme ceux des humains.

Chaque commande présente un **aperçu privé** : salon, périmètre, nombre de messages,
dates extrêmes et protections. **Supprimer définitivement** confirme ; **Annuler**
ne change rien. L'aperçu expire après une minute et ne survit pas à un redémarrage.
La sélection est figée : les messages arrivés après la commande ne sont pas inclus.

La suppression concerne tout le monde, pièces jointes comprises, sans restauration
par Moka. Aucun transcript ni copie des contenus n'est créé. L'aperçu ne garde que
des identifiants en mémoire ; le journal staff conserve l'auteur, le salon et le
bilan, sans texte des conversations. Ni les soldes, ni l'XP, ni le compteur de jeu
ne sont remis à zéro en supprimant des messages.

Les permissions et les rôles sont rechargés depuis Discord au lancement et par lot
pendant le nettoyage. Un seul nettoyage s'exécute à la fois dans chaque salon ;
les doubles clics sont consommés une fois. Les épingles et panneaux sont relus
avant suppression, par pages d'historique plutôt que par une requête pour chaque
message. Seuls les identifiants de la sélection confirmée peuvent être supprimés.
Le compteur affiche les messages vérifiés sur le total et se met à jour pendant
la vérification, avant même la première suppression. Les messages déjà disparus
sont comptés séparément.

Selon [l'API Discord](https://docs.discord.com/developers/resources/message#bulk-delete-messages),
les lots contiennent de 2 à 100 messages de moins de deux semaines. Moka prend
une marge d'un jour et traite les autres individuellement. Les messages anciens
restent donc supprimables, mais plus lentement. Une opération examine au plus
5 000 messages ; au-delà elle refuse **avant toute suppression**. Choisir une
période plus courte. Après dix minutes de travail ou un refus Discord, Moka arrête
et annonce le résultat partiel ; relancer un aperçu pour continuer.

Ce nettoyage est ponctuel : aucun effacement planifié ni filtre d'historique selon
la date d'arrivée des membres n'est activé. Les fils de discussion ne sont pas
parcourus avec leur salon parent et ne sont pas acceptés comme cible.

Le comportement a été étudié dans le dépôt MIT
[Silvers12/bot_voltron](https://github.com/Silvers12/bot_voltron/blob/fe1e67d4fdd2c63959efffcffaba33e18b7d340f/src/modules/moderation/messages.admin.ts).
L'implémentation Python et les textes sont propres à Moka.

Validation du 30 octobre 2026 : tests hors ligne des sélections, dates, permissions,
confirmations, lots et échecs partiels. Sur Discord, suppression par lot de deux
messages jetables du bot, puis aperçu privé d'un troisième message et annulation
vérifiée. Les droits de Moka et l'enregistrement des cinq sous-commandes ont été
relus. Aucune conversation de membres n'a été supprimée pendant cette recette.
