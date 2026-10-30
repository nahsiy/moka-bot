# Matrice des fonctions — 0.4.0

Cette matrice décrit la version 0.4.0 et distingue le code validé des parcours
Discord qui demandent encore une recette complète.

Les mentions « implémenté » décrivent du code, pas une recette Discord réussie.
Les tests locaux et les vérifications externes sont séparés dans VALIDATION.md.

| Fonction | État local | Écart ou choix explicite |
| --- | --- | --- |
| XP écrit | Implémenté et testé | 15 XP par message éligible, délai 60 s ; valeurs proposées |
| XP vocal | Adaptateur implémenté | Deux humains éligibles, non muets/non sourds, hors AFK ; pas de rattrapage après déconnexion ; aucun audio enregistré |
| Niveaux | Implémenté et testé | Niveau = partie entière de racine(XP/100), monnaie par niveau configurable |
| Classements | Implémenté et testé | Top 10, profils privés exclus |
| [Rôles XP](ROLES-XP.md) | Implémentés et testés | Palier exclusif au Comptoir, niveau zéro, attribution à l'arrivée, rattrapage automatique et /roles niveaux ; mode cumulatif historique conservé |
| Portefeuille et banque | Implémenté et testé | Profil privé illustré avec boutons déposer, retirer, acheter de la capacité et actualiser ; prix et prochain palier visibles ; plafonds et transferts atomiques ; [règles](BANQUE.md) |
| [Tableau du Barista](BARISTA.md) | Implémenté et testé localement ; espace staff disponible | Tableau de bord permanent privé, rôle de gestion du bot sans permission Discord globale, `/equipe` relu sur Discord ; panneau privé, modules préparés puis enregistrés, règles par serveur, formulaires atomiques, droits vérifiés au clic |
| [Profil et souvenirs](PROFIL-ET-SOUVENIRS.md) | Implémentés et testés localement | Navigation privée, historique, boutique, inventaire, 8 badges sans gain de monnaie et 4 titres décoratifs achetables |
| [Le Juke-box](JUKEBOX.md) | Implémenté et testé localement | Texte réservé commandes/lecteur et vocal sans micro, file et votes ; source YouTube et décodage Opus vérifiés ; recette Discord séparée dans VALIDATION.md |
| Récompenses | Implémenté et testé | Périodes glissantes de 24 h et 7 j, pas reset à minuit |
| Intérêts | Implémenté et testé | Réclamation manuelle toutes les 24 h, versée au portefeuille |
| Améliorations banque | Implémenté et testé | Capacité, taux borné et protection contre les vols |
| Paris | Implémenté et testé | 45 % de chance, retour ×2 mise incluse ; 10 % d'une perte alimentent la cagnotte |
| Jackpot | Implémenté et testé | Un ticket payé par personne ; tirage uniforme ; événement ouvert par staff ; cagnotte conservée sans participant |
| Vol | Implémenté et testé | Portefeuille uniquement, amende en cas d'échec, protection temporaire de la cible |
| Vol bancaire / rôles immunisés | À développer si retenu | Non inclus dans cette version |
| Hack | Implémenté et testé | Difficulté et préparation, boutons tenter/abandonner ; pas de simulation d'intrusion réelle |
| [Tournée de Moka](TOURNEE.md) | Implémentée et testée | Carte café illustrée, inscriptions, minimum/maximum/délai configurables, récompense collective ; apparition automatique désactivée par défaut |
| [Câlin collectif](CALIN-COLLECTIF.md) | Implémenté et testé | Carte illustrée, bouton persistant, participation gratuite et facultative ; 200 cœurs × nombre de participants pour chacun, sans apparition automatique |
| Counting | Implémenté et testé localement | Calculs arithmétiques, auteurs alternés ; paliers et bonus surprise (5 %, 10–50 cœurs), reçus persistants ; erreur ou texte → amende bornée au portefeuille et pile ou face (reprise ou retour à 1) ; record conservé ; [règles](COUNTING.md) |
| Rôle d'erreur | Implémenté et testé localement ; permissions relues sur Discord | ☕ Café renversé pendant 1 h, pause commune aux deux jeux, écriture interdite dans leurs deux salons, état stocké et retrait repris après redémarrage |
| [Corvée après modification](CORVEE.md) | Implémentée et testée localement | Nombre validé puis changé/invalide → rôle distinct, pause de tous les jeux, échéance persistée, `/debloquer` ; nombres et identifiants conservés 30 jours, sans texte brut |
| Suite de mots | Implémenté et testé | Association libre par défaut ou dernière lettre en option ; un mot inédit, auteurs alternés ; le lien sémantique reste apprécié par les joueurs |
| Compliments / insultes | Implémenté et testé localement | 50 compliments et 50 taquineries bienveillantes ; exclusion des 5 dernières phrases par catégorie et serveur, persistée ; délai commun de 15 s par auteur, sans ping ; cartes illustrées, éditions 60/30/10 ; pas de génération IA |
| [Horoscope](HOROSCOPE.md) | Implémenté et testé localement | Salon dédié, menu des 12 signes, signe enregistré facultatif ; aperçu RSS daté et cinq notes de Mon Horoscope du Jour, texte complet chez l'éditeur ; vérification du jour à Paris, aucun texte inventé en secours |
| Taux et duos | Implémenté et testé localement | 8 types solo, 6 en duo ; stables jusqu'à minuit à Paris et duos symétriques ; 14 illustrations originales, avatars et jauges ; aucun effet sur les cœurs ; [détails](RATES.md) |
| Boutique / cadeaux | Implémenté et testé | Achat et inventaire privés ; cadeau annoncé dans un encart public avec l'auteur, l'objet et le destinataire, sans ping ; catalogue de démonstration décoratif |
| Gemmes / fabrication | Exclu | Choix du projet |
| [Rôles à choisir](ROLES-A-CHOISIR.md) | Implémentés et testés | 8 rubriques et 51 choix, listes directes et confirmations privées, retrait en un clic, groupes exclusifs et composants persistants ; titres réservés exclus |
| [Accueil sur entretien](ACCUEIL.md) | Implémenté ; clôture des entretiens validés | Salon privé individuel, charte et notification staff, écrit/vocal facultatif, décision humaine ; entretien validé rangé et supprimé après sept jours, échéance persistée, sans transcript ; accès séparé des rôles XP |
| [Présence et pauses](PRESENCE.md) | Implémenté ; activation explicite | 21 jours sans échange observé, rôle sans permission, absences annoncées et bilan staff privé ; aucune exclusion automatique |
| Tickets | État/concurrence testés, adaptateur implémenté | Un ouvert par personne, staff explicitement configuré ; fermer conserve le salon, pas de suppression ni transcript |
| Vocaux temporaires | Adaptateur implémenté | Création par vocal d'entrée, nom et limite ; droits de catégorie conservés, suppression des salons suivis et vides |
| Trombinoscope | État testé, adaptateur implémenté | Niveau/pré-accès, photo originale validée par staff, aucun fichier téléchargé ; module désactivé par défaut |
| Modération | Adaptateur implémenté ; nettoyage confirmé disponible | Timeout/retrait ; [nettoyage manuel](NETTOYAGE-MESSAGES.md) avec aperçu privé et confirmation, épinglés/panneaux protégés, lots récents et suppression individuelle des anciens ; pas de ban/kick/anti-raid automatique |
| Sauvegardes | Sauvegarde SQLite testée | Locale quotidienne au plus, contrôlée chaque heure ; copie hors machine à organiser |
| Reprise après redémarrage | Métier testé | Événements réglés une fois, boutons persistants et notifications finales réessayées |

## Reste nécessaire avant un usage communautaire

1. Recette dans un serveur Discord de test avec deux comptes humains.
2. Valider les règles proposées et les automatismes utiles avec les membres.
3. Choisir le catalogue, les textes, les montants et le nom définitif.
4. Ajuster les interfaces de jeux si l'on veut retrouver exactement leur
   ergonomie précédente (menus de vol, déroulé du hack, notifications).
5. Captures réelles, revue du dépôt, puis publication explicitement demandée.

Aucun ancien solde, niveau ou inventaire n'est récupéré automatiquement.
