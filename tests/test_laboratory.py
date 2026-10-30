from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.base import DomainError
from moka.laboratory import LAB_NAME, PENALTY_ROLE_COLOUR, PENALTY_ROLE_NAME, prepare


async def test_laboratory_rejects_other_guild_before_any_mutation(service):
    guild = SimpleNamespace(id=999, name=LAB_NAME, fetch_roles=AsyncMock())
    with pytest.raises(DomainError):
        await prepare(guild, None, service)
    guild.fetch_roles.assert_not_called()


async def test_laboratory_rejects_name_mismatch_before_any_mutation(service):
    guild = SimpleNamespace(id=1, name="Serveur de production", fetch_roles=AsyncMock())
    with pytest.raises(ValueError, match="attendu"):
        await prepare(guild, None, service)
    guild.fetch_roles.assert_not_called()


@pytest.mark.parametrize(
    "existing_penalty", [None, "Pas-doué", "Pas doué (test)", "Ancienne pause"]
)
async def test_laboratory_builds_once_and_preserves_ids(service, existing_penalty):
    serial = iter(range(100, 200))
    roles, channels = [], []
    default_role = MagicMock(spec=discord.Role)
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(manage_roles=True, manage_channels=True)

    async def new_role(**kwargs):
        role = MagicMock(spec=discord.Role)
        role.id, role.name, role.managed = next(serial), kwargs["name"], False
        role.permissions = kwargs["permissions"]
        role.hoist, role.colour = (
            kwargs.get("hoist", False),
            kwargs.get("colour", discord.Colour(0)),
        )

        async def edit_role(**updates):
            for key, value in updates.items():
                if key != "reason":
                    setattr(role, key, value)
            return role

        role.edit = AsyncMock(side_effect=edit_role)
        return role

    if existing_penalty:
        previous = await new_role(name=existing_penalty, permissions=discord.Permissions.none())
        roles.append(previous)
        if existing_penalty == "Ancienne pause":
            service.set_setting(1, "role:counting_failure", previous.id)

    async def new_category(name, **kwargs):
        category = MagicMock(spec=discord.CategoryChannel)
        category.id, category.name = next(serial), name
        category.overwrites = kwargs.get("overwrites", {})
        return category

    async def new_text(name, **kwargs):
        channel = MagicMock(spec=discord.TextChannel)
        channel.id, channel.name = next(serial), name
        channel.category_id = kwargs["category"].id
        channel.overwrites = dict(kwargs["overwrites"])
        channel.overwrites_for.side_effect = lambda role: discord.PermissionOverwrite.from_pair(
            *channel.overwrites.get(role, discord.PermissionOverwrite()).pair()
        )

        async def set_permissions(role, *, overwrite, reason):
            channel.overwrites[role] = overwrite

        channel.set_permissions = AsyncMock(side_effect=set_permissions)
        return channel

    async def new_voice(name, **kwargs):
        channel = MagicMock(spec=discord.VoiceChannel)
        channel.id, channel.name = next(serial), name
        channel.category_id = kwargs["category"].id
        channels.append(channel)
        return channel

    guild = SimpleNamespace(
        id=1,
        name=LAB_NAME,
        default_role=default_role,
        fetch_roles=AsyncMock(return_value=roles),
        fetch_channels=AsyncMock(return_value=channels),
        create_role=AsyncMock(side_effect=new_role),
        create_category=AsyncMock(side_effect=new_category),
        create_text_channel=AsyncMock(side_effect=new_text),
        create_voice_channel=AsyncMock(side_effect=new_voice),
    )
    first = await prepare(guild, member, service)
    journal = next(c for c in channels if c.id == first["channels"]["logs"])
    staff_role = next(r for r in roles if r.id == first["roles"]["Staff test"])
    # Reproduit le salon existant qui n'hérite plus de l'accès staff de la catégorie.
    journal.overwrites[staff_role] = discord.PermissionOverwrite(send_messages=False)
    original_overwrites = {role: overwrite.pair() for role, overwrite in journal.overwrites.items()}
    second = await prepare(guild, member, service)
    assert first == second
    assert guild.create_role.await_count == (5 if existing_penalty else 6)
    assert guild.create_category.await_count == 4
    assert guild.create_text_channel.await_count == 5
    assert guild.create_voice_channel.await_count == 1
    assert service.get_setting(1, "channel:counting") == first["channels"]["counting"]
    private_calls = [
        call for call in guild.create_category.call_args_list if "overwrites" in call.kwargs
    ]
    assert len(private_calls) == 2
    assert all(
        call.kwargs["overwrites"][default_role].view_channel is False for call in private_calls
    )
    penalty_id = first["roles"][PENALTY_ROLE_NAME]
    penalty = next(r for r in roles if r.id == penalty_id)
    assert penalty.name == PENALTY_ROLE_NAME and penalty.hoist
    assert penalty.colour.value == PENALTY_ROLE_COLOUR
    assert service.get_setting(1, "role:counting_failure") == penalty_id
    if existing_penalty:
        assert penalty_id == previous.id
        assert penalty.edit.await_count == 1
    assert journal.overwrites_for(staff_role).view_channel is True
    assert journal.overwrites_for(staff_role).read_message_history is True
    assert journal.overwrites_for(staff_role).send_messages is False
    for role, overwrite in original_overwrites.items():
        if role != staff_role:
            assert journal.overwrites_for(role).pair() == overwrite


async def test_legacy_privileged_penalty_is_not_renamed(service):
    staff = SimpleNamespace(
        id=101, name="Staff test", managed=False, permissions=discord.Permissions.none()
    )
    penalty = SimpleNamespace(
        id=102,
        name="Pas-doué",
        managed=False,
        permissions=discord.Permissions(administrator=True),
        edit=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1, name=LAB_NAME, fetch_roles=AsyncMock(return_value=[staff, penalty])
    )
    member = SimpleNamespace(
        guild_permissions=discord.Permissions(manage_roles=True, manage_channels=True)
    )
    with pytest.raises(ValueError, match="sans permissions"):
        await prepare(guild, member, service)
    penalty.edit.assert_not_called()
