# Profil et banque

`/profile` ouvre une grande carte privée : niveau, progression dans le niveau,
portefeuille, banque, capacité et prix du prochain palier. `/argent consulter`
ouvre le même écran. Les réponses ne sont visibles que par la personne qui
utilise la commande. Le réglage `/confidentialite` reste indépendant et contrôle
la consultation de son profil par les autres membres.

## Boutons du profil

- **Déposer** : saisir le montant à déplacer du portefeuille vers la banque.
- **Retirer** : saisir le montant à remettre dans le portefeuille.
- **Agrandir · prix** : acheter le prochain palier de capacité au prix indiqué,
  prélevé sur le portefeuille. Le bouton est désactivé si les fonds sont insuffisants.
- **Actualiser** : relire les soldes et renouveler les boutons.

Les actions mettent la carte à jour. Un bouton indisponible est grisé : par
exemple, aucun retrait si la banque est vide, aucun dépôt si elle est pleine.
Les boutons sont retirés après trois minutes sans action ; rouvrir `/profile`
les renouvelle. Actualiser remplace l’ancien écran et son échéance.
Consulter le profil d'un autre membre n'affiche aucun bouton bancaire.

## Pourquoi une capacité de 1 000 cœurs ?

C'est la **capacité initiale proposée par le jeu**, pas une limite de Discord.
Les défauts sont :

| Palier | Capacité | Prix pour atteindre ce palier |
| --- | --- | --- |
| 0 | 1 000 | Départ |
| 1 | 2 000 | 500 |
| 2 | 3 000 | 1 000 |
| 3 | 4 000 | 1 500 |
| 20 | 21 000 | 10 000 |

La capacité vaut `bank_capacity × (palier + 1)`. Le prochain achat coûte
`bank_upgrade_cost × (palier + 1)` ; les prix sont payés à chaque achat, pas
seulement la différence entre deux paliers. Les règles se configurent dans le
TOML pour les valeurs de départ ; `/barista` les ajuste ensuite par serveur,
sans redémarrage. Le bouton du profil achète seulement le prochain palier : il
ne modifie pas les règles du serveur.

Les commandes restent disponibles : `/banque deposer montant`,
`/banque retirer montant`, `/banque ameliorer amelioration:capacity` et
`/banque interets`. Les améliorations d'intérêts et de protection restent dans
`/banque ameliorer` ; le bouton du profil augmente uniquement la capacité.

## Garanties

Les contrôles d'auteur, de serveur et d'activation des modules sont refaits
au clic et à la validation du formulaire. Les mouvements conservent le total
des cœurs et respectent les soldes et la capacité. Les reçus empêchent un même
formulaire ou achat d'être exécuté deux fois. Un ancien profil ne permet pas
d'acheter un palier suivant au prix affiché pour le précédent : il faut actualiser.

Le rendu est local, avec description accessible et repli texte si l'image
échoue. Aucun avatar humain ni donnée de membre n'est embarqué dans le dépôt.
