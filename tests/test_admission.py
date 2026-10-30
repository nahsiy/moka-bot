from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from moka.admission import keyword_hash
from moka.admission_discord import AdmissionView, ReadingModal, entry_overwrites, require_access
from moka.admission_setup import (
    charter,
    gate_overwrites,
    prepare_admission,
    validate_arrival_announcements,
)
from moka.base import DomainError
from moka.bot import MokaBot
from moka.cogs.admission import AdmissionCog
from moka.discord_ui import context
from moka.role_panels import protected_roles


@pytest.fixture
def enabled(service):
    service.set_setting(1, "admission:enabled", True)
    service.set_setting(1, "admission:keyword_hash", keyword_hash("Noisette"))
    service.set_setting(1, "admission:member_role", 100)
    service.set_setting(1, "admission:waiting_role", 101)
    service.set_setting(1, "admission:staff_roles", [102])
    service.begin_admission(1, 10)
    return service


def test_state_is_isolated_persistent_and_idempotent(enabled):
    first = enabled.admission(1, 10)
    assert enabled.begin_admission(1, 10, established=True) == first
    assert not enabled.admitted(1, 10)
    assert enabled.admitted(2, 10)  # Pas d'accueil activé dans l'autre serveur.
    enabled.set_setting(2, "admission:enabled", True)
    assert not enabled.admitted(2, 10)
    assert enabled.admission(2, 10) is None
    with pytest.raises(DomainError):
        enabled.begin_admission(3, 10)


def test_reading_retry_cooldown_and_required_before_approval(enabled):
    with pytest.raises(DomainError, match="lecture"):
        enabled.decide_admission(1, 10, 20, "approved")
    assert not enabled.confirm_reading(1, 10, "wrong")
    with pytest.raises(DomainError, match="secondes"):
        enabled.confirm_reading(1, 10, "noisette")
    enabled.clock.advance(5)
    assert enabled.confirm_reading(1, 10, "  NOISETTE  ")
    assert enabled.confirm_reading(1, 10, "any")  # Une lecture déjà confirmée reste confirmée.
    assert enabled.decide_admission(1, 10, 20, "approved")
    assert not enabled.decide_admission(1, 10, 20, "approved")
    assert enabled.admitted(1, 10)
    with pytest.raises(DomainError, match="déjà"):
        enabled.decide_admission(1, 10, 20, "refused")
    with pytest.raises(DomainError):
        enabled.decide_admission(1, 10, 10, "approved")


def test_refusal_reopening_and_minimal_personal_export(enabled):
    enabled.request_interview_voice(1, 10)
    enabled.decide_admission(1, 10, 20, "refused")
    assert not enabled.admitted(1, 10)
    with pytest.raises(DomainError):
        enabled.confirm_reading(1, 10, "noisette")
    enabled.reopen_admission(1, 10)
    row = enabled.admission(1, 10)
    assert row["read_at"] is None and not row["voice_requested"]
    assert enabled.export_user(1, 10)["admissions"] == [row]
    enabled.forget_user(1, 10)
    assert enabled.admission(1, 10) == row  # L'effacement du jeu ne contourne pas la porte.
    assert "noisette" not in str(row).lower()


@pytest.fixture
def guild(enabled, monkeypatch):
    client = discord.Client(intents=discord.Intents.none())
    state = client._connection

    async def members(self, **kwargs):
        for member in self.members:
            yield member

    monkeypatch.setattr(discord.Guild, "fetch_members", members)
    state.user = discord.ClientUser(
        state=state, data={"id": "999", "username": "Moka", "discriminator": "0", "avatar": None}
    )
    base = discord.Permissions(
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        connect=True,
        speak=True,
        use_application_commands=True,
    )
    roles = [
        {"id": str(rid), "name": name, "permissions": str(perms.value), "position": pos}
        for rid, name, perms, pos in (
            (1, "@everyone", base, 0),
            (100, "Membre", discord.Permissions.none(), 1),
            (101, "En attente", discord.Permissions.none(), 2),
            (102, "Staff", discord.Permissions.none(), 4),
            (103, "Niveau", discord.Permissions.none(), 3),
            (104, "Préférence", discord.Permissions.none(), 3),
            (
                199,
                "Moka",
                discord.Permissions(
                    manage_roles=True,
                    manage_channels=True,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                ),
                99,
            ),
        )
    ]
    g = discord.Guild(
        state=state,
        data={
            "id": "1",
            "name": "Exemple",
            "owner_id": "90",
            "roles": roles,
            "emojis": [],
            "stickers": [],
            "features": [],
        },
    )
    for uid, rids in ((10, []), (20, [102]), (30, [100]), (40, []), (90, []), (999, [199])):
        member = discord.Member(
            guild=g,
            state=state,
            data={
                "user": {
                    "id": str(uid),
                    "username": f"Personne{uid}",
                    "discriminator": "0",
                    "avatar": None,
                    "bot": uid == 999,
                },
                "roles": [str(r) for r in rids],
                "flags": 0,
            },
        )
        g._add_member(member)
    state._guilds[g.id] = g
    monkeypatch.setattr(
        discord.Guild, "fetch_member", AsyncMock(side_effect=lambda uid: g.get_member(uid))
    )
    return g


def channel(guild, cid, overwrites, *, category=None, voice=False):
    data = {
        "id": str(cid),
        "name": "exemple",
        "position": 0,
        "type": 2 if voice else 0,
        "bitrate": 64000,
        "user_limit": 0,
        "parent_id": str(category) if category else None,
        "permission_overwrites": [
            {
                "id": str(t.id),
                "type": 0 if isinstance(t, discord.Role) else 1,
                "allow": str(o.pair()[0].value),
                "deny": str(o.pair()[1].value),
            }
            for t, o in overwrites.items()
        ],
    }
    cls = discord.VoiceChannel if voice else discord.TextChannel
    ch = cls(state=guild._state, guild=guild, data=data)
    guild._channels[ch.id] = ch
    return ch


@pytest.mark.parametrize("voice", [False, True])
def test_private_room_permissions_candidate_staff_bot_only(enabled, guild, voice):
    ch = channel(
        guild,
        501,
        entry_overwrites(guild, enabled, candidate=guild.get_member(10), writable=True),
        voice=voice,
    )
    for uid in (10, 20, 999, 90):
        p = ch.permissions_for(guild.get_member(uid))
        assert p.view_channel
    for uid in (30, 40):
        assert not ch.permissions_for(guild.get_member(uid)).view_channel
    closed = channel(
        guild,
        502,
        entry_overwrites(guild, enabled, candidate=guild.get_member(10), writable=False),
        voice=voice,
    )
    assert closed.permissions_for(guild.get_member(10)).view_channel
    assert not closed.permissions_for(guild.get_member(10)).send_messages
    if voice:
        assert not closed.permissions_for(guild.get_member(10)).connect
    assert closed.permissions_for(guild.get_member(20)).send_messages


def test_gate_preserves_private_staff_and_game_sanctions(enabled, guild):
    public = channel(
        guild, 510, {guild.get_role(101): discord.PermissionOverwrite(send_messages=False)}
    )
    private = channel(
        guild,
        511,
        {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(102): discord.PermissionOverwrite(view_channel=True),
        },
    )
    for ch in (public, private):
        gated = channel(
            guild,
            ch.id + 10,
            gate_overwrites(ch, guild, guild.get_role(100), [guild.get_role(102)]),
        )
        for role_ids in ([], [101], [101, 103, 104]):
            pending = guild.get_member(10)
            pending._roles = discord.utils.SnowflakeList(role_ids)
            assert not gated.permissions_for(pending).view_channel
        assert gated.permissions_for(guild.get_member(20)).view_channel
        if ch == public:
            assert gated.permissions_for(guild.me).view_channel
        assert gated.permissions_for(guild.get_member(30)).view_channel == (ch == public)
    assert (
        gate_overwrites(public, guild, guild.get_role(100), [guild.get_role(102)])[
            guild.get_role(101)
        ].send_messages
        is False
    )


def test_context_blocks_stale_buttons_and_role_alone_cannot_open_commands(enabled, guild):
    m = guild.get_member(10)
    i = SimpleNamespace(guild=guild, user=m, id=5, client=SimpleNamespace(service=enabled))
    with pytest.raises(DomainError, match="premier café"):
        context(i)
    m._roles = discord.utils.SnowflakeList([100])
    with pytest.raises(DomainError):
        context(i)
    enabled.confirm_reading(1, 10, "noisette")
    enabled.decide_admission(1, 10, 20, "approved")
    assert context(i) == (1, 10, "5")
    m._roles = discord.utils.SnowflakeList([])
    with pytest.raises(DomainError):
        require_access(enabled, m)
    assert context(i, allow_pending=True) == (1, 10, "5")
    assert {100, 101, 102} <= protected_roles(enabled, 1)


def interaction(guild, service, uid=20, cid=501):
    return SimpleNamespace(
        guild=guild,
        guild_id=guild.id,
        user=guild.get_member(uid),
        channel_id=cid,
        client=SimpleNamespace(service=service),
    )


def cog(service):
    bot = SimpleNamespace(
        service=service, store=service.store, audit=AsyncMock(), level_roles=AsyncMock()
    )
    return AdmissionCog(bot)


async def test_fresh_staff_permissions_and_candidate_channel_checked(enabled, guild):
    enabled.bind_admission(1, 10, channel=501)
    c = cog(enabled)
    assert c.candidate(interaction(guild, enabled, uid=10))["user"] == 10
    with pytest.raises(DomainError):
        c.candidate(interaction(guild, enabled, uid=40))
    with pytest.raises(DomainError):
        c.candidate(interaction(guild, enabled, uid=10, cid=555))
    assert (await c.staff_candidate(interaction(guild, enabled)))["user"] == 10
    guild.get_member(20)._roles = discord.utils.SnowflakeList([])
    with pytest.raises(DomainError, match="staff"):
        await c.staff_candidate(interaction(guild, enabled))
    with pytest.raises(DomainError):
        await c.staff_candidate(interaction(guild, enabled, uid=10))


async def test_approval_partial_discord_failure_resumes_without_new_decision(enabled, guild):
    enabled.bind_admission(1, 10, channel=501)
    enabled.confirm_reading(1, 10, "noisette")
    c = cog(enabled)
    c.sync = AsyncMock(side_effect=[DomainError("Discord temporairement indisponible"), None])
    with pytest.raises(DomainError):
        await c.decide(interaction(guild, enabled), "approved")
    assert enabled.admission(1, 10)["status"] == "approved"
    await c.decide(interaction(guild, enabled), "approved")
    assert c.sync.await_count == 2
    assert enabled.admission(1, 10)["decided_by"] == 20


async def test_voice_requires_candidate_request_and_staff(enabled, guild):
    enabled.bind_admission(1, 10, channel=501)
    c = cog(enabled)
    with pytest.raises(DomainError, match="demander"):
        await c.open_voice(interaction(guild, enabled))
    enabled.request_interview_voice(1, 10)
    with pytest.raises(DomainError, match="staff"):
        await c.open_voice(interaction(guild, enabled, uid=10))


async def test_pending_messages_do_not_create_account_or_reward(enabled, guild):
    bot = MokaBot(enabled.config, enabled)
    try:
        m = SimpleNamespace(
            guild=guild, author=guild.get_member(10), webhook_id=None, content="Bonjour", id=90
        )
        await bot.on_message(m)
        with enabled.store.read() as con:
            assert con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
        await bot.level_roles(guild.get_member(10))
        with enabled.store.read() as con:
            assert con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
    finally:
        await bot.close()


async def test_persistent_components_and_rules_age():
    view = AdmissionView()
    assert view.is_persistent()
    assert len({i.custom_id for i in view.children}) == 5
    assert "21 ans" in charter("noisette").description
    assert "30 ans" not in charter("noisette").description
    assert ReadingModal().keyword.max_length == 80


async def test_installer_rejects_unreviewed_role_bypass_before_discord_mutation(enabled, guild):
    enabled.set_setting(1, "admission:enabled", False)
    channel(guild, 600, {guild.get_role(103): discord.PermissionOverwrite(view_channel=True)})
    with pytest.raises(DomainError, match="non staff"):
        await prepare_admission(guild, enabled, keyword="noisette")


def test_arrival_notices_must_not_reveal_pending_members_to_the_community(enabled, guild):
    room = channel(guild, 810, {guild.default_role: discord.PermissionOverwrite(view_channel=True)})
    guild._system_channel_id = room.id
    guild._system_channel_flags = 0
    with pytest.raises(DomainError, match="annonces d'arrivée"):
        validate_arrival_announcements(guild, enabled)
    # Un salon masqué à @everyone mais ouvert aux membres reste un salon commun.
    room = channel(
        guild,
        810,
        {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(100): discord.PermissionOverwrite(view_channel=True),
        },
    )
    with pytest.raises(DomainError):
        validate_arrival_announcements(guild, enabled)
    guild._system_channel_flags = discord.SystemChannelFlags(join_notifications=False).value
    validate_arrival_announcements(guild, enabled)
    guild._system_channel_flags = 0
    channel(
        guild,
        810,
        {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(102): discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        },
    )
    validate_arrival_announcements(guild, enabled)


async def test_installation_refuses_public_arrival_notices_before_other_mutations(enabled, guild):
    enabled.set_setting(1, "admission:enabled", False)
    room = channel(guild, 810, {})
    guild._system_channel_id = room.id
    guild._system_channel_flags = 0
    with pytest.raises(DomainError, match="annonces d'arrivée"):
        await prepare_admission(guild, enabled, keyword="noisette")


def test_unloaded_system_channel_cannot_bypass_arrival_check(enabled, guild):
    guild._system_channel_id = 999999
    guild._system_channel_flags = 0
    with pytest.raises(DomainError, match="salon système"):
        validate_arrival_announcements(guild, enabled)
    guild._system_channel_flags = discord.SystemChannelFlags(join_notifications=False).value
    validate_arrival_announcements(guild, enabled)


async def test_duplicate_joins_and_restart_reuse_private_room(enabled, guild, monkeypatch):
    import asyncio

    category = discord.CategoryChannel(
        state=guild._state,
        guild=guild,
        data={"id": "700", "name": "Entrée", "position": 0, "type": 4, "permission_overwrites": []},
    )
    guild._channels[700] = category
    enabled.set_setting(1, "admission:category", 700)
    created = []

    async def create(self, name, **kwargs):
        ch = channel(guild, 701, kwargs["overwrites"], category=700)
        ch.topic = kwargs["topic"]
        created.append(ch)
        return ch

    async def add(self, *roles, **kwargs):
        self._roles = discord.utils.SnowflakeList({*self._roles, *(r.id for r in roles)})

    monkeypatch.setattr(discord.Guild, "create_text_channel", create)
    monkeypatch.setattr(discord.Member, "add_roles", add)
    monkeypatch.setattr(discord.TextChannel, "edit", AsyncMock())
    c = cog(enabled)
    c.refresh = AsyncMock()
    await asyncio.gather(
        c.ensure_member(guild.get_member(10)), c.ensure_member(guild.get_member(10))
    )
    assert len(created) == 1
    assert enabled.admission(1, 10)["channel"] == 701
    assert [r.id for r in guild.get_member(10).roles] == [1, 101]
    # Interruption après création Discord mais avant liaison SQLite : le topic privé sert à reprendre.
    enabled.bind_admission(1, 10, channel=None)
    restarted = cog(enabled)
    restarted.refresh = AsyncMock()
    await restarted.ensure_member(guild.get_member(10))
    assert len(created) == 1
    assert enabled.admission(1, 10)["channel"] == 701


async def test_admission_commands_are_in_offline_command_tree(service):
    from moka.__main__ import check_commands

    commands = await check_commands(service.config)
    welcome = next(c for c in commands if c["name"] == "accueil")
    assert {opt["name"] for opt in welcome["options"]} == {"etat", "reprendre"}


@pytest.fixture
def reading_notice(enabled, guild, monkeypatch):
    room = channel(
        guild, 501, entry_overwrites(guild, enabled, candidate=guild.get_member(10), writable=True)
    )
    enabled.bind_admission(1, 10, channel=501, message=600)
    sent = []

    async def send(self, content=None, **kwargs):
        message = SimpleNamespace(
            id=900 + len(sent), author=guild.me, embeds=[kwargs["embed"]], content=content
        )
        sent.append((message, kwargs))
        return message

    async def history(self, **kwargs):
        for message, _ in sent:
            yield message

    monkeypatch.setattr(discord.TextChannel, "send", send)
    monkeypatch.setattr(discord.TextChannel, "history", history)
    c = cog(enabled)
    c.refresh = AsyncMock()
    i = interaction(guild, enabled, uid=10)
    i.client.get_cog = lambda _: c
    i.response = SimpleNamespace(defer=AsyncMock())
    i.followup = SimpleNamespace(send=AsyncMock())
    modal = ReadingModal()
    modal.keyword._value = "noisette"
    return SimpleNamespace(
        room=room, sent=sent, cog=c, interaction=i, modal=modal, service=enabled, guild=guild
    )


async def test_reading_confirmation_creates_one_staff_alert(reading_notice):
    p = reading_notice
    i, modal, sent, enabled, room = p.interaction, p.modal, p.sent, p.service, p.room
    await modal.on_submit(i)
    await modal.on_submit(i)
    assert enabled.admission(1, 10)["read_at"] is not None
    assert len(sent) == 1, (
        "La lecture doit créer un nouveau message, pas seulement modifier le panneau."
    )
    message, kwargs = sent[0]
    assert "<@20>" in message.content and "<@10>" not in message.content
    assert "noisette" not in message.embeds[0].description.casefold()
    assert kwargs["allowed_mentions"].to_dict()["users"] == [20, 90]
    assert room.id == 501


async def test_reading_alert_recovers_after_restart_and_lost_receipt(reading_notice):
    p = reading_notice
    await p.modal.on_submit(p.interaction)
    restarted = cog(p.service)
    assert not await restarted.notify_reading(p.guild, 10)
    p.service.set_setting(1, "admission:reading_notice:10", {})
    # Simuler le retour JSON de Discord après normalisation du timestamp.
    p.sent[0][0].embeds = [discord.Embed.from_dict(p.sent[0][0].embeds[0].to_dict())]
    assert not await restarted.notify_reading(p.guild, 10)
    assert len(p.sent) == 1
    assert p.service.get_setting(1, "admission:reading_notice:10")["message"] == 900


async def test_wrong_keyword_does_not_alert_staff(reading_notice):
    p = reading_notice
    p.modal.keyword._value = "incorrect"
    await p.modal.on_submit(p.interaction)
    assert not p.sent and p.service.admission(1, 10)["read_at"] is None


async def test_reading_notification_failure_retries_without_reconfirming(
    reading_notice, monkeypatch
):
    p = reading_notice
    sender = discord.TextChannel.send
    monkeypatch.setattr(
        discord.TextChannel,
        "send",
        AsyncMock(
            side_effect=discord.Forbidden(SimpleNamespace(status=403, reason="refus"), "refus")
        ),
    )
    await p.modal.on_submit(p.interaction)
    assert p.service.admission(1, 10)["read_at"] is not None
    assert not p.service.get_setting(1, "admission:reading_notice:10")
    monkeypatch.setattr(discord.TextChannel, "send", sender)
    assert await p.cog.notify_reading(p.guild, 10)
    assert len(p.sent) == 1


async def test_reading_alert_rejects_a_public_interview(reading_notice):
    p = reading_notice
    p.service.confirm_reading(1, 10, "noisette")
    channel(p.guild, 501, {p.guild.default_role: discord.PermissionOverwrite(view_channel=True)})
    assert not await p.cog.notify_reading(p.guild, 10)
    assert not p.sent


async def test_new_reading_after_refusal_creates_a_new_alert(reading_notice):
    p = reading_notice
    await p.modal.on_submit(p.interaction)
    p.service.decide_admission(1, 10, 20, "refused")
    p.service.reopen_admission(1, 10)
    p.service.clock.advance(10)
    await p.modal.on_submit(p.interaction)
    assert len(p.sent) == 2


async def test_closed_admission_is_not_announced_as_pending(reading_notice):
    p = reading_notice
    p.service.confirm_reading(1, 10, "noisette")
    p.service.decide_admission(1, 10, 20, "approved")
    assert not await p.cog.notify_reading(p.guild, 10)
    channel(
        p.guild,
        501,
        entry_overwrites(p.guild, p.service, candidate=p.guild.get_member(10), writable=False),
    )
    assert await p.cog.notify_reading(p.guild, 10, include_closed=True, ping=False)
    message, kwargs = p.sent[0]
    assert message.content is None and kwargs["allowed_mentions"].to_dict()["users"] == []
    assert "déjà été validé" in message.embeds[0].description


@pytest.mark.parametrize("status", ["pending", "refused", "approved"])
async def test_interest_room_roles_follow_admission_status(enabled, guild, monkeypatch, status):
    enabled.set_setting(1, "role_channels", {"104": 800})
    member = guild.get_member(10)
    member._roles = discord.utils.SnowflakeList([100, 103, 104])
    room = channel(
        guild,
        800,
        {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_role(104): discord.PermissionOverwrite(view_channel=True),
        },
    )
    if status == "approved":
        enabled.confirm_reading(1, 10, "noisette")
        enabled.decide_admission(1, 10, 20, status)
    elif status == "refused":
        enabled.decide_admission(1, 10, 20, status)

    async def remove(self, *roles, **kwargs):
        self._roles = discord.utils.SnowflakeList(set(self._roles) - {r.id for r in roles})

    async def add(self, *roles, **kwargs):
        self._roles = discord.utils.SnowflakeList(set(self._roles) | {r.id for r in roles})

    monkeypatch.setattr(discord.Member, "remove_roles", remove)
    monkeypatch.setattr(discord.Member, "add_roles", add)
    c = cog(enabled)
    c.refresh = AsyncMock()
    await c.sync(member)
    assert (104 in member._roles) == (status == "approved")
    assert room.permissions_for(member).view_channel == (status == "approved")
    assert 103 in member._roles  # Le rôle de niveau, sans accès, est conservé.


@pytest.fixture
def closing_case(enabled, guild, monkeypatch):
    from moka.admission_closure import close_approved

    enabled.confirm_reading(1, 10, "noisette")
    enabled.decide_admission(1, 10, 20, "approved")
    enabled.bind_admission(1, 10, channel=501, message=601, voice=502)
    candidate = guild.get_member(10)
    candidate._roles = discord.utils.SnowflakeList([100])
    private = entry_overwrites(guild, enabled, candidate=candidate, writable=False)
    room = channel(guild, 501, private)
    room.topic = "moka-admission:10"
    voice = channel(guild, 502, private, voice=True)
    for key, cid in (("general_channel", 510), ("roles_channel", 511)):
        channel(
            guild,
            cid,
            {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.get_role(100): discord.PermissionOverwrite(view_channel=True),
            },
        )
        enabled.set_setting(1, "admission:" + key, cid)
    p = SimpleNamespace(
        service=enabled,
        guild=guild,
        cog=cog(enabled),
        room=room,
        voice=voice,
        sent=[],
        deleted=[],
        occupied=[],
        categories=[],
    )

    async def fetch(self, cid):
        found = self.get_channel(cid)
        if found is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "absent")
        return found

    async def fetch_member(self, uid):
        member = self.get_member(uid)
        if member is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "parti")
        return member

    async def create(self, name, **kwargs):
        seed = channel(guild, 700, kwargs["overwrites"])
        category = discord.CategoryChannel(
            state=guild._state,
            guild=guild,
            data={"id": "700", "name": name, "type": 4, "position": 0, "permission_overwrites": []},
        )
        category._overwrites = seed._overwrites
        guild._channels[700] = category
        p.categories.append(category)
        return category

    async def edit(self, **kwargs):
        if "category" in kwargs:
            assert kwargs["sync_permissions"] is False
            assert kwargs["overwrites"] == private
            self.category_id = kwargs["category"].id
        return self

    async def send(self, **kwargs):
        msg = SimpleNamespace(
            id=800 + len(p.sent),
            author=guild.me,
            embeds=[discord.Embed.from_dict(kwargs["embed"].to_dict())],
        )
        p.sent.append((msg, kwargs))
        return msg

    async def history(self, **kwargs):
        for message, _ in p.sent:
            yield message

    async def delete(self, **kwargs):
        p.deleted.append(self.id)
        guild._channels.pop(self.id, None)

    monkeypatch.setattr(discord.Guild, "fetch_channel", fetch)
    monkeypatch.setattr(discord.Guild, "fetch_member", fetch_member)
    monkeypatch.setattr(
        discord.Guild, "fetch_channels", AsyncMock(side_effect=lambda: list(guild.channels))
    )
    monkeypatch.setattr(discord.Guild, "create_category", create)
    monkeypatch.setattr(discord.TextChannel, "edit", edit)
    monkeypatch.setattr(discord.VoiceChannel, "edit", edit)
    monkeypatch.setattr(discord.TextChannel, "send", send)
    monkeypatch.setattr(discord.TextChannel, "history", history)
    monkeypatch.setattr(discord.TextChannel, "delete", delete)
    monkeypatch.setattr(discord.VoiceChannel, "delete", delete)
    monkeypatch.setattr(discord.VoiceChannel, "members", property(lambda self: p.occupied))

    async def close():
        async with p.cog.lock(1, 10):
            await close_approved(p.cog, guild, 10)

    p.close = close
    return p


async def test_approved_interview_closes_once_with_links_and_seven_day_deadline(closing_case):
    p = closing_case
    await p.close()
    first = p.service.admission_closure(1, 10)
    assert first["delete_at"] == p.service.clock() + 7 * 86400
    assert first["notice"] == 800
    assert p.room.category_id == p.voice.category_id == p.categories[0].id
    assert not p.room.permissions_for(p.guild.get_member(10)).send_messages
    assert not p.room.permissions_for(p.guild.get_member(30)).view_channel
    assert p.room.permissions_for(p.guild.get_member(20)).send_messages
    assert not p.categories[0].permissions_for(p.guild.get_member(30)).view_channel
    text = p.sent[0][0].embeds[0].description
    assert "/1/510)" in text and "/1/511)" in text
    assert str(int(first["delete_at"])) in text
    assert p.sent[0][1]["allowed_mentions"].to_dict()["parse"] == []
    p.service.clock.advance(7 * 86400 - 1)
    await p.close()
    assert p.service.admission_closure(1, 10) == first
    assert len(p.sent) == len(p.categories) == 1
    assert p.deleted == []


async def test_closure_concurrent_calls_and_restart_do_not_duplicate_notice(closing_case):
    import asyncio

    p = closing_case
    await asyncio.gather(p.close(), p.close())
    p.cog = cog(p.service)
    await p.close()
    assert len(p.sent) == len(p.categories) == 1


async def test_closing_notice_recovers_sent_message_before_local_ack(closing_case, monkeypatch):
    p = closing_case
    ack = p.service.acknowledge_admission_closure
    monkeypatch.setattr(
        p.service,
        "acknowledge_admission_closure",
        lambda *a: (_ for _ in ()).throw(RuntimeError("interruption")),
    )
    with pytest.raises(RuntimeError):
        await p.close()
    first = p.service.admission_closure(1, 10)
    assert first["notice"] is None
    p.service.clock.advance(86400)
    monkeypatch.setattr(p.service, "acknowledge_admission_closure", ack)
    await p.close()
    recovered = p.service.admission_closure(1, 10)
    assert len(p.sent) == 1 and recovered["notice"] == 800
    assert recovered["delete_at"] == first["delete_at"]


async def test_failed_closing_notice_restarts_full_seven_day_period(closing_case, monkeypatch):
    p = closing_case
    send = discord.TextChannel.send
    monkeypatch.setattr(
        discord.TextChannel,
        "send",
        AsyncMock(
            side_effect=discord.Forbidden(
                SimpleNamespace(status=403, reason="Forbidden"), "indisponible"
            )
        ),
    )
    with pytest.raises(discord.Forbidden):
        await p.close()
    p.service.clock.advance(8 * 86400)
    monkeypatch.setattr(discord.TextChannel, "send", send)
    await p.close()
    assert p.service.admission_closure(1, 10)["delete_at"] == p.service.clock() + 7 * 86400
    assert p.deleted == []


async def test_expired_interview_deletes_only_bound_rooms_and_preserves_approval(closing_case):
    from moka.service import Service

    p = closing_case
    await p.close()
    original = p.service.admission(1, 10)
    p.service.clock.advance(7 * 86400)
    # Nouvelle instance métier, mêmes données persistantes, aucun timer en mémoire.
    p.service = Service(p.service.store, p.service.config, clock=p.service.clock)
    p.cog = cog(p.service)
    await p.close()
    assert p.deleted == [501, 502]
    assert p.guild.get_channel(510) is not None
    row = p.service.admission(1, 10)
    assert row["status"] == "approved" and row["decided_by"] == original["decided_by"]
    assert row["read_at"] == original["read_at"]
    assert row["channel"] is row["voice"] is row["message"] is None
    assert p.service.admission_closure(1, 10) is None
    assert p.service.approved_interviews(1) == []
    assert p.service.begin_admission(1, 10)["status"] == "approved"
    await p.close()
    assert p.deleted == [501, 502]


async def test_expiry_runs_for_departed_member_from_database(closing_case):
    p = closing_case
    await p.close()
    p.guild._members.pop(10)
    p.service.clock.advance(7 * 86400)
    p.cog.ensure_member = AsyncMock()
    await p.cog.reconcile(p.guild)
    assert p.deleted == [501, 502]
    assert p.service.admitted(1, 10)


async def test_expiry_waits_for_occupied_voice_then_finishes(closing_case):
    p = closing_case
    await p.close()
    p.service.clock.advance(7 * 86400)
    p.occupied.append(p.guild.get_member(20))
    await p.close()
    assert p.deleted == [501]
    assert p.service.admission(1, 10)["voice"] == 502
    assert p.service.admission_closure(1, 10) is not None
    p.occupied.clear()
    await p.close()
    assert p.deleted == [501, 502]
    assert p.service.admission_closure(1, 10) is None


async def test_expiry_retries_forbidden_and_recovers_already_deleted_rooms(
    closing_case, monkeypatch
):
    p = closing_case
    await p.close()
    p.service.clock.advance(7 * 86400)
    monkeypatch.setattr(
        discord.TextChannel,
        "delete",
        AsyncMock(
            side_effect=discord.Forbidden(
                SimpleNamespace(status=403, reason="Forbidden"), "indisponible"
            )
        ),
    )
    with pytest.raises(discord.Forbidden):
        await p.close()
    assert p.service.admission(1, 10)["channel"] == 501
    # Discord a supprimé le texte, mais Moka a été interrompu avant sa mise à jour locale.
    p.guild._channels.pop(501)
    await p.close()
    assert p.service.admission_closure(1, 10) is None
    assert p.deleted == [502]


@pytest.mark.parametrize("fault", ["topic", "privacy", "binding"])
async def test_expiry_refuses_unrecognized_or_public_rooms(closing_case, fault):
    p = closing_case
    await p.close()
    p.service.clock.advance(7 * 86400)
    if fault == "topic":
        p.room.topic = "salon communautaire"
    elif fault == "privacy":
        p.room._overwrites = []
    else:
        p.service.bind_admission(1, 10, channel=510)
    with pytest.raises(DomainError):
        await p.close()
    assert p.deleted == []
    assert p.service.admission_closure(1, 10) is not None


@pytest.mark.parametrize("status", ["pending", "refused"])
async def test_only_approved_interviews_are_scheduled(enabled, guild, status):
    from moka.admission_closure import close_approved

    enabled.bind_admission(1, 10, channel=501)
    if status == "refused":
        enabled.decide_admission(1, 10, 20, status)
    await close_approved(cog(enabled), guild, 10)
    assert enabled.plan_admission_closure(1, 10) is None
    assert enabled.approved_interviews(1) == []


def test_closure_schema_is_additive_and_server_isolated(enabled):
    with enabled.store.transaction() as con:
        con.execute("DROP TABLE admission_closures")
    enabled.store.initialize()
    enabled.store.initialize()
    enabled.bind_admission(1, 10, channel=501)
    enabled.confirm_reading(1, 10, "noisette")
    enabled.decide_admission(1, 10, 20, "approved")
    planned = enabled.plan_admission_closure(1, 10)
    assert planned["notice"] is planned["delete_at"] is None
    assert enabled.admission_closure(2, 10) is None
    assert enabled.approved_interviews(2) == []
    with pytest.raises(DomainError):
        enabled.admission_closure(3, 10)
    with pytest.raises(DomainError):
        enabled.finish_admission_closure(1, 10)


@pytest.mark.parametrize("failed_sync", [False, True])
async def test_reconcile_closes_each_interview_once_and_retries_failed_member(
    closing_case, monkeypatch, failed_sync
):
    from moka.cogs import admission

    p = closing_case
    close = AsyncMock(wraps=admission.close_approved)
    monkeypatch.setattr(admission, "close_approved", close)

    async def ensure(member):
        if member.id != 10:
            return
        if failed_sync:
            raise DomainError("Synchronisation momentanément impossible")
        async with p.cog.lock(1, 10):
            await admission.close_approved(p.cog, p.guild, 10)

    p.cog.ensure_member = ensure
    await p.cog.reconcile(p.guild)
    close.assert_awaited_once_with(p.cog, p.guild, 10)
    assert len(p.sent) == 1
    assert p.service.admission_closure(1, 10)["notice"] is not None
