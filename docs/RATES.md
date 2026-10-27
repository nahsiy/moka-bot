# Taux du jour et duos illustrés

## Périmètre

Individuel : chance, choupitude, suspicion, criminalité fictive, loutritude,
flemme, sagesse et chaos. Duo : amour, amitié, complicité, rivalité, esprit
d'équipe et chaos à deux. Ces résultats sont aléatoires et ludiques : ils ne
mesurent pas les personnes ni leurs relations et ne dépendent pas des messages.

Référence de comportement :
[bot_voltron, module rates](https://github.com/Silvers12/bot_voltron/tree/c3d58dd5fd87cf08b3d088c771fb7309de464dfe/src/modules/rates),
MIT, copyright 2026 Silvers. Adaptation Python et commentaires propres à Moka ;
illustrations originales. Aucune conversation Discord n'est incluse dans le
dépôt, les prompts de génération ou le pack d'illustrations.

## Commandes

- `/taux type:choupitude` : ton taux ; `membre` permet de choisir quelqu'un.
- `/duo type:amitie membre:@quelqu’un` : votre duo ; `avec` permet de choisir
  le premier membre à ta place. Il faut deux membres différents.
- Le bot Moka peut participer aux jeux ; les autres applications ne sont pas
  des cibles. Une courte temporisation protège le rendu contre le spam.
- Le staff peut utiliser `/config module nom:rates actif:false` pour désactiver
  ces deux commandes. Les autres distractions gardent leur propre réglage.

Le pourcentage est dérivé de SHA-256 sur l'identifiant du serveur, celui du
membre (ou la paire triée), le type et la date à Paris. Le résultat va de 0 à
100 et reste identique pour les mêmes entrées toute la journée. Un duo dans
l'autre sens donne le même résultat ; deux dates peuvent fortuitement donner
le même pourcentage. Aucun historique ni profil psychologique n'est enregistré.

## Images et cartes

Les quatorze PNG transparents se trouvent dans `src/moka/assets/rates/` et
gardent les noms de fichiers attendus par Voltron : ils peuvent être copiés
dans son dossier `content/taux/`. Les originaux mesurent au moins 512 pixels.
Les prompts sont conservés dans le même dossier. Les polices Nunito (interface)
et Noto Sans (pseudos, y compris caractères grecs et cyrilliques) et leurs
licences OFL sont livrées dans `src/moka/assets/fonts/`. Noto Color Emoji
(v2.047, même dossier et licence OFL) assure le rendu local en couleur des
emojis des pseudos, dont les feuilles décoratives, les variantes de peau et les
séquences jointes. La troncature préserve ces séquences.

Chaque carte de 1 360 × 600 pixels contient l'avatar, le nom, le pourcentage,
une jauge, l'illustration qui se colore du bas vers le haut et un commentaire.
Les noms trop longs sont raccourcis. Un avatar indisponible est remplacé par
une initiale ; si la carte ne peut pas être produite, le texte du résultat
reste disponible dans Discord. La génération des cartes se fait localement
avec Pillow, sans appel IA ni envoi des avatars à ImageGen.

Les exemples de `assets/previews/` sont des rendus de contrôle avec des
pourcentages illustratifs ; ils ne sont pas des résultats de commandes réelles.
