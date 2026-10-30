from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from moka.base import DomainError
from moka.bot import MokaBot, counting_reward_card
from moka.config import Rules
from moka.service import Service


def random_source(draw=0.0, prize=25):
    return SimpleNamespace(random=Mock(return_value=draw), randint=Mock(return_value=prize))


@pytest.mark.parametrize(("draw", "expected"), [(0.0, 25), (0.049999, 25), (0.05, 0), (0.9, 0)])
def test_five_percent_boundary_and_only_valid_author_is_credited(service, draw, expected):
    service.rng = rng = random_source(draw)
    result = service.counting(1, 5, 10, "0+1", 100)
    assert result["valid"] and result["bonus"] == expected and result["reward"] == 0
    assert service.profile(1, 10)["wallet"] == expected
    assert service.profile(1, 20)["wallet"] == 0
    rng.random.assert_called_once_with()
    if expected:
        rng.randint.assert_called_once_with(10, 50)
    else:
        rng.randint.assert_not_called()


def test_bonus_can_be_disabled_and_economy_off_never_draws(service):
    service.rng = rng = random_source()
    service.config = replace(
        service.config, rules=replace(service.config.rules, counting_bonus_chance_bps=0)
    )
    assert service.counting(1, 5, 10, "1", 100)["bonus"] == 0
    service.config = replace(
        service.config, rules=replace(service.config.rules, counting_bonus_chance_bps=500)
    )
    service.set_setting(1, "feature:economy", False)
    assert service.counting(1, 5, 20, "2", 101)["bonus"] == 0
    rng.random.assert_not_called()
    rng.randint.assert_not_called()


def test_error_keeps_its_coin_flip_but_never_draws_a_bonus(service):
    service.rng = rng = random_source()
    result = service.counting(1, 5, 10, "nope", 100)
    assert not result["valid"] and result["restart"] and result["bonus"] == 0
    rng.random.assert_called_once_with()  # La pièce d'erreur uniquement.
    rng.randint.assert_not_called()


def test_same_author_blocked_and_old_messages_never_award_bonus(service):
    service.rng = rng = random_source(0.9)
    service.counting(1, 5, 10, "1", 100)
    rng.random.reset_mock()
    bad = service.counting(1, 5, 10, "2", 101)
    assert bad["reason"] == "same_user" and bad["bonus"] == 0
    rng.random.assert_called_once_with()  # Erreur, aucune seconde chance de bonus.
    rng.randint.assert_not_called()
    rng.random.reset_mock()
    assert service.counting(1, 5, 20, "2", 99)["ignored"]
    rng.random.assert_not_called()


def test_active_game_pause_excludes_the_draw(service):
    service.set_setting(1, "role:counting_failure", 55)
    service.rng = rng = random_source()
    service.counting(1, 5, 10, "nope", 100)
    rng.random.reset_mock()
    assert service.counting(1, 5, 10, "1", 101)["blocked"]
    rng.random.assert_not_called()
    rng.randint.assert_not_called()


def test_bonus_and_milestone_stack_and_are_capped_sequentially(service, fund):
    service.config = replace(
        service.config,
        rules=replace(service.config.rules, counting_reward_every=1, counting_reward=10),
    )
    service.rng = random_source(prize=50)
    fund(10, service.config.rules.max_amount - 15)
    result = service.counting(1, 5, 10, "1", 100)
    assert (result["reward"], result["bonus"]) == (10, 5)
    assert service.profile(1, 10)["wallet"] == service.config.rules.max_amount
    with service.store.read() as con:
        entries = {
            r["reason"]: r["wallet_delta"]
            for r in con.execute(
                "SELECT * FROM ledger WHERE reason IN ('counting','counting-bonus')"
            )
        }
    assert entries == {"counting": 10, "counting-bonus": 5}
    embed = counting_reward_card(result)
    assert "+15 ❤️" in embed.description and "+5 ❤️" in embed.description


def test_same_message_is_paid_once_concurrently_and_not_redrawn_after_restart(service):
    service.rng = rng = random_source(prize=50)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.counting(1, 5, 10, "1", 100), range(2)))
    assert sum(r["replayed"] for r in results) == 1
    rng.random.assert_called_once()
    rng.randint.assert_called_once()
    assert service.profile(1, 10)["wallet"] == 50
    forbidden = SimpleNamespace(random=Mock(side_effect=AssertionError("No redraw")))
    restarted = Service(service.store, service.config, clock=service.clock, rng=forbidden)
    result = restarted.counting(1, 5, 10, "1", 100)
    assert result["replayed"] and result["bonus"] == 50
    assert restarted.profile(1, 10)["wallet"] == 50
    with service.store.read() as con:
        assert (
            con.execute("SELECT COUNT(*) FROM ledger WHERE reason='counting-bonus'").fetchone()[0]
            == 1
        )
    # Un identifiant identique dans un autre serveur n'en partage pas le reçu.
    result = service.counting(2, 5, 10, "1", 100)
    assert not result["replayed"] and result["bonus"] == 50


def test_bonus_failure_rolls_back_the_counter_milestone_and_receipt(service, monkeypatch):
    service.config = replace(
        service.config, rules=replace(service.config.rules, counting_reward_every=1)
    )
    service.rng = random_source()
    real_credit = service.credit_prize

    def credit(con, guild, user, amount, reason):
        if reason == "counting-bonus":
            raise DomainError("Interruption de la transaction")
        return real_credit(con, guild, user, amount, reason)

    monkeypatch.setattr(service, "credit_prize", credit)
    with pytest.raises(DomainError):
        service.counting(1, 5, 10, "1", 100)
    assert service.counting_status(1, 5)["next"] == 1
    assert service.profile(1, 10)["wallet"] == 0
    with service.store.read() as con:
        assert (
            con.execute("SELECT COUNT(*) FROM receipts WHERE action='counting'").fetchone()[0] == 0
        )
        assert con.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0


@pytest.mark.parametrize(
    "fields",
    [
        {"counting_bonus_chance_bps": 10001},
        {"counting_bonus_chance_bps": -1},
        {"counting_bonus_min": 0},
        {"counting_bonus_min": 51, "counting_bonus_max": 50},
    ],
)
def test_invalid_bonus_configuration_is_refused(fields):
    with pytest.raises(ValueError):
        replace(Rules(), **fields).validate()


def test_reward_card_handles_historical_receipts_and_absent_gains():
    assert counting_reward_card({"reward": 0}) is None
    assert "Palier" in counting_reward_card({"reward": 100}).title
    assert "chance" in counting_reward_card({"reward": 0, "bonus": 10}).title


async def test_discord_bonus_is_framed_no_ping_and_not_announced_twice(service):
    service.set_setting(1, "feature:xp", False)
    service.set_setting(1, "channel:counting", 5)
    service.rng = random_source(prize=50)
    bot = MokaBot(service.config, service)
    message = SimpleNamespace(
        guild=SimpleNamespace(id=1),
        author=SimpleNamespace(id=10, bot=False),
        channel=SimpleNamespace(id=5),
        content="1",
        id=100,
        webhook_id=None,
        add_reaction=AsyncMock(),
        reply=AsyncMock(),
    )
    try:
        await bot.on_message(message)
        await bot.on_message(message)
        message.reply.assert_awaited_once()
        payload = message.reply.call_args.kwargs
        assert "+50 ❤️" in payload["embed"].description
        assert payload["mention_author"] is False
        assert service.profile(1, 10)["wallet"] == 50
    finally:
        await bot.close()
