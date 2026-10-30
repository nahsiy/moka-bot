# Revue avant la release 0.4.0

Revue du 30 octobre 2026 sur les changements depuis la version 0.3.0.

## Corrections et regroupements

| Zone | Résultat |
| --- | --- |
| Réglages | `/barista` et le tableau de bord utilisent la même ouverture privée et le même contrôle d'autorisation ; le bloc dupliqué est retiré. |
| Maintenance des accueils | Une clôture déjà reprise pendant la synchronisation du membre n'est pas retraitée dans le même passage. Les départs et synchronisations échouées conservent leur reprise dédiée. |
| Maintenance du serveur | Chaque module a son contrôle d'erreur : un échec d'accueil, de communauté ou de présence n'empêche plus les autres tâches de passer. |
| Horoscope | Lecteur séparé des commandes générales, cache quotidien borné par signe, requêtes simultanées regroupées et version HTTP issue du paquet. |
| Périmètres | Modération native et gestion de Moka restent distinctes. Les rôles de gestion sont protégés des préférences. |
| Distribution | Version alignée entre paquet, code et documentation ; guide VPS sans configuration réelle ; ressources du conteneur bornées. |

La recherche AST des corps de fonctions identiques non triviaux a trouvé le
doublon d'ouverture des réglages, maintenant regroupé. La revue n'a pas établi
de module source entièrement mort à supprimer. Les callbacks décorés sont
appelés par Discord ; l'absence d'appel Python direct ne suffit pas à les supprimer.

## Compatibilités conservées

Les anciens boutons de rôles, panneaux persistants, clés de configuration et
identifiants internes d'animations restent nécessaires aux messages et données
existants. Ils sont conservés. Les preuves, bases, sauvegardes et environnements
de test restent dans les répertoires locaux ignorés par Git.

La nouvelle table de clôture est additive. Une mise à jour ne remet à zéro ni
les comptes ni les décisions. La rétention de sept jours des entretiens validés
est annoncée explicitement dans les notes de version, y compris pour les entretiens
déjà validés avant mise à jour.

## Vérification

Les **524 tests passent sous Python 3.12 et 3.13**, dont huit régressions ajoutées
pendant cette revue : indépendance des six tâches de maintenance et traitement
unique des clôtures avec reprise des synchronisations échouées.

Ruff, formatage, sérialisation des 38 commandes et démo SQLite hors ligne sont
vérifiés. Les paquets sont contrôlés pour les ressources, liens locaux et données
privées. Les essais de conteneur et les parcours Discord sont distingués dans
[VALIDATION.md](VALIDATION.md), avec leurs limites réelles.

Les alertes de dépréciation des dépendances restent visibles. Cette revue n'est
pas une affirmation de performance chiffrée globale ni un audit de sécurité exhaustif.

[Notes 0.4.0](RELEASE-0.4.0.md) · [Préparation VPS](DEPLOIEMENT-VPS.md)
