# Compliments et taquineries

`/compliment membre:@quelqu’un` adresse une phrase chaleureuse à un membre.
`/insulter membre:@quelqu’un` envoie une taquinerie légère. Sans cible, la
commande s'adresse à son auteur. Les applications ne sont pas des cibles.

Le catalogue contient **50 compliments et 50 taquineries originales**, dans
[`social_catalog.py`](../src/moka/social_catalog.py). Les blagues portent sur
le café, les biscuits, les onglets et les petits ratés du quotidien. Elles
évitent les attaques sur le physique, les identités et les sujets sensibles.
Il n'y a ni génération IA, ni analyse des conversations, ni classement des membres.

Exemples :

- « Tu es une bonne nouvelle avec un pseudo. »
- « Tu mérites une tasse toujours chaude et un câble qui se branche du premier coup. »
- « Tu ouvres le frigo comme s'il allait publier de nouvelles fonctionnalités. »
- « Tu as demandé à Moka de te taquiner. Ton sens de la délégation est impeccable. »

## Tirage et limites

Le hasard tire d’abord une édition : **La petite attention** (60 %),
**La perle du Comptoir** (30 %) ou **La pépite de Moka** (10 %). Le catalogue
de chaque catégorie est réparti en 30, 12 et 8 phrases. Dans cette édition,
il choisit parmi les phrases qui ne figurent pas dans les **cinq derniers
résultats de la même catégorie sur le serveur**, tous auteurs et cibles confondus.
Chaque catégorie a son propre historique, conservé après redémarrage. Il ne
contient que les phrases du catalogue, sans identifiant de cible.

Les deux commandes partagent un **délai de 15 secondes par auteur et serveur**.
Un reçu rejoué ne tire pas une nouvelle phrase et ne fait pas avancer
l'historique. Aucun cœur ni XP n'est crédité ou prélevé par ces commandes.

La réponse est publique dans le salon de la commande, mais ne déclenche aucun
ping. Une carte originale affiche la phrase, le pseudo et l’édition, avec une
description accessible et sans texte recopié au-dessus. Le staff peut désactiver
ces deux commandes avec `/config module nom:fun actif:false`.

## Étendre les phrases

Ajouter des textes dans `COMPLIMENTS` ou `TAUNTS`, en gardant des phrases courtes
et compréhensibles sans connaître la personne. Relire leur ton avant publication,
éviter les doublons et adapter le test de taille du catalogue. Le tirage et
l'historique sont gérés par `Community.social_message`.
