# Identité visuelle de Moka

Moka est un petit compagnon café : chaleureux, lisible et joueur. Chaque nouvelle
réponse possède un cadre, avec un titre court qui indique son sujet. Une action
simple reste compacte ; une carte de profil ou un personnage a davantage de place.

## Palette et présentation

| Usage | Couleur |
| --- | --- |
| Accent des encarts Discord | Café `#BC8053` |
| Fond des cartes illustrées | Bleu nuit `#12232E` |
| Texte des cartes | Crème `#FFF4DB` |
| Texte secondaire | Gris bleuté `#A4B9C1` |
| Profil et progression | Menthe `#72D2BE` |

Les taux gardent leur accent thématique : rose pour la choupitude, vert pour
la chance, etc. Les polices et emojis des images restent embarqués et rendus
localement. Les textes Discord utilisent la typographie native du client.

## Réponses textuelles

Les achats, récompenses, opérations bancaires, cadeaux, confirmations, erreurs,
messages de jeux et outils du staff utilisent le même constructeur `card`.

- Un titre avec une icône et un sujet précis : « Achat confirmé », « Tes rôles ».
- Une phrase directe qui donne le résultat ; mettre les montants utiles en gras.
- Pas de répétition intégrale du titre dans le corps, ni d'identifiant technique
  ajouté à une nouvelle confirmation pour la décorer.
- Les pièces jointes de données personnelles restent privées, accompagnées
  d'un encart explicatif. Les erreurs restent privées dans les interactions.
- Les références des événements existants restent conservées pour leurs boutons
  et leur reprise après redémarrage.

## Cartes illustrées

Les taux, duos, profils et tournées ont **leur cadre intégré dans l'image**. Ils sont
envoyés directement en pièce jointe pour garder une grande taille d'affichage.
Leur contenu n'est pas recopié au-dessus dans une légende ou un second encart.
La description accessible contient les informations utiles aux lecteurs d'écran.

Une opération bancaire depuis le profil affiche sa confirmation dans la carte
mise à jour et dans sa description accessible. Si le rendu échoue, le repli
texte utilise un encart avec les mêmes informations et les mêmes boutons.

La tournée utilise Moka en tablier, avec un plateau de cafés : fond bleu nuit,
titres dorés, progression menthe et texte crème. Sa carte de 1 200 × 900 affiche
les inscriptions, l'objectif et les cœurs ; elle est actualisée à chaque inscription
et environ toutes les dix secondes jusqu'à la fermeture. Son bouton conserve
la référence technique sans l'afficher dans l'image. Le résultat remplace la
carte d'attente et retire le bouton.

## Visibilité et exemples publics

Le style ne détermine pas la visibilité : achats, banque et profil restent
privés ; les cadeaux et résultats publics gardent leur visibilité publique.
Les notifications de mention restent contrôlées par le bot.

Les exemples du dépôt et des publications utilisent des noms fictifs et la
mascotte. Les captures du client, avatars humains, identifiants réels, secrets
et données de membres restent hors des fichiers distribués.

## Petites attentions et musique

Trois nouvelles illustrations originales prolongent la mascotte en céramique et
son tablier : Moka offre un cœur, taquine avec le dernier biscuit, et présente un
juke-box ancien en bois et laiton. Les PNG conservent leur transparence.

Les compliments et taquineries ont une carte de 1 200 × 820, le lecteur musical
une carte de 1 200 × 900. Le cadre, le texte et les emojis sont composés localement ;
les illustrations générées n’embarquent pas de texte. Les descriptions accessibles
reprennent les informations utiles sans légende visuelle en doublon.

Les éditions des petites attentions sont lisibles par leur nom et leur couleur :
La petite attention (menthe, 60 %), La perle du Comptoir (rose, 30 %), La pépite de
Moka (doré, 10 %). Chaque catégorie de 50 phrases est répartie en 30/12/8 phrases ;
les cinq dernières sont évitées, y compris dans l’édition la plus rare. Aucun gain,
aucune moquerie agressive et aucune mention notifiée.

Le Juke-box utilise des boutons natifs : Ajouter un morceau ouvre directement le
formulaire ; Pause et Reprendre sont séparés ; Passer / voter explique le contrôle
collectif ; Voir la file ouvre le détail privé. Les achats montrent le prix avant
de prélever des cœurs. Les identifiants techniques n’habillent aucune carte.
