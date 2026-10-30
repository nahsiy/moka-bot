# Le tableau du Barista

`/barista` ouvre un panneau privé de cinq minutes, réservé au propriétaire,
aux rôles de gestion de Moka configurés et à la permission Discord
**Gérer le serveur**. L’identité, le serveur, l’accueil et l'autorisation actuelle
sont vérifiés à chaque action, y compris après ouverture d’un formulaire.

## L'arrière-comptoir

L'installation communautaire dispose d'une catégorie privée **🔐 L’ARRIÈRE-COMPTOIR** :

- **🧭・tableau-de-bord** : encart permanent et boutons Réglages, Équipe, Diagnostic et Guide.
- **💬・coulisses** : coordination de l'équipe.
- **📋・journal-moka** : journal conservé, en lecture pour le staff.

Le rôle **☕ Baristas** donne la gestion de Moka via le réglage local
`moka:admin_roles`. Ses permissions Discord globales restent à zéro. Le rôle
**🫖 Équipe du Comptoir** est configuré pour l'accueil et les tickets.
Ces rôles sont exclus des rôles que les membres peuvent choisir eux-mêmes.

`/equipe` et le bouton **Qui gère Moka ?** affichent en privé les responsables,
l'équipe d'accueil, les personnes autorisées aux tickets et les permissions de
modération Discord. Les rôles et les membres sont relus depuis Discord à chaque
consultation ; les mentions n'envoient aucune notification. Le propriétaire et
les personnes ayant Gérer le serveur gardent leur accès, même sans rôle Moka.

Les commandes de gestion restent visibles sans exiger une permission Discord
globale ; la vérification de l'autorisation se fait à chaque exécution. Retirer le
rôle ou sa configuration retire cet accès. Le rôle ne donne pas les permissions
Discord Gérer les messages ou Exclure temporairement des membres : ces droits
restent indispensables aux nettoyages et aux timeouts correspondants.

## Les réglages privés

Le menu propose une vue d’ensemble, les fonctions actives et des rubriques par
usage. Un formulaire prérempli modifie les règles d’une rubrique ensemble :
aucune moitié de configuration n’est enregistrée si une valeur est invalide.
Les montants sont en cœurs, les durées indiquent leur unité et les probabilités
sont présentées en pourcentage.

La sélection des modules est une préparation : **Enregistrer les modules** applique
le choix. Une modification concurrente impose une actualisation. Le même contrôle
protège les formulaires de règles. Les réglages sont persistés par serveur dans
SQLite ; les valeurs TOML restent les valeurs de départ. Le plafond général de
monnaie reste dans TOML. Une baisse de capacité bancaire ne peut pas invalider
un solde existant.

Les événements déjà engagés gardent leur règlement initial et sont réglés jusqu’au
bout. Les récompenses quotidiennes et hebdomadaires gardent leurs périodes
respectives de 24 heures et 7 jours. Les nouvelles pauses ne modifient pas
l’échéance des sanctions déjà attribuées.

Les rubriques Salons et rôles, Accueil, Petites attentions et Juke-box expliquent
les réglages et les commandes spécialisées. Elles ne réécrivent pas les permissions
à l’ouverture du panneau. L’accueil et les droits du staff restent séparés des
fonctions ludiques.
