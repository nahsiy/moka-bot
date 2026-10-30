# Les préférences du Comptoir

Moka gère les rôles à choisir directement dans Discord, sans second bot.
Le salon `#rôles` présente huit rubriques encadrées aux couleurs café.
Le menu déroulant est directement sous chaque rubrique. La sélection remplace
les préférences de cette rubrique ; sélectionner tous les rôles souhaités avant
de fermer la liste pour valider. La confirmation est privée et indique les rôles
retenus. Les rôles attribués restent visibles sur le profil Discord.

Le menu public est commun aux membres : il ne pré-coche pas leurs préférences
individuelles. Après une sélection ou un retrait, Moka remet la liste à vide
pour éviter de conserver des cases cochées devenues trompeuses. La confirmation
privée et le profil indiquent les rôles réellement actifs ; une liste vide ne
signifie donc pas que tous les rôles ont été retirés. `/roles choisir` reste
disponible pour revoir ses préférences dans un menu privé pré-coché.

| Rubrique | Choix | Règle |
| --- | --- | --- |
| Comment te présenter ? | 4 pronoms ou absence de précision | Un seul, facultatif |
| Rythme de présence | Matin, soir, horaires variables | Un seul, facultatif |
| Signe | 12 signes pour retrouver sa lecture au [café des astres](HOROSCOPE.md) | Un seul, facultatif ; aucune date de naissance |
| MP | Ouverts, sur demande, fermés | Un seul, facultatif |
| Entraide | Coup de main | Ajouter ou retirer |
| Région | 15 repères larges, dont outre-mer et autre coin du monde | Un seul, facultatif |
| Centres d'intérêt | 10 passions | Plusieurs choix possibles |
| Notifications | Annonces, animations, sessions de jeu | Plusieurs choix possibles |

Les 51 choix sont facultatifs. Aucune information de profil n'est déduite ou
attribuée à une personne pendant l'installation. Un rôle de MP exprime une
préférence : il ne bloque pas techniquement les messages. Les rôles de
notification permettent les mentions du staff ; ils ne créent pas à eux seuls
un envoi automatique de notifications.

## Les coins du Comptoir

Dans l'installation communautaire, les dix rôles de centres d'intérêt ouvrent
chacun un salon sous **🛋️ LES COINS DU COMPTOIR** : lecture, jeux vidéo, jeux de
société, films et séries, discussions musicales, cuisine, atelier créatif,
animaux, sport et tech. Les discussions musicales et le lecteur du Juke-box
gardent deux usages distincts.

Sans le rôle correspondant, le salon est masqué. Choisir le rôle le fait apparaître ;
le retirer le masque de nouveau. Le staff conserve un accès à ces espaces.
Les rôles de pronoms, signe, région, rythme et MP restent des informations de profil.

La configuration locale `role_channels` associe les identifiants de rôles aux
salons du même serveur. Les menus publics indiquent le salon associé et la
confirmation privée donne les liens des salons choisis. Aucun rôle n'est attribué
automatiquement par cette installation et les permissions globales des rôles
restent à zéro.

L'accueil reste obligatoire pour choisir des rôles. Le contrôle est renouvelé
après le verrou partagé avec l'accueil, pour éviter qu'une ancienne sélection
ne rétablisse l'accès pendant une remise en attente. Moka retire les rôles liés
à des salons lors d'un refus ou d'une remise en attente ; les rubriques sans accès
supplémentaire sont conservées. La maintenance reprend ce retrait si Discord échoue.
Il n'y a pas de suppression des messages lorsqu'un rôle est retiré, ni de filtre
d'historique selon la date de choix du rôle.

Pour une rubrique à choix unique, **Aucun choix** retire le rôle directement
à l'intérieur de la liste, sans bouton supplémentaire. **Tout retirer** reste
sous les listes à choix multiples (centres d'intérêt et notifications), pour
effacer cette rubrique en un clic. Valider une sélection vide permet aussi le
retrait. Sur un catalogue personnalisé de 25 rôles dans une rubrique unique,
le bouton reste disponible pour respecter la limite de 25 options Discord.
Le retrait et le rafraîchissement
de la liste sont confirmés en privé. Les autres rubriques, le titre du propriétaire, les rôles du
staff, les paliers XP et le rôle de pause sont préservés.

## Installer et publier

Le serveur doit être autorisé dans la configuration. Moka doit pouvoir gérer
les rôles et être placé au-dessus des rôles de préférences. Le staff disposant
d'un rôle de gestion de Moka ou de Gérer le serveur utilise :

```text
/roles installer
/roles publier
```

La première commande prépare le catalogue et réutilise les rôles existants
compatibles. La seconde publie dans le salon courant, ou actualise les panneaux
déjà publiés dans ce salon. Un message supprimé est recréé. L'installation et
la publication ne nécessitent pas de payer un service tiers.

Le salon peut être ouvert en lecture à tous les membres avec l'écriture réservée
au bot. Les choix fonctionnent directement avec les listes déroulantes, sans écrire dans ce salon.
Les réponses de configuration et les confirmations de sélection restent privées.

`/roles choisir` ouvre aussi un sélecteur privé des rubriques. Pour personnaliser
le catalogue, `/config role_choix` accepte une `rubrique`, un rôle et éventuellement
un `groupe_exclusif`. Une rubrique contient au plus 25 choix ; le panneau est
limité à 25 rubriques. Sans rubriques, l'ancien menu simple reste compatible.

## Reprise et contrôles

Les listes et boutons de retrait sont reconstruits après redémarrage grâce
à leur référence de rubrique. La liste autorisée, la rubrique, les permissions du rôle et le module
sont relus à la validation. Une fenêtre ancienne ne peut pas réattribuer un rôle
retiré du catalogue. Les demandes concurrentes d'un membre partagent un verrou.

Les rôles privilégiés, gérés par une intégration ou placés trop haut sont refusés.
Les rôles connus du staff des tickets, de progression, de pause et d'accès photo,
ainsi que Le Barista, sont exclus du choix libre. Les rôles de préférence n'ont
aucune permission globale ; seuls ceux liés explicitement à un salon ouvrent
cet espace, conformément à la configuration des Coins du Comptoir.
