from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from moka.base import DomainError


def test_counting_alternation_reset_and_message_replay(service):
    assert service.counting(1, 5, 10, "1", 101)["valid"]
    result = service.counting(1, 5, 10, "2", 102)
    assert not result["valid"] and result["score"] == 0
    assert service.counting(1, 5, 11, "1", 103)["valid"]
    assert service.counting(1, 5, 10, "2", 104)["valid"]
    assert service.counting(1, 5, 11, "1", 103)["replayed"]
    assert service.counting(1, 5, 11, "3", 105)["valid"]
    assert service.counting(1, 5, 10, "bonjour", 106)["ignored"]


def test_counting_milestone_paid_once_and_penalty_persisted(service):
    service.config = replace(
        service.config, rules=replace(service.config.rules, counting_reward_every=2)
    )
    service.set_setting(1, "role:counting_failure", 99)
    service.counting(1, 5, 10, "1", 101)
    assert service.counting(1, 5, 11, "2", 102)["reward"] == 100
    service.counting(1, 5, 11, "2", 102)
    assert service.profile(1, 11, viewer=11)["wallet"] == 100
    service.counting(1, 5, 10, "999", 103)
    with service.store.read() as con:
        grant = con.execute("SELECT * FROM role_grants").fetchone()
        assert grant["role"] == 99 and grant["until"] - service.clock() == 10800


def test_word_modes_normalization_and_reset(fast_rules):
    s = fast_rules
    s.set_setting(1, "words:mode", "last_letter")
    assert s.word(1, 5, 10, "Café", 101)["word"] == "café"
    assert s.word(1, 5, 11, "éléphant", 102)["valid"]
    with pytest.raises(DomainError, match="commencer"):
        s.word(1, 5, 10, "chat", 103)
    assert s.word(1, 5, 10, "tasse", 104)["valid"]
    with pytest.raises(DomainError, match="déjà"):
        s.word(1, 5, 11, "CAFÉ", 105)
    s.reset_game(1, 5, "words")
    assert s.word(1, 5, 10, "CAFÉ", 106)["valid"]


def test_word_rejects_same_author_and_multiword_input(fast_rules):
    fast_rules.word(1, 5, 10, "soleil", 101)
    with pytest.raises(DomainError, match="autre membre"):
        fast_rules.word(1, 5, 10, "lune", 102)
    assert fast_rules.word(1, 5, 11, "deux mots", 103)["ignored"]


def test_goblin_minimum_and_restart_settlement(service):
    from moka.service import Service

    event = service.start_event(1, 5, 10, "goblin", "start")
    for user in (10, 11, 12):
        service.join_event(1, user, event["event_id"], f"join:{user}")
    with pytest.raises(DomainError, match="déjà"):
        service.join_event(1, 10, event["event_id"], "join-again")
    with pytest.raises(DomainError, match="pas encore"):
        service.settle_event(1, event["event_id"])
    service.clock.advance(61)
    restarted = Service(service.store, service.config, clock=service.clock)
    result = restarted.settle_event(1, event["event_id"])
    assert result["count"] == 3 and result["reward"] == 100
    restarted.settle_event(1, event["event_id"])
    assert service.profile(1, 10, viewer=10)["wallet"] == 100
    assert len(service.pending_event_notifications()) == 1
    service.event_notified(1, event["event_id"])
    assert service.pending_event_notifications() == []


def test_insufficient_goblin_players_no_rewards(service):
    event = service.start_event(1, 5, 10, "goblin", "start")
    service.join_event(1, 10, event["event_id"], "join")
    service.clock.advance(61)
    assert service.settle_event(1, event["event_id"])["reward"] == 0


def test_active_events_are_unique_per_guild_and_kind(service):
    service.start_event(1, 5, 10, "goblin", "start")
    with pytest.raises(DomainError, match="déjà"):
        service.start_event(1, 6, 11, "goblin", "other-start")
    service.start_event(2, 5, 10, "goblin", "start")


def test_event_ids_do_not_bypass_guild_boundary(service):
    event = service.start_event(1, 5, 10, "goblin", "start")
    with pytest.raises(DomainError):
        service.get_event(2, event["event_id"])
    with pytest.raises(DomainError):
        service.join_event(2, 10, event["event_id"], "join")


def test_concurrent_ticket_clicks_pay_once(service, fund):
    fund(10, 1000)
    event = service.start_event(1, 5, 10, "jackpot", "start")

    def join(key):
        try:
            service.join_event(1, 10, event["event_id"], key)
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(join, ("click-a", "click-b"))) == 1
    assert service.profile(1, 10, viewer=10)["wallet"] == 900
    assert service.pot(1) == 100


def test_jackpot_pays_exactly_once_and_preserves_empty_pot(service, fund):
    fund(10, 1000)
    fund(11, 1000)
    event = service.start_event(1, 5, 10, "jackpot", "start")
    service.join_event(1, 10, event["event_id"], "join10")
    service.join_event(1, 11, event["event_id"], "join11")
    service.clock.advance(301)
    result = service.settle_event(1, event["event_id"])
    assert result["winner"] == 10 and result["reward"] == 200
    service.settle_event(1, event["event_id"])
    assert service.profile(1, 10, viewer=10)["wallet"] == 1100
    assert service.pot(1) == 0
    with service.store.transaction() as con:
        service.add_pot(con, 1, 500)
    empty = service.start_event(1, 5, 10, "jackpot", "empty")
    service.clock.advance(301)
    service.settle_event(1, empty["event_id"])
    assert service.pot(1) == 500


def test_jackpot_cap_carries_overflow_instead_of_stalling(service, fund):
    fund(10, service.config.rules.max_amount)
    event = service.start_event(1, 5, 10, "jackpot", "start")
    service.join_event(1, 10, event["event_id"], "join")
    with service.store.transaction() as con:
        service.add_pot(con, 1, 500)
    service.clock.advance(301)
    result = service.settle_event(1, event["event_id"])
    assert result["reward"] == 100 and result["carried"] == 500
    assert service.pot(1) == 500


def test_hack_only_owner_can_finish_and_cannot_double_pay(service):
    event = service.start_event(1, 5, 10, "hack", "start")
    with pytest.raises(DomainError, match="autre membre"):
        service.finish_hack(1, 11, event["event_id"], "attack")
    result = service.finish_hack(1, 10, event["event_id"], "attack")
    assert result["win"] and result["reward"] == 200
    service.finish_hack(1, 10, event["event_id"], "attack")
    assert service.profile(1, 10, viewer=10)["wallet"] == 200
    with pytest.raises(DomainError, match="déjà"):
        service.finish_hack(1, 10, event["event_id"], "another-attack")


def test_expired_hack_cannot_pay(service):
    event = service.start_event(1, 5, 10, "hack", "start")
    service.clock.advance(31)
    with pytest.raises(DomainError, match="expiré"):
        service.finish_hack(1, 10, event["event_id"], "attack")
    assert service.settle_event(1, event["event_id"])["abandoned"]


def test_disabling_module_does_not_lose_paid_tickets(service, fund):
    fund(10, 1000)
    event = service.start_event(1, 5, 10, "jackpot", "start")
    service.join_event(1, 10, event["event_id"], "join")
    service.set_setting(1, "feature:jackpot", False)
    service.clock.advance(301)
    assert service.settle_event(1, event["event_id"])["reward"] == 100
