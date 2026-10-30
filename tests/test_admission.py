from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from moka.admission import keyword_hash
from moka.admission_discord import AdmissionView, ReadingModal, entry_overwrites, require_access
from moka.admission_setup import charter, gate_overwrites, prepare_admission
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
