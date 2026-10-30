"""Nombres validés et corvées persistantes, sans conserver les messages."""

from moka.base import BaseService, DomainError
from moka.counting_expression import evaluate_expression

TRACE_SECONDS = 30 * 86400


class CountingIntegrity(BaseService):
    def _track_counting(self, con, guild, channel, user, message, number):
        con.execute(
            "DELETE FROM counting_validations WHERE guild=? AND created<?",
            (guild, self.clock() - TRACE_SECONDS),
        )
        con.execute(
            "INSERT INTO counting_validations(guild,channel,message,user,number,created) VALUES(?,?,?,?,?,?)",
            (guild, channel, message, user, number, self.clock()),
        )

    def counting_validation(self, guild, channel, message):
        self.allowed(guild)
        with self.store.read() as con:
            row = con.execute(
                "SELECT * FROM counting_validations WHERE guild=? AND channel=? AND message=? AND created>=?",
                (guild, channel, message, self.clock() - TRACE_SECONDS),
            ).fetchone()
            return dict(row) if row else None

    def inspect_counting_edit(self, guild, channel, message, content, *, author=None):
        self.allowed(guild)
        value = evaluate_expression(content)
        with self.store.transaction() as con:
            row = con.execute(
                "SELECT * FROM counting_validations WHERE guild=? AND channel=? AND message=? AND created>=?",
                (guild, channel, message, self.clock() - TRACE_SECONDS),
            ).fetchone()
            if not row or (author is not None and author != row["user"]):
                return None
            if row["sanction_until"] is not None:
                return {**dict(row), "replayed": True}
            if value == row["number"]:
                return None
            if not self.setting(con, guild, "feature:counting", self.config.features["counting"]):
                return None
            role = self.setting(
                con, guild, "role:counting_cheat", self.config.roles.get("counting_cheat")
            )
            seconds = self.rules_for(guild, con).counting_cheat_seconds
            if not role or not seconds:
                return None
            # Un rôle partagé avec un autre usage ne doit pas écraser sa tâche de retrait.
            existing = con.execute(
                "SELECT reason FROM role_grants WHERE guild=? AND user=? AND role=?",
                (guild, row["user"], role),
            ).fetchone()
            if existing and existing["reason"] != "counting-edit":
                raise DomainError("Configure un rôle dédié à la corvée de vaisselle.")
            until = self.clock() + seconds
            con.execute(
                "INSERT INTO role_grants(guild,user,role,reason,until) VALUES(?,?,?,'counting-edit',?) ON CONFLICT(guild,user,role) DO UPDATE SET until=MAX(role_grants.until,excluded.until),applied=0",
                (guild, row["user"], role, until),
            )
            until = con.execute(
                "SELECT until FROM role_grants WHERE guild=? AND user=? AND role=?",
                (guild, row["user"], role),
            ).fetchone()[0]
            con.execute(
                "UPDATE counting_validations SET sanction_until=?,sanction_role=? WHERE guild=? AND message=?",
                (until, role, guild, message),
            )
            row = con.execute(
                "SELECT * FROM counting_validations WHERE guild=? AND message=?", (guild, message)
            ).fetchone()
            return {**dict(row), "replayed": False}

    def pending_counting_edits(self):
        guilds = self.config.guild_ids
        if not guilds:
            return []
        placeholders = ",".join("?" for _ in guilds)
        with self.store.read() as con:
            return [
                dict(row)
                for row in con.execute(
                    "SELECT * FROM counting_validations WHERE sanction_until IS NOT NULL AND notified=0 "
                    f"AND guild IN ({placeholders}) AND created>=? ORDER BY created LIMIT 25",
                    (*guilds, self.clock() - TRACE_SECONDS),
                )
            ]

    def counting_edit_notified(self, guild, message):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute(
                "UPDATE counting_validations SET notified=1 WHERE guild=? AND message=? AND sanction_until IS NOT NULL",
                (guild, message),
            )

    def prune_counting_validations(self):
        with self.store.transaction() as con:
            for guild in self.config.guild_ids:
                con.execute(
                    "DELETE FROM counting_validations WHERE guild=? AND created<?",
                    (guild, self.clock() - TRACE_SECONDS),
                )
