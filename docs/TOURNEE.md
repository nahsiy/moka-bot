# La tournée de Moka

Une pause café collective : Moka prépare le plateau, les membres réservent une
tasse et chacun reçoit des cœurs si le groupe minimum est réuni à la fermeture.
La participation est gratuite. Les cœurs sont une monnaie fictive.

## Jouer

Le staff lance `/animation lancer` et choisit **☕ Tournée de Moka** dans le salon
souhaité. Les membres cliquent sur **☕ Je prends un café**. Une confirmation
privée accompagne leur inscription ; la grande carte publique affiche le temps
restant, les cafés réservés, les places, l'objectif et la récompense.

La jauge suit l'objectif minimum, pas le remplissage de toutes les places.
Le temps est actualisé à chaque inscription et environ toutes les dix secondes.
La description accessible donne aussi l'heure de fermeture à Paris.

À la fermeture, la même carte devient **La tournée est servie !** si le groupe
est réuni. Sinon, elle propose une prochaine pause, sans récompense. Le bouton
disparaît. Les plafonds économiques habituels restent applicables.

## Réglages et compatibilité

Les montants et les règles du jeu collectif sont conservés. Le laboratoire
utilise 30 secondes, un minimum de 1 personne, 20 places et 100 cœurs par personne.
Les apparitions automatiques restent désactivées par défaut.

Pour conserver les configurations et événements existants, les clés TOML
`goblin_seconds`, `goblin_min_players`, `goblin_max_players`, `goblin_reward` et
`goblin_interval_minutes`, le module et l'usage de salon `goblin` restent valides.
`/config module nom:tournee` accepte aussi le nouveau nom. Aucun renommage des
données économiques ou de l'historique n'est nécessaire.

Les inscriptions et échéances sont persistées. Après redémarrage, le bouton
fonctionne et une personne ne reçoit qu'une récompense. Les anciens boutons
d'événements restent reconnus. Un événement dont le message est supprimé peut
être réannoncé par la maintenance, sans nouveau paiement.

## Illustration

La mascotte originale est une tasse de café robot en tablier, avec un plateau
de cinq cafés. Le PNG transparent est embarqué dans le paquet ; le cadre et
les textes sont rendus localement. Aucun nom, avatar humain ou identifiant de
membre n'apparaît sur cette carte. Si le rendu échoue, Moka conserve un encart
texte avec le bouton. Voir [le prompt de création](../src/moka/assets/events/PROMPTS.md).
