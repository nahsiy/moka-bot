# Le café des astres

L'horoscope fictif à quatre phrases est remplacé par un lecteur d'horoscope
publié, disponible depuis la version 0.4.0. Cela ne change ni l'XP ni les cœurs.

## Parcours

Le salon **✨・le-café-des-astres** se trouve dans **🍪 LA PAUSE CAFÉ**. Son panneau
illustré présente directement les douze signes dans une liste. **Mon signe
enregistré** retrouve le rôle facultatif choisi dans la rubrique Signe ; aucun
profil astrologique, anniversaire, lieu ou heure de naissance n'est demandé.
Sans signe unique, le membre est invité à utiliser la liste.

La lecture apparaît uniquement pour la personne qui consulte. Le menu commun
revient à son état initial après un choix. Le salon peut ainsi rester lisible,
sans accumuler une carte à chaque consultation. Les commandes `/horoscope`
avec signe facultatif fonctionnent dans ce salon ; ailleurs, Moka indique son lien.
Les droits d'accueil et le module Horoscope sont contrôlés à chaque consultation.

La carte contient :

- Le signe, la date de l'édition et un aperçu RSS limité à 25 mots.
- Les cinq notes effectivement publiées : humeur, amour, argent, travail, loisirs.
- Le nom et le lien de la source.
- **Lire l'horoscope complet**, vers le texte gratuit de l'éditeur, avec ses rubriques
  détaillées, dont amour en couple et célibataire. Le texte intégral reste sur ce site.

## Source et limites

Source choisie : **Mon Horoscope du Jour**, éditeur francophone spécialisé qui
présente ses astrologues et propose des flux RSS individuels par signe.
Ce choix donne une source éditoriale identifiable ; il ne classe pas les
horoscopes selon une précision prédictive démontrée. La lecture relève de
l'astrologie de divertissement.

- [Flux RSS officiels](https://www.mon-horoscope-du-jour.com/qui-sommes-nous/restez-connecte/rss.htm)
- [Équipe et charte éditoriale](https://www.mon-horoscope-du-jour.com/qui-sommes-nous/charte-de-qualite.htm)
- [Solution pour webmasters](https://www.mon-horoscope-du-jour.com/qui-sommes-nous/restez-connecte/webmaster-horoscope-gratuit/)

Le widget gratuit est prévu pour une intégration web avec son code conservé.
Il n'est pas transformé en copie du texte intégral dans Discord. Moka conserve
un court aperçu attribué et des notes factuelles, et renvoie vers l'éditeur.
Aucun abonnement ni clé d'API n'est nécessaire pour ce parcours. Une diffusion
intégrale sous licence demanderait un accord adapté avec un fournisseur.

## Date, cache et incidents

La date du flux **et** celle du titre de la page doivent correspondre au jour
courant en **Europe/Paris** et au signe demandé. Les notes sont extraites de la
page du même signe, jamais tirées au hasard. Si l'édition manque, si le format
change, si des notes manquent ou si le réseau échoue, Moka affiche une indisponibilité
avec le lien vers la source. Il ne présente ni une ancienne édition ni un texte
généré comme l'horoscope du jour.

Une seule édition par signe et serveur est mise en cache pour la journée : court
aperçu, notes, date et URL publique. Le nouveau jour remplace le cache précédent
à la première consultation. Les appels simultanés sont regroupés ; les échecs
sont temporisés une minute. Le cache persiste après redémarrage. Le panneau
actualise son repère de date au passage de minuit, sans mention générale ni nouveau
message quotidien. Il n'annonce pas que l'éditeur a déjà publié avant vérification.

Seuls les douze chemins HTTPS prévus sont interrogés ; aucune donnée Discord
n'est envoyée au fournisseur. Requêtes bornées en durée et taille, aucun suivi de
redirection, aucun cookie. La source est une dépendance externe dont la disponibilité
et le format peuvent évoluer.

## Installation et exploitation

La création du salon est explicite. Le lier par `channel:horoscope`, puis publier
le panneau avec `HoroscopeCog.refresh_home`. Son identifiant est conservé dans
`horoscope:message`. `horoscope:edition:<signe>` contient le cache limité de lecture.
Les membres validés lisent le salon et utilisent les commandes et composants ;
le staff et Moka peuvent écrire. Le salon reste masqué aux personnes en attente.
Les permissions doivent être relues après installation.

Après modification de la signature de `/horoscope`, synchroniser l'arbre dans
le seul serveur autorisé. Les composants sont persistants et restent utilisables
après redémarrage. Si le panneau a été envoyé avant une interruption de sa liaison
locale, Moka peut le retrouver sans republier un doublon.

Illustration originale générée avec l'outil intégré imagegen, avec la mascotte
du projet comme référence. Le prompt est conservé dans `assets/branding/PROMPTS.md`.
