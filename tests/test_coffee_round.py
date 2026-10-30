import asyncio
import io
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from PIL import Image

from moka.__main__ import check_commands
from moka.base import DomainError
from moka.coffee_round_cards import ART, SIZE, render_round_card, round_description, round_state
from moka.discord_ui import (
    CoffeeJoin,
    CoffeeRoundView,
    event_embed,
    event_message,
    interaction_event,
)


def start(service):
    result = service.start_event(1, 5, 10, "goblin", "start")
    return service.get_event(1, result["event_id"])


def interaction_for(service, event, *, user_id=10, message_id=555):
    member = Mock(spec=discord.Member)
    member.id = user_id
    lock = asyncio.Lock()
    bot = SimpleNamespace(service=service, user=SimpleNamespace(id=999), event_lock=lambda _: lock)
    return SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=member,
        id=123,
        client=bot,
        message=SimpleNamespace(
            id=message_id,
            author=bot.user,
            channel=SimpleNamespace(id=5),
            embeds=[],
            edit=AsyncMock(),
        ),
        response=SimpleNamespace(defer=AsyncMock(), is_done=Mock(return_value=True)),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.mark.parametrize("state", ["open", "served", "missed"])
def test_coffee_round_states_render_without_visible_identifiers(service, state):
    event = start(service)
    if state == "served":
        for user in (10, 11, 12):
            service.join_event(1, user, event["id"], str(user))
    if state != "open":
        service.clock.advance(61)
        service.settle_event(1, event["id"])
    event = service.get_event(1, event["id"])
    data = round_state(event, service.clock())
    assert data["served"] is (state == "served")
    assert data["finished"] is (state != "open")
    text = round_description(event, service.clock())
    assert event["id"] not in text and "gobelin" not in text.lower()
    with Image.open(io.BytesIO(render_round_card(event, service.clock()))) as image:
        assert image.size == SIZE and image.width / image.height <= 1.4


def test_round_counter_never_goes_negative_and_zero_reward_can_still_be_served(service):
    event = start(service)
    assert round_state(event, event["deadline"] + 10)["remaining"] == 0
    event["result"] = {"count": 3, "reward": 0}
    assert round_state(event, service.clock())["served"]
    assert "servie" in round_description(event, service.clock())


def test_round_art_is_distributed_with_real_transparency():
    with Image.open(ART) as image:
        assert image.width == image.height and image.width >= 512
        assert image.getchannel("A").getextrema() == (0, 255)


async def test_round_payload_is_large_attachment_with_a_persistent_coffee_button(service):
    event = start(service)
    payload = await event_message(event, service)
    assert "embed" not in payload and "content" not in payload
    assert payload["file"].filename == "moka-tournee.png"
    assert event["id"] not in payload["file"].description
    view = payload["view"]
    assert isinstance(view, CoffeeRoundView) and view.is_persistent()
    assert view.children[0].item.label == "Je prends un café"
    assert payload["allowed_mentions"].to_dict() == {"parse": []}


async def test_dynamic_button_reconstructed_after_restart_joins_once(service):
    event = start(service)
    original = CoffeeJoin(event["id"])
    match = re.fullmatch(r"moka:tournee:join:(?P<event_id>[0-9a-f]{32})", original.custom_id)
    reconstructed = await CoffeeJoin.from_custom_id(None, original.item, match)
    interaction = interaction_for(service, event)
    await reconstructed.callback(interaction)
    assert service.get_event(1, event["id"])["participants"] == [10]
    assert interaction.message.edit.await_count == 1
    edited = interaction.message.edit.call_args.kwargs
    assert edited["embeds"] == [] and edited["content"] is None
    assert edited["attachments"][0].filename == "moka-tournee.png"
    interaction.id = 124
    await reconstructed.callback(interaction)
    assert service.get_event(1, event["id"])["participants"] == [10]
    assert "déjà" in interaction.followup.send.call_args.kwargs["embed"].description


def test_explicit_event_reference_rejects_wrong_bot_channel_and_message(service):
    event = start(service)
    interaction = interaction_for(service, event)
    interaction.message.author = SimpleNamespace(id=111)
    with pytest.raises(DomainError, match="pas un événement"):
        interaction_event(interaction, event["id"])
    interaction.message.author = interaction.client.user
    interaction.message.channel.id = 6
    with pytest.raises(DomainError, match="correspond"):
        interaction_event(interaction, event["id"])
    interaction.message.channel.id = 5
    service.bind_event(1, event["id"], 777)
    with pytest.raises(DomainError, match="correspond"):
        interaction_event(interaction, event["id"])


async def test_round_fallback_keeps_button_and_finished_round_removes_it(service, monkeypatch):
    event = start(service)

    def unavailable(*args):
        raise OSError("Illustration indisponible")

    monkeypatch.setattr("moka.discord_ui.render_round_card", unavailable)
    payload = await event_message(event, service, editing=True)
    assert payload["attachments"] == [] and payload["view"].is_persistent()
    assert event["id"] not in str(payload["embeds"][0].to_dict())
    service.clock.advance(61)
    service.settle_event(1, event["id"])
    payload = await event_message(service.get_event(1, event["id"]), service, editing=True)
    assert payload["view"] is None


async def test_round_launch_choice_keeps_legacy_value_with_new_public_name(service):
    commands = await check_commands(service.config)
    animation = next(c for c in commands if c["name"] == "animation")
    launcher = next(c for c in animation["options"] if c["name"] == "lancer")
    choice = next(c for c in launcher["options"][0]["choices"] if c["value"] == "goblin")
    assert "Tournée de Moka" in choice["name"]


def test_round_fallback_has_no_goblin_or_technical_footer(service):
    event = start(service)
    embed = event_embed(event, service)
    assert "tournée" in embed.title.lower()
    assert event["id"] not in str(embed.to_dict())
