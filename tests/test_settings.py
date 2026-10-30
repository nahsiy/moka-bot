from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.staff_panel import Field, StaffPanel, authorize


def test_guild_rules_drive_rewards_xp_and_capacity_without_changing_other_guilds(service):
    service.update_rules(
        1, {"daily_coins": 42, "message_xp": 2, "message_coins": 1, "bank_capacity": 2000}
    )
    assert service.claim(1, 10, "daily")["amount"] == 42
    assert service.claim(2, 10, "daily")["amount"] == 200
    assert service.activity(1, 10, "message")["xp"] == 2
    assert service.profile(1, 10)["capacity"] == 2000
    assert service.profile(2, 10)["capacity"] == 1000


def test_invalid_bundle_stale_revision_and_bank_overflow_are_atomic(service, fund):
    fund(10)
    service.bank_move(1, 10, 900, "deposit")
    for patch in [
        {"bank_capacity": 800},
        {"counting_bonus_min": 200, "daily_coins": 900},
        {"max_amount": 10},
    ]:
        with pytest.raises(DomainError):
            service.update_rules(1, patch, revision=0)
    assert service.rules_revision(1) == 0
    assert service.rules_for(1).daily_coins == 200
    service.update_rules(1, {"daily_coins": 300}, revision=0)
    with pytest.raises(DomainError, match="Actualise"):
        service.update_rules(1, {"daily_coins": 800}, revision=0)
    assert service.rules_for(1).daily_coins == 300


def test_legacy_settings_survive_then_migrate_without_overriding_new_values(service):
    service.set_setting(1, "counting:fine", 30)
    assert service.rules_for(1).counting_fine == 30
    service.update_rules(1, {"counting_fine": 70})
    assert service.get_setting(1, "counting:fine") is None
    assert service.counting_status(1, 50)["fine"] == 70


def test_modules_require_explicit_save_and_reject_concurrent_changes(service):
    from moka.config import FEATURES

    service.update_modules(1, {"xp"}, expected=FEATURES)
    assert service.is_enabled(1, "xp") and not service.is_enabled(1, "economy")
    with pytest.raises(DomainError, match="Actualise"):
        service.update_modules(1, {"bank"}, expected=FEATURES)
    assert service.is_enabled(2, "economy")


@pytest.mark.parametrize(
    "value,divisor,text", [(3600, 60, "60"), (1000, 100, "10"), (125, 100, "1.25"), (0, 60, "0")]
)
def test_units_round_trip(value, divisor, text):
    field = Field("test", "Test", divisor=divisor)
    assert field.display(value) == text
    assert field.parse(text) == value


async def test_private_panel_rechecks_current_permissions_and_owner(service):
    interaction = SimpleNamespace(
        guild=SimpleNamespace(
            id=1,
            fetch_member=AsyncMock(
                return_value=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=True))
            ),
        ),
        user=Mock(spec=discord.Member, id=10, bot=False),
        client=SimpleNamespace(service=service),
        id=123,
    )
    await authorize(interaction, 1, 10)
    with pytest.raises(DomainError, match="autre personne"):
        await authorize(interaction, 1, 20)
    interaction.guild.fetch_member.return_value.guild_permissions.manage_guild = False
    with pytest.raises(DomainError, match="Gérer le serveur"):
        await authorize(interaction, 1, 10)
    view = StaffPanel(service, 1, 10, "modules", pending={"xp"})
    assert service.is_enabled(1, "economy")
    assert view.pending_modules == {"xp"}


def test_jackpot_price_is_kept_when_rules_change_after_opening(service, fund):
    from moka.discord_ui import event_embed
    from moka.service import Service

    fund(10, 1000)
    fund(20, 1000)
    service.update_rules(1, {"jackpot_ticket_cost": 100})
    event = service.start_event(1, 50, 10, "jackpot", "start")
    service.update_rules(1, {"jackpot_ticket_cost": 300})
    restarted = Service(service.store, service.config, clock=service.clock, rng=service.rng)
    restarted.join_event(1, 10, event["event_id"], "join")
    restarted.join_event(1, 20, event["event_id"], "join2")
    assert restarted.profile(1, 10)["wallet"] == 900
    assert restarted.profile(1, 20)["wallet"] == 900
    current = restarted.get_event(1, event["event_id"])
    assert "**100 ❤️**" in event_embed(current, restarted).description
    service.clock.advance(301)
    restarted.settle_event(1, event["event_id"])
    new = restarted.start_event(1, 50, 10, "jackpot", "new")
    assert restarted.get_event(1, new["event_id"])["payload"]["ticket_cost"] == 300


@pytest.mark.parametrize(
    "action", ["daily", "deposit", "upgrade", "interest", "message", "counting", "words", "robbery"]
)
def test_economic_actions_read_rules_from_their_existing_transaction(
    service, fund, monkeypatch, action
):
    fund(10, 5000)
    fund(20, 5000)
    service.bank_move(1, 10, 900, "initial-deposit")

    def forbidden_read():
        raise AssertionError(
            "Une action atomique ne doit pas ouvrir une seconde connexion de lecture"
        )

    monkeypatch.setattr(service.store, "read", forbidden_read)
    actions = {
        "daily": lambda: service.claim(1, 10, "claim"),
        "deposit": lambda: service.bank_move(1, 10, 50, "deposit"),
        "upgrade": lambda: service.bank_upgrade(1, 10, "upgrade"),
        "interest": lambda: service.interest(1, 10, "interest"),
        "message": lambda: service.activity(1, 10, "message"),
        "counting": lambda: service.counting(1, 40, 10, "1", 1001),
        "words": lambda: service.word(1, 41, 10, "cafe", 1002),
        "robbery": lambda: service.rob(1, 10, 20, "robbery"),
    }
    assert actions[action]()
