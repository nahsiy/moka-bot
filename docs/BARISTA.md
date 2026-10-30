# Le tableau du Barista

`/barista` ouvre un panneau privé de cinq minutes, réservé à la permission
**Gérer le serveur**. L’identité, le serveur, l’accueil et la permission actuelle
sont vérifiés à chaque action, y compris après ouverture d’un formulaire.

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
