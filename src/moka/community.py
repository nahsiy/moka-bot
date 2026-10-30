from __future__ import annotations

import json
import sqlite3
import uuid

from moka.base import BaseService, DomainError, level
from moka.social_catalog import SOCIAL_CATALOG


class Community(BaseService):
    def social_message(self, guild, user, key, kind):
        if kind not in SOCIAL_CATALOG:
            raise DomainError("Choisis un compliment ou une taquinerie.")

        def run(con):
            self.cooldown(con, guild, user, "fun", 15)
            catalog = SOCIAL_CATALOG[kind]
            setting_key = "fun:recent:" + kind
            recent = self.setting(con, guild, setting_key, [])
            recent = [line for line in recent if line in catalog][-5:]
            draw = self.rng.random()
            rarity = "classic" if draw < 0.60 else "rare" if draw < 0.90 else "epic"
            pool = (
                catalog[:30]
                if rarity == "classic"
                else catalog[30:42]
                if rarity == "rare"
                else catalog[42:]
            )
            text = self.rng.choice([line for line in pool if line not in recent])
            self._set_setting(con, guild, setting_key, (recent + [text])[-5:])
            return {"text": text, "kind": kind, "rarity": rarity}

        return self.perform(guild, user, "fun", key, ["fun"], run)

    def reserve_ticket(self, guild, user, key):
        def run(con):
            existing = con.execute(
                "SELECT * FROM tickets WHERE guild=? AND user=? AND status IN ('creating','open')",
                (guild, user),
            ).fetchone()
            if existing:
                return dict(existing)
            self.cooldown(con, guild, user, "ticket", 60)
            ticket_id = uuid.uuid4().hex
            con.execute(
                "INSERT INTO tickets(id,guild,user,created) VALUES(?,?,?,?)",
                (ticket_id, guild, user, self.clock()),
            )
            return dict(con.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())

        return self.perform(guild, user, "ticket-reserve", key, ["tickets"], run)

    def bind_ticket(self, guild, ticket_id, channel):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute(
                "UPDATE tickets SET channel=?,status='open' WHERE id=? AND guild=? AND status='creating'",
                (channel, ticket_id, guild),
            )

    def fail_ticket(self, guild, ticket_id):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute(
                "UPDATE tickets SET status='failed' WHERE id=? AND guild=? AND status='creating'",
                (ticket_id, guild),
            )

    def ticket(self, guild, channel):
        self.allowed(guild)
        with self.store.read() as con:
            row = con.execute(
                "SELECT * FROM tickets WHERE guild=? AND channel=? AND status='open'",
                (guild, channel),
            ).fetchone()
            if not row:
                raise DomainError("Ce salon n'est pas un ticket ouvert de Moka.")
            return dict(row)

    def ticket_by_id(self, guild, ticket_id):
        self.allowed(guild)
        with self.store.read() as con:
            row = con.execute(
                "SELECT * FROM tickets WHERE guild=? AND id=?", (guild, ticket_id)
            ).fetchone()
            if not row:
                raise DomainError("Ticket introuvable.")
            return dict(row)

    def close_ticket(self, guild, channel):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute(
                "UPDATE tickets SET status='closed' WHERE guild=? AND channel=? AND status='open'",
                (guild, channel),
            )

    def pending_tickets(self, guild):
        self.allowed(guild)
        with self.store.read() as con:
            return [
                dict(r)
                for r in con.execute(
                    "SELECT * FROM tickets WHERE guild=? AND status='creating'", (guild,)
                )
            ]

    def add_photo(self, guild, user, message):
        self.allowed(guild)
        with self.store.transaction() as con:
            self.enabled(con, guild, "trombi")
            account = self.account(con, guild, user)
            minimum = self.rules_for(guild, con).trombi_min_level
            if level(account["xp"]) < minimum:
                raise DomainError(f"Le trombinoscope demande le niveau {minimum}.")
            con.execute(
                "INSERT OR IGNORE INTO photos(guild,user,message) VALUES(?,?,?)",
                (guild, user, message),
            )

    def review_photo(self, guild, message, *, approve):
        self.allowed(guild)
        with self.store.transaction() as con:
            self.enabled(con, guild, "trombi")
            row = con.execute(
                "SELECT * FROM photos WHERE guild=? AND message=?", (guild, message)
            ).fetchone()
            if not row or row["status"] != "pending":
                raise DomainError("Cette photo n'est plus en attente.")
            con.execute(
                "UPDATE photos SET status=? WHERE guild=? AND message=?",
                ("approved" if approve else "rejected", guild, message),
            )
            return row["user"]

    def delete_photo(self, guild, message):
        self.allowed(guild)
        with self.store.transaction() as con:
            row = con.execute(
                "SELECT user FROM photos WHERE guild=? AND message=?", (guild, message)
            ).fetchone()
            con.execute(
                "UPDATE photos SET status='deleted' WHERE guild=? AND message=?", (guild, message)
            )
            return row[0] if row else None

    def approved_photos(self, guild, user):
        self.allowed(guild)
        with self.store.read() as con:
            return con.execute(
                "SELECT COUNT(*) FROM photos WHERE guild=? AND user=? AND status='approved'",
                (guild, user),
            ).fetchone()[0]

    def set_privacy(self, guild, user, private):
        self.allowed(guild)
        with self.store.transaction() as con:
            self.account(con, guild, user)
            con.execute(
                "UPDATE accounts SET private_profile=? WHERE guild=? AND user=?",
                (int(private), guild, user),
            )

    def export_user(self, guild, user):
        self.allowed(guild)
        tables = (
            "accounts",
            "admissions",
            "presence",
            "counting_validations",
            "inventory",
            "collections",
            "profile_titles",
            "cooldowns",
            "ledger",
            "role_grants",
            "tickets",
            "photos",
        )
        with self.store.read() as con:
            return {
                table: [
                    dict(row)
                    for row in con.execute(
                        f"SELECT * FROM {table} WHERE guild=? AND user=?", (guild, user)
                    )
                ]
                for table in tables
            }

    def forget_user(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            # Ne pas effacer une dette technique active : expiration de rôle,
            # photo à retirer ou participation dont le gain reste à verser.
            pending = con.execute(
                "SELECT 1 FROM participants p JOIN events e ON e.id=p.event WHERE e.guild=? AND p.user=? AND e.status='active' UNION ALL SELECT 1 FROM events WHERE guild=? AND owner=? AND status='active' UNION ALL SELECT 1 FROM role_grants WHERE guild=? AND user=? UNION ALL SELECT 1 FROM tickets WHERE guild=? AND user=? AND status IN ('creating','open') UNION ALL SELECT 1 FROM photos WHERE guild=? AND user=? AND status IN ('pending','approved')",
                (guild, user, guild, user, guild, user, guild, user, guild, user),
            ).fetchone()
            if pending:
                raise DomainError(
                    "Termine tes événements et tickets, retire tes photos et attends l'expiration de tes rôles temporaires avant l'effacement."
                )
            for table in (
                "accounts",
                "inventory",
                "collections",
                "profile_titles",
                "cooldowns",
                "ledger",
                "tickets",
                "photos",
                "presence",
                "counting_validations",
            ):
                con.execute(f"DELETE FROM {table} WHERE guild=? AND user=?", (guild, user))
            # Garde seulement un marqueur anonyme contre le rejeu d'une ancienne
            # interaction. Ni identité ni ancien résultat dans ce marqueur.
            con.execute(
                "UPDATE receipts SET user=0,result='{}' WHERE guild=? AND user=?", (guild, user)
            )
            for row in con.execute(
                "SELECT key,result FROM receipts WHERE guild=?", (guild,)
            ).fetchall():
                result = json.loads(row["result"])
                if result.get("target") == user:
                    result["target"] = 0
                    con.execute(
                        "UPDATE receipts SET result=? WHERE guild=? AND key=?",
                        (json.dumps(result), guild, row["key"]),
                    )
            con.execute("UPDATE events SET owner=0 WHERE guild=? AND owner=?", (guild, user))
            for row in con.execute(
                "SELECT id,result FROM events WHERE guild=? AND result IS NOT NULL", (guild,)
            ).fetchall():
                result = json.loads(row["result"])
                if result.get("winner") == user:
                    result["winner"] = 0
                    con.execute(
                        "UPDATE events SET result=? WHERE id=?", (json.dumps(result), row["id"])
                    )
            con.execute(
                "DELETE FROM participants WHERE user=? AND event IN (SELECT id FROM events WHERE guild=?)",
                (user, guild),
            )
            con.execute("UPDATE games SET last_user=0 WHERE guild=? AND last_user=?", (guild, user))

    def check_integrity(self):
        with self.store.read() as con:
            try:
                return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            except sqlite3.DatabaseError:
                return False
