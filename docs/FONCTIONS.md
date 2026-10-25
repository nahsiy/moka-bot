# Matrice des fonctions — 0.1.0

Les mentions « implémenté » décrivent du code, pas une recette Discord réussie.
Les tests locaux et les vérifications externes sont séparés dans VALIDATION.md.

| Fonction | État local | Écart ou choix explicite |
| --- | --- | --- |
| XP écrit | Implémenté et testé | 15 XP par message éligible, délai 60 s ; valeurs proposées |
| XP vocal | Adaptateur implémenté | Deux humains éligibles, non muets/non sourds, hors AFK ; pas de rattrapage après déconnexion ; aucun audio enregistré |
| Niveaux | Implémenté et testé | Niveau = partie entière de racine(XP/100), monnaie par niveau configurable |
| Classements | Implémenté et testé | Top 10, profils privés exclus |
| Récompenses de rôle | Adaptateur implémenté | Rôles cumulatifs, rattrapage par /roles niveaux ; permissions vérifiées |
| Portefeuille et banque | Implémenté et testé | Plafonds et transferts atomiques ; montants entiers |
| Récompenses | Implémenté et testé | Périodes glissantes de 24 h et 7 j, pas reset à minuit |
| Intérêts | Implémenté et testé | Réclamation manuelle toutes les 24 h, versée au portefeuille |
| Améliorations banque | Implémenté et testé | Capacité, taux borné et protection contre les vols |
| Paris | Implémenté et testé | 45 % de chance, retour ×2 mise incluse ; 10 % d'une perte alimentent la cagnotte |
| Jackpot | Implémenté et testé | Un ticket payé par personne ; tirage uniforme ; événement ouvert par staff ; cagnotte conservée sans participant |
| Vol | Implémenté et testé | Portefeuille uniquement, amende en cas d'échec, protection temporaire de la cible |
| Vol bancaire / rôles immunisés | À développer si retenu | Ancien guide les évoque, réglage effectif du QG non vérifié |
| Hack | Implémenté et testé | Difficulté et préparation, boutons tenter/abandonner ; pas de simulation d'intrusion réelle |
| Gobelin | Implémenté et testé | Minimum/maximum/délai configurables, récompense en cœurs ; apparition automatique désactivée par défaut |
| Counting | Implémenté et testé | Alterner les auteurs ; erreur de nombre → retour à 1 ; texte ordinaire ignoré ; record conservé |
| Rôle d'erreur | Implémenté et testé avec adaptateur simulé | 3 h par défaut, état stocké et retrait repris après redémarrage |
| Suite de mots | Implémenté et testé | Association libre ou dernière lettre ; un mot inédit, auteurs alternés ; anciennes règles encore à confirmer |
| Compliments / insultes | Implémenté | Textes originaux courts, taquineries légères ; pas de génération IA ni messages de l'ancien auteur |
| Horoscope | Implémenté | Divertissement déterministe par signe/jour UTC, sans prétention scientifique |
| Boutique / cadeaux | Implémenté et testé | Catalogue de démonstration décoratif ; catalogue communautaire final à construire |
| Gemmes / fabrication | Exclu | Demande de Chris |
| Rôles à choisir | Adaptateur implémenté, sécurité testée | Menu ≤25 rôles, groupes exclusifs ; pas de rôle staff sélectionnable |
| Tickets | État/concurrence testés, adaptateur implémenté | Un ouvert par personne, staff explicitement configuré ; fermer conserve le salon, pas de suppression ni transcript |
| Vocaux temporaires | Adaptateur implémenté | Création par vocal d'entrée, nom et limite ; droits de catégorie conservés, suppression des salons suivis et vides |
| Trombinoscope | État testé, adaptateur implémenté | Niveau/pré-accès, photo originale validée par staff, aucun fichier téléchargé ; module désactivé par défaut |
| Modération | Adaptateur implémenté | Timeout/retrait de timeout uniquement ; pas de ban/kick/purge/anti-raid automatique |
| Sauvegardes | Sauvegarde SQLite testée | Locale quotidienne au plus, contrôlée chaque heure ; copie hors machine à organiser |
| Reprise après redémarrage | Métier testé | Événements réglés une fois, boutons persistants et notifications finales réessayées |

## Reste nécessaire avant une proposition au QG

1. Recette dans un serveur Discord de test avec deux comptes humains.
2. Vérifier les anciennes règles de suite de mots et les automatismes manquants.
3. Choisir le catalogue, les textes, les montants et le nom définitif.
4. Ajuster les interfaces de jeux si l'on veut retrouver exactement leur
   ergonomie précédente (menus de vol, déroulé du hack, notifications).
5. Captures réelles, revue du dépôt, puis publication explicitement demandée.

Aucun ancien solde, niveau ou inventaire n'est récupéré automatiquement.
