from concurrent.futures import ThreadPoolExecutor

import pytest

from moka.base import DomainError


def balance(service, user, guild=1):
    p = service.profile(guild, user, viewer=user)
    return p["wallet"] + p["bank"]


def test_daily_retry_is_idempotent_and_survives_restart(service):
    from moka.service import Service

    a = service.claim(1, 10, "click")
    restarted = Service(service.store, service.config, clock=service.clock)
    b = restarted.claim(1, 10, "click")
    assert a["replayed"] is False and b["replayed"] is True
    assert balance(service, 10) == 200
    with pytest.raises(DomainError, match="Patience"):
        service.claim(1, 10, "another-click")
    service.clock.advance(86400)
    service.claim(1, 10, "tomorrow")
    assert balance(service, 10) == 400


def test_receipt_cannot_be_reused_by_another_actor_or_action(service):
    service.claim(1, 10, "same")
    with pytest.raises(DomainError, match="autre action"):
        service.claim(1, 11, "same")
    with pytest.raises(DomainError, match="autre action"):
        service.bet(1, 10, 1, "same")


@pytest.mark.parametrize("amount", [-1, 0, True, 1.5, 10**12])
def test_invalid_amounts_cannot_modify_balances(service, fund, amount):
    fund(10)
    with pytest.raises(DomainError):
        service.transfer(1, 10, 11, amount, "gift")
    assert balance(service, 10) == 5000 and balance(service, 11) == 0


def test_failed_transfer_rolls_back_debit_and_receipt(service, fund):
    fund(10, 100)
    fund(11, service.config.rules.max_amount)
    with pytest.raises(DomainError, match="plafond"):
        service.transfer(1, 10, 11, 50, "gift")
    assert balance(service, 10) == 100
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM receipts WHERE key='gift'").fetchone()[0] == 0


def test_concurrent_transfers_cannot_overspend(service, fund):
    fund(10, 100)

    def spend(target):
        try:
            service.transfer(1, 10, target, 80, f"transfer:{target}")
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(spend, (11, 12)))
    assert sum(results) == 1
    assert balance(service, 10) == 20
    assert balance(service, 11) + balance(service, 12) == 80


def test_concurrent_daily_claims_pay_once(service):
    def claim(index):
        try:
            return service.claim(1, 10, f"claim:{index}")["amount"]
        except DomainError:
            return 0

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(claim, range(6))) == 200


def test_bank_capacity_transfer_and_interest(service, fund):
    fund(10)
    with pytest.raises(DomainError, match="capacité"):
        service.bank_move(1, 10, 1001, "too-much")
    service.bank_move(1, 10, 1000, "deposit")
    assert balance(service, 10) == 5000
    assert service.interest(1, 10, "interest")["amount"] == 10
    with pytest.raises(DomainError, match="Patience"):
        service.interest(1, 10, "interest2")
    service.bank_move(1, 10, 100, "withdraw", deposit=False)
    assert service.profile(1, 10, viewer=10)["bank"] == 900


def test_failed_bank_operation_does_not_debit(service, fund):
    fund(10, 10)
    with pytest.raises(DomainError, match="insuffisant"):
        service.bank_move(1, 10, 100, "deposit")
    assert service.profile(1, 10, viewer=10)["bank"] == 0
    assert balance(service, 10) == 10


def test_upgrade_is_charged_once_and_effective(service, fund):
    fund(10)
    service.bank_upgrade(1, 10, "upgrade")
    service.bank_upgrade(1, 10, "upgrade")
    assert balance(service, 10) == 4500
    assert service.profile(1, 10, viewer=10)["capacity"] == 2000


def test_shop_gift_and_repeat_purchase(service, fund):
    fund(10, 100)
    service.buy(1, 10, "cafe", "buy")
    service.buy(1, 10, "cafe", "buy")
    assert balance(service, 10) == 50
    service.give_item(1, 10, 11, "cafe", "gift")
    assert service.inventory(1, 10) == []
    assert service.inventory(1, 11) == [{"item": "cafe", "quantity": 1}]
    with pytest.raises(DomainError, match="possèdes"):
        service.give_item(1, 10, 11, "cafe", "another-gift")


def test_bet_uses_server_randomness_and_no_free_payout(service, fund):
    fund(10, 100)
    assert service.bet(1, 10, 100, "bet")["net"] == 100
    assert balance(service, 10) == 200
    service.clock.advance(6)
    service.rng.value = 0.99
    assert service.bet(1, 10, 100, "lose")["net"] == -100
    assert balance(service, 10) == 100 and service.pot(1) == 10
    with pytest.raises(DomainError):
        service.bet(1, 10, 200, "too-much")
    assert balance(service, 10) == 100


def test_robbery_conserves_money_and_protects_target(service, fund):
    fund(10, 1000)
    fund(11, 1000)
    fund(12, 1000)
    outcome = service.rob(1, 10, 11, "steal")
    assert outcome["win"]
    assert balance(service, 10) + balance(service, 11) == 2000
    with pytest.raises(DomainError, match="protection"):
        service.rob(1, 12, 11, "steal-again")


def test_failed_robbery_never_touches_target(service, fund):
    fund(10, 1000)
    fund(11, 1000)
    service.rng.value = 0.99
    outcome = service.rob(1, 10, 11, "steal")
    assert not outcome["win"] and balance(service, 11) == 1000
    assert balance(service, 10) == 900


def test_modules_and_guilds_are_isolated(service, fund):
    fund(10, 100)
    service.set_setting(1, "feature:economy", False)
    with pytest.raises(DomainError, match="désactivé"):
        service.claim(1, 10, "daily")
    service.claim(2, 10, "daily")
    assert balance(service, 10, 2) == 200 and balance(service, 10) == 100
    with pytest.raises(DomainError, match="autorisé"):
        service.claim(3, 10, "daily")


def test_activity_cooldown_level_and_no_money_when_disabled(service):
    for index in range(7):
        service.activity(1, 10, f"message:{index}")
        service.clock.advance(60)
    p = service.profile(1, 10, viewer=10)
    assert p["xp"] == 105 and p["level"] == 1 and p["wallet"] == 121
    service.set_setting(1, "feature:economy", False)
    service.activity(1, 10, "next")
    assert service.profile(1, 10, viewer=10)["wallet"] == 121


def test_activity_at_cap_still_grants_xp(service, fund):
    fund(10, service.config.rules.max_amount)
    result = service.activity(1, 10, "message")
    assert result["coins"] == 0 and result["xp"] == 15


def test_privacy_hides_rank_and_profile_but_not_own_access(service):
    service.activity(1, 10, "message")
    service.set_privacy(1, 10, True)
    assert service.leaderboard(1) == []
    with pytest.raises(DomainError, match="privé"):
        service.profile(1, 10, viewer=11)
    assert service.profile(1, 10, viewer=10)["xp"] == 15
