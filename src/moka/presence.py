"""Dates de participation et pauses annoncées, sans contenu de conversation."""

import re
import unicodedata

from moka.base import BaseService, DomainError

DAY = 86400
INACTIVE_AFTER = 21 * DAY


def conversational_text(text):
    """Indice syntaxique modeste ; ne prétend pas mesurer la qualité d'un échange."""
    text = unicodedata.normalize("NFKC", text).strip()
    if text.startswith(("/", "!", "?", ".")):
        return False
    text = re.sub(r"https?://\S+|<[^>]*>", " ", text)
    words = re.findall(r"[^\W\d_]+", text, re.UNICODE)
    return len(words) >= 4 and sum(map(len, words)) >= 20


class Presence(BaseService):
    def presence_enabled(self, guild):
        return bool(self.get_setting(guild, "presence:enabled", False))

    def _presence_member(self, con, guild, user):
        if type(user) is not int or user <= 0:
            raise DomainError("Membre invalide.")
        con.execute(
            "INSERT OR IGNORE INTO presence(guild,user,started) VALUES(?,?,?)",
            (guild, user, self.clock()),
        )

    def presence_member(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            self._presence_member(con, guild, user)
            row = dict(
                con.execute(
                    "SELECT * FROM presence WHERE guild=? AND user=?", (guild, user)
                ).fetchone()
            )
        reference = max(row["started"], row["last_at"] or 0, row["absent_until"] or 0)
        row["due_at"] = reference + INACTIVE_AFTER
        row["announced"] = (row["absent_until"] or 0) > self.clock()
        row["inactive"] = not row["announced"] and self.clock() >= row["due_at"]
        return row

    def record_participation(self, guild, user, kind):
        self.allowed(guild)
        if kind not in {"message", "voice"}:
            raise ValueError("Participation inconnue")
        if not self.presence_enabled(guild) or not self.admitted(guild, user):
            return False
        with self.store.transaction() as con:
            self._presence_member(con, guild, user)
            con.execute(
                "UPDATE presence SET last_at=?,last_kind=?,absent_until=NULL WHERE guild=? AND user=?",
                (self.clock(), kind, guild, user),
            )
        return True

    def announce_absence(self, guild, user, days):
        self.allowed(guild)
        if not self.presence_enabled(guild):
            raise DomainError("Le suivi des pauses n'est pas activé sur ce serveur.")
        if not self.admitted(guild, user):
            raise DomainError("Termine d'abord ton accueil au Comptoir.")
        if type(days) is not int or not 1 <= days <= 365:
            raise DomainError("Choisis une absence de 1 à 365 jours.")
        with self.store.transaction() as con:
            self._presence_member(con, guild, user)
            con.execute(
                "UPDATE presence SET absent_until=? WHERE guild=? AND user=?",
                (self.clock() + days * DAY, guild, user),
            )
        return self.presence_member(guild, user)

    def return_from_absence(self, guild, user):
        self.allowed(guild)
        if not self.presence_enabled(guild) or not self.admitted(guild, user):
            raise DomainError("Le suivi n'est pas disponible pour ce membre.")
        with self.store.transaction() as con:
            self._presence_member(con, guild, user)
            # Une déclaration de retour ouvre une nouvelle grâce sans inventer un échange.
            con.execute(
                "UPDATE presence SET started=?,absent_until=NULL WHERE guild=? AND user=?",
                (self.clock(), guild, user),
            )
        return self.presence_member(guild, user)

    def remove_presence(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute("DELETE FROM presence WHERE guild=? AND user=?", (guild, user))
