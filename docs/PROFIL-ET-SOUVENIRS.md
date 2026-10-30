# Mon profil et mes souvenirs

`/profile` ouvre une carte privée illustrée. Déposer, retirer, agrandir la banque
et actualiser restent directement accessibles. Les boutons Quotidienne et
Hebdomadaire indiquent le gain ou le délai avant la prochaine réclamation.

Le menu **Explorer mon profil** donne accès aux mouvements de cœurs (huit par page),
à la boutique, à l’inventaire, aux badges, aux titres et à un guide. Chaque page
permet de revenir à Mon profil. Les pages privées et leurs boutons appartiennent
à leur auteur et à leur serveur ; un autre membre n’y effectue aucune opération.
`/boutique` et `/inventaire` utilisent les mêmes pages.

## Acheter et offrir

La boutique affiche le portefeuille, les prix et la distinction entre objets et
titres. Choisir un article prépare l’achat ; le bouton **Acheter · prix** prélève
les cœurs. Les achats sont atomiques et les interactions rejouées ne débitent pas
deux fois. Un titre déjà acquis ne peut pas être racheté.

Les objets se donnent avec `/offrir`, qui annonce publiquement le cadeau sans
notification de mention. Les achats restent privés. Les titres sont personnels,
décoratifs, sans rôle ni permission Discord.

| Titre | Prix en cœurs fictifs |
| --- | ---: |
| La pause douceur | 500 |
| Gardien des biscuits | 800 |
| Esprit espresso | 1 200 |
| Au rythme des vinyles | 1 200 |

Dans Mes titres, le menu équipe un titre acquis ou retire le titre. Le changement
est gratuit ; le titre apparaît sur la carte de profil, selon sa confidentialité.

## Badges

Huit souvenirs s’obtiennent à son rythme : premier message comptabilisé,
100 messages, 60 minutes de vocal éligible, 500 cœurs en banque, premier objet
offert, première tournée ou premier câlin terminé, niveau 3 et 25 bons nombres.

La page indique chaque condition et sa progression. Les badges sont attribués une
seule fois à partir de faits déjà présents en base, quand la collection est
consultée. Ils restent acquis et ne distribuent pas de monnaie supplémentaire.
Aucune série quotidienne obligatoire. La progression du counting utilise les
reçus des bonnes réponses, pas la trace de contrôle des modifications limitée à
30 jours.

Le module `collection` active badges et titres. Les données de collection et le
titre équipé figurent dans `/mes_donnees` et sont supprimés par `/oublier`, selon
les mêmes protections que le compte. Aucun prénom ni avatar réel dans les exemples
publics du dépôt.

Les écrans privés retirent leurs commandes après trois minutes sans action.
Un écran remplacé cède la main au nouveau ; sa minuterie ne le désactive pas.
Un formulaire bancaire expiré invite à rouvrir `/profile` avant tout prélèvement.
