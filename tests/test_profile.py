import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from PIL import Image

from moka.base import DomainError
from moka.profile_cards import PROFILE_SIZE, level_progress, render_profile_card
from moka.profile_ui import BankAmountModal, ProfileView, parse_amount, send_profile


def interaction_for(service, *, user_id=10, guild_id=1, key=123):
    user = Mock(spec=discord.Member)
    user.id, user.bot, user.display_name = user_id, False, "🌿 Alex 🌿"
    user.guild = SimpleNamespace(id=guild_id)
    user.display_avatar.with_format.return_value.with_size.return_value.read = AsyncMock(
        return_value=None
    )
    return SimpleNamespace(
        guild=user.guild,
        user=user,
        id=key,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(defer=AsyncMock(), send_modal=AsyncMock()),
        edit_original_response=AsyncMock(),
    )


def view_for(service, key="profile"):
    profile = service.profile(1, 10, viewer=10)
    cost = service.config.rules.bank_upgrade_cost * (profile["bank_tier"] + 1)
    return ProfileView(1, 10, profile, key, True, cost)


@pytest.mark.parametrize("value,expected", [("250", 250), ("1 000", 1000), ("1\u202f000", 1000)])
def test_bank_modal_parses_only_positive_whole_amounts(value, expected):
    assert parse_amount(value) == expected


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "1e3", "", "tout", "9" * 11])
def test_bank_modal_rejects_invalid_amounts(value):
    with pytest.raises(DomainError):
        parse_amount(value)


def test_profile_progress_starts_at_the_current_level():
    profile = {"level": 4, "xp": 1830, "next_xp": 2500}
    assert level_progress(profile) == pytest.approx(230 / 900)
    assert level_progress({**profile, "xp": 1600}) == 0


def test_profile_card_handles_maximum_balance_and_unicode(service):
    profile = service.profile(1, 10, viewer=10)
    profile["wallet"] = 1_000_000_000
    png = render_profile_card(profile, "🌿 Αlеx 🌿", None)
    with Image.open(io.BytesIO(png)) as image:
        assert image.size == PROFILE_SIZE and image.width / image.height <= 1.4


async def test_own_profile_has_private_image_and_bank_buttons(service, fund):
    fund(10, 750)
    interaction = interaction_for(service)
    await send_profile(interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    sent = interaction.edit_original_response.call_args.kwargs
    assert sent["attachments"][0].filename == "moka-profile.png"
    assert "Prochain palier 2000 cœurs, prix 500 cœurs" in sent["attachments"][0].description
    assert sent["embeds"] == [] and sent["content"] is None
    assert sent["allowed_mentions"].to_dict() == {"parse": []}
    view = sent["view"]
    assert not view.deposit.disabled and view.withdraw.disabled
    assert not view.upgrade.disabled and "500" in view.upgrade.label


async def test_other_member_profile_is_read_only_and_privacy_is_enforced(service):
    interaction = interaction_for(service)
    target = interaction_for(service, user_id=20).user
    await send_profile(interaction, target)
    assert interaction.edit_original_response.call_args.kwargs["view"] is None
    service.set_privacy(1, 20, True)
    with pytest.raises(DomainError, match="privé"):
        await send_profile(interaction, target)


@pytest.mark.parametrize("user,guild", [(20, 1), (10, 2)])
async def test_profile_actions_reject_other_owners_and_guilds(service, user, guild):
    view = view_for(service)
    interaction = interaction_for(service, user_id=user, guild_id=guild)
    with pytest.raises(DomainError, match="autre profil"):
        await view.interaction_check(interaction)
    modal = BankAmountModal(1, 10, "nonce", True)
    modal.amount._value = "1"
    with pytest.raises(DomainError, match="autre profil"):
        await modal.on_submit(interaction)


async def test_deposit_modal_and_withdraw_update_profile_and_replay_only_once(service, fund):
    fund(10, 750)
    interaction = interaction_for(service)
    await view_for(service).open_amount(interaction, True)
    modal = interaction.response.send_modal.call_args.args[0]
    modal.amount._value = "250"
    await modal.on_submit(interaction)
    modal.amount._value = "400"
    await modal.on_submit(interaction)
    assert interaction.edit_original_response.call_args.kwargs["content"] is None
    assert (
        "Dépôt en banque déjà pris en compte : 250 ❤️"
        in interaction.edit_original_response.call_args.kwargs["attachments"][0].description
    )
    profile = service.profile(1, 10, viewer=10)
    assert (profile["wallet"], profile["bank"]) == (500, 250)
    fresh = interaction.edit_original_response.call_args.kwargs["view"]
    assert not fresh.withdraw.disabled
    withdrawal = BankAmountModal(1, 10, "withdraw", False)
    withdrawal.amount._value = "100"
    await withdrawal.on_submit(interaction)
    profile = service.profile(1, 10, viewer=10)
    assert (profile["wallet"], profile["bank"]) == (600, 150)


async def test_profile_upgrade_is_charged_once_and_old_quote_cannot_buy_next_tier(service, fund):
    fund(10, 5000)
    old = view_for(service, "old-quote")
    view = view_for(service, "current")
    interaction = interaction_for(service)
    await view.upgrade.callback(interaction)
    await view.upgrade.callback(interaction)
    assert service.profile(1, 10, viewer=10)["wallet"] == 4500
    assert service.profile(1, 10, viewer=10)["capacity"] == 2000
    with pytest.raises(DomainError, match="palier a changé"):
        await old.upgrade.callback(interaction)
    assert service.profile(1, 10, viewer=10)["wallet"] == 4500


async def test_bank_disabled_after_opening_profile_refuses_mutations(service, fund):
    fund(10, 1000)
    view = view_for(service)
    service.set_setting(1, "feature:bank", False)
    interaction = interaction_for(service)
    with pytest.raises(DomainError, match="désactivée"):
        await view.open_amount(interaction, True)
    modal = BankAmountModal(1, 10, "nonce", True)
    modal.amount._value = "100"
    with pytest.raises(DomainError, match="désactivé"):
        await modal.on_submit(interaction)
    with pytest.raises(DomainError, match="désactivé"):
        await view.upgrade.callback(interaction)
    assert service.profile(1, 10, viewer=10)["wallet"] == 1000


async def test_profile_image_failure_keeps_private_balances_and_actions(service, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("Rendu indisponible")

    monkeypatch.setattr("moka.profile_ui.render_profile_card", unavailable)
    interaction = interaction_for(service)
    await send_profile(interaction)
    sent = interaction.edit_original_response.call_args.kwargs
    assert sent["attachments"] == []
    assert len(sent["embeds"]) == 1 and isinstance(sent["view"], ProfileView)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)


async def test_profile_refresh_retires_old_controls_and_expiry_clears_the_current_view(service):
    old = view_for(service)
    old.message = SimpleNamespace(edit=AsyncMock())
    interaction = interaction_for(service)
    await old.refresh.callback(interaction)
    assert old.is_finished() and old.message is None
    current = interaction.edit_original_response.call_args.kwargs["view"]
    message = current.message
    await current.on_timeout()
    message.edit.assert_awaited_once_with(view=None)
    assert current.expired


async def test_expired_bank_modal_cannot_mutate_balances(service, fund):
    fund(10, 500)
    view = view_for(service)
    interaction = interaction_for(service)
    await view.open_amount(interaction, True)
    modal = interaction.response.send_modal.call_args.args[0]
    modal.amount._value = "100"
    await view.on_timeout()
    with pytest.raises(DomainError, match="expiré"):
        await modal.on_submit(interaction)
    assert service.profile(1, 10)["wallet"] == 500
