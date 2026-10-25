from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.base import DomainError
from moka.laboratory import LAB_NAME, prepare


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


async def test_laboratory_builds_once_and_preserves_ids(service):
    serial = iter(range(100, 200))
    roles, channels = [], []
    default_role = MagicMock(spec=discord.Role)
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = discord.Permissions(manage_roles=True, manage_channels=True)

    async def new_role(**kwargs):
        role = MagicMock(spec=discord.Role)
        role.id, role.name, role.managed = next(serial), kwargs["name"], False
        role.permissions = kwargs["permissions"]
        return role

    async def new_category(name, **kwargs):
        category = MagicMock(spec=discord.CategoryChannel)
        category.id, category.name = next(serial), name
        category.overwrites = kwargs.get("overwrites", {})
        return category

    async def new_text(name, **kwargs):
        channel = MagicMock(spec=discord.TextChannel)
        channel.id, channel.name = next(serial), name
        channel.category_id = kwargs["category"].id
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
    second = await prepare(guild, member, service)
    assert first == second
    assert guild.create_role.await_count == 6
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
