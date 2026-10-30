import asyncio
import io
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from PIL import Image

from moka.__main__ import check_commands
from moka.base import DomainError
from moka.coffee_round_cards import HUG_ART, SIZE, render_round_card, round_description, round_state
from moka.cogs.staff import StaffCog
from moka.config import Rules
from moka.discord_ui import HugJoin, HugView, event_embed, event_message
from moka.service import Service


def launch(service, *, guild=1, key="start"):
    result = service.start_event(guild, 5, 10, "hug", key)
    return service.get_event(guild, result["event_id"])


def interaction_for(service, event, *, user=10):
    member = Mock(spec=discord.Member)
    member.id, member.guild_permissions = user, discord.Permissions.none()
    lock = asyncio.Lock()
    bot = SimpleNamespace(service=service, user=SimpleNamespace(id=999), event_lock=lambda _: lock)
    return SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=member,
        id=123,
        client=bot,
        channel=Mock(spec=discord.TextChannel),
        channel_id=5,
        message=SimpleNamespace(
            id=555, author=bot.user, channel=SimpleNamespace(id=5), embeds=[], edit=AsyncMock()
        ),
        response=SimpleNamespace(
            defer=AsyncMock(), is_done=Mock(return_value=True), send_message=AsyncMock()
        ),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.mark.parametrize("players", [0, 1, 3])
def test_each_hugger_gets_base_times_count_once_even_after_restart(service, players):
    event = launch(service)
    for user in range(10, 10 + players):
        before = service.profile(1, user)["wallet"]
        service.join_event(1, user, event["id"], f"join:{user}")
        assert service.profile(1, user)["wallet"] == before
    service.clock.advance(61)
    restarted = Service(service.store, service.config, clock=service.clock)
    expected = {"kind": "hug", "count": players, "reward": 200 * players}
    result = restarted.settle_event(1, event["id"])
    assert {k: result[k] for k in expected} == expected
    assert restarted.settle_event(1, event["id"]) == result
    for user in range(10, 10 + players):
        assert restarted.profile(1, user)["wallet"] == 200 * players
    with service.store.read() as con:
        rows = con.execute("SELECT * FROM ledger WHERE reason='hug'").fetchall()
        assert len(rows) == players
        assert sum(r["wallet_delta"] for r in rows) == 200 * players * players


def test_hug_and_coffee_are_independent_and_guilds_are_isolated(service):
    event = launch(service)
    assert launch(service)["id"] == event["id"]  # Même reçu, même lancement.
    with pytest.raises(DomainError, match="déjà en cours"):
        launch(service, key="duplicate")
    service.start_event(1, 5, 10, "goblin", "coffee")
    other = launch(service, guild=2)
    with pytest.raises(DomainError, match="inscription"):
        service.join_event(2, 20, event["id"], "wrong-guild")
    assert other["id"] != event["id"]


def test_snapshot_rules_late_registration_and_module_disable(service):
    event = launch(service)
    service.join_event(1, 10, event["id"], "join")
    assert service.join_event(1, 10, event["id"], "join")["replayed"]
    with pytest.raises(DomainError, match="déjà"):
        service.join_event(1, 10, event["id"], "join-again")
    service.config = replace(service.config, rules=replace(service.config.rules, hug_reward=999))
    service.set_setting(1, "feature:hug", False)
    with pytest.raises(DomainError, match="désactivé"):
        service.join_event(1, 20, event["id"], "disabled")
    service.set_setting(1, "feature:economy", False)
    service.clock.advance(61)
    assert service.settle_event(1, event["id"])["reward"] == 200
    assert service.profile(1, 10)["wallet"] == 200
    service.set_setting(1, "feature:hug", True)
    service.set_setting(1, "feature:economy", True)
    with pytest.raises(DomainError, match="terminé"):
        service.join_event(1, 20, event["id"], "late")


def test_last_place_cannot_be_claimed_twice_concurrently(service):
    service.config = replace(service.config, rules=replace(service.config.rules, hug_max_players=1))
    event = launch(service)

    def join(user):
        try:
            service.join_event(1, user, event["id"], str(user))
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(join, [10, 20]))
    assert sum(result) == 1
    assert len(service.get_event(1, event["id"])["participants"]) == 1


def test_hug_credit_capped_per_member_without_repeated_payment(service, fund):
    event = launch(service)
    fund(10, service.config.rules.max_amount - 10)
    for user in (10, 20):
        service.join_event(1, user, event["id"], str(user))
    service.clock.advance(61)
    result = service.settle_event(1, event["id"])
    assert result["capped"] and result["reward"] == 400
    assert service.profile(1, 10)["wallet"] == service.config.rules.max_amount
    assert service.profile(1, 20)["wallet"] == 400
    service.settle_event(1, event["id"])
    assert service.profile(1, 20)["wallet"] == 400


@pytest.mark.parametrize("field", ["hug_seconds", "hug_max_players"])
def test_hug_cannot_have_zero_duration_or_places(field):
    with pytest.raises(ValueError):
        replace(Rules(), **{field: 0}).validate()


@pytest.mark.parametrize("state", ["open", "success", "empty"])
def test_cards_are_large_accessible_and_do_not_list_members(service, state):
    event = launch(service)
    if state == "success":
        for user in (10, 20):
            service.join_event(1, user, event["id"], str(user))
    if state != "open":
        service.clock.advance(61)
        service.settle_event(1, event["id"])
    event = service.get_event(1, event["id"])
    data = round_state(event, service.clock())
    assert data["served"] == (state == "success")
    text = round_description(event, service.clock())
    assert event["id"] not in text and "<@" not in text
    assert "solitaire" not in text
    if state == "success":
        assert data["reward"] == 400 and "200 × 2" in text
    with Image.open(io.BytesIO(render_round_card(event, service.clock()))) as image:
        assert image.size == SIZE
    with Image.open(HUG_ART) as image:
        assert image.mode == "RGBA" and image.getchannel("A").getextrema() == (0, 255)


async def test_persistent_hug_button_reconstructs_and_rejects_foreign_event(service):
    event = launch(service)
    button = HugJoin(event["id"])
    match = re.fullmatch(r"moka:hug:join:(?P<event_id>[0-9a-f]{32})", button.custom_id)
    restarted = await HugJoin.from_custom_id(None, button.item, match)
    i = interaction_for(service, event)
    await restarted.callback(i)
    assert service.get_event(1, event["id"])["participants"] == [10]
    assert i.followup.send.call_args.kwargs["ephemeral"]
    assert i.message.edit.call_args.kwargs["attachments"][0].filename == "moka-calin.png"
    i.id += 1
    await restarted.callback(i)
    assert "déjà" in i.followup.send.call_args.kwargs["embed"].description
    coffee = service.start_event(1, 5, 10, "goblin", "coffee")
    await HugJoin(coffee["event_id"]).callback(i)
    assert "ne correspond pas" in i.followup.send.call_args.kwargs["embed"].description
    assert service.get_event(1, coffee["event_id"])["participants"] == []


async def test_render_fallback_and_finished_button(service, monkeypatch):
    event = launch(service)
    payload = await event_message(event, service)
    assert isinstance(payload["view"], HugView) and payload["view"].is_persistent()
    assert payload["file"].filename == "moka-calin.png"
    assert payload["view"].children[0].item.label == "Je rejoins le câlin"
    assert payload["allowed_mentions"].to_dict() == {"parse": []}

    def fail(*args):
        raise OSError("Artwork unavailable")

    monkeypatch.setattr("moka.discord_ui.render_round_card", fail)
    fallback = await event_message(event, service, editing=True)
    assert fallback["attachments"] == [] and fallback["view"].is_persistent()
    assert "câlin" in fallback["embeds"][0].title.lower()
    assert event["id"] not in str(event_embed(event, service).to_dict())
    service.clock.advance(61)
    service.settle_event(1, event["id"])
    assert (await event_message(service.get_event(1, event["id"]), service))["view"] is None


async def test_hug_choice_exists_and_launch_still_checks_staff_at_execution(service):
    commands = await check_commands(service.config)
    animation = next(c for c in commands if c["name"] == "animation")
    launcher = next(c for c in animation["options"] if c["name"] == "lancer")
    choices = launcher["options"][0]["choices"]
    assert {"name": "🤗 Câlin collectif", "value": "hug"} in choices
    event = launch(service)
    i = interaction_for(service, event)
    with pytest.raises(DomainError, match="permission"):
        await StaffCog.start_event.callback(
            StaffCog(i.client), i, discord.app_commands.Choice(name="Câlin", value="hug")
        )
