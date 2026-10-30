from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.presence import PresenceCog, private_staff_channel
from moka.presence import DAY, INACTIVE_AFTER, conversational_text
from moka.role_panels import protected_roles
from moka.service import Service


def activate(service, guild=1):
    service.set_setting(guild, "presence:enabled", True)
    service.set_setting(guild, "presence:role", 77)
    service.set_setting(guild, "presence:channels", [55, 56, 57])


def test_baseline_boundary_and_restart(service):
    activate(service)
    initial = service.presence_member(1, 10)
    assert initial["last_at"] is None
    assert initial["due_at"] == service.clock() + INACTIVE_AFTER
    service.clock.advance(INACTIVE_AFTER - 1)
    assert not service.presence_member(1, 10)["inactive"]
    restarted = Service(service.store, service.config, clock=service.clock)
    service.clock.advance(1)
    assert restarted.presence_member(1, 10)["inactive"]
    assert restarted.presence_member(1, 10)["started"] == initial["started"]
    assert not restarted.presence_member(2, 10)["inactive"]


def test_activity_restores_without_reward_or_archived_content(service):
    activate(service)
    service.presence_member(1, 10)
    service.clock.advance(INACTIVE_AFTER)
    assert service.record_participation(1, 10, "message")
    row = service.presence_member(1, 10)
    assert not row["inactive"] and row["last_kind"] == "message"
    assert service.export_user(1, 10)["accounts"] == []
    assert set(service.export_user(1, 10)["presence"][0]) == {
        "guild",
        "user",
        "started",
        "last_at",
        "last_kind",
        "absent_until",
    }
    assert row["due_at"] == service.clock() + INACTIVE_AFTER


def test_announce_absence_grace_and_return_no_fake_participation(service):
    activate(service)
    service.presence_member(1, 10)
    service.clock.advance(INACTIVE_AFTER)
    row = service.announce_absence(1, 10, 30)
    assert row["announced"] and not row["inactive"]
    service.clock.advance(30 * DAY)
    assert not service.presence_member(1, 10)["inactive"]
    service.clock.advance(INACTIVE_AFTER)
    assert service.presence_member(1, 10)["inactive"]
    row = service.return_from_absence(1, 10)
    assert not row["inactive"] and row["last_at"] is None
    service.announce_absence(1, 10, 7)
    service.record_participation(1, 10, "voice")
    row = service.presence_member(1, 10)
    assert row["absent_until"] is None and row["last_kind"] == "voice"


@pytest.mark.parametrize("days", [0, -1, 366, True, 2.5])
def test_absence_validation(service, days):
    activate(service)
    with pytest.raises(DomainError):
        service.announce_absence(1, 10, days)


def test_disabled_pending_and_guild_boundary(service):
    assert not service.record_participation(1, 10, "message")
    activate(service)
    service.set_setting(1, "admission:enabled", True)
    service.begin_admission(1, 10)
    assert not service.record_participation(1, 10, "message")
    with pytest.raises(DomainError):
        service.announce_absence(1, 10, 7)
    with pytest.raises(DomainError):
        service.presence_member(3, 10)
    with pytest.raises(ValueError):
        service.record_participation(1, 10, "command")


def test_forget_and_remove_presence_are_guild_scoped(service):
    activate(service)
    service.presence_member(1, 10)
    service.presence_member(2, 10)
    service.forget_user(1, 10)
    assert service.export_user(1, 10)["presence"] == []
    assert service.export_user(2, 10)["presence"]
    service.remove_presence(2, 10)
    assert service.export_user(2, 10)["presence"] == []


@pytest.mark.parametrize(
    "text,eligible",
    [
        ("Bonjour", False),
        ("Salut à tous !", False),
        ("☕ ☕ ☕ ☕", False),
        ("https://example.com/bonjour-tout-le-monde", False),
        ("/commande une longue phrase pour tricher", False),
        ("<@123456789012345678> <@123456789012345678> <@123456789012345678>", False),
        ("Comment se passe votre journée au comptoir ?", True),
        ("Aujourd’hui je prépare quelques biscuits maison.", True),
    ],
)
def test_message_heuristic(text, eligible):
    assert conversational_text(text) is eligible


def harness(service):
    activate(service)
    role = Mock(spec=discord.Role)
    role.id, role.name, role.managed = 77, "🌙 En pause café", False
    role.permissions = discord.Permissions.none()
    role.is_default.return_value = False
    role.__ge__ = Mock(return_value=False)
    guild = SimpleNamespace(
        id=1,
        owner_id=90,
        roles=[role],
        members=[],
        voice_channels=[],
        stage_channels=[],
        afk_channel=None,
    )
    guild.me = SimpleNamespace(
        guild_permissions=discord.Permissions(manage_roles=True), top_role=Mock()
    )
    guild.get_role = lambda rid: role if rid == 77 else None
    for uid in (10, 20):
        member = Mock(spec=discord.Member)
        member.id, member.guild, member.bot, member.roles = uid, guild, False, []
        member.guild_permissions = discord.Permissions.none()
        member.voice = SimpleNamespace(
            self_deaf=False, deaf=False, self_mute=False, mute=False, suppress=False
        )
        member.add_roles, member.remove_roles = AsyncMock(), AsyncMock()
        guild.members.append(member)
    guild.get_member = lambda uid: next((m for m in guild.members if m.id == uid), None)
    guild.fetch_member = AsyncMock(side_effect=lambda uid: guild.get_member(uid))
    bot = SimpleNamespace(
        config=service.config,
        service=service,
        channel_id=lambda gid, key: {"counting": 56, "words": 57}.get(key),
    )
    return PresenceCog(bot), guild, role


def message(guild, uid, mid, *, channel=55, text="Comment se passe votre journée au comptoir ?"):
    return SimpleNamespace(
        guild=guild,
        author=guild.get_member(uid),
        id=mid,
        channel=SimpleNamespace(id=channel),
        content=text,
        webhook_id=None,
        type=discord.MessageType.default,
    )


async def test_exchange_counts_both_actors_not_solo_or_games_or_short_messages(service):
    cog, guild, _ = harness(service)
    cog.sync_member = AsyncMock()
    await cog.on_message(message(guild, 10, 100))
    await cog.on_message(message(guild, 10, 101))
    assert service.export_user(1, 10)["presence"] == []
    await cog.on_message(message(guild, 20, 102, text="Bonjour"))
    await cog.on_message(message(guild, 20, 103, channel=56))
    await cog.on_message(message(guild, 20, 104, channel=57))
    await cog.on_message(message(guild, 20, 105, channel=99))
    assert service.export_user(1, 20)["presence"] == []
    await cog.on_message(message(guild, 20, 106))
    assert service.presence_member(1, 10)["last_at"] == service.clock()
    assert service.presence_member(1, 20)["last_at"] == service.clock()
    assert cog.sync_member.await_count == 2
    service.clock.advance(10)
    await cog.on_message(message(guild, 20, 106))
    assert cog.sync_member.await_count == 2


async def test_old_exchange_and_disconnect_do_not_count(service):
    cog, guild, _ = harness(service)
    cog.sync_member = AsyncMock()
    await cog.on_message(message(guild, 10, 100))
    service.clock.advance(1801)
    await cog.on_message(message(guild, 20, 101))
    cog.sync_member.assert_not_awaited()
    await cog.on_disconnect()
    await cog.on_message(message(guild, 10, 102))
    cog.sync_member.assert_not_awaited()


async def test_voice_five_minutes_and_no_catchup(service):
    cog, guild, _ = harness(service)
    cog.sync_member = AsyncMock()
    guild.voice_channels = [SimpleNamespace(id=88, members=guild.members)]
    for t in range(0, 300, 60):
        await cog.voice_tick([guild], now=t)
    cog.sync_member.assert_not_awaited()
    await cog.voice_tick([guild], now=300)
    assert cog.sync_member.await_count == 2
    assert service.presence_member(1, 10)["last_kind"] == "voice"
    await cog.voice_tick([guild], now=10000)
    assert set(cog.voice.values()) == {0}
    await cog.on_disconnect()
    assert not cog.voice and cog.last_voice_tick is None


async def test_voice_solo_muted_and_afk_do_not_count(service):
    cog, guild, _ = harness(service)
    cog.sync_member = AsyncMock()
    channel = SimpleNamespace(id=88, members=[guild.members[0]])
    guild.voice_channels = [channel]
    for t in range(0, 420, 60):
        await cog.voice_tick([guild], now=t)
    assert not cog.voice
    channel.members = guild.members
    guild.members[1].voice.self_mute = True
    await cog.voice_tick([guild], now=420)
    assert not cog.voice
    guild.members[1].voice.self_mute = False
    guild.afk_channel = channel
    await cog.voice_tick([guild], now=480)
    assert not cog.voice
    cog.sync_member.assert_not_awaited()


async def test_voice_state_change_cuts_continuity(service):
    cog, guild, _ = harness(service)
    cog.voice = {(1, 10, 88): 240, (1, 20, 88): 240}
    await cog.on_voice_state_update(guild.members[0], None, None)
    assert cog.voice == {(1, 20, 88): 240}


async def test_role_add_remove_and_retry_preserves_other_roles(service):
    cog, guild, role = harness(service)
    member = guild.members[0]
    service.presence_member(1, 10)
    service.clock.advance(INACTIVE_AFTER)
    await cog.sync_member(member)
    member.add_roles.assert_awaited_once_with(
        role, reason="Moka : pause après 21 jours sans échange observé"
    )
    member.roles = [role, Mock()]
    await cog.sync_member(member)
    assert member.add_roles.await_count == 1
    service.record_participation(1, 10, "message")
    member.remove_roles.side_effect = discord.Forbidden(
        Mock(status=403, reason="Forbidden"), "test"
    )
    with pytest.raises(discord.Forbidden):
        await cog.sync_member(member)
    member.remove_roles.side_effect = None
    await cog.sync_member(member)
    assert member.remove_roles.await_count == 2
    assert member.remove_roles.call_args.args == (role,)


async def test_recheck_before_role_add_prevents_stale_sanction(service):
    cog, guild, _ = harness(service)
    member = guild.members[0]
    service.presence_member(1, 10)
    service.clock.advance(INACTIVE_AFTER)

    async def fetch(uid):
        service.record_participation(1, uid, "message")
        return member

    guild.fetch_member.side_effect = fetch
    await cog.sync_member(member)
    member.add_roles.assert_not_awaited()


@pytest.mark.parametrize(
    "unsafe", ["permissions", "managed", "level", "staff", "admission", "penalty"]
)
async def test_unsafe_role_never_modified(service, unsafe):
    cog, guild, role = harness(service)
    if unsafe == "permissions":
        role.permissions = discord.Permissions(administrator=True)
    if unsafe == "managed":
        role.managed = True
    if unsafe == "level":
        service.set_setting(1, "level_rewards", {"3": 77})
    if unsafe == "staff":
        service.set_setting(1, "admission:staff_roles", [77])
    if unsafe == "admission":
        service.set_setting(1, "admission:member_role", 77)
    if unsafe == "penalty":
        service.set_setting(1, "role:counting_failure", 77)
    with pytest.raises(DomainError):
        await cog.sync_member(guild.members[0])
    guild.members[0].add_roles.assert_not_awaited()
    assert 77 in protected_roles(service, 1)


def test_private_report_refuses_public_role_or_member_overwrite(service):
    cog, guild, role = harness(service)
    channel = Mock(spec=discord.TextChannel)
    channel.guild = guild
    channel.overwrites = {}
    channel.permissions_for.return_value = discord.Permissions.none()
    assert private_staff_channel(service, channel)
    channel.permissions_for.return_value = discord.Permissions(view_channel=True)
    assert not private_staff_channel(service, channel)
    channel.permissions_for.return_value = discord.Permissions.none()
    channel.overwrites = {guild.members[0]: discord.PermissionOverwrite(view_channel=True)}
    assert not private_staff_channel(service, channel)


async def test_staff_bilan_checks_current_roles_not_cached_permissions(service):
    cog, guild, _ = harness(service)
    interaction = SimpleNamespace(
        guild=guild,
        guild_id=1,
        user=guild.members[0],
        id=123,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    with pytest.raises(DomainError, match="réservé au staff"):
        await cog.bilan.callback(cog, interaction, 1)
    interaction.followup.send.assert_not_awaited()
    guild.members[0].guild_permissions = discord.Permissions(manage_guild=True)
    await cog.bilan.callback(cog, interaction, 1)
    assert interaction.followup.send.call_args.kwargs["ephemeral"] is True


async def test_report_is_updated_in_place_and_fails_closed(service):
    cog, guild, _ = harness(service)
    role = guild.roles[0]
    channel = Mock(spec=discord.TextChannel)
    channel.guild, channel.overwrites = guild, {}
    channel.permissions_for.return_value = discord.Permissions.none()
    channel.send = AsyncMock(return_value=SimpleNamespace(id=987))
    partial = SimpleNamespace(edit=AsyncMock())
    bot_message = SimpleNamespace(author=SimpleNamespace(id=999), delete=AsyncMock())
    cog.bot.user = SimpleNamespace(id=999)
    channel.fetch_message = AsyncMock(return_value=bot_message)
    channel.get_partial_message.return_value = partial
    guild.get_channel = lambda _: channel
    service.set_setting(1, "presence:journal", 66)
    rows = cog.rows(guild)
    await cog.publish_report(guild, rows)
    await cog.publish_report(guild, rows)
    channel.send.assert_awaited_once()
    assert channel.send.call_args.kwargs["allowed_mentions"].everyone is False
    cog.report_stamps.clear()
    await cog.publish_report(guild, rows)
    partial.edit.assert_awaited_once()
    channel.permissions_for.return_value = discord.Permissions(view_channel=True)
    with pytest.raises(DomainError, match="uniquement par le staff"):
        await cog.publish_report(guild, rows)
    assert partial.edit.await_count == 1
    bot_message.delete.assert_awaited_once()
    assert service.get_setting(1, "presence:report") == 0
    assert role.id == 77


async def test_absence_private_own_account_and_honest_retry(service):
    cog, guild, _ = harness(service)
    interaction = SimpleNamespace(
        guild=guild,
        guild_id=1,
        user=guild.members[0],
        id=123,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    cog.sync_member = AsyncMock(side_effect=DomainError("Role missing"))
    await cog.absence.callback(cog, interaction, 7)
    assert service.presence_member(1, 10)["announced"]
    assert service.export_user(1, 20)["presence"] == []
    payload = interaction.followup.send.call_args.kwargs
    assert payload["ephemeral"] is True
    assert "n'a pas encore pu" in payload["embed"].description
    await cog.retour.callback(cog, interaction)
    assert not service.presence_member(1, 10)["announced"]
    assert service.presence_member(1, 10)["last_at"] is None


async def test_deleted_report_recreated_once_and_other_messages_preserved(service):
    cog, guild, _ = harness(service)
    cog.bot.user = SimpleNamespace(id=999)
    channel = Mock(spec=discord.TextChannel)
    channel.guild, channel.overwrites = guild, {}
    channel.permissions_for.return_value = discord.Permissions.none()
    channel.send = AsyncMock(return_value=SimpleNamespace(id=988))
    partial = SimpleNamespace(
        edit=AsyncMock(side_effect=discord.NotFound(Mock(status=404, reason="Not found"), "test"))
    )
    channel.get_partial_message.return_value = partial
    guild.get_channel = lambda _: channel
    service.set_setting(1, "presence:journal", 66)
    service.set_setting(1, "presence:report", 987)
    await cog.publish_report(guild, cog.rows(guild))
    channel.send.assert_awaited_once()
    assert service.get_setting(1, "presence:report") == 988
    other_message = SimpleNamespace(author=SimpleNamespace(id=123), delete=AsyncMock())
    channel.fetch_message = AsyncMock(return_value=other_message)
    await cog.hide_exposed_report(guild, channel)
    other_message.delete.assert_not_awaited()


async def test_member_departure_erases_only_presence_and_own_candidate(service):
    cog, guild, _ = harness(service)
    service.presence_member(1, 10)
    service.presence_member(2, 10)
    cog.conversations = {(1, 55): (10, service.clock(), 100), (2, 55): (10, service.clock(), 100)}
    await cog.on_member_remove(guild.members[0])
    assert service.export_user(1, 10)["presence"] == []
    assert service.export_user(2, 10)["presence"]
    assert (1, 55) not in cog.conversations and (2, 55) in cog.conversations
