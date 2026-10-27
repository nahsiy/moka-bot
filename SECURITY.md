# Sécurité et signalement

Pour un incident, utiliser le contact privé du mainteneur du dépôt. Ne jamais
publier un token, une base, une photo de membre ou des logs contenant des secrets
dans une issue publique. Utiliser les moyens de contact privés proposés par
le mainteneur sur son profil GitHub, sans joindre de secret à une discussion
publique. Le dépôt public est [nahsiy/moka-bot](https://github.com/nahsiy/moka-bot).

Un token de bot donne un accès technique à l'application : conserver le token
dans l'environnement, limiter les comptes qui peuvent le lire, le régénérer en
cas d'exposition, puis mettre à jour le service. Les secrets et les sauvegardes
ne sont pas des ressources à publier avec le code.

Pas de permission Administrateur. Les rôles attribuables ne doivent porter ni
droits de modération ni administration. Le bot vérifie aussi la hiérarchie au
moment de l'attribution. La monnaie est fictive : aucun achat réel, dépôt réel,
conversion en euros, paiement ou gain réel n'est prévu.

Les tests locaux ne remplacent pas une revue des permissions et des salons sur
un serveur Discord de test. Voir docs/INSTALLATION.md et docs/VALIDATION.md.
