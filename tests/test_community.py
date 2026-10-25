import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from moka.base import DomainError


def test_concurrent_ticket_reservations_create_one_ticket(service):
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(lambda i: service.reserve_ticket(1, 10, f"ticket:{i}"), range(3)))
    assert len({r["id"] for r in rows}) == 1
    service.bind_ticket(1, rows[0]["id"], 555)
    assert service.ticket(1, 555)["user"] == 10
    service.close_ticket(1, 555)
    service.clock.advance(61)
    new = service.reserve_ticket(1, 10, "new")
    assert new["id"] != rows[0]["id"]
    # Le reçu rejoué n'est pas une preuve de statut : relecture de la base.
    old = service.reserve_ticket(1, 10, "ticket:0")
    assert service.ticket_by_id(1, old["id"])["status"] == "closed"


def test_ticket_read_and_bind_cannot_cross_guild(service):
    ticket = service.reserve_ticket(1, 10, "open")
    service.bind_ticket(2, ticket["id"], 555)
    with pytest.raises(DomainError):
        service.ticket(2, 555)
    with pytest.raises(DomainError):
        service.ticket_by_id(2, ticket["id"])
    assert service.ticket_by_id(1, ticket["id"])["channel"] is None


def test_photo_needs_level_then_explicit_approval(service):
    with pytest.raises(DomainError, match="niveau"):
        service.add_photo(1, 10, 999)
    service.config = replace(
        service.config, rules=replace(service.config.rules, trombi_min_level=0)
    )
    service.add_photo(1, 10, 999)
    assert service.approved_photos(1, 10) == 0
    assert service.review_photo(1, 999, approve=True) == 10
    assert service.approved_photos(1, 10) == 1
    with pytest.raises(DomainError):
        service.review_photo(1, 999, approve=True)
    assert service.delete_photo(1, 999) == 10
    assert service.approved_photos(1, 10) == 0


def test_deleted_photo_cannot_be_approved(service):
    service.config = replace(
        service.config, rules=replace(service.config.rules, trombi_min_level=0)
    )
    service.add_photo(1, 10, 999)
    service.delete_photo(1, 999)
    with pytest.raises(DomainError, match="attente"):
        service.review_photo(1, 999, approve=True)


def test_backup_is_consistent_and_never_overwrites(service, fund, tmp_path):
    fund(10, 500)
    target = service.store.backup(tmp_path / "backup.sqlite3")
    with sqlite3.connect(target) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT wallet FROM accounts WHERE user=10").fetchone()[0] == 500
    with pytest.raises(ValueError):
        service.store.backup(target)
    with pytest.raises(ValueError):
        service.store.backup(service.store.path)
    assert target.stat().st_mode & 0o777 == 0o600


def test_future_schema_is_not_downgraded(service):
    with service.store.transaction() as con:
        con.execute("PRAGMA user_version=999")
    with pytest.raises(ValueError, match="plus récente"):
        service.store.initialize()


def test_failed_backup_never_appears_as_healthy_file(service, tmp_path, monkeypatch):
    class InterruptedSource:
        def backup(self, destination):
            raise RuntimeError("interruption simulée")

        def close(self):
            pass

    monkeypatch.setattr(service.store, "connect", lambda: InterruptedSource())
    target = tmp_path / "moka-backup.sqlite3"
    with pytest.raises(RuntimeError, match="interruption"):
        service.store.backup(target)
    assert not target.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_forget_scrubs_account_and_preserves_replay_barrier(service, fund):
    fund(10, 100)
    fund(11, 100)
    service.transfer(1, 11, 10, 50, "gift")
    service.claim(1, 10, "daily")
    service.forget_user(1, 10)
    assert all(not rows for rows in service.export_user(1, 10).values())
    with pytest.raises(DomainError):
        service.claim(1, 10, "daily")
    with service.store.read() as con:
        result = json.loads(
            con.execute("SELECT result FROM receipts WHERE key='gift'").fetchone()[0]
        )
        assert result["target"] == 0
    assert service.profile(1, 10, viewer=10)["wallet"] == 0


def test_forget_waits_for_active_obligations(service):
    event = service.start_event(1, 5, 10, "goblin", "start")
    service.join_event(1, 11, event["event_id"], "join")
    with pytest.raises(DomainError, match="événements"):
        service.forget_user(1, 11)
    service.clock.advance(61)
    service.settle_event(1, event["event_id"])
    service.forget_user(1, 11)
    assert service.get_event(1, event["event_id"])["participants"] == []
