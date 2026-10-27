from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.bot import MokaBot
from moka.cogs.community import CommunityCog
from moka.service import Service


@pytest.mark.parametrize("game", ["counting", "words"])
def test_one_hour_penalty_is_shared_persistent_and_not_extended(service, fund, game):
    service.set_setting(1, "role:counting_failure", 99)
    fund(10, 5000)
    method = service.counting if game == "counting" else service.word
    error = method(1, 5, 10, "deux mots", 100)
    assert not error["valid"]
    assert error["penalty_until"] == service.clock() + 3600
    assert error["penalty_role"] == 99
    wallet = service.profile(1, 10, viewer=10)["wallet"]
    restarted = Service(service.store, service.config, clock=service.clock, rng=service.rng)
    service.clock.advance(120)
    assert method(1, 5, 10, "deux mots", 100)["replayed"]
    assert restarted.counting(1, 6, 10, "1", 101)["blocked"]
    assert restarted.word(1, 7, 10, "tomate", 102)["blocked"]
    assert restarted.game_penalty(1, 10)["penalty_until"] == error["penalty_until"]
    assert restarted.profile(1, 10, viewer=10)["wallet"] == wallet
    # Autres personnes et autres serveurs ne sont pas suspendus.
    assert restarted.counting(1, 6, 11, "1", 103)["valid"]
    assert restarted.word(2, 7, 10, "tomate", 104)["valid"]
    service.clock.advance(3480)
    assert restarted.game_penalty(1, 10) is None
    assert restarted.counting(1, 6, 10, "2", 105)["valid"]
    assert restarted.word(1, 7, 10, "tomate", 106)["valid"]


@pytest.mark.parametrize("content", ["soleil", "tomate", "deux mots", "123", ""])
def test_word_errors_persist_role_without_money_or_chain_reset(service, fund, content):
    service.set_setting(1, "role:counting_failure", 99)
    fund(10, 1000)
    service.word(1, 5, 10, "tomate", 100)
    service.word(1, 5, 11, "fruit", 101)
    # Mauvais tour pour soleil ; doublon pour tomate ; autres entrées invalides.
    user = 11 if content == "soleil" else 10
    result = service.word(1, 5, user, content, 102)
    assert not result["valid"] and result["penalty_role"] == 99
    assert service.profile(1, 10, viewer=10)["wallet"] == 1000
    with service.store.read() as con:
        state = con.execute("SELECT * FROM games WHERE kind='words'").fetchone()
        assert state["value"] == "fruit" and state["score"] == 2
        grant = con.execute("SELECT * FROM role_grants").fetchone()
        assert grant["reason"] == "words" and grant["until"] == service.clock() + 3600


def test_simultaneous_game_errors_create_only_one_pause_and_fine(service, fund):
    service.set_setting(1, "role:counting_failure", 99)
    fund(10, 5000)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda msg: service.counting(1, msg, 10, "oops", msg), (101, 102)))
    assert sum(bool(r.get("blocked")) for r in results) == 1
    assert sum(r.get("fine", 0) for r in results) == 1000
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM role_grants").fetchone()[0] == 1


async def test_penalty_blocks_admin_like_messages_without_xp_or_fine(service, fund):
    service.set_setting(1, "role:counting_failure", 99)
    service.set_setting(1, "channel:counting", 5)
    service.set_setting(1, "channel:words", 6)
    fund(10, 5000)
    service.counting(1, 5, 10, "oops", 100)
    bot = MokaBot(service.config, service=service)
    message = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        author=SimpleNamespace(id=10, bot=False),
        channel=SimpleNamespace(id=6),
        content="tomate",
        id=101,
        webhook_id=None,
        add_reaction=AsyncMock(),
        reply=AsyncMock(),
    )
    await bot.on_message(message)
    assert "pause" in message.reply.call_args.args[0]
    message.add_reaction.assert_not_awaited()
    assert service.profile(1, 10, viewer=10)["xp"] == 0
    assert service.profile(1, 10, viewer=10)["wallet"] == 4000
    await bot.close()


async def test_word_error_applies_role_immediately_and_does_not_repeat(service):
    service.set_setting(1, "role:counting_failure", 99)
    service.set_setting(1, "channel:words", 6)
    service.set_setting(1, "feature:xp", False)
    bot = MokaBot(service.config, service=service)
    community = SimpleNamespace(apply_role_grant=AsyncMock())
    bot.get_cog = lambda _: community
    message = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        author=SimpleNamespace(id=10, bot=False),
        channel=SimpleNamespace(id=6),
        content="deux mots",
        id=101,
        webhook_id=None,
        add_reaction=AsyncMock(),
        reply=AsyncMock(),
    )
    await bot.on_message(message)
    community.apply_role_grant.assert_awaited_once()
    message.add_reaction.assert_awaited_once_with("❌")
    assert "<@&99>" in message.reply.call_args.args[0]
    await bot.on_message(message)
    assert message.reply.await_count == 1
    await bot.close()


async def test_missing_member_cache_is_fetched_and_expiration_removes_role(service):
    service.set_setting(1, "role:counting_failure", 99)
    service.word(1, 5, 10, "deux mots", 100)
    role = MagicMock(spec=discord.Role)
    role.id = 99
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    member = SimpleNamespace(id=10, roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
    guild = SimpleNamespace(
        id=1,
        me=SimpleNamespace(top_role=100),
        get_role=lambda _: role,
        get_member=lambda _: None,
        fetch_member=AsyncMock(return_value=member),
    )
    role.guild = guild
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    await cog.apply_role_grant(guild, grant, service.clock())
    guild.fetch_member.assert_awaited_once_with(10)
    member.add_roles.assert_awaited_once()
    member.roles = [role]
    service.clock.advance(3600)
    await cog.apply_role_grant(guild, grant, service.clock())
    member.remove_roles.assert_awaited_once()
    assert service.game_penalty(1, 10) is None


async def test_missing_role_does_not_cancel_active_game_pause(service):
    service.set_setting(1, "role:counting_failure", 99)
    service.word(1, 5, 10, "deux mots", 100)
    guild = SimpleNamespace(
        id=1, get_role=lambda _: None, get_member=lambda _: SimpleNamespace(id=10)
    )
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    await cog.apply_role_grant(guild, grant, service.clock())
    assert service.game_penalty(1, 10) is not None


async def test_penalty_role_restricts_only_both_game_channels_and_preserves_access(service):
    role = MagicMock(spec=discord.Role)
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    rooms = {}
    for channel_id in (5, 6, 7):
        room = MagicMock(spec=discord.TextChannel)
        room.overwrites_for.return_value = discord.PermissionOverwrite(
            view_channel=True, attach_files=False
        )
        room.set_permissions = AsyncMock()
        rooms[channel_id] = room
    guild = SimpleNamespace(id=1, me=SimpleNamespace(top_role=100), get_channel=rooms.get)
    role.guild = guild
    cog = CommunityCog(
        SimpleNamespace(
            service=service,
            store=service.store,
            channel_id=lambda _, usage: {"counting": 5, "words": 6}[usage],
        )
    )
    await cog.configure_game_role(guild, role)
    for channel_id in (5, 6):
        rooms[channel_id].set_permissions.assert_awaited_once()
        overwrite = rooms[channel_id].set_permissions.call_args.kwargs["overwrite"]
        assert overwrite.send_messages is False and overwrite.send_messages_in_threads is False
        assert overwrite.view_channel is True and overwrite.attach_files is False
    rooms[7].set_permissions.assert_not_awaited()
