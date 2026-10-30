# Moka 0.4.0 — Le Comptoir s'organise

Cette version facilite l'accueil et le travail de l'équipe, ouvre les salons
selon les centres d'intérêt et remplace l'horoscope fictif par une lecture sourcée.
Elle conserve la monnaie fictive, l'humour bienveillant et les données existantes.

## Une équipe identifiable

- Tableau de bord permanent de l'arrière-comptoir, avec réglages, diagnostic et guide.
- Rôles de gestion de **Moka** distincts des privilèges globaux de Discord.
- `/equipe` montre qui gère le bot, l'accueil, les tickets et la modération native.
- Les personnes citées dans le journal apparaissent avec leur pseudo, sans notification.

Les rôles de gestion sont exclus des menus de préférences. Gérer Moka n'accorde
ni Administrateur, ni Gérer les messages, ni Exclure temporairement des membres.

## Accueil, confidentialité et rangement

- Une confirmation de lecture de la charte crée un nouveau message privé et
  mentionne les recruteurs autorisés. Le mot attendu n'est pas affiché.
- Les annonces d'arrivée natives doivent être coupées ou envoyées dans un salon
  réservé au staff avant activation de l'accueil.
- Après validation, l'entretien et son éventuel vocal sont rangés dans les
  premiers cafés terminés. Le membre garde la lecture, sans écriture.
- Un message de clôture indique les liens utiles et la date de suppression.
  **Les salons d'entretien validés sont supprimés après sept jours**, sans transcript.
  Les entretiens déjà validés reçoivent eux aussi une annonce et sept jours complets.
  Les refus et entretiens en attente ne sont pas concernés.
- Les échéances reprennent après redémarrage, même si le membre est parti.
  Un vocal occupé attend d'être vide ; la validation reste acquise.

Discord peut encore montrer un compte dans la liste d'un salon partagé, comme
la charte. Ce parcours ne crée pas de filtrage de l'historique selon la date d'arrivée.

## Des salons selon ses envies

Les préférences peuvent ouvrir des salons liés aux centres d'intérêt. Les listes
indiquent quel salon sera ouvert et les confirmations donnent ses liens.
Une fenêtre ancienne ne rétablit pas ces rôles pendant un retour à l'entretien :
sélection et accueil partagent le même verrou et revérifient les accès.

## Un coup de propre, avec confirmation

`/messages` prépare un aperçu privé : salon entier, avant une date, ancienneté,
depuis un message ou message unique. La confirmation expire après une minute,
appartient à son auteur et annonce une suppression irréversible.

Les nouveaux messages et panneaux interactifs de Moka sont conservés ; les
épinglés le sont par défaut. Lots récents et suppressions individuelles des anciens
sont séparés, avec contrôle des permissions et compte rendu de progression.
Ce nettoyage reste manuel et ne sauvegarde pas le contenu des échanges.

## Le café des astres

Un salon dédié avec illustration originale, douze signes et un raccourci vers
le signe facultatif enregistré. Chaque lecture privée donne un aperçu RSS daté,
les cinq notes publiées par **Mon Horoscope du Jour**, sa source et un bouton
vers le texte complet gratuit chez l'éditeur.

La date est vérifiée dans le flux et sur la page, en heure de Paris. Si la source
manque, Moka l'indique ; aucun texte inventé ou ancien n'est présenté comme l'édition du jour.

## Nettoyage du code

- Ouverture du panneau de réglages réunie pour `/barista` et le tableau de bord.
- Une clôture d'entretien est réconciliée une seule fois par passage de maintenance.
  Les personnes parties et les synchronisations échouées restent reprises.
- L'échec d'un module de maintenance n'empêche plus les autres de s'exécuter.
- Version du lecteur externe liée à celle du paquet, sans numéro recopié à maintenir.
- Compatibilités des anciens boutons et réglages conservées.

## Mettre à jour depuis 0.3.0

1. Lire la règle de conservation des entretiens ci-dessus et prévenir l'équipe.
2. Sauvegarder la base avec `moka backup`, puis arrêter l'ancienne instance.
3. Mettre à jour les sources et exécuter `uv sync --locked`, ou reconstruire l'image.
4. Conserver le TOML, le fichier d'environnement et le volume de données. Une table
   de suivi des clôtures est ajoutée sans réinitialiser les comptes ou décisions.
5. Resynchroniser une fois les commandes dans les seuls serveurs autorisés,
   puis remettre `MOKA_SYNC_COMMANDS=0`. La file musicale repart vide au redémarrage.
6. Vérifier les permissions et panneaux après reprise. Rôles administratifs,
   salons par intérêt et horoscope demandent une configuration explicite ;
   aucune installation communautaire générale n'est lancée à l'invitation du bot.

Le [guide VPS](DEPLOIEMENT-VPS.md) prépare une migration avec arrêt de l'ancienne
instance et copie cohérente de la base. Cette release ne déploie pas le bot à votre place.

## Vérifications et limites

- 524 tests sous Python 3.12 et sous Python 3.13 ; Ruff, formatage et 38 commandes validés.
- Wheel et archive source contrôlés, installation hors dépôt et rendu des cartes vérifiés.
- Conteneur Linux ARM64 testé sans token ni connexion Discord, avec ses protections
  et limites de ressources. La CI vérifie aussi le conteneur sur son runner Linux.
- Recettes Discord des panneaux, de l'accueil et de l'horoscope distinguées des
  simulations ; pas de donnée de membre dans les exemples ou fichiers distribués.

La recette complète d'arrivée avec un nouveau compte humain, les votes musicaux
à plusieurs et le Juke-box depuis le futur VPS restent à faire.

[Validation et limites](VALIDATION.md) · [Revue du code](NETTOYAGE-0.4.0.md) ·
[Installation](INSTALLATION.md) · [Changelog](../CHANGELOG.md)
