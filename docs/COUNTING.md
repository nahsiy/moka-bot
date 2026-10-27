# Counting de Moka

## Règles

Les membres comptent à tour de rôle, à partir de 1. Un nombre ou un calcul dont
le résultat est le prochain entier attendu reçoit ✅. Exemples : `2+3`,
`3×2`, `(10-2)/2`, `2^3`. Opérations : `+`, `-`, `*` / `×` / `x`,
`/` / `÷` / `:`, puissances `^` et parenthèses. Les calculs suivent la priorité
arithmétique usuelle, sans arrondi : `-2^2` vaut -4, `(1/3)*3` vaut 1.

Un mauvais nombre, un calcul invalide ou non entier, du texte, ou deux messages
consécutifs de la même personne constituent une erreur et reçoivent ❌.

À chaque erreur :

- une amende de **1 000 cœurs par défaut**, réglable, est prélevée sur le
  portefeuille seulement, sans jamais le rendre négatif ;
- Moka tire à pile ou face : **Face** remet le compteur à zéro (prochain nombre
  1), **Pile** conserve la série ; les chances sont de 50 % chacune ;
- l'auteur précédent est libéré : chacun peut proposer le prochain nombre ;
- le rôle **Pas-doué** bloque les deux jeux pendant **une heure** lorsqu'il
  est configuré : [pause commune](GAME-PENALTIES.md).

Le record et les récompenses de paliers de Moka sont conservés. Si l'économie
est désactivée, aucune amende ni récompense n'est versée. Les bots et webhooks
ne participent pas. Moka ne modifie pas rétroactivement les anciens messages.

## Configuration

`/config comptage` affiche le prochain nombre, le record et l'amende.
`/config comptage amende:1000` règle l'amende ; `amende:0` la désactive.
La permission Gérer le serveur est vérifiée à chaque exécution. Le TOML
`[rules].counting_fine` fournit le défaut, remplacé par le réglage Discord.
Le salon et le rôle utilisent toujours `/config salon usage:counting` et
`/config role usage:counting_failure` ; mettre `counting_failure_seconds=0`
désactive les nouvelles attributions de ce rôle.
Ce réglage s'applique au counting et à la suite de mots ; la durée par défaut
est de 3 600 secondes, y compris dans le laboratoire.

## Fiabilité

L'évaluateur accepte au plus 60 caractères hors espaces, 240 caractères bruts
et des exposants entiers de 0 à 20. Les numérateurs et dénominateurs
intermédiaires sont limités à 10¹². Il refuse appels, noms, attributs et tout
autre élément Python ; aucun `eval` ni `exec`.

SQLite sérialise les tentatives : compteur, amende, journal et résultat du
tirage sont validés ensemble. Rejouer un message ne prélève pas une seconde
amende et ne relance pas la pièce, même après un redémarrage. Les messages
plus anciens que le dernier message traité sont ignorés. Les réactions et
réponses Discord ne constituent pas la preuve d'une transaction économique.

## Origine

Règles inspirées du counting de Silvers dans
[bot_voltron](https://github.com/Silvers12/bot_voltron/tree/d5220229c5efd9a1dddbd2ce05069b857dd8f550/src/modules/counting),
publié sous licence MIT, copyright 2026 Silvers. Adaptation originale en Python
pour le moteur transactionnel de Moka ; aucun code TypeScript intégré.
