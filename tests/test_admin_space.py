from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.admin_space import AdminHub, is_moka_admin, show_team, team_embed
from moka.base import DomainError
from moka.cogs.staff import staff
from moka.role_panels import protected_roles
from moka.staff_panel import authorize


def member(uid=20, *, roles=(), **permissions):
    return SimpleNamespace(
        id=uid,
        bot=False,
        mention=f"<@{uid}>",
        roles=[SimpleNamespace(id=rid) for rid in roles],
        guild_permissions=discord.Permissions(**permissions),
    )


def interaction(service, user):
    m = Mock(spec=discord.Member)
    m.id, m.bot, m.roles, m.guild_permissions = user.id, False, user.roles, user.guild_permissions
    guild = SimpleNamespace(id=1, owner_id=10, fetch_member=AsyncMock(return_value=m))
    m.guild = guild
    return SimpleNamespace(
        guild=guild,
        user=m,
        id=123,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


def test_bot_admin_role_is_scoped_isolated_and_not_self_assignable(service):
    guild = SimpleNamespace(id=1, owner_id=10)
    service.set_setting(1, "moka:admin_roles", [500])
    assert is_moka_admin(service, member(roles=[500]), guild)
    assert is_moka_admin(service, member(10), guild)
    assert is_moka_admin(service, member(manage_guild=True), guild)
    assert not is_moka_admin(service, member(roles=[501]), guild)
    assert not is_moka_admin(service, member(roles=[500]), SimpleNamespace(id=2, owner_id=10))
    assert 500 in protected_roles(service, 1)
    service.set_setting(1, "moka:admin_roles", [])
    assert not is_moka_admin(service, member(roles=[500]), guild)


async def test_settings_recheck_role_membership_and_registration_at_each_action(service):
    service.set_setting(1, "moka:admin_roles", [500])
    i = interaction(service, member(roles=[500]))
    assert await authorize(i, 1, 20) == (1, 20)
    i.guild.fetch_member.return_value = member(20)
    with pytest.raises(DomainError, match="Gérer le serveur"):
        await authorize(i, 1, 20)
    i.guild.fetch_member.return_value = member(20, roles=[500])
    service.set_setting(1, "moka:admin_roles", [])
    with pytest.raises(DomainError):
        await authorize(i, 1, 20)
    with pytest.raises(DomainError, match="autre personne"):
        await authorize(i, 1, 999)


def test_bot_admin_role_does_not_grant_native_moderation(service):
    service.set_setting(1, "moka:admin_roles", [500])
    i = interaction(service, member(roles=[500]))
    assert staff(i) == (1, 20, "123")
    for permission in ("manage_messages", "moderate_members"):
        with pytest.raises(DomainError, match="permission"):
            staff(i, permission)


def test_team_directory_reports_real_authority_and_omits_bot(service):
    service.set_setting(1, "moka:admin_roles", [500])
    service.set_setting(1, "admission:staff_roles", [501])
    service.set_setting(1, "ticket_staff_roles", [501])
    g = SimpleNamespace(
        id=1, owner_id=10, get_role=lambda rid: SimpleNamespace(mention=f"<@&{rid}>")
    )
    bot = member(99, roles=[500])
    bot.bot = True
    members = [
        member(10, manage_guild=True, manage_messages=True),
        member(20, roles=[500]),
        member(30, roles=[501]),
        member(40, manage_guild=True),
        member(50),
        bot,
    ]
    embed = team_embed(g, service, members)
    admins = embed.fields[0].value
    assert all(f"<@{uid}>" in admins for uid in (10, 20, 40))
    assert all(f"<@{uid}>" not in admins for uid in (30, 50, 99))
    assert "<@30>" in embed.fields[1].value and "<@30>" in embed.fields[2].value
    assert "<@20>" not in embed.fields[3].value
    assert "<@&500>" in embed.fields[4].value


async def test_team_lookup_uses_current_roles_and_members_and_is_private(service):
    i = interaction(service, member())
    guild = SimpleNamespace(id=1, owner_id=10, get_role=lambda _: None)

    async def members(**kwargs):
        yield member(10, manage_guild=True)

    guild.fetch_members = members
    i.client.fetch_guild = AsyncMock(return_value=guild)
    await show_team(i)
    i.client.fetch_guild.assert_awaited_once_with(1)
    response = i.followup.send.call_args.kwargs
    assert response["ephemeral"] and response["allowed_mentions"].to_dict() == {"parse": []}
    assert "<@10>" in response["embed"].fields[0].value


async def test_hub_is_persistent_and_rejects_unauthorized_settings_and_diagnostic(service):
    hub = AdminHub()
    assert hub.is_persistent() and len(hub.children) == 4
    i = interaction(service, member())
    with pytest.raises(DomainError):
        await hub.settings.callback(i)
    with pytest.raises(DomainError):
        await hub.diagnostic.callback(i)
    i.response.defer.assert_not_awaited()
