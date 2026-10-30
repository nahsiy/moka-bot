from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.collection import BADGES
from moka.profile_hub import HubView, show_hub


def test_badges_are_once_only_guild_scoped_and_do_not_mint_money(service, fund):
    fund(10, 1000)
    service.bank_move(1, 10, 500, "deposit")
    service.activity(1, 10, "message")
    before = service.profile(1, 10)
    first = service.collection(1, 10)
    assert {r["item"] for r in first["owned"]} == {"premier_cafe", "reserve"}
    assert service.collection(1, 10) == first
    assert service.profile(1, 10) == before
    assert not service.collection(2, 10)["owned"]
    service.bank_move(1, 10, 500, "withdraw", deposit=False)
    assert "reserve" in {r["item"] for r in service.collection(1, 10)["owned"]}


def test_counting_and_finished_events_unlock_real_progress(service):
    service.counting(1, 99, 10, "1", 1001)
    assert service.collection(1, 10)["progress"]["grains"] == 1
    service.counting(1, 99, 20, "2", 1002)
    assert service.collection(1, 10)["progress"]["grains"] == 1
    event = service.start_event(1, 30, 10, "hug", "hug")
    service.join_event(1, 10, event["event_id"], "join")
    assert service.collection(1, 10)["progress"]["tournee"] == 0
    service.clock.advance(61)
    service.settle_event(1, event["event_id"])
    assert service.collection(1, 10)["progress"]["tournee"] == 1


def test_title_purchase_equip_replay_privacy_and_erasure(service, fund):
    fund(10, 2000)
    with pytest.raises(DomainError):
        service.equip_title(1, 10, "biscuit", "equip")
    first = service.buy_title(1, 10, "biscuit", "buy")
    assert service.buy_title(1, 10, "biscuit", "buy")["replayed"]
    assert first["price"] == 800 and service.profile(1, 10)["wallet"] == 1200
    with pytest.raises(DomainError, match="déjà"):
        service.buy_title(1, 10, "biscuit", "buy2")
    with pytest.raises(DomainError):
        service.equip_title(2, 10, "biscuit", "equip")
    service.equip_title(1, 10, "biscuit", "equip")
    assert service.profile(1, 10)["title"] == "Gardien des biscuits"
    service.set_privacy(1, 10, True)
    with pytest.raises(DomainError, match="privé"):
        service.profile(1, 10, viewer=20)
    assert service.export_user(1, 10)["collections"]
    service.forget_user(1, 10)
    assert not service.export_user(1, 10)["collections"]
    assert not service.export_user(1, 10)["profile_titles"]


async def test_hub_has_clear_navigation_private_data_and_owner_checks(service):
    user = Mock(spec=discord.Member, id=10, bot=False)
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=user,
        id=1,
        client=SimpleNamespace(service=service),
        edit_original_response=AsyncMock(),
    )
    await show_hub(interaction, "badges")
    sent = interaction.edit_original_response.call_args.kwargs
    assert len(sent["embeds"][0].fields) == len(BADGES)
    assert sent["content"] is None and sent["allowed_mentions"].to_dict() == {"parse": []}
    view = sent["view"]
    interaction.user = Mock(spec=discord.Member, id=20, bot=False)
    with pytest.raises(DomainError):
        await view.interaction_check(interaction)
    shop = HubView(service, 1, 10, "shop")
    assert shop.purchase.disabled


def test_history_and_claim_status_do_not_disclose_other_users(service, fund):
    for _i in range(10):
        fund(10, 1)
    fund(20, 123)
    assert service.heart_history(1, 10)["more"]
    assert len(service.heart_history(1, 10, 1)["rows"]) == 2
    assert all(r["wallet_delta"] == 1 for r in service.heart_history(1, 10)["rows"])
    assert service.reward_status(1, 10) == {"daily": 0, "weekly": 0}
    service.claim(1, 10, "daily")
    assert service.reward_status(1, 10)["daily"] == 86400
