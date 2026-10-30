# Le premier café — accueil sur entretien

L'accueil est facultatif et désactivé par défaut. Son installation est explicite,
limitée au serveur autorisé ; une simple invitation de Moka ne change aucun accès.

## Parcours

- Une personne arrive : Moka lui attribue **🛎️ En attente** et crée un salon
  **☕・premier-café-pseudo**, privé pour elle, le staff configuré et Moka.
- Elle peut lire **📜・la-charte-du-comptoir**, séparé et en lecture seule.
  Les autres salons restent invisibles, même si Moka est momentanément arrêté.
- **J'ai lu la charte** ouvre une fenêtre privée demandant le mot glissé dans la
  charte. Une mauvaise réponse invite à relire ; délai de cinq secondes entre
  essais. Une bonne réponse affiche **Lecture confirmée** dans l'entretien et crée
  un nouveau message **✅ Charte confirmée** dans ce salon privé. Les recruteurs
  qui peuvent lire le salon sont mentionnés individuellement, sans mention globale
  ni affichage du mot attendu. La notification ne valide pas l'entrée au serveur.
- L'échange se fait à l'écrit. **Je préfère un vocal** prévient dans le panneau ;
  le staff ouvre ensuite un vocal privé. Moka n'enregistre pas l'audio.
- Le staff valide humainement l'arrivée après l'entretien et la lecture.
  Moka donne **☕ Membre du Comptoir**, retire l'attente et ouvre la communauté.
  Le premier rôle XP peut alors être attribué. Aucun XP ni cœur n'est gagné
  pendant l'attente, y compris dans le vocal d'entretien.
- Après validation, l'entretien et son éventuel vocal sont rangés dans
  **📁 Les premiers cafés · terminés**. Chaque salon garde ses permissions
  individuelles : membre accueilli et staff uniquement ; le membre peut relire
  le texte mais plus y écrire. Un nouveau message de clôture donne les liens
  configurés vers le général et les rôles, ainsi que la date exacte de suppression.
- Les salons liés à cet entretien sont **supprimés automatiquement après sept
  jours**, sans transcript ni export des échanges. La validation reste acquise.
  Le journal staff conserve une trace de la décision et de la suppression.
- Le refus demande une confirmation : accès fermés et entretien en lecture seule,
  sans expulsion ni bannissement automatique. **/accueil reprendre**, dans ce
  salon, permet au staff de rouvrir un accueil refusé. **/accueil etat** donne le suivi.

Le Comptoir est réservé aux **21 ans et plus**. La confirmation est déclarative,
avec échange humain : aucune pièce d'identité ni date de naissance n'est demandée.
Trouver le mot ne prouve pas que toute la charte est comprise ; le staff reste
responsable de l'entretien et de la décision. Une validation déjà donnée est
conservée en cas de départ puis retour sur le même serveur.

## Accès et installation

Le module `admission_setup.prepare_admission` prépare l'installation avec un mot
choisi par l'exploitant. Il vérifie les permissions, les rôles staff et les
exceptions de visibilité avant de fermer les accès. Les identifiants sont dans
les réglages locaux SQLite, jamais dans les exemples publics.

Avant installation, sauvegarder la base et la configuration des salons/rôles.
Les annonces d'arrivée automatiques de Discord doivent être désactivées ou envoyées
dans le journal réservé au staff. Un salon commun, même masqué à `@everyone` mais
ouvert aux membres validés, dévoilerait les candidatures avant l'entretien.
La préparation refuse cette configuration. Ce réglage natif reste effectif lorsque
Moka est arrêté ; il se modifie dans les paramètres du serveur, sans donner Gérer
le serveur au bot. Rediriger ces annonces vers le journal ne crée pas d'annonce
publique lors de la validation : seul le staff voit l'arrivée automatique.

Tous les membres humains déjà présents reçoivent leur accès avant la fermeture.
Le plan initial de visibilité et la liste de ces membres sont conservés pour
reprendre une préparation interrompue sans approuver de nouveaux arrivants.
Après préparation, relire les permissions effectives pour un candidat sans rôle,
avec les rôles XP/préférences, un membre validé et le staff. Activer seulement
ensuite `admission:enabled` ; redémarrer Moka avec synchronisation des commandes
si l'arbre a changé.

Le bot doit avoir **Gérer les salons**, **Gérer les rôles**, les accès de lecture et
d'écriture nécessaires, et un rôle supérieur aux deux rôles d'accueil. Aucun
Administrateur n'est demandé. Les recruteurs sont le propriétaire, les personnes
avec Gérer le serveur ou celles portant un rôle explicitement listé dans
`admission:staff_roles`. Cela n'accorde aucun privilège Discord global au rôle staff.
Les boutons revérifient le membre staff par l'API au moment de la décision.

Le rôle d'accès est distinct des niveaux et exclu des menus de préférences.
Les catégories et chaque salon existant sont fermés à `@everyone` ; seuls les
anciens salons publics sont ouverts au rôle membre. Les salons staff restent
privés. Les refus d'écriture de jeux sont conservés. Moka garde ses accès.
Un rôle XP ou une préférence seule ne doit jamais autoriser Voir le salon.

Créer les nouveaux salons communautaires sous une catégorie déjà protégée et
vérifier leur synchronisation. Une permission nominative ou un autre rôle
accordant Voir le salon peut contourner un refus de rôle : revoir les accès après
une modification manuelle. Le propriétaire et les administrateurs contournent les
permissions Discord ; leur vue ne constitue pas un test de nouvel arrivant.
Voir la [documentation officielle des permissions](https://docs.discord.com/developers/topics/permissions).

## Reprise, confidentialité et limites

### Fin des entretiens validés

La clôture concerne uniquement les accueils `approved` disposant d'un salon suivi.
Les refus et entretiens en attente ne sont ni déplacés ni supprimés par cette règle.
Lors du premier chargement, un entretien déjà validé bénéficie lui aussi d'une
annonce et d'un délai complet de sept jours ; la date de sa décision passée ne
déclenche jamais une suppression immédiate.

L'échéance et l'accusé du message sont persistés dans `admission_closures`, sans
contenu d'entretien. Après une interruption entre l'envoi Discord et son accusé,
Moka retrouve son annonce horodatée au lieu de la répéter. Un échec d'envoi
reporte le début des sept jours jusqu'à l'annonce réussie. La maintenance reprend
les étapes inachevées, même après le départ du membre ; si Moka était arrêté à
l'échéance, la suppression reprend à son retour. Un vocal encore occupé attend
d'être vide : personne n'est déconnecté par la suppression automatique.

Avant suppression, Moka vérifie le statut validé, les identifiants liés, le type
des salons, leurs permissions privées et le marqueur propre au salon textuel.
Un refus d'accès Discord ou une liaison incohérente suspend l'opération et laisse
les références disponibles pour une reprise ; aucun autre salon n'est sélectionné.
Une suppression manuelle déjà faite est reconnue. Après clôture complète,
les références des salons et reçus devenus inutiles sont retirées, tout en gardant
la décision et les métadonnées minimales d'accueil.

La catégorie terminée est créée à la première clôture et liée par
`admission:closed_category`. Elle reste fermée aux membres ordinaires ; chaque
entretien conserve une permission nominative, sans synchronisation avec la
catégorie. Les réglages optionnels `admission:general_channel` et
`admission:roles_channel` désignent les salons des deux liens de bienvenue.
Seuls les liens effectivement visibles par le membre sont affichés.

### État minimal de l'accueil

Une ligne SQLite par personne et serveur conserve les états pending/approved/refused,
la confirmation de lecture, la demande de vocal, la décision et les identifiants
techniques nécessaires. Le mot est haché dans les réglages ; il reste volontairement
lisible dans la charte. Il ne s'agit pas d'un secret de sécurité.

Les créations sont sérialisées par candidat. Un salon déjà créé peut être retrouvé
après interruption grâce à son marqueur privé. Les décisions sont persistées avant
l'application des rôles ; la maintenance réessaie toutes les minutes après une
indisponibilité Discord et au redémarrage. Les boutons restent utilisables après
redémarrage. Il n'y a qu'une instance de Moka par base.

La notification de lecture conserve un reçu minimal (date de confirmation,
identifiants du salon et du message), sans mot de lecture ni contenu d'entretien.
Une répétition de la validation ne renvoie pas d'alerte. Après un échec Discord,
la maintenance reprend l'envoi ; après un envoi réussi suivi d'une interruption
avant son accusé local, Moka recherche la notification datée déjà présente.
Une nouvelle lecture après réouverture d'un entretien refusé produit une nouvelle
alerte. Les accueils déjà clôturés ne déclenchent pas de rattrapage automatique.

Moka n'exporte ni ne transcrit les conversations d'accueil. Le journal staff
mentionne seulement la décision et son auteur. Les échanges restent cependant
hébergés **dans Discord** : ils ne sont pas supprimés automatiquement. Après une
décision, le salon et le vocal sont conservés privés, avec lecture seule pour la
personne ; le vocal n'est plus accessible pour s'y connecter. Le staff gère leur
conservation. Aucun effacement de salon ni copie de transcript n'est automatique.

Ce parcours ne rend pas un compte totalement invisible sur Discord : des personnes
qui partagent un salon lisible, comme la charte, peuvent encore le voir dans sa liste
de membres. La confidentialité des annonces et des entretiens est distincte de cette
présence dans l'interface Discord.

**/mes_donnees** inclut l'état d'accueil personnel et reste disponible pendant
l'attente. **/oublier** efface les données de jeu selon ses contrôles habituels,
mais conserve l'état minimal d'accueil nécessaire aux accès tant que la personne
reste membre. Ces commandes ne modifient pas les conversations hébergées par Discord.

Les tests hors ligne vérifient le métier, les permissions calculées par discord.py,
les contrôles de boutons et la reprise. Une vraie arrivée avec un second compte
reste une recette distincte ; une simulation ne remplace pas cet essai.
