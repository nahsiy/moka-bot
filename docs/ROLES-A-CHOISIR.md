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
| Signe | 12 signes pour les horoscopes fictifs | Un seul, facultatif |
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
de Gérer le serveur utilise :

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
ainsi que Le Barista, sont exclus du choix libre. Aucun rôle de préférence ne
donne de permission supplémentaire dans le catalogue fourni.
