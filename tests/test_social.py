from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.members import MembersCog
from moka.service import Service
from moka.social_catalog import COMPLIMENTS, SOCIAL_CATALOG, TAUNTS


def test_catalog_is_large_unique_and_ready_for_discord():
    assert len(COMPLIMENTS) == len(TAUNTS) == 50
    assert len(set(COMPLIMENTS + TAUNTS)) == 100
    assert all(20 < len(line) < 250 and "@" not in line for line in COMPLIMENTS + TAUNTS)


@pytest.mark.parametrize("kind", SOCIAL_CATALOG)
def test_five_recent_phrases_are_avoided_and_history_survives_restart(service, kind):
    texts = []
    for index in range(12):
        restarted = Service(service.store, service.config, clock=service.clock, rng=service.rng)
        text = restarted.social_message(1, 10, str(index), kind)["text"]
        assert text in SOCIAL_CATALOG[kind] and text not in texts[-5:]
        texts.append(text)
        service.clock.advance(15)
    assert service.get_setting(1, "fun:recent:" + kind) == texts[-5:]
    assert service.get_setting(2, "fun:recent:" + kind, []) == []


def test_categories_share_cooldown_but_not_phrase_history_and_preserve_money(service, fund):
    fund(10, 450)
    before = service.profile(1, 10)
    service.social_message(1, 10, "first", "compliment")
    with pytest.raises(DomainError, match="15 secondes"):
        service.social_message(1, 10, "too-soon", "taunt")
    assert service.get_setting(1, "fun:recent:taunt", []) == []
    service.clock.advance(15)
    assert service.social_message(1, 10, "later", "taunt")["text"] == TAUNTS[0]
    assert service.profile(1, 10) == before


def test_replay_does_not_draw_again_or_advance_history(service):
    first = service.social_message(1, 10, "first", "compliment")
    replay = service.social_message(1, 10, "first", "compliment")
    assert replay == {**first, "replayed": True}
    assert service.get_setting(1, "fun:recent:compliment") == [first["text"]]
    service.social_message(1, 20, "second", "compliment")
    assert len(service.get_setting(1, "fun:recent:compliment")) == 2


def test_module_and_guild_refusals_leave_history_untouched(service):
    service.set_setting(1, "feature:fun", False)
    for guild, kind in [(1, "compliment"), (999, "taunt"), (2, "unknown")]:
        with pytest.raises(DomainError):
            service.social_message(guild, 10, str(guild), kind)
    assert service.get_setting(1, "fun:recent:compliment", []) == []


@pytest.mark.parametrize("insult", [False, True])
async def test_discord_command_is_public_escapes_name_and_never_pings(service, insult):
    user = Mock(spec=discord.Member)
    user.id, user.bot, user.display_name = 10, False, "**Camille** @everyone"
    bot = SimpleNamespace(service=service)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=user,
        id=123,
        client=bot,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    cog = MembersCog(bot)
    await cog.fun(interaction, None, insult)
    sent = interaction.response.send_message.call_args.kwargs
    assert sent["allowed_mentions"].to_dict() == {"parse": []}
    assert not sent.get("ephemeral", False)
    assert r"\*\*Camille\*\*" in sent["embed"].description
    assert sent["embed"].description.endswith((TAUNTS if insult else COMPLIMENTS)[0])
