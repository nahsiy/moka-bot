# Moka — plan de développement

Nom de travail, projet local indépendant du vault. Python 3.12+, discord.py,
SQLite, installation Docker ou uv. Aucun service Discord ou GitHub n'est créé
par le développement local.

## Objectif accepté

Remplacer les fonctions utiles de Sylhbot : progression écrit/vocal,
classements et récompenses ; monnaie fictive, banque, intérêts, cadeaux ;
paris, jackpot, vol, hack, gobelin ; counting et suite de mots ; animations ;
rôles, tickets et automatismes communautaires. Pas de gemmes ni de fabrication
de gemmes. Boutique en cœurs. Modules indépendants pour cohabiter avec DraftBot.

## Preuves et inconnues

- Ancien guide de Sylhaance, 22 octobre 2026, lu dans distractions : XP,
  économie/banque, vol, hack, profils et boutique.
- Messages du bot : gobelin collectif (minimum de participants et délai),
  jackpot, compliments/taquineries et horoscope.
- Capture fournie par Chris : counting repris par DraftBot ; rôle d'erreur
  durant trois heures. Rôles/tickets DraftBot également observés.
- Chris confirme que le reste de distractions marchait bien et demande la
  suite de mots. Ses règles exactes restent inconnues : prévoir des modes
  explicitement configurés, sans prétendre reproduire des règles non vérifiées.
- Modération interne, salons temporaires et trombinoscope : périmètre à
  confronter au staff. Les mécanismes livrés doivent être documentés comme
  une proposition, et non comme une reproduction exacte de l'ancien bot.
- Aucun code, texte, graphique, token ni base de l'ancien bot disponible.
  Réimplémentation originale, aucune promesse de récupération des soldes.

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

Installation dans le QG, dépenses/hébergement de production, publication
GitHub, envoi à la fondatrice ou à Alf, nom définitif et validation en vrai
serveur : à faire explicitement ensuite. Les tests locaux ne prouvent pas la
validation des permissions ni le rendu dans Discord.
