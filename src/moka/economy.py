from __future__ import annotations

from moka.base import BaseService, DomainError

# Catalogue original de démonstration. Aucun rôle privilégié n'est commercialisé.
CATALOG = {
    "cafe": {"name": "Café virtuel", "price": 50},
    "biscuit": {"name": "Biscuit porte-bonheur", "price": 100},
    "trophee": {"name": "Petit trophée du QG", "price": 500},
}


class Economy(BaseService):
    def claim(self, guild, user, key, period="daily"):
        if period not in {"daily", "weekly"}:
            raise DomainError("Récompense inconnue.")
        amount = (
            self.config.rules.daily_coins if period == "daily" else self.config.rules.weekly_coins
        )

        def run(con):
            self.cooldown(con, guild, user, period, 86400 if period == "daily" else 604800)
            self.money(con, guild, user, wallet=amount, reason=period)
            return {"amount": amount}

        return self.perform(guild, user, period, key, ["economy"], run)

    def transfer(self, guild, user, target, amount, key):
        self.amount(amount)
        if target == user:
            raise DomainError("Choisis un autre membre.")

        def run(con):
            self.money(con, guild, user, wallet=-amount, reason="gift-out")
            self.money(con, guild, target, wallet=amount, reason="gift-in")
            return {"amount": amount, "target": target}

        return self.perform(guild, user, "transfer", key, ["economy"], run)

    def bank_move(self, guild, user, amount, key, *, deposit=True):
        self.amount(amount)

        def run(con):
            account = self.account(con, guild, user)
            if deposit and account["bank"] + amount > self.capacity(account):
                raise DomainError("La capacité de ta banque est insuffisante.")
            self.money(
                con,
                guild,
                user,
                wallet=-amount if deposit else amount,
                bank=amount if deposit else -amount,
                reason="deposit" if deposit else "withdraw",
            )
            return {"amount": amount, "deposit": deposit}

        return self.perform(
            guild, user, "deposit" if deposit else "withdraw", key, ["economy", "bank"], run
        )

    def bank_upgrade(self, guild, user, key, kind="capacity"):
        columns = {
            "capacity": "bank_tier",
            "interest": "interest_tier",
            "protection": "protection_tier",
        }
        if kind not in columns:
            raise DomainError("Amélioration inconnue.")

        def run(con):
            account = self.account(con, guild, user)
            column = columns[kind]
            tier = account[column]
            if (
                tier >= 20
                or (
                    kind == "interest"
                    and self.config.rules.bank_interest_bps * (tier + 1)
                    >= self.config.rules.bank_interest_max_bps
                )
                or (kind == "protection" and tier >= 5)
            ):
                raise DomainError("Amélioration maximale déjà atteinte.")
            cost = self.config.rules.bank_upgrade_cost * (tier + 1)
            self.money(con, guild, user, wallet=-cost, reason="bank-upgrade")
            con.execute(
                f"UPDATE accounts SET {column}={column}+1 WHERE guild=? AND user=?", (guild, user)
            )
            return {"kind": kind, "tier": tier + 1, "cost": cost}

        return self.perform(guild, user, "upgrade", key, ["economy", "bank"], run)

    def interest(self, guild, user, key):
        def run(con):
            account = self.account(con, guild, user)
            rate = min(
                self.config.rules.bank_interest_max_bps,
                self.config.rules.bank_interest_bps * (account["interest_tier"] + 1),
            )
            amount = account["bank"] * rate // 10000
            if amount == 0:
                raise DomainError(
                    "Le solde de ta banque est trop faible pour produire des intérêts."
                )
            self.cooldown(con, guild, user, "interest", 86400)
            self.money(con, guild, user, wallet=amount, reason="interest")
            return {"amount": amount, "rate_bps": rate}

        return self.perform(guild, user, "interest", key, ["economy", "bank"], run)

    def pot(self, guild):
        self.allowed(guild)
        with self.store.read() as con:
            row = con.execute("SELECT amount FROM pots WHERE guild=?", (guild,)).fetchone()
            return row[0] if row else 0

    def add_pot(self, con, guild, amount):
        con.execute(
            "INSERT INTO pots VALUES(?,?) ON CONFLICT(guild) DO UPDATE SET amount=amount+excluded.amount",
            (guild, amount),
        )

    def bet(self, guild, user, amount, key):
        self.amount(amount)

        def run(con):
            self.cooldown(con, guild, user, "bet", 5)
            self.money(con, guild, user, wallet=-amount, reason="bet-stake")
            win = self.rng.random() < 0.45
            payout = amount * 2 if win else 0
            if payout:
                self.money(con, guild, user, wallet=payout, reason="bet-prize")
            else:
                self.add_pot(con, guild, amount // 10)
            return {"win": win, "stake": amount, "payout": payout, "net": payout - amount}

        return self.perform(guild, user, "bet", key, ["economy", "bet"], run)

    def rob(self, guild, user, target, key):
        if target == user:
            raise DomainError("Tu ne peux pas te voler toi-même.")

        def run(con):
            thief, victim = self.account(con, guild, user), self.account(con, guild, target)
            minimum = self.config.rules.robbery_min_wallet
            if min(thief["wallet"], victim["wallet"]) < minimum:
                raise DomainError(
                    f"Les deux portefeuilles doivent contenir au moins {minimum} cœurs."
                )
            shield = con.execute(
                "SELECT until FROM cooldowns WHERE guild=? AND user=? AND action='robbed'",
                (guild, target),
            ).fetchone()
            if shield and shield[0] > self.clock():
                raise DomainError("Cette cible bénéficie d'une protection temporaire.")
            self.cooldown(con, guild, user, "robbery", self.config.rules.robbery_cooldown)
            chance = max(0.10, 0.55 - victim["protection_tier"] * 0.08)
            win = self.rng.random() < chance
            if win:
                amount = min(
                    victim["wallet"],
                    self.config.rules.robbery_max_loot,
                    max(1, victim["wallet"] * self.rng.randint(5, 20) // 100),
                )
                self.money(con, guild, target, wallet=-amount, reason="robbery-loss")
                self.money(con, guild, user, wallet=amount, reason="robbery-gain")
                self.cooldown(
                    con, guild, target, "robbed", self.config.rules.robbery_protection_seconds
                )
            else:
                amount = min(thief["wallet"], max(1, thief["wallet"] // 10))
                self.money(con, guild, user, wallet=-amount, reason="robbery-fine")
            return {"win": win, "amount": amount, "target": target}

        return self.perform(guild, user, "robbery", key, ["economy", "robbery"], run)

    def buy(self, guild, user, item, key):
        if item not in CATALOG:
            raise DomainError("Article inconnu.")

        def run(con):
            self.money(con, guild, user, wallet=-CATALOG[item]["price"], reason="shop:" + item)
            con.execute(
                "INSERT INTO inventory VALUES(?,?,?,1) ON CONFLICT(guild,user,item) DO UPDATE SET quantity=quantity+1",
                (guild, user, item),
            )
            return {"item": item, **CATALOG[item]}

        return self.perform(guild, user, "buy", key, ["economy", "shop"], run)

    def inventory(self, guild, user):
        self.allowed(guild)
        with self.store.read() as con:
            self.enabled(con, guild, "shop")
            return [
                dict(row)
                for row in con.execute(
                    "SELECT item,quantity FROM inventory WHERE guild=? AND user=? AND quantity>0",
                    (guild, user),
                )
            ]

    def give_item(self, guild, user, target, item, key):
        if target == user or item not in CATALOG:
            raise DomainError("Cadeau invalide.")

        def run(con):
            self.account(con, guild, target)
            updated = con.execute(
                "UPDATE inventory SET quantity=quantity-1 WHERE guild=? AND user=? AND item=? AND quantity>0",
                (guild, user, item),
            )
            if not updated.rowcount:
                raise DomainError("Tu ne possèdes pas cet objet.")
            con.execute(
                "INSERT INTO inventory VALUES(?,?,?,1) ON CONFLICT(guild,user,item) DO UPDATE SET quantity=quantity+1",
                (guild, target, item),
            )
            return {"item": item, "target": target}

        return self.perform(guild, user, "give-item", key, ["shop"], run)
