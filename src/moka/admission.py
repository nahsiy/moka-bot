"""Admission persistante ; aucun contenu d'entretien n'est enregistré."""

import hashlib
import hmac
import unicodedata

from moka.base import BaseService, DomainError


def keyword_hash(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return hashlib.sha256(" ".join(value.split()).encode()).hexdigest()


class Admission(BaseService):
    def admission_enabled(self, guild):
        return bool(self.get_setting(guild, "admission:enabled", False))

    def admission(self, guild, user=None, *, channel=None):
        self.allowed(guild)
        with self.store.read() as con:
            if channel is not None:
                row = con.execute(
                    "SELECT * FROM admissions WHERE guild=? AND channel=?", (guild, channel)
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT * FROM admissions WHERE guild=? AND user=?", (guild, user)
                ).fetchone()
            return dict(row) if row else None

    def admitted(self, guild, user):
        if not self.admission_enabled(guild):
            return True
        row = self.admission(guild, user)
        return bool(row and row["status"] == "approved")

    def begin_admission(self, guild, user, *, established=False):
        self.allowed(guild)
        if user <= 0:
            raise DomainError("Membre invalide.")
        with self.store.transaction() as con:
            con.execute(
                "INSERT OR IGNORE INTO admissions(guild,user,status,created,updated) VALUES(?,?,?,?,?)",
                (guild, user, "approved" if established else "pending", self.clock(), self.clock()),
            )
        return self.admission(guild, user)

    def bind_admission(self, guild, user, **fields):
        self.allowed(guild)
        if not fields or set(fields) - {"channel", "message", "voice"}:
            raise ValueError("Liaison d'accueil invalide")
        with self.store.transaction() as con:
            con.execute(
                "UPDATE admissions SET "
                + ",".join(key + "=?" for key in fields)
                + ",updated=? WHERE guild=? AND user=?",
                (*fields.values(), self.clock(), guild, user),
            )

    def confirm_reading(self, guild, user, keyword):
        self.allowed(guild)
        expected = self.get_setting(guild, "admission:keyword_hash")
        if not expected or not self.admission_enabled(guild):
            raise DomainError("L'accueil n'est pas encore activé.")
        with self.store.transaction() as con:
            row = con.execute(
                "SELECT * FROM admissions WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            if not row or row["status"] != "pending":
                raise DomainError("Aucun entretien en attente pour toi.")
            if row["read_at"] is not None:
                return True
            if row["attempt_at"] is not None and self.clock() - row["attempt_at"] < 5:
                raise DomainError("Prends quelques secondes pour relire tranquillement la charte.")
            valid = hmac.compare_digest(expected, keyword_hash(keyword))
            con.execute(
                "UPDATE admissions SET attempt_at=?,read_at=?,updated=? WHERE guild=? AND user=?",
                (self.clock(), self.clock() if valid else None, self.clock(), guild, user),
            )
        return valid

    def request_interview_voice(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            result = con.execute(
                "UPDATE admissions SET voice_requested=1,updated=? WHERE guild=? AND user=? AND status='pending'",
                (self.clock(), guild, user),
            )
            if not result.rowcount:
                raise DomainError("Aucun entretien en attente pour toi.")

    def decide_admission(self, guild, user, actor, decision):
        self.allowed(guild)
        if decision not in {"approved", "refused"} or actor == user:
            raise DomainError("Décision d'accueil invalide.")
        with self.store.transaction() as con:
            row = con.execute(
                "SELECT * FROM admissions WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            if not row:
                raise DomainError("Entretien introuvable.")
            if row["status"] == decision:
                return False
            if row["status"] != "pending":
                raise DomainError("Cet entretien a déjà reçu une décision.")
            if decision == "approved" and row["read_at"] is None:
                raise DomainError("La lecture de la charte doit d'abord être confirmée.")
            con.execute(
                "UPDATE admissions SET status=?,decided_by=?,updated=? WHERE guild=? AND user=?",
                (decision, actor, self.clock(), guild, user),
            )
        return True

    def reopen_admission(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            result = con.execute(
                "UPDATE admissions SET status='pending',read_at=NULL,attempt_at=NULL,voice_requested=0,decided_by=NULL,updated=? WHERE guild=? AND user=? AND status='refused'",
                (self.clock(), guild, user),
            )
            if not result.rowcount:
                raise DomainError("Seul un entretien refusé peut être repris.")
