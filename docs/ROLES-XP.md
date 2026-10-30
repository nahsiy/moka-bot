# Les habitués du Comptoir

Chaque membre humain reçoit un seul rôle de progression : le plus haut palier
atteint. Les XP déjà acquis sont conservés. Le titre du propriétaire **☕ Le Barista**,
les rôles du staff, les préférences et **☕ Café renversé** restent indépendants.

| Niveau | XP cumulés | Rôle | Couleur |
| --- | --- | --- | --- |
| 0 | 0 | 🌱 Petit grain | Crème `#FFF4DB` |
| 3 | 900 | ☕ Première gorgée | Caramel `#BC8053` |
| 7 | 4 900 | 🪑 Habitué du comptoir | Cuivré `#D89562` |
| 12 | 14 400 | 🍪 Complice de la pause | Menthe `#72D2BE` |
| 20 | 40 000 | 🫶 Pilier du comptoir | Turquoise `#36B8B2` |
| 30 | 90 000 | ✨ Légende du comptoir | Doré `#E7C37E` |

Les rôles sont décoratifs, sans permissions supplémentaires, et affichés séparément
dans la liste des membres. Les seuils utilisent la progression existante :
`niveau = floor(sqrt(XP / 100))`. Cette installation ne modifie ni les gains d'XP,
ni les cœurs, ni les soldes.

## Attribution et reprise

Les membres déjà présents sont rattrapés. Les nouveaux arrivants reçoivent leur
premier rôle ; les activités éligibles actualisent le palier. Une vérification
automatique chaque minute répare les attributions manquantes, y compris après
redémarrage ou échec Discord. `/roles niveaux` permet aussi de demander la mise
à jour immédiatement.

Le nouveau palier est ajouté avant le retrait des anciens. En cas d'échec,
la maintenance réessaie ; un retrait refusé peut laisser temporairement deux
paliers. Seuls les rôles présents dans la configuration de progression sont
remplacés : les autres rôles sont conservés. L'état du membre et son niveau
sont relus sous un verrou commun aux demandes concurrentes.

## Configuration

Le staff associe chaque rôle avec `/config niveau_role niveau:0 role:…`, puis
les autres seuils. Le niveau zéro est accepté. Les rôles doivent être sous Moka,
non gérés par une intégration et dépourvus de permissions privilégiées.

Le Comptoir utilise `level_role_mode = exclusive` dans les réglages persistés ;
les associations sont dans `level_rewards`. Les installations existantes gardent
le mode cumulatif par défaut pour conserver leur comportement. La vérification
automatique s'applique uniquement aux serveurs autorisés dont le module de rôles
est actif, et ignore les bots. Un rôle absent de Discord est ignoré.
