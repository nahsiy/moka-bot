from moka.admission import Admission
from moka.collection import Collection
from moka.community import Community
from moka.counting_integrity import CountingIntegrity
from moka.economy import Economy
from moka.games import Games
from moka.presence import Presence
from moka.settings import Settings


class Service(
    Economy, Games, Community, Admission, Presence, CountingIntegrity, Settings, Collection
):
    """Métier indépendant de Discord, avec horloge et hasard injectables."""
