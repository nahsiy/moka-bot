import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from moka.base import DomainError
from moka.bot import MokaBot
from moka.cogs.community import CommunityCog


@pytest.fixture
async def progression(service):
    guild = SimpleNamespace(id=1)

    def role(rid, position):
        return discord.Role(
            guild=guild,
            state=None,
            data={
                "id": str(rid),
                "name": f"Rôle {rid}",
                "position": position,
                "permissions": "0",
                "color": 0,
                "hoist": True,
                "managed": False,
            },
        )

    ranks = [role(101, 1), role(102, 2), role(103, 3)]
    barista, penalty = role(201, 5), role(202, 4)
    all_roles = [*ranks, barista, penalty]
    guild.me = SimpleNamespace(top_role=role(999, 10))
    guild.get_role = lambda rid: next((r for r in all_roles if r.id == rid), None)
    member = SimpleNamespace(id=10, bot=False, guild=guild, roles=[])

    async def add(*roles, **kwargs):
        member.roles.extend(r for r in roles if r not in member.roles)

    async def remove(*roles, **kwargs):
        member.roles[:] = [r for r in member.roles if r not in roles]

    member.add_roles, member.remove_roles = (
        AsyncMock(side_effect=add),
        AsyncMock(side_effect=remove),
    )
    guild.fetch_member, guild.members = AsyncMock(return_value=member), [member]
    service.set_setting(1, "level_rewards", {"0": 101, "3": 102, "7": 103})
    service.set_setting(1, "level_role_mode", "exclusive")
    service.profile(1, 10, viewer=10)

    def set_level(level):
        with service.store.transaction() as con:
            con.execute("UPDATE accounts SET xp=? WHERE guild=1 AND user=10", (100 * level**2,))

    bot = MokaBot(service.config, service=service)
    await bot.add_cog(CommunityCog(bot))
    yield SimpleNamespace(
        bot=bot,
        guild=guild,
        member=member,
        ranks=ranks,
        barista=barista,
        penalty=penalty,
        set_level=set_level,
        add=add,
    )
    await bot.close()


@pytest.mark.parametrize("level,expected", [(0, 0), (3, 1), (7, 2), (50, 2)])
async def test_highest_rank_only_preserves_owner_penalty_and_account(
    progression, service, level, expected
):
    p = progression
    p.set_level(level)
    p.member.roles = [*p.ranks, p.barista, p.penalty]
    before = service.profile(1, 10, viewer=10)
    await p.bot.level_roles(p.member)
    assert set(p.member.roles) == {p.ranks[expected], p.barista, p.penalty}
    assert service.profile(1, 10, viewer=10) == before


async def test_concurrent_same_level_activity_assigns_once(progression):
    p = progression
    p.set_level(3)
    await asyncio.gather(*(p.bot.level_roles(p.member) for _ in range(5)))
    assert p.member.roles == [p.ranks[1]]
    assert p.member.add_roles.await_count == 1


async def test_privileged_rank_refused_before_removal(progression):
    p = progression
    p.set_level(3)
    p.member.roles = [p.ranks[0], p.barista]
    p.ranks[1]._permissions = discord.Permissions(administrator=True).value
    with pytest.raises(DomainError, match="permissions"):
        await p.bot.level_roles(p.member)
    p.member.add_roles.assert_not_called()
    p.member.remove_roles.assert_not_called()


async def test_failed_add_keeps_old_rank_then_maintenance_retries(progression):
    p = progression
    p.set_level(3)
    p.member.roles = [p.ranks[0]]
    p.member.add_roles.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "Refus"
    )
    await p.bot.reconcile_level_roles(p.guild)
    assert p.member.roles == [p.ranks[0]]
    p.member.remove_roles.assert_not_called()
    p.member.add_roles.side_effect = p.add
    p.bot.last_level_role_sync.clear()  # Passage de maintenance suivant, sans attendre une minute.
    await p.bot.reconcile_level_roles(p.guild)
    assert p.member.roles == [p.ranks[1]]
    calls = p.guild.fetch_member.await_count
    await p.bot.reconcile_level_roles(p.guild)
    assert p.guild.fetch_member.await_count == calls


async def test_newcomer_gets_level_zero_and_bots_are_ignored(progression):
    p = progression
    await p.bot.on_member_join(p.member)
    assert p.member.roles == [p.ranks[0]]
    p.member.bot = True
    calls = p.guild.fetch_member.await_count
    await p.bot.on_member_join(p.member)
    await p.bot.reconcile_level_roles(p.guild)
    assert p.guild.fetch_member.await_count == calls


async def test_disabled_module_or_foreign_guild_cannot_assign(progression, service):
    p = progression
    service.set_setting(1, "feature:roles", False)
    await p.bot.level_roles(p.member)
    p.guild.fetch_member.assert_not_called()
    p.guild.id = 999
    with pytest.raises(DomainError, match="autorisé"):
        await p.bot.level_roles(p.member)
    p.member.add_roles.assert_not_called()


async def test_legacy_cumulative_mode_remains_available(progression, service):
    p = progression
    p.set_level(3)
    service.set_setting(1, "level_role_mode", "cumulative")
    await p.bot.level_roles(p.member)
    assert set(p.member.roles) == set(p.ranks[:2])
    p.member.remove_roles.assert_not_called()
