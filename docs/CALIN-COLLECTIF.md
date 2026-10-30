# Le câlin collectif de Moka

Le staff utilise **/animation lancer**, puis choisit **🤗 Câlin collectif**, au
même endroit que la tournée de café. Chaque membre peut cliquer sur
**🤗 Je rejoins le câlin** : la participation est gratuite et facultative.

La carte affiche le temps restant, les participants, les places et le gain
courant par personne. La confirmation d'inscription est privée ; la carte
publique est actualisée sans doubler ses textes avec un second encart.
Aucun nom, avatar ou identifiant de membre ne figure dans l'illustration.

## Récompense

À la fermeture, chacun reçoit **200 cœurs × le nombre de participants** par
défaut. Par exemple, trois participants reçoivent **600 cœurs chacun**.
Les cœurs sont fictifs. Les plafonds de compte habituels s'appliquent et sont
signalés si un gain est réduit. Un double clic ou un redémarrage ne double
ni l'inscription ni le paiement.

Une seule personne peut participer ; aucun minimum de groupe n'est imposé.
Sans participant, aucun gain n'est versé et la carte devient **Les bras restent
ouverts**, avec un message léger invitant à une prochaine occasion. Aucun
reproche n'est adressé aux personnes qui ne souhaitent pas participer.
Le bouton disparaît à la clôture.

## Réglages

```toml
[features]
hug = true

[rules]
hug_seconds = 60
hug_max_players = 20
hug_reward = 200
```

Le laboratoire utilise 30 secondes ; les autres valeurs sont identiques.
Le module peut être désactivé avec **/config module nom:calin actif:false**.
La base et les paramètres d'un événement sont figés à son lancement.
Une désactivation ne supprime pas les récompenses déjà promises.

Un seul câlin peut être ouvert par serveur ; une tournée de café peut se
dérouler en parallèle. Les deux animations gardent leurs règles distinctes.
Aucun déclenchement automatique n'est ajouté. Le lancement nécessite Gérer
le serveur, contrôlé à l'exécution. L'accès communautaire est requis pour
participer lorsque l'accueil sur entretien est activé.

## Rendu et reprise

Carte de 1200 × 900 pixels, cadre bleu nuit, crème, turquoise et rose doux.
Moka porte son tablier et un coussin cœur : l'illustration originale est
embarquée avec le paquet. Le cadre, le compte à rebours et les textes sont
rendus localement. Si l'image échoue, un encart texte prend le relais avec
le bouton conservé. Voir [le prompt de création](../src/moka/assets/events/PROMPTS.md).

Les inscriptions, l'échéance et le règlement sont persistés dans SQLite.
La maintenance actualise les cartes environ toutes les dix secondes et reprend
les événements au redémarrage. Les boutons incluent une référence persistante
et vérifient le message, le serveur et le type d'événement.

Le principe du gain croissant a été observé dans le dépôt public
[bot_voltron](https://github.com/Silvers12/bot_voltron/blob/182d810deed1c25f3effc471dc4c1b8158168ae3/src/modules/events/grouphug.service.ts),
consulté le 28 octobre 2026. Implémentation Python, illustration et textes
originaux de Moka ; aucun fichier TypeScript ou visuel tiers n'est incorporé.
