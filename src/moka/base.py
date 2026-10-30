from __future__ import annotations

import json
import math
import random
import time
from collections.abc import Callable

from moka.config import Config
from moka.store import Store


class DomainError(Exception):
    """Refus métier affichable à l'utilisateur, sans trace technique."""


def level(xp: int) -> int:
    return math.isqrt(xp // 100)


class BaseService:
    def __init__(self, store: Store, config: Config, *, clock: Callable = time.time, rng=None):
        self.store, self.config, self.clock = store, config, clock
        self.rng = rng or random.SystemRandom()

    def allowed(self, guild: int):
        if guild not in self.config.guild_ids:
            raise DomainError("Ce serveur n'est pas autorisé dans la configuration de Moka.")

    def setting(self, con, guild, key, default=None):
        row = con.execute(
            "SELECT value FROM settings WHERE guild=? AND key=?", (guild, key)
        ).fetchone()
        return json.loads(row[0]) if row else default

    def get_setting(self, guild, key, default=None):
        self.allowed(guild)
        with self.store.read() as con:
            return self.setting(con, guild, key, default)

    def _set_setting(self, con, guild, key, value):
        con.execute(
            "INSERT INTO settings VALUES(?,?,?) ON CONFLICT(guild,key) DO UPDATE SET value=excluded.value",
            (guild, key, json.dumps(value)),
        )

    def set_setting(self, guild, key, value):
        self.allowed(guild)
        with self.store.transaction() as con:
            self._set_setting(con, guild, key, value)

    def enabled(self, con, guild, feature):
        if not self.setting(con, guild, "feature:" + feature, self.config.features[feature]):
            label = {"goblin": "tournée de Moka", "hug": "câlin collectif"}.get(feature, feature)
            raise DomainError(f"Le module {label} est désactivé sur ce serveur.")

    def is_enabled(self, guild, feature):
        self.allowed(guild)
        with self.store.read() as con:
            return bool(
                self.setting(con, guild, "feature:" + feature, self.config.features[feature])
            )

    def account(self, con, guild, user):
        if user <= 0:
            raise DomainError("Membre invalide.")
        con.execute("INSERT OR IGNORE INTO accounts(guild,user) VALUES(?,?)", (guild, user))
        return dict(
            con.execute("SELECT * FROM accounts WHERE guild=? AND user=?", (guild, user)).fetchone()
        )

    def capacity(self, account, con=None):
        return self.rules_for(account["guild"], con).bank_capacity * (account["bank_tier"] + 1)

    def profile(self, guild, user, *, viewer=None):
        self.allowed(guild)
        with self.store.transaction() as con:
            account = self.account(con, guild, user)
            if account["private_profile"] and viewer != user:
                raise DomainError("Ce membre a choisi de garder son profil privé.")
            account.update(
                level=level(account["xp"]),
                next_xp=100 * (level(account["xp"]) + 1) ** 2,
                capacity=self.capacity(account, con),
            )
            title = con.execute(
                "SELECT title FROM profile_titles WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            from moka.collection import TITLES

            account["title"] = TITLES.get(title[0], {}).get("name") if title else None
            return account

    def leaderboard(self, guild, category="xp"):
        self.allowed(guild)
        if category not in {"xp", "money"}:
            raise DomainError("Classement inconnu.")
        with self.store.read() as con:
            self.enabled(con, guild, "xp" if category == "xp" else "economy")
            column = "xp" if category == "xp" else "wallet+bank"
            return [
                dict(row)
                for row in con.execute(
                    f"SELECT user,{column} AS score FROM accounts WHERE guild=? AND private_profile=0 ORDER BY score DESC,user LIMIT 10",
                    (guild,),
                )
            ]

    def _all_games_penalty(self, con, guild, user):
        row = con.execute(
            "SELECT role,until FROM role_grants WHERE guild=? AND user=? AND reason='counting-edit' AND until>? ORDER BY until DESC LIMIT 1",
            (guild, user, self.clock()),
        ).fetchone()
        return (
            {"penalty_until": row["until"], "penalty_role": row["role"], "scope": "all"}
            if row
            else None
        )

    def all_games_penalty(self, guild, user):
        self.allowed(guild)
        with self.store.read() as con:
            return self._all_games_penalty(con, guild, user)

    def _require_play(self, con, guild, user):
        if penalty := self._all_games_penalty(con, guild, user):
            raise DomainError(
                "🧽 Tu es de corvée de vaisselle : pause de tous les jeux jusqu’à "
                f"<t:{int(penalty['penalty_until'])}:t> (<t:{int(penalty['penalty_until'])}:R>). "
                "Le staff peut lever la sanction avec /debloquer."
            )

    def require_play(self, guild, user):
        self.allowed(guild)
        with self.store.read() as con:
            self._require_play(con, guild, user)

    def perform(self, guild, user, action, key, features, fn, *, game_exit=False):
        self.allowed(guild)
        if not key or len(str(key)) > 200:
            raise ValueError("Reçu invalide")
        with self.store.transaction() as con:
            if not game_exit and (
                action in {"bet", "robbery", "join", "hack-finish"} or action.startswith("start:")
            ):
                self._require_play(con, guild, user)
            previous = con.execute(
                "SELECT * FROM receipts WHERE guild=? AND key=?", (guild, str(key))
            ).fetchone()
            if previous:
                if previous["user"] != user or previous["action"] != action:
                    raise DomainError("Ce reçu appartient à une autre action.")
                return {**json.loads(previous["result"]), "replayed": True}
            for feature in features:
                self.enabled(con, guild, feature)
            self.account(con, guild, user)
            result = fn(con)
            con.execute(
                "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                (guild, str(key), user, action, json.dumps(result), self.clock()),
            )
            return {**result, "replayed": False}

    def amount(self, value):
        if type(value) is not int or not 1 <= value <= self.config.rules.max_amount:
            raise DomainError(
                f"Le montant doit être compris entre 1 et {self.config.rules.max_amount:,}."
            )
        return value

    def money(self, con, guild, user, wallet=0, bank=0, reason=""):
        account = self.account(con, guild, user)
        if account["wallet"] + wallet < 0 or account["bank"] + bank < 0:
            raise DomainError("Solde insuffisant.")
        if account["wallet"] + wallet + account["bank"] + bank > self.config.rules.max_amount:
            raise DomainError("Le plafond de monnaie virtuelle serait dépassé.")
        con.execute(
            "UPDATE accounts SET wallet=wallet+?, bank=bank+? WHERE guild=? AND user=?",
            (wallet, bank, guild, user),
        )
        if wallet or bank:
            con.execute(
                "INSERT INTO ledger(guild,user,wallet_delta,bank_delta,reason,created) VALUES(?,?,?,?,?,?)",
                (guild, user, wallet, bank, reason, self.clock()),
            )

    def cooldown(self, con, guild, user, action, seconds):
        row = con.execute(
            "SELECT until FROM cooldowns WHERE guild=? AND user=? AND action=?",
            (guild, user, action),
        ).fetchone()
        now = self.clock()
        if row and row[0] > now:
            raise DomainError(f"Patience : encore {math.ceil(row[0] - now)} secondes.")
        con.execute(
            "INSERT INTO cooldowns VALUES(?,?,?,?) ON CONFLICT(guild,user,action) DO UPDATE SET until=excluded.until",
            (guild, user, action, now + seconds),
        )

    def credit_prize(self, con, guild, user, amount, reason):
        account = self.account(con, guild, user)
        actual = min(
            amount, max(0, self.config.rules.max_amount - account["wallet"] - account["bank"])
        )
        self.money(con, guild, user, wallet=actual, reason=reason)
        return actual

    def add_xp(self, con, guild, user, xp):
        account = self.account(con, guild, user)
        before, after = level(account["xp"]), level(account["xp"] + xp)
        con.execute("UPDATE accounts SET xp=xp+? WHERE guild=? AND user=?", (xp, guild, user))
        coins = (after - before) * self.rules_for(guild, con).level_coins
        # Les niveaux continuent de fonctionner si l'économie est désactivée.
        if coins and self.setting(con, guild, "feature:economy", self.config.features["economy"]):
            coins = self.credit_prize(con, guild, user, coins, "level")
        else:
            coins = 0
        return {"xp": xp, "level": after, "previous_level": before, "level_coins": coins}

    def activity(self, guild, user, key, kind="message"):
        if kind not in {"message", "voice"}:
            raise ValueError("Activité inconnue")

        def run(con):
            rules = self.rules_for(guild, con)
            self.cooldown(
                con, guild, user, kind, rules.message_cooldown if kind == "message" else 55
            )
            result = self.add_xp(
                con, guild, user, rules.message_xp if kind == "message" else rules.voice_xp
            )
            coins = rules.message_coins if kind == "message" else rules.voice_coins
            if self.setting(con, guild, "feature:economy", self.config.features["economy"]):
                coins = self.credit_prize(con, guild, user, coins, kind)
            else:
                coins = 0
            column = "messages" if kind == "message" else "voice_minutes"
            con.execute(
                f"UPDATE accounts SET {column}={column}+1 WHERE guild=? AND user=?", (guild, user)
            )
            return {**result, "coins": coins}

        return self.perform(guild, user, kind, key, ["xp"], run)

    def adjust(self, guild, user, amount, key):
        if type(amount) is not int or abs(amount) > self.config.rules.max_amount:
            raise DomainError("Ajustement invalide.")

        def run(con):
            self.money(con, guild, user, wallet=amount, reason="staff-adjustment")
            return {"amount": amount}

        return self.perform(guild, user, "adjust", key, ["economy"], run)
