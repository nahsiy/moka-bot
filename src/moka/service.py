from moka.community import Community
from moka.economy import Economy
from moka.games import Games


class Service(Economy, Games, Community):
    """Métier indépendant de Discord, avec horloge et hasard injectables."""
