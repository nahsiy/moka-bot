# De corvée de vaisselle

Une modification qui change la valeur d'un nombre **déjà accepté** dans le
counting, ou rend ce message invalide, déclenche le rôle **🧽 De corvée de
vaisselle** et une pause de tous les jeux pendant **une heure**, réglable.

Une autre expression donnant le même entier, des espaces ou des zéros initiaux
ne sont pas sanctionnés. Un message refusé dès le départ relève de **☕ Café
renversé**, limité au counting et à l'association de mots. Le contrôle est
syntaxique : Moka constate la modification, sans prétendre connaître l'intention.

## Conséquences

- Le nombre validé reste la référence. La série et le record continuent ; aucune
  nouvelle amende, aucun retrait d'XP ni annulation des gains antérieurs.
- Pause des paris, vols, hacks, jackpot, counting, association de mots, taux/duos,
  et inscriptions aux tournées/câlins collectifs. Les anciens boutons vérifient
  aussi la pause, même après redémarrage ou avec un compte administrateur.
- Les échanges ordinaires, le vocal, la banque, les cadeaux, la boutique,
  l'aide, les données et les commandes staff restent disponibles. La personne
  conserve ses accès aux salons. Le rôle interdit seulement l'écriture dans les
  deux salons de jeux textuels ; les autres refus sont contrôlés par Moka.
- Un hack peut être abandonné. Les événements auxquels la personne était déjà
  inscrite sont réglés normalement, pour conserver les engagements antérieurs.
- Une tentative de rejouer les mêmes événements Discord ou une nouvelle édition
  du même message ne renouvelle pas la peine. Un autre message validé puis
  altéré peut déclencher une nouvelle corvée. Remettre la bonne valeur ne lève
  pas automatiquement une sanction déjà enregistrée.

Une annonce encadrée indique le nombre validé, le lien vers le message, le
prochain nombre et l'échéance. Aucune copie du texte modifié, aucun ping forcé,
aucun changement de pseudo ni barreaux sur l'avatar. En cas d'envoi Discord
échoué, la maintenance réessaie ; la peine et les gains ne sont pas rejoués.
Une annonce déjà envoyée est recherchée parmi les trente derniers messages
pour reprendre un envoi interrompu avant confirmation en base. Cette recherche
bornée réduit les doublons, sans garantir leur impossibilité après une longue
interruption et beaucoup de nouveaux messages.

## Staff et configuration

`/debloquer membre` lève les deux types de pauses et retire leurs rôles. Le
contrôle Gérer le serveur est effectué à l'exécution ; confirmation privée et
journal staff. Un retrait Discord échoué est repris par la maintenance. Une
ancienne demande de déblocage rejouée n'annule pas une sanction plus récente.
Retirer le rôle à la main ne suffit pas : la sanction métier reste persistée.

`/config role usage:counting_cheat role:…` configure un rôle dédié, sans permission
et sous Moka. Il doit être distinct des rôles d'accueil, XP, staff, présence,
photo et Café renversé. Il est exclu des préférences personnelles.

`/config corvee minutes:60` règle les nouvelles peines ; zéro les désactive.
Le réglage initial est `[rules].counting_cheat_seconds = 3600`. Sans rôle
configuré, aucune nouvelle corvée n'est appliquée. Modifier ou désactiver ces
réglages ne lève pas les corvées déjà enregistrées. Un rôle supprimé ou retiré
à la main n'arrête pas non plus l'échéance métier.

Les nouveaux serveurs doivent configurer ce rôle explicitement. L'installation
ne demande aucun droit Administrateur. Une panne Discord peut retarder
l'affichage ou le retrait du rôle ; les autorisations de jeu restent contrôlées
en base, jusqu'à l'échéance exacte ou au déblocage.

## Données et couverture

Le suivi commence avec les nouvelles validations après installation : aucun
historique de messages n'est importé. `counting_validations` conserve serveur,
salon, identifiant du message et de l'auteur, entier validé, date, état de
sanction et d'annonce pendant **30 jours**. Aucun contenu de conversation ni
expression d'origine n'est conservé. Les traces sont purgées au fil des
validations et par le contrôle horaire des sauvegardes. Le contrôle fonctionne
sans cache du message ; il ne voit pas les modifications survenues pendant une
coupure de Moka ni au-delà de la rétention. Supprimer un message ne déclenche
pas cette sanction.

`/mes_donnees` inclut les traces ; `/oublier` les efface après les opérations et
rôles actifs, comme les autres données de jeu. Les annonces Discord et les
sauvegardes ont leur propre conservation. Ne pas partager leurs preuves privées.

Inspiration fonctionnelle : contrôle des éditions du counting dans
[Silvers12/bot_voltron](https://github.com/Silvers12/bot_voltron/blob/fe1e67d4fdd2c63959efffcffaba33e18b7d340f/src/modules/counting/counting.service.ts).
Implémentation Python originale : la prison et ses textes/visuels ne sont pas
repris. Moka garde sa direction café et ne conserve pas le texte brut du message.
