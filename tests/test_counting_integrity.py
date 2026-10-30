from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.base import DomainError
from moka.bot import MokaBot
from moka.cogs.community import CommunityCog
from moka.cogs.rates import RatesCog
from moka.counting_integrity import TRACE_SECONDS
from moka.service import Service


def tracked(service):
    service.set_setting(1, "role:counting_cheat", 77)
    assert service.counting(1, 5, 10, "0+1", 100)["valid"]


def penalize(service, message=100):
    return service.inspect_counting_edit(1, 5, message, "999")


def test_only_accepted_numbers_traced_without_content(service):
    tracked(service)
    row = service.counting_validation(1, 5, 100)
    assert row["number"] == 1 and row["user"] == 10 and row["sanction_until"] is None
    assert "content" not in row
    assert service.counting_validation(1, 6, 100) is None
    assert service.counting_validation(2, 5, 100) is None
    service.counting(1, 5, 20, "oops", 101)
    assert service.counting_validation(1, 5, 101) is None
    assert service.inspect_counting_edit(1, 5, 101, "1") is None
    assert service.inspect_counting_edit(1, 5, 999, "1") is None


@pytest.mark.parametrize("equivalent", ["1", " 0 + 1 ", "(2-1)", "01", "2/2"])
def test_equivalent_edits_are_not_sanctioned(service, equivalent):
    tracked(service)
    assert service.inspect_counting_edit(1, 5, 100, equivalent) is None
    assert service.game_penalty(1, 10) is None


@pytest.mark.parametrize("replacement", ["2", "1/2", "bonjour", ""])
def test_changed_or_invalid_value_sanctions_without_altering_chain_or_money(service, replacement):
    tracked(service)
    service.counting(1, 5, 20, "2", 101)
    state = service.counting_status(1, 5)
    balance = service.profile(1, 10, viewer=10)
    row = service.inspect_counting_edit(1, 5, 100, replacement)
    assert row["sanction_until"] == service.clock() + 3600
    assert service.all_games_penalty(1, 10)["penalty_role"] == 77
    assert service.counting_status(1, 5) == state
    assert service.profile(1, 10, viewer=10) == balance
    assert service.word(1, 6, 10, "tomate", 102)["scope"] == "all"
    assert service.counting(1, 5, 10, "3", 103)["blocked"]
    assert service.all_games_penalty(1, 20) is None
    assert service.all_games_penalty(2, 10) is None


def test_repeated_concurrent_edits_do_not_renew_or_duplicate(service):
    tracked(service)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: penalize(service), range(2)))
    assert sum(not r["replayed"] for r in results) == 1
    first = results[0]["sanction_until"]
    service.clock.advance(900)
    assert penalize(service)["replayed"]
    assert service.all_games_penalty(1, 10)["penalty_until"] == first
    assert len(service.pending_counting_edits()) == 1
    with service.store.read() as con:
        assert (
            con.execute("SELECT COUNT(*) FROM role_grants WHERE reason='counting-edit'").fetchone()[
                0
            ]
            == 1
        )


def test_boundary_restart_disabled_role_and_wrong_author(service):
    tracked(service)
    assert service.inspect_counting_edit(1, 5, 100, "2", author=20) is None
    service.set_setting(1, "feature:counting", False)
    assert penalize(service) is None
    service.set_setting(1, "feature:counting", True)
    service.set_setting(1, "counting:cheat_seconds", 0)
    assert penalize(service) is None
    service.set_setting(1, "counting:cheat_seconds", 3600)
    row = penalize(service)
    restart = Service(service.store, service.config, clock=service.clock)
    assert restart.all_games_penalty(1, 10)
    service.set_setting(1, "counting:cheat_seconds", 0)
    assert restart.all_games_penalty(1, 10)
    service.clock.advance(3600)
    assert restart.all_games_penalty(1, 10) is None
    assert restart.inspect_counting_edit(1, 5, 100, "3")["sanction_until"] == row["sanction_until"]
    with pytest.raises(DomainError):
        service.inspect_counting_edit(999, 5, 100, "2")


def test_no_role_means_no_new_corvee_and_collision_is_atomic(service):
    service.counting(1, 5, 10, "1", 100)
    assert penalize(service) is None
    service.set_setting(1, "role:counting_cheat", 77)
    with service.store.transaction() as con:
        con.execute("INSERT INTO role_grants VALUES(1,10,77,'other',?,0)", (service.clock() + 100,))
    with pytest.raises(DomainError, match="dédié"):
        penalize(service)
    assert service.counting_validation(1, 5, 100)["sanction_until"] is None
    with service.store.read() as con:
        assert con.execute("SELECT reason FROM role_grants").fetchone()[0] == "other"


@pytest.mark.parametrize(
    "game", ["bet", "rob", "hack", "jackpot", "goblin", "hug", "join", "finish"]
)
def test_games_and_old_buttons_block_before_mutation(service, fund, game):
    fund(10, 5000)
    fund(20, 5000)
    tracked(service)
    hack = service.start_event(1, 8, 10, "hack", "pre-hack")["event_id"]
    hug = service.start_event(1, 8, 20, "hug", "pre-hug")["event_id"]
    old = service.bet(1, 10, 10, "old-bet")
    penalize(service)
    before = service.profile(1, 10, viewer=10)
    actions = {
        "bet": lambda: service.bet(1, 10, 10, "old-bet"),
        "rob": lambda: service.rob(1, 10, 20, "new-rob"),
        "hack": lambda: service.start_event(1, 8, 10, "hack", "new-hack"),
        "jackpot": lambda: service.start_event(1, 8, 10, "jackpot", "new-jackpot"),
        "goblin": lambda: service.start_event(1, 8, 10, "goblin", "new-goblin"),
        "hug": lambda: service.start_event(1, 8, 10, "hug", "new-hug"),
        "join": lambda: service.join_event(1, 10, hug, "new-join"),
        "finish": lambda: service.finish_hack(1, 10, hack, "new-finish"),
    }
    with pytest.raises(DomainError, match="corvée"):
        actions[game]()
    assert service.profile(1, 10, viewer=10) == before
    assert service.get_event(1, hack)["status"] == "active"
    assert not service.get_event(1, hug)["participants"]
    assert old["replayed"] is False


def test_ordinary_penalty_stays_limited_and_bank_data_exit_settlement_remain_available(
    service, fund
):
    fund(10, 5000)
    tracked(service)
    service.set_setting(1, "role:counting_failure", 99)
    service.word(1, 6, 10, "deux mots", 200)
    assert service.bet(1, 10, 10, "before")["replayed"] is False
    hack = service.start_event(1, 8, 10, "hack", "pre-hack")["event_id"]
    event = service.start_event(1, 8, 20, "hug", "pre-hug")["event_id"]
    service.join_event(1, 10, event, "pre-join")
    penalize(service)
    assert service.bank_move(1, 10, 100, "deposit")["amount"] == 100
    assert service.export_user(1, 10)["counting_validations"]
    assert service.finish_hack(1, 10, hack, "abandon", abandon=True)["abandoned"]
    service.clock.advance(61)
    # Un gain déjà promis est réglé même si le membre est désormais suspendu.
    assert service.settle_event(1, event)["count"] == 1


def test_unpause_clears_both_types_and_replay_cannot_clear_new_corvee(service):
    tracked(service)
    service.counting(1, 5, 20, "2", 101)
    service.counting(1, 5, 10, "3", 102)
    service.set_setting(1, "role:counting_failure", 99)
    service.word(1, 6, 10, "deux mots", 200)
    penalize(service)
    result = service.release_game_penalty(1, 10, "staff-release")
    assert result["roles"] == [77, 99] and result["all_games"]
    assert service.game_penalty(1, 10) is None
    service.clock.advance(1)
    new = penalize(service, 102)
    assert service.release_game_penalty(1, 10, "staff-release")["replayed"]
    assert service.all_games_penalty(1, 10)["penalty_until"] == new["sanction_until"]
    assert penalize(service, 100)["replayed"]


def test_trace_retention_export_forget_and_schema_upgrade(service):
    tracked(service)
    row = service.export_user(1, 10)["counting_validations"][0]
    assert row["number"] == 1
    service.store.initialize()
    assert service.counting_validation(1, 5, 100)
    service.forget_user(1, 10)
    assert not service.export_user(1, 10)["counting_validations"]
    assert penalize(service) is None
    service.counting(1, 5, 20, "2", 101)
    service.clock.advance(TRACE_SECONDS + 1)
    assert service.counting_validation(1, 5, 101) is None
    service.prune_counting_validations()
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM counting_validations").fetchone()[0] == 0


def test_counting_rollback_does_not_leave_trace(service):
    service.config = replace(
        service.config, rules=replace(service.config.rules, counting_reward_every=1)
    )

    def fail(*args, **kwargs):
        raise RuntimeError("test credit failure")

    service.credit_prize = fail
    with pytest.raises(RuntimeError):
        service.counting(1, 5, 10, "1", 100)
    assert service.counting_validation(1, 5, 100) is None
    assert service.counting_status(1, 5)["next"] == 1


def bot_harness(service):
    tracked(service)
    bot = MokaBot(service.config, service=service)
    bot._connection.user = SimpleNamespace(id=999)
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 5
    channel.send = AsyncMock()

    async def history(**kwargs):
        for x in []:
            yield x

    channel.history = history
    guild = SimpleNamespace(id=1, get_channel=lambda _: channel)
    bot.get_guild = lambda _: guild
    community = SimpleNamespace(apply_role_grant=AsyncMock())
    bot.get_cog = lambda _: community
    return bot, channel, community


def payload(content="2", **extra):
    data = {
        "content": content,
        "edited_timestamp": "2026-10-30T10:00:00+00:00",
        "author": {"id": "10"},
    }
    data.update(extra)
    return SimpleNamespace(guild_id=1, channel_id=5, message_id=100, data=data)


async def test_raw_edit_without_message_cache_sanctions_once_and_frames_notice(service):
    bot, channel, community = bot_harness(service)
    await bot.on_raw_message_edit(payload())
    await bot.on_raw_message_edit(payload("3"))
    channel.send.assert_awaited_once()
    embed = channel.send.call_args.kwargs["embed"]
    assert "nombre **1**" in embed.description and "prochain nombre **2**" in embed.description
    assert "tous les jeux" in embed.description
    assert not channel.send.call_args.kwargs["allowed_mentions"].users
    community.apply_role_grant.assert_awaited_once()
    assert not service.pending_counting_edits()
    await bot.close()


async def test_embed_only_edits_wrong_author_and_equivalent_are_ignored(service):
    bot, channel, _ = bot_harness(service)
    await bot.on_raw_message_edit(payload("1"))
    await bot.on_raw_message_edit(payload("2", edited_timestamp=None))
    await bot.on_raw_message_edit(payload("2", author={"id": "20"}))
    event = payload()
    event.data = {"embeds": []}
    await bot.on_raw_message_edit(event)
    assert service.game_penalty(1, 10) is None
    channel.send.assert_not_awaited()
    await bot.close()


async def test_notification_failure_retries_without_extending_sanction(service):
    bot, channel, _ = bot_harness(service)
    channel.send.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "test"
    )
    await bot.on_raw_message_edit(payload())
    row = service.pending_counting_edits()[0]
    until = row["sanction_until"]
    service.clock.advance(60)
    channel.send.side_effect = None
    await bot.notify_counting_edit(row)
    assert service.all_games_penalty(1, 10)["penalty_until"] == until
    assert not service.pending_counting_edits()
    await bot.close()


async def test_restart_finds_previous_notice_and_does_not_claim_lifted_corvee_is_active(service):
    bot, channel, _ = bot_harness(service)
    row = penalize(service)
    old = SimpleNamespace(
        author=SimpleNamespace(id=999),
        embeds=[
            SimpleNamespace(
                title="🧽 De corvée de vaisselle", url="https://discord.com/channels/1/5/100"
            )
        ],
        edit=AsyncMock(),
    )

    async def history(**kwargs):
        yield old

    channel.history = history
    service.release_game_penalty(1, 10, "staff")
    await bot.notify_counting_edit(row)
    channel.send.assert_not_awaited()
    old.edit.assert_awaited_once()
    assert "déjà été levée" in old.edit.call_args.kwargs["embed"].description
    await bot.close()


async def test_corvee_role_reconciliation_and_release_retries(service):
    tracked(service)
    penalize(service)
    role = MagicMock(spec=discord.Role)
    role.id = 77
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    member = SimpleNamespace(id=10, roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
    guild = SimpleNamespace(
        id=1, me=SimpleNamespace(top_role=100), get_role=lambda _: role, get_member=lambda _: member
    )
    role.guild = guild
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    await cog.apply_role_grant(guild, grant, service.clock())
    member.add_roles.assert_awaited_once()
    member.roles = [role]
    result = service.release_game_penalty(1, 10, "staff")
    member.remove_roles.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "test"
    )
    assert await cog.release_game_roles(guild, 10, result["roles"])
    assert service.all_games_penalty(1, 10) is None
    member.remove_roles.side_effect = None
    assert not await cog.release_game_roles(guild, 10, result["roles"])


async def test_rate_callback_rejects_sanction_before_rendering(service):
    tracked(service)
    penalize(service)
    member = MagicMock(spec=discord.Member)
    member.id = 10
    guild = SimpleNamespace(id=1)
    i = SimpleNamespace(guild=guild, user=member, id=700, client=SimpleNamespace(service=service))
    bot = SimpleNamespace(service=service)
    cog = RatesCog(bot)
    with pytest.raises(DomainError, match="corvée"):
        await cog.show(i, "chance", [member])


async def test_corvee_configuration_is_staff_only_and_keeps_existing_deadline(service):
    from moka.cogs.staff import StaffCog

    tracked(service)
    until = penalize(service)["sanction_until"]
    member = MagicMock(spec=discord.Member)
    member.id = 20
    member.guild_permissions = discord.Permissions.none()
    bot = SimpleNamespace(service=service)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=member,
        id=900,
        client=bot,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    cog = StaffCog(bot)
    with pytest.raises(DomainError, match="permission"):
        await cog.corvee.callback(cog, interaction, 0)
    assert service.get_setting(1, "counting:cheat_seconds") is None
    member.guild_permissions = discord.Permissions(manage_guild=True)
    await cog.corvee.callback(cog, interaction, 0)
    assert interaction.response.send_message.call_args.kwargs["ephemeral"]
    assert service.all_games_penalty(1, 10)["penalty_until"] == until


async def test_reserved_or_privileged_role_is_not_configured_as_corvee(service):
    service.set_setting(1, "role:counting_failure", 99)
    role = MagicMock(spec=discord.Role)
    role.id = 99
    role.permissions = discord.Permissions.none()
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    guild = SimpleNamespace(id=1, me=SimpleNamespace(top_role=100))
    role.guild = guild
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with pytest.raises(DomainError, match="distinct"):
        await cog.configure_game_role(guild, role, usage="counting_cheat")
    role.edit.assert_not_called()
    role.id = 77
    role.permissions = discord.Permissions(send_messages=True)
    with pytest.raises(DomainError, match="sans permission"):
        await cog.configure_game_role(guild, role, usage="counting_cheat")


def test_disallowed_guild_does_not_starve_pending_notifications(service):
    tracked(service)
    penalize(service)
    with service.store.transaction() as con:
        for message in range(30):
            con.execute(
                "INSERT INTO counting_validations(guild,channel,message,user,number,created,sanction_until,sanction_role) VALUES(3,5,?,10,1,?, ?,77)",
                (message, service.clock() - 100, service.clock() + 3600),
            )
    assert [r["message"] for r in service.pending_counting_edits()] == [100]


async def test_role_changed_to_privileged_after_configuration_is_not_assigned(service):
    tracked(service)
    penalize(service)
    role = MagicMock(spec=discord.Role)
    role.id = 77
    role.permissions = discord.Permissions(send_messages=True)
    role.managed = False
    role.is_default.return_value = False
    role.__ge__.return_value = False
    member = SimpleNamespace(id=10, roles=[], add_roles=AsyncMock())
    guild = SimpleNamespace(
        id=1, me=SimpleNamespace(top_role=100), get_role=lambda _: role, get_member=lambda _: member
    )
    role.guild = guild
    cog = CommunityCog(SimpleNamespace(service=service, store=service.store))
    with service.store.read() as con:
        grant = dict(con.execute("SELECT * FROM role_grants").fetchone())
    with pytest.raises(DomainError, match="sans permission"):
        await cog.apply_role_grant(guild, grant, service.clock())
    member.add_roles.assert_not_awaited()
    assert service.all_games_penalty(1, 10)
