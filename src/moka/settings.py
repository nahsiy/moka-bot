"""Réglages métier par serveur, validés et enregistrés ensemble."""

from dataclasses import fields, replace

from moka.base import BaseService, DomainError
from moka.config import FEATURES, Rules

LEGACY_RULES = {
    "counting_fine": "counting:fine",
    "counting_cheat_seconds": "counting:cheat_seconds",
}
EDITABLE_RULES = frozenset(f.name for f in fields(Rules)) - {"max_amount"}


class Settings(BaseService):
    def rules_for(self, guild, con=None):
        self.allowed(guild)
        if con is None:
            with self.store.read() as connection:
                return self.rules_for(guild, connection)
        patch = self.setting(con, guild, "rule_overrides", {})
        for name, key in LEGACY_RULES.items():
            value = self.setting(con, guild, key)
            if value is not None:
                patch[name] = value
        rules = replace(self.config.rules, **patch)
        rules.validate()
        return rules

    def rules_snapshot(self, guild):
        self.allowed(guild)
        with self.store.transaction() as con:
            return self.rules_for(guild, con), self.setting(con, guild, "rules_revision", 0)

    def rules_revision(self, guild):
        return self.get_setting(guild, "rules_revision", 0)

    def update_rules(self, guild, changes, *, revision=None):
        self.allowed(guild)
        if (
            not changes
            or set(changes) - EDITABLE_RULES
            or any(type(v) is not int for v in changes.values())
        ):
            raise DomainError("Ces réglages ne sont pas modifiables dans le panneau.")
        with self.store.transaction() as con:
            current_revision = self.setting(con, guild, "rules_revision", 0)
            if revision is not None and revision != current_revision:
                raise DomainError(
                    "Les réglages ont changé. Actualise le panneau avant de réessayer."
                )
            try:
                rules = replace(self.rules_for(guild, con), **changes)
                rules.validate()
            except (ValueError, TypeError) as error:
                message = (
                    str(error)
                    .replace(
                        "Counting : bonus minimum supérieur au maximum",
                        "Le gain minimum d’une surprise doit être inférieur ou égal au maximum.",
                    )
                    .replace(
                        "Gobelin : minimum supérieur au maximum",
                        "Le nombre minimum de participants doit être inférieur ou égal au maximum.",
                    )
                    .replace(
                        "Intérêts : 0 < taux initial <= taux maximum <= 1000 points de base",
                        "Les intérêts doivent respecter : 0 % < taux initial ≤ taux maximum ≤ 10 %.",
                    )
                )
                raise DomainError(message) from error
            if "bank_capacity" in changes:
                overflow = con.execute(
                    "SELECT 1 FROM accounts WHERE guild=? AND bank>?*(bank_tier+1) LIMIT 1",
                    (guild, rules.bank_capacity),
                ).fetchone()
                if overflow:
                    raise DomainError(
                        "Cette capacité serait inférieure à une banque existante. Choisis une capacité plus grande."
                    )
            patch = self.setting(con, guild, "rule_overrides", {})
            patch.update(changes)
            self._set_setting(con, guild, "rule_overrides", patch)
            for name, key in LEGACY_RULES.items():
                if name in changes:
                    con.execute("DELETE FROM settings WHERE guild=? AND key=?", (guild, key))
            self._set_setting(con, guild, "rules_revision", current_revision + 1)
            return current_revision + 1

    def update_modules(self, guild, selected, *, expected=None):
        self.allowed(guild)
        selected = set(selected)
        if selected - FEATURES:
            raise DomainError("Un module inconnu figure dans cette sélection.")
        with self.store.transaction() as con:
            current = {
                key
                for key in FEATURES
                if self.setting(con, guild, "feature:" + key, self.config.features[key])
            }
            if expected is not None and current != set(expected):
                raise DomainError(
                    "Les modules ont changé. Actualise le panneau avant de les enregistrer."
                )
            for key in FEATURES:
                self._set_setting(con, guild, "feature:" + key, key in selected)

    def staff_overview(self, guild):
        self.allowed(guild)
        with self.store.read() as con:
            account = con.execute(
                "SELECT COUNT(*) AS members,COALESCE(SUM(wallet+bank),0) AS circulation FROM accounts WHERE guild=?",
                (guild,),
            ).fetchone()
            active = con.execute(
                "SELECT COUNT(*) FROM events WHERE guild=? AND status='active'", (guild,)
            ).fetchone()[0]
            pending = con.execute(
                "SELECT COUNT(*) FROM admissions WHERE guild=? AND status='pending'", (guild,)
            ).fetchone()[0]
            penalties = con.execute(
                "SELECT COUNT(DISTINCT user) FROM role_grants WHERE guild=? AND until>? AND reason IN ('counting','words','counting-edit')",
                (guild, self.clock()),
            ).fetchone()[0]
            return {
                **dict(account),
                "events": active,
                "admissions": pending,
                "penalties": penalties,
            }
