# Moka — plan de développement

Nom de travail, projet local indépendant du vault. Python 3.12+, discord.py,
SQLite, installation Docker ou uv. Aucun service Discord ou GitHub n'est créé
par le développement local.

## Objectif accepté

Remplacer les fonctions utiles de Sylhbot : progression écrit/vocal,
classements et récompenses ; monnaie fictive, banque, intérêts, cadeaux ;
paris, jackpot, vol, hack, tournée de Moka ; counting et association de mots ; animations ;
rôles, tickets et automatismes communautaires ; accueil sur entretien,
badges/titres, panneau privé de réglages et Juke-box partagé. Pas de gemmes ni de fabrication
de gemmes. Boutique en cœurs. Modules indépendants pour cohabiter avec DraftBot.

## Périmètre et références

- Implémentation originale : aucun ancien solde, niveau, inventaire, token ou
  fichier privé n'est récupéré automatiquement.
- La suite de mots utilise l'association d'idées libre par défaut ; le mode
  dernière lettre reste optionnel. Le bot contrôle la forme, les doublons et
  l'alternance, sans prétendre juger le lien sémantique.
- Le counting et les taux ludiques s'inspirent de comportements décrits dans
  un dépôt public MIT ; les références et crédits figurent dans les guides.
- Les montants, catalogue et règles sont modifiables, sans promesse de parité
  complète avec un ancien bot communautaire.
- Les essais réels et les parcours restant à tester sont documentés séparément
  dans `docs/VALIDATION.md`.

## Étapes et critères

1. **Fondations** : configuration stricte, autorisation de serveurs, SQLite
   transactionnel, migrations, sauvegarde cohérente, journal économique.
2. **Métier** : progression, banque/économie, jeux et récompenses atomiques,
   salons de jeux, reprise après redémarrage et protection des doubles clics.
3. **Discord** : commandes françaises, boutons persistants, événements
   écrit/vocal, tâches récurrentes, rôles temporaires, tickets, rôles à choisir,
   salons vocaux temporaires, validation de photos et journal de modération.
4. **Validation** : tests métier sur horloge/aléatoire injectés, courses,
   idempotence, isolement entre serveurs, chargement de l'arbre Discord hors
   ligne, lint, installation et CLI sans token.
5. **Livraison locale** : README honnête, matrice des fonctions, installation,
   permissions, exploitation et démonstration reproductible hors ligne.

## Garde-fous de conception

- Monnaie virtuelle, sans achat, conversion ou paiement réel.
- Application limitée aux serveurs explicitement autorisés ; pas de commande
  globale ni synchronisation implicite.
- Aucun droit Administrateur demandé. Validation de la hiérarchie des rôles,
  boutons limités à leur auteur quand nécessaire et contrôles au clic.
- Incréments monétaires atomiques, portefeuille non négatif, reçus uniques,
  tirages côté serveur ; jamais de solde décidé par le client Discord.
- Seuls les identifiants et états indispensables sont conservés. Pas de
  transcription vocale ni d'archivage des conversations/photos.
- Une base ne s'utilise qu'avec une instance du bot. Les reprises d'événements
  et expirations reposent sur des états persistés, pas seulement sur des timers.

## Hors de cette étape

Installation dans une communauté, dépenses et hébergement de production :
à décider explicitement par les responsables du serveur. Les tests locaux ne prouvent pas la
validation des permissions ni le rendu dans Discord.
