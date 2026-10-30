"""Souvenirs décoratifs du Comptoir : attribution unique, sans privilège Discord."""

from moka.base import BaseService, DomainError, level

BADGES = {
    "premier_cafe": {
        "name": "Premier café",
        "emoji": "☕",
        "description": "Participer à une première discussion.",
        "metric": "messages",
        "goal": 1,
    },
    "conversation": {
        "name": "Un brin de causette",
        "emoji": "💬",
        "description": "100 messages comptabilisés, à ton rythme.",
        "metric": "messages",
        "goal": 100,
    },
    "voix": {
        "name": "Une chaise au comptoir",
        "emoji": "🎧",
        "description": "60 minutes de vocal comptabilisées.",
        "metric": "voice_minutes",
        "goal": 60,
    },
    "reserve": {
        "name": "La petite réserve",
        "emoji": "🏦",
        "description": "Mettre 500 cœurs en banque.",
        "metric": "bank",
        "goal": 500,
    },
    "cadeau": {
        "name": "La main sur le cœur",
        "emoji": "🎁",
        "description": "Offrir un premier objet de la boutique.",
        "metric": "gifts",
        "goal": 1,
    },
    "tournee": {
        "name": "Tous à la même table",
        "emoji": "🫶",
        "description": "Participer à une tournée ou un câlin arrivé à son terme.",
        "metric": "rounds",
        "goal": 1,
    },
    "niveau": {
        "name": "Les petites habitudes",
        "emoji": "🌱",
        "description": "Atteindre le niveau 3.",
        "metric": "level",
        "goal": 3,
    },
    "grains": {
        "name": "Le compte est bon",
        "emoji": "🫘",
        "description": "Proposer 25 bons nombres au counting.",
        "metric": "counts",
        "goal": 25,
    },
}
TITLES = {
    "pause_douce": {"name": "La pause douceur", "price": 500},
    "biscuit": {"name": "Gardien des biscuits", "price": 800},
    "espresso": {"name": "Esprit espresso", "price": 1200},
    "vinyle": {"name": "Au rythme des vinyles", "price": 1200},
}


class Collection(BaseService):
    def collection(self, guild, user):
        self.allowed(guild)
        with self.store.transaction() as con:
            self.enabled(con, guild, "collection")
            account = self.account(con, guild, user)
            metrics = {**account, "level": level(account["xp"])}
            metrics["gifts"] = con.execute(
                "SELECT COUNT(*) FROM receipts WHERE guild=? AND user=? AND action='give-item'",
                (guild, user),
            ).fetchone()[0]
            metrics["rounds"] = con.execute(
                "SELECT COUNT(*) FROM participants p JOIN events e ON e.id=p.event WHERE e.guild=? AND p.user=? AND e.kind IN ('hug','goblin') AND e.status='finished'",
                (guild, user),
            ).fetchone()[0]
            # Les reçus ne contiennent pas les messages des membres.
            metrics["counts"] = con.execute(
                "SELECT COUNT(*) FROM receipts WHERE guild=? AND user=? AND action='counting' AND json_extract(result,'$.valid')=1",
                (guild, user),
            ).fetchone()[0]
            for key, badge in BADGES.items():
                if metrics[badge["metric"]] >= badge["goal"]:
                    con.execute(
                        "INSERT OR IGNORE INTO collections VALUES(?,?,?,?,?)",
                        (guild, user, "badge", key, self.clock()),
                    )
            owned = [
                dict(row)
                for row in con.execute(
                    "SELECT kind,item,earned FROM collections WHERE guild=? AND user=? ORDER BY earned,item",
                    (guild, user),
                )
            ]
            title = con.execute(
                "SELECT title FROM profile_titles WHERE guild=? AND user=?", (guild, user)
            ).fetchone()
            earned_badges = {row["item"] for row in owned if row["kind"] == "badge"}
            return {
                "owned": owned,
                "title": title[0] if title else None,
                "progress": {
                    key: b["goal"] if key in earned_badges else min(b["goal"], metrics[b["metric"]])
                    for key, b in BADGES.items()
                },
            }

    def buy_title(self, guild, user, title, key):
        if title not in TITLES:
            raise DomainError("Ce titre ne figure pas dans la boutique.")

        def run(con):
            if con.execute(
                "SELECT 1 FROM collections WHERE guild=? AND user=? AND kind='title' AND item=?",
                (guild, user, title),
            ).fetchone():
                raise DomainError(
                    "Tu possèdes déjà ce titre. Tu peux l’afficher depuis Mes titres."
                )
            self.money(con, guild, user, wallet=-TITLES[title]["price"], reason="title:" + title)
            con.execute(
                "INSERT INTO collections VALUES(?,?,?,?,?)",
                (guild, user, "title", title, self.clock()),
            )
            return {"title": title, **TITLES[title]}

        return self.perform(guild, user, "buy-title", key, ["collection", "economy", "shop"], run)

    def equip_title(self, guild, user, title, key):
        if title is not None and title not in TITLES:
            raise DomainError("Titre inconnu.")

        def run(con):
            if (
                title is not None
                and not con.execute(
                    "SELECT 1 FROM collections WHERE guild=? AND user=? AND kind='title' AND item=?",
                    (guild, user, title),
                ).fetchone()
            ):
                raise DomainError("Ce titre ne fait pas encore partie de ta collection.")
            con.execute(
                "INSERT INTO profile_titles VALUES(?,?,?) ON CONFLICT(guild,user) DO UPDATE SET title=excluded.title",
                (guild, user, title),
            )
            return {"title": title}

        return self.perform(guild, user, "equip-title", key, ["collection"], run)

    def heart_history(self, guild, user, page=0):
        self.allowed(guild)
        if type(page) is not int or page < 0:
            raise DomainError("Page inconnue.")
        with self.store.read() as con:
            rows = [
                dict(row)
                for row in con.execute(
                    "SELECT wallet_delta,bank_delta,reason,created FROM ledger WHERE guild=? AND user=? ORDER BY id DESC LIMIT 9 OFFSET ?",
                    (guild, user, page * 8),
                )
            ]
        return {"rows": rows[:8], "more": len(rows) > 8, "page": page}

    def reward_status(self, guild, user):
        self.allowed(guild)
        with self.store.read() as con:
            return {
                period: max(
                    0,
                    (
                        row[0]
                        if (
                            row := con.execute(
                                "SELECT until FROM cooldowns WHERE guild=? AND user=? AND action=?",
                                (guild, user, period),
                            ).fetchone()
                        )
                        else 0
                    )
                    - self.clock(),
                )
                for period in ("daily", "weekly")
            }
