# Présenter Moka en cinq minutes

Moka est un prototype Python que l'équipe peut reprendre, modifier et héberger.
La démo sert à choisir les fonctions utiles et recueillir des retours. Le nom,
le catalogue et l'équilibrage restent ajustables. Aucun choix de déploiement
dans une communauté n'est imposé par cette présentation.

## Sans compte Discord

Depuis une copie du dépôt, avec Python et uv :

```sh
uv sync --locked
uv run moka demo
```

Ce scénario hors ligne crée une base jetable, attribue des récompenses, dépose
100 cœurs en banque, achète et offre un café, avance le counting puis règle un
gobelin collectif. Il termine par une sauvegarde et un contrôle d'intégrité.
Il n'utilise aucun token ni donnée de membre. À titre de repère, l'exécution du
25 octobre 2026 donne 153 cœurs au portefeuille, 100 en banque, un café offert,
un counting à 2 et trois participants récompensés de 100 cœurs au gobelin.
Les champs `backup_created` et `database_integrity` valent `true`.

## Dans le serveur de test

Un responsable démarre Moka avec la configuration de laboratoire et le token
local. Voir [l'installation](INSTALLATION.md). Les visiteurs utilisent leur
compte Discord habituel ; ils n'ont besoin ni du token ni du Developer Portal.
Le bot tourne actuellement sur la machine de développement : organiser un
créneau avec cette machine allumée et connectée.

| Durée | Manipulation | À regarder |
| --- | --- | --- |
| 0–1 min | `/aide`, `/argent journalier`, `/profile` | Commandes françaises, réponse personnelle, portefeuille |
| 1–2 min | Bouton « Choisir mes rôles », choisir Lecteur | Attribution réelle du rôle, menu configurable |
| 2–3 min | `/ticket ouvrir` | Création d'un salon privé ; un deuxième compte ordinaire sert à vérifier la visibilité |
| 3–4 min | Dans counting : `1`, puis `3` | Réactions, remise à zéro et pénalité de 30 secondes dans le laboratoire |
| 4–5 min | Le staff lance `/animation lancer jeu:goblin`, puis bouton Participer | Compte à rebours de 30 secondes, inscription, règlement collectif |

Avec deux personnes, alterner les auteurs pour avancer dans counting et
suite-de-mots. La suite de mots utilise ici l'association libre : un mot inédit
par message, avec alternance des auteurs. L'ancien fonctionnement exact de la
communauté cible reste à confirmer.

Pour revoir la reprise d'un gobelin, le responsable peut redémarrer le processus
pendant les 30 secondes : le même message et son bouton restent utilisables.
Le résultat et le journal économique permettent de vérifier le paiement unique.

## Ce que cette démo établit

Les [captures](images/discord-demo.png) et le [compte rendu](VALIDATION.md)
documentent les parcours réellement essayés. Le [counting](images/discord-counting.png)
a aussi été vérifié avec attribution et expiration du rôle temporaire.

Une partie des fonctions reste à essayer dans Discord : XP vocal avec deux
humains éligibles, banque, autres jeux, vocaux temporaires, trombinoscope et
modération. Les tests locaux couvrent des invariants métier et certains
adaptateurs ; ils ne remplacent pas ces essais.

## Points à décider avec l'équipe

- Les modules à garder et ceux déjà assurés par un autre bot.
- Les règles des jeux, récompenses, catalogue et permissions souhaitées.
- Les responsables durables de l'application, du dépôt et de l'hébergement.

Le dépôt peut être repris ou forké sous licence MIT. Pour rendre l'installation
indépendante d'une personne, l'équipe doit également maîtriser l'application
Discord, les secrets, l'hébergement et les sauvegardes. Le dépôt public seul
ne garantit pas cette autonomie.
