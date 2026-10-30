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
    assert sent["file"].filename == "moka-attention.png"
    assert sent["file"].description.endswith((TAUNTS if insult else COMPLIMENTS)[0])
    assert "embed" not in sent


@pytest.mark.parametrize(
    "article,label",
    [
        ("cafe", "café virtuel"),
        ("biscuit", "biscuit porte-bonheur"),
        ("trophee", "petit trophée du serveur"),
    ],
)
async def test_purchase_is_private_and_gift_is_public_with_both_members(
    service, fund, article, label
):
    fund(10, 1000)
    user = Mock(spec=discord.Member)
    user.id, user.bot = 10, False
    recipient = Mock(spec=discord.Member)
    recipient.id, recipient.bot = 20, False
    bot = SimpleNamespace(service=service)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=user,
        id=123,
        client=bot,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    cog = MembersCog(bot)
    await MembersCog.buy.callback(cog, interaction, article)
    assert interaction.response.send_message.call_args.kwargs["ephemeral"] is True
    interaction.id = 124
    interaction.response.send_message.reset_mock()
    await MembersCog.give_item.callback(cog, interaction, recipient, article)
    sent = interaction.response.send_message.call_args
    assert not sent.kwargs.get("ephemeral", False)
    assert not sent.args and "content" not in sent.kwargs
    assert sent.kwargs["embed"].title == "🎁 Un cadeau !"
    assert sent.kwargs["embed"].description == f"<@10> offre un **{label}** à <@20>."
    assert sent.kwargs["allowed_mentions"].to_dict() == {"parse": []}
    assert service.inventory(1, 10) == []
    assert service.inventory(1, 20) == [{"item": article, "quantity": 1}]


async def test_failed_gift_does_not_publish_a_success(service):
    user = Mock(spec=discord.Member)
    user.id, user.bot = 10, False
    recipient = Mock(spec=discord.Member)
    recipient.id, recipient.bot = 20, False
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=user,
        id=123,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    with pytest.raises(DomainError, match="possèdes pas"):
        await MembersCog.give_item.callback(
            MembersCog(interaction.client), interaction, recipient, "cafe"
        )
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.parametrize(
    "draw,rarity,pool",
    [
        (0.59, "classic", COMPLIMENTS[:30]),
        (0.60, "rare", COMPLIMENTS[30:42]),
        (0.90, "epic", COMPLIMENTS[42:]),
    ],
)
def test_rarity_selects_distinct_phrases_and_remains_replay_safe(service, draw, rarity, pool):
    service.rng.value = draw
    result = service.social_message(1, 10, "draw", "compliment")
    assert result["rarity"] == rarity and result["text"] in pool
    assert service.social_message(1, 10, "draw", "compliment")["text"] == result["text"]
    recent = []
    for i in range(10):
        service.clock.advance(15)
        result = service.social_message(1, 10, f"next:{i}", "compliment")
        assert result["text"] not in recent[-5:]
        recent.append(result["text"])
