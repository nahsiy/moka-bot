# Moka — consignes du projet

Compagnon Discord Python, initialement développé pour proposer une alternative
communautaire à Sylhbot. Réimplémentation originale ; ne pas récupérer de code,
base, textes ou images de l'ancien développeur sans autorisation.

- Lire PLAN.md et docs/FONCTIONS.md pour le périmètre et les inconnues.
- Python 3.12, dépendances verrouillées avec uv.lock.
- Métier dans base/economy/games/community ; Discord dans bot/cogs/discord_ui.
- Pas de gemmes ni fabrication de gemmes. Monnaie fictive uniquement.
- Tester les invariants économiques, l'isolement des serveurs, les doubles clics,
  la reprise des échéances et les permissions des callbacks.
- Une commande staff doit vérifier ses permissions à l'exécution ; la visibilité
  du menu Discord n'est pas un contrôle suffisant.
- Aucune connexion Discord, synchronisation, installation au QG, publication
  GitHub ou dépense d'hébergement sans instruction explicite correspondante.
- Le token se configure localement dans l'environnement ; ne jamais l'afficher.
- Ne jamais committer .env, bases, sauvegardes ou données de membres.
- Ne pas confondre tests hors ligne, simulation des adaptateurs et recette réelle.
- Les règles non vérifiées de l'ancien bot restent signalées dans la matrice.
- Créer les branches sous codex/ et ne pas toucher au vault Alfred pour coder.

Vérifications :

```sh
uv sync --locked --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run moka --config config.example.toml check
uv run moka demo
```
