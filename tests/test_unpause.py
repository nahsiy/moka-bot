import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.community import CommunityCog
from moka.cogs.staff import StaffCog


def suspended(service):
    service.set_setting(1, "role:counting_failure", 99)
    service.counting(1, 5, 10, "oops", 101)


def discord_context(service):
    role = SimpleNamespace(id=99)
    member = SimpleNamespace(id=10, roles=[role], remove_roles=AsyncMock())
    guild = SimpleNamespace(id=1, get_role=lambda _: role, get_member=lambda _: member)
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    return cog, guild, member


def test_unpause_clears_both_games_and_preserves_money_other_roles_and_guilds(service, fund):
    fund(10, 5000)
    suspended(service)
    service.set_setting(2, "role:counting_failure", 88)
    service.word(2, 7, 10, "deux mots", 201)
    with service.store.transaction() as con:
        con.execute(
            "INSERT INTO role_grants VALUES(1,10,77,'other',?,1)", (service.clock() + 5000,)
        )
    before = service.profile(1, 10, viewer=10)["wallet"]
    result = service.release_game_penalty(1, 10, "release-1")
    assert result["roles"] == [99]
    assert service.game_penalty(1, 10) is None
    assert service.game_penalty(2, 10) is not None
    assert service.profile(1, 10, viewer=10)["wallet"] == before
    assert service.counting(1, 6, 10, "1", 301)["valid"]
    assert service.word(1, 7, 10, "tomate", 302)["valid"]
    with service.store.read() as con:
        assert (
            con.execute("SELECT until FROM role_grants WHERE role=77").fetchone()[0]
            > service.clock()
        )
    with pytest.raises(DomainError, match="autorisé"):
        service.release_game_penalty(999, 10, "release-2")


def test_replayed_unpause_does_not_clear_newer_sanction(service):
    suspended(service)
    first = service.release_game_penalty(1, 10, "release-1")
    service.clock.advance(1)
    second = service.counting(1, 5, 10, "oops", 102)
    replayed = service.release_game_penalty(1, 10, "release-1")
    assert replayed == {**first, "replayed": True}
    assert service.game_penalty(1, 10)["penalty_until"] == second["penalty_until"]


async def test_unpause_removes_role_and_old_maintenance_snapshot_cannot_restore_it(service):
    suspended(service)
    cog, guild, member = discord_context(service)
    with service.store.read() as con:
        old_grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    result = service.release_game_penalty(1, 10, "release-1")
    assert not await cog.release_game_roles(guild, 10, result["roles"])
    member.remove_roles.assert_awaited_once()
    await cog.apply_role_grant(guild, old_grant, service.clock())
    assert service.game_penalty(1, 10) is None
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM role_grants").fetchone()[0] == 0


async def test_unpause_queues_failed_discord_removal_for_maintenance(service):
    suspended(service)
    cog, guild, member = discord_context(service)
    member.remove_roles.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "Accès refusé"
    )
    result = service.release_game_penalty(1, 10, "release-1")
    assert await cog.release_game_roles(guild, 10, result["roles"])
    assert service.game_penalty(1, 10) is None
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
        assert grant["until"] <= service.clock()
    member.remove_roles.side_effect = None
    await cog.apply_role_grant(guild, grant, service.clock())
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM role_grants").fetchone()[0] == 0


async def test_unpause_can_remove_manual_penalty_role_without_active_db_record(service):
    service.set_setting(1, "role:counting_failure", 99)
    cog, guild, member = discord_context(service)
    result = service.release_game_penalty(1, 10, "release-1")
    assert not await cog.release_game_roles(guild, 10, result["roles"])
    member.remove_roles.assert_awaited_once()


async def test_unpause_during_role_assignment_finishes_with_role_removed(service):
    suspended(service)
    role = MagicMock(spec=discord.Role)
    role.id = 99
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    started, proceed = asyncio.Event(), asyncio.Event()

    async def add_role(*args, **kwargs):
        started.set()
        await proceed.wait()
        member.roles = [role]

    async def remove_role(*args, **kwargs):
        member.roles = []

    member = SimpleNamespace(
        id=10,
        roles=[],
        add_roles=AsyncMock(side_effect=add_role),
        remove_roles=AsyncMock(side_effect=remove_role),
    )
    guild = SimpleNamespace(
        id=1, me=SimpleNamespace(top_role=100), get_role=lambda _: role, get_member=lambda _: member
    )
    role.guild = guild
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    assignment = asyncio.create_task(cog.apply_role_grant(guild, grant, service.clock()))
    await started.wait()
    result = service.release_game_penalty(1, 10, "release-1")
    removal = asyncio.create_task(cog.release_game_roles(guild, 10, result["roles"]))
    proceed.set()
    await assignment
    assert not await removal
    assert member.roles == []


async def test_unpause_command_checks_staff_permission_and_responds_privately(service):
    suspended(service)
    role = SimpleNamespace(id=99)
    target = MagicMock(spec=discord.Member)
    target.id, target.bot, target.mention, target.roles = 10, False, "<@10>", [role]
    target.remove_roles = AsyncMock()
    guild = SimpleNamespace(id=1, get_role=lambda _: role, get_member=lambda _: target)
    target.guild = guild
    user = MagicMock(spec=discord.Member)
    user.id, user.guild_permissions = 20, discord.Permissions.none()
    bot = SimpleNamespace(service=service, store=service.store, audit=AsyncMock())
    community = CommunityCog(bot)
    bot.get_cog = lambda _: community
    cog = StaffCog(bot)
    interaction = SimpleNamespace(
        guild=guild,
        user=user,
        id=12345,
        client=bot,
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    with pytest.raises(DomainError, match="permission"):
        await StaffCog.unpause.callback(cog, interaction, target)
    interaction.response.defer.assert_not_awaited()
    assert service.game_penalty(1, 10) is not None
    user.guild_permissions = discord.Permissions(manage_guild=True)
    await StaffCog.unpause.callback(cog, interaction, target)
    target.remove_roles.assert_awaited_once()
    assert interaction.followup.send.call_args.kwargs["ephemeral"] is True
    assert (
        "accès aux deux jeux rétabli"
        in interaction.followup.send.call_args.kwargs["embed"].description
    )
    bot.audit.assert_awaited_once()
    assert service.game_penalty(1, 10) is None
