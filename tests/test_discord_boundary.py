from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import discord
import pytest

from moka.__main__ import check_commands, demo, main
from moka.base import DomainError
from moka.bot import MokaBot
from moka.cogs.community import (
    CommunityCog,
    PhotoReviewView,
    RolePanelView,
    RoleSelect,
    TicketPanelView,
)
from moka.cogs.staff import staff
from moka.config import Config
from moka.discord_ui import HackView, JoinView, event_embed, interaction_event


async def test_discord_tree_serializes_without_token_or_network(service):
    data = await check_commands(service.config)
    names = {c["name"] for c in data}
    assert {
        "profile",
        "xp",
        "argent",
        "banque",
        "config",
        "roles",
        "ticket",
        "vocal",
        "hack",
    } <= names
    config = next(c for c in data if c["name"] == "config")
    assert int(config["default_member_permissions"]) & discord.Permissions(manage_guild=True).value


async def test_persistent_buttons_survive_restart():
    for view in (JoinView(), HackView(), RolePanelView(), TicketPanelView(), PhotoReviewView()):
        assert view.is_persistent()
        assert len({button.custom_id for button in view.children}) == len(view.children)


async def test_expired_role_is_removed_after_restart_even_if_module_disabled(service):
    service.set_setting(1, "role:counting_failure", 55)
    service.counting(1, 5, 10, "8", 1001)
    service.clock.advance(10801)
    service.set_setting(1, "feature:counting", False)
    role = SimpleNamespace(id=55)
    member = SimpleNamespace(id=10, roles=[role], remove_roles=AsyncMock())
    guild = SimpleNamespace(id=1, get_role=lambda _: role, get_member=lambda _: member)
    bot = SimpleNamespace(service=service, store=service.store)
    cog = CommunityCog(bot)
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    await cog.apply_role_grant(guild, grant, service.clock())
    member.remove_roles.assert_awaited_once()
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM role_grants").fetchone()[0] == 0


async def test_ticket_channel_is_private_and_staff_is_explicit(service):
    i = fake_interaction(service)
    default_role = MagicMock(spec=discord.Role)
    staff_role = MagicMock(spec=discord.Role)
    staff_role.id = 99
    staff_role.is_default.return_value = False
    me = Mock(spec=discord.Member)
    me.id = 999
    room = Mock(spec=discord.TextChannel)
    room.id, room.mention = 555, "#ticket"
    room.send = AsyncMock()
    i.guild = SimpleNamespace(
        id=1,
        get_role=lambda _: staff_role,
        get_channel=lambda _: None,
        text_channels=[],
        default_role=default_role,
        me=me,
        create_text_channel=AsyncMock(return_value=room),
    )
    i.response, i.followup = SimpleNamespace(defer=AsyncMock()), SimpleNamespace(send=AsyncMock())
    bot = SimpleNamespace(service=service, store=service.store, channel_id=lambda *args: None)
    cog = CommunityCog(bot)
    with pytest.raises(DomainError, match="equipe_tickets"):
        await cog.open_ticket(i)
    i.guild.create_text_channel.assert_not_called()
    service.set_setting(1, "ticket_staff_roles", [99])
    await cog.open_ticket(i)
    overwrites = i.guild.create_text_channel.call_args.kwargs["overwrites"]
    assert overwrites[default_role].view_channel is False
    assert overwrites[i.user].view_channel is True
    assert overwrites[staff_role].view_channel is True
    assert all(p.administrator is None for p in overwrites.values())
    assert service.ticket(1, 555)["user"] == 10


def fake_interaction(service, *, guild_id=1, manage=False):
    member = Mock(spec=discord.Member)
    member.id = 10
    member.guild_permissions = discord.Permissions(manage_guild=manage)
    guild = SimpleNamespace(id=guild_id)
    return SimpleNamespace(
        guild=guild,
        guild_id=guild_id,
        user=member,
        id=1234,
        client=SimpleNamespace(service=service),
    )


def test_staff_checks_actual_permissions_not_just_command_visibility(service):
    with pytest.raises(DomainError, match="permission"):
        staff(fake_interaction(service))
    assert staff(fake_interaction(service, manage=True)) == (1, 10, "1234")
    with pytest.raises(DomainError, match="autorisé"):
        staff(fake_interaction(service, guild_id=999, manage=True))


def test_automatic_role_cannot_grant_staff_permissions():
    guild = SimpleNamespace(id=1, me=SimpleNamespace(top_role=100))
    role = MagicMock(spec=discord.Role)
    role.guild = guild
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    role.permissions = discord.Permissions(manage_roles=True)
    with pytest.raises(DomainError, match="interdit"):
        CommunityCog.safe_role(guild, role)
    role.permissions = discord.Permissions.none()
    role.__ge__.return_value = True
    with pytest.raises(DomainError, match="au-dessus"):
        CommunityCog.safe_role(guild, role)


def test_forged_event_message_is_rejected(service):
    event = service.start_event(1, 5, 10, "goblin", "start")
    i = fake_interaction(service)
    i.client.user = SimpleNamespace(id=999)
    i.message = SimpleNamespace(
        author=SimpleNamespace(id=998),
        embeds=[event_embed(service.get_event(1, event["event_id"]), service)],
        channel=SimpleNamespace(id=5),
        id=555,
    )
    with pytest.raises(DomainError, match="pas un événement"):
        interaction_event(i)
    i.message.author.id = 999
    i.message.channel.id = 6
    with pytest.raises(DomainError, match="correspond"):
        interaction_event(i)
    i.message.channel.id = 5
    assert interaction_event(i)["id"] == event["event_id"]
    assert service.get_event(1, event["event_id"])["message"] == 555


async def test_role_selection_rechecks_removed_allowlist(service):
    i = fake_interaction(service)
    role = SimpleNamespace(id=55, name="Loisirs")
    member = SimpleNamespace(id=10, roles=[], guild=SimpleNamespace(get_role=lambda _: role))
    selector = RoleSelect(member, {"55": ""})
    selector._values = ["55"]
    i.client.get_cog = lambda _: SimpleNamespace(service=service)
    with pytest.raises(DomainError, match="menu a changé"):
        await selector.callback(i)


async def test_hack_button_cannot_be_used_by_another_member(service):
    event = service.start_event(1, 5, 10, "hack", "start")
    i = fake_interaction(service)
    i.user.id = 11
    i.client.user = SimpleNamespace(id=999)
    i.message = SimpleNamespace(
        author=SimpleNamespace(id=999),
        embeds=[event_embed(service.get_event(1, event["event_id"]), service)],
        channel=SimpleNamespace(id=5),
        id=555,
    )
    with pytest.raises(DomainError, match="autre membre"):
        await HackView().finish(i, False)


async def test_configurable_no_global_sync_by_default(service):
    bot = MokaBot(service.config, service=service)
    assert not bot.config.sync_commands
    assert bot.allowed_mentions.everyone is False
    assert bot.allowed_mentions.users is False
    assert bot.allowed_mentions.roles is False
    await bot.close()


async def test_voice_tick_with_real_discord_guild(service):
    bot = MokaBot(service.config, service=service)
    guild = discord.Guild(
        data={"id": "1", "name": "Laboratoire", "roles": [], "afk_channel_id": "5"},
        state=bot._connection,
    )
    channel = discord.VoiceChannel(
        state=bot._connection,
        guild=guild,
        data={
            "id": "5",
            "name": "AFK",
            "type": 2,
            "permission_overwrites": [],
            "position": 0,
            "bitrate": 64000,
            "user_limit": 0,
        },
    )
    guild._channels[channel.id] = channel
    bot._connection._guilds[guild.id] = guild
    bot.is_ready = lambda: True
    await MokaBot.voice_rewards.coro(bot)
    assert bot.voice_eligible == set()
    assert bot.last_voice_tick is not None
    await bot.close()


def test_demo_is_offline_and_real_sqlite():
    result = demo()
    assert not result["discord_connected"]
    assert result["database_integrity"] and result["backup_created"]
    assert result["goblin"]["reward"] == 100


def test_run_without_configured_guild_fails_before_any_connection(monkeypatch, capsys):
    monkeypatch.delenv("MOKA_GUILD_IDS", raising=False)
    monkeypatch.delenv("MOKA_CONFIG", raising=False)
    assert main(["run"]) == 2
    assert "MOKA_GUILD_IDS" in capsys.readouterr().err


def test_config_rejects_unknown_features_and_boolean_amounts(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[features]\ngems = true\n")
    with pytest.raises(ValueError):
        Config.load(path)
    path.write_text("[rules]\ndaily_coins = true\n")
    with pytest.raises(ValueError):
        Config.load(path)
