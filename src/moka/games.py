from __future__ import annotations

import json
import re
import unicodedata
import uuid

from moka.base import BaseService, DomainError


def normalize_word(text):
    return unicodedata.normalize("NFKC", text).casefold().strip()


def letters(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if c.isalpha())


class Games(BaseService):
    def counting(self, guild, channel, user, content, message):
        text = content.strip()
        if not re.fullmatch(r"[0-9]{1,12}", text):
            return {"ignored": True}
        number = int(text)

        def run(con):
            con.execute(
                "INSERT OR IGNORE INTO games(guild,channel,kind) VALUES(?,?,'counting')",
                (guild, channel),
            )
            state = dict(
                con.execute(
                    "SELECT * FROM games WHERE guild=? AND channel=? AND kind='counting'",
                    (guild, channel),
                ).fetchone()
            )
            if message <= state["last_message"]:
                return {"ignored": True}
            expected = state["score"] + 1
            valid = number == expected and user != state["last_user"]
            score = number if valid else 0
            con.execute(
                "UPDATE games SET score=?, record=MAX(record,?), last_user=?, last_message=? WHERE guild=? AND channel=? AND kind='counting'",
                (score, score, user if valid else 0, message, guild, channel),
            )
            reward = 0
            if (
                valid
                and score % self.config.rules.counting_reward_every == 0
                and self.setting(con, guild, "feature:economy", self.config.features["economy"])
            ):
                reward = self.config.rules.counting_reward
                self.money(con, guild, user, wallet=reward, reason="counting")
            role = self.setting(
                con, guild, "role:counting_failure", self.config.roles.get("counting_failure")
            )
            if not valid and role:
                con.execute(
                    "INSERT INTO role_grants(guild,user,role,reason,until) VALUES(?,?,?,'counting',?) ON CONFLICT(guild,user,role) DO UPDATE SET until=excluded.until",
                    (guild, user, role, self.clock() + self.config.rules.counting_failure_seconds),
                )
            return {
                "valid": valid,
                "score": score,
                "expected": expected,
                "reward": reward,
                "record": max(state["record"], score),
                "reason": "same_user" if user == state["last_user"] else "number",
            }

        return self.perform(guild, user, "counting", f"count:{message}", ["counting"], run)

    def word(self, guild, channel, user, content, message):
        word = normalize_word(content)
        if len(word) > 40 or not re.fullmatch(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", word):
            return {"ignored": True}

        def run(con):
            con.execute(
                "INSERT OR IGNORE INTO games(guild,channel,kind) VALUES(?,?,'words')",
                (guild, channel),
            )
            state = dict(
                con.execute(
                    "SELECT * FROM games WHERE guild=? AND channel=? AND kind='words'",
                    (guild, channel),
                ).fetchone()
            )
            if message <= state["last_message"]:
                return {"ignored": True}
            if state["last_user"] == user:
                raise DomainError("Laisse un autre membre proposer le prochain mot.")
            if con.execute(
                "SELECT 1 FROM words WHERE guild=? AND channel=? AND round=? AND word=?",
                (guild, channel, state["round"], word),
            ).fetchone():
                raise DomainError("Ce mot a déjà été proposé pendant cette partie.")
            mode = self.setting(con, guild, "words:mode", self.config.word_mode)
            if (
                mode == "last_letter"
                and state["value"]
                and letters(state["value"])[-1] != letters(word)[0]
            ):
                raise DomainError(f"Le mot doit commencer par « {letters(state['value'])[-1]} ».")
            self.cooldown(con, guild, user, "words", self.config.rules.words_cooldown)
            con.execute("INSERT INTO words VALUES(?,?,?,?)", (guild, channel, state["round"], word))
            score = state["score"] + 1
            con.execute(
                "UPDATE games SET value=?, last_user=?, score=?, record=MAX(record,?), last_message=? WHERE guild=? AND channel=? AND kind='words'",
                (word, user, score, score, message, guild, channel),
            )
            return {"valid": True, "word": word, "score": score, "mode": mode}

        return self.perform(guild, user, "words", f"word:{message}", ["words"], run)

    def reset_game(self, guild, channel, kind):
        self.allowed(guild)
        if kind not in {"counting", "words"}:
            raise DomainError("Jeu inconnu.")
        with self.store.transaction() as con:
            con.execute(
                "UPDATE games SET value='', last_user=0,score=0,round=round+1 WHERE guild=? AND channel=? AND kind=?",
                (guild, channel, kind),
            )
            con.execute("DELETE FROM words WHERE guild=? AND channel=?", (guild, channel))

    def get_event(self, guild, event_id):
        self.allowed(guild)
        with self.store.read() as con:
            row = con.execute(
                "SELECT * FROM events WHERE id=? AND guild=?", (event_id, guild)
            ).fetchone()
            if not row:
                raise DomainError("Événement introuvable sur ce serveur.")
            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            event["result"] = json.loads(event["result"]) if event["result"] else None
            event["participants"] = [
                r[0]
                for r in con.execute(
                    "SELECT user FROM participants WHERE event=? ORDER BY user", (event_id,)
                )
            ]
            return event

    def active_events(self):
        with self.store.read() as con:
            return [
                dict(row)
                for row in con.execute("SELECT * FROM events WHERE status='active'")
                if row["guild"] in self.config.guild_ids
            ]

    def pending_event_notifications(self):
        with self.store.read() as con:
            return [
                dict(row)
                for row in con.execute(
                    "SELECT * FROM events WHERE status='finished' AND notified=0"
                )
                if row["guild"] in self.config.guild_ids
            ]

    def event_notified(self, guild, event_id):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute("UPDATE events SET notified=1 WHERE guild=? AND id=?", (guild, event_id))

    def bind_event(self, guild, event_id, message):
        self.allowed(guild)
        with self.store.transaction() as con:
            con.execute(
                "UPDATE events SET message=? WHERE id=? AND guild=?", (message, event_id, guild)
            )

    def start_event(self, guild, channel, user, kind, key, *, difficulty="normal", prepared=False):
        if kind not in {"goblin", "jackpot", "hack"}:
            raise DomainError("Événement inconnu.")
        if difficulty not in {"easy", "normal", "hard"}:
            raise DomainError("Difficulté inconnue.")

        def run(con):
            active = con.execute(
                "SELECT id FROM events WHERE guild=? AND kind=? AND status='active' AND (?!='hack' OR owner=?)",
                (guild, kind, kind, user),
            ).fetchone()
            if active:
                raise DomainError("Un événement de ce type est déjà en cours.")
            rules = self.config.rules
            seconds = {
                "goblin": rules.goblin_seconds,
                "jackpot": rules.jackpot_seconds,
                "hack": 30,
            }[kind]
            payload = {}
            if kind == "goblin":
                payload = {
                    "minimum": rules.goblin_min_players,
                    "maximum": rules.goblin_max_players,
                    "reward": rules.goblin_reward,
                }
            elif kind == "hack":
                self.cooldown(con, guild, user, "hack", 300)
                payload = {"difficulty": difficulty, "prepared": prepared}
            event_id = uuid.uuid4().hex
            con.execute(
                "INSERT INTO events(id,guild,channel,kind,owner,deadline,payload) VALUES(?,?,?,?,?,?,?)",
                (event_id, guild, channel, kind, user, self.clock() + seconds, json.dumps(payload)),
            )
            return {"event_id": event_id, "seconds": seconds, "kind": kind}

        return self.perform(guild, user, "start:" + kind, key, [kind, "economy"], run)

    def join_event(self, guild, user, event_id, key):
        def run(con):
            row = con.execute(
                "SELECT * FROM events WHERE guild=? AND id=?", (guild, event_id)
            ).fetchone()
            if not row or row["kind"] not in {"goblin", "jackpot"}:
                raise DomainError("Cet événement n'accepte pas d'inscription.")
            self.enabled(con, guild, row["kind"])
            if row["status"] != "active" or row["deadline"] <= self.clock():
                raise DomainError("Cet événement est terminé.")
            if con.execute(
                "SELECT 1 FROM participants WHERE event=? AND user=?", (event_id, user)
            ).fetchone():
                raise DomainError("Tu participes déjà à cet événement.")
            count = con.execute(
                "SELECT COUNT(*) FROM participants WHERE event=?", (event_id,)
            ).fetchone()[0]
            if row["kind"] == "goblin" and count >= json.loads(row["payload"])["maximum"]:
                raise DomainError("Le groupe est complet.")
            if row["kind"] == "jackpot":
                cost = self.config.rules.jackpot_ticket_cost
                self.money(con, guild, user, wallet=-cost, reason="jackpot-ticket")
                self.add_pot(con, guild, cost)
            con.execute("INSERT INTO participants VALUES(?,?)", (event_id, user))
            return {"event_id": event_id, "count": count + 1}

        return self.perform(guild, user, "join", key, ["economy"], run)

    def settle_event(self, guild, event_id):
        self.allowed(guild)
        with self.store.transaction() as con:
            event = con.execute(
                "SELECT * FROM events WHERE guild=? AND id=?", (guild, event_id)
            ).fetchone()
            if not event:
                raise DomainError("Événement introuvable.")
            if event["status"] != "active":
                return json.loads(event["result"])
            if event["deadline"] > self.clock():
                raise DomainError("Cet événement n'est pas encore terminé.")
            participants = [
                r[0]
                for r in con.execute(
                    "SELECT user FROM participants WHERE event=? ORDER BY user", (event_id,)
                )
            ]
            data = json.loads(event["payload"])
            result = {"kind": event["kind"], "count": len(participants), "reward": 0}
            # Un module désactivé n'efface pas les engagements d'un événement déjà lancé.
            if event["kind"] == "goblin" and len(participants) >= data["minimum"]:
                capped = False
                for user in participants:
                    actual = self.credit_prize(con, guild, user, data["reward"], "goblin")
                    capped |= actual != data["reward"]
                result["reward"] = data["reward"]
                result["capped"] = capped
            elif event["kind"] == "jackpot" and participants:
                pot_row = con.execute("SELECT amount FROM pots WHERE guild=?", (guild,)).fetchone()
                pot = pot_row[0] if pot_row else 0
                winner = self.rng.choice(participants)
                paid = self.credit_prize(con, guild, winner, pot, "jackpot-prize")
                con.execute("UPDATE pots SET amount=amount-? WHERE guild=?", (paid, guild))
                result.update(winner=winner, reward=paid, carried=pot - paid)
            elif event["kind"] == "hack":
                result["abandoned"] = True
            con.execute(
                "UPDATE events SET status='finished',result=? WHERE id=?",
                (json.dumps(result), event_id),
            )
            return result

    def finish_hack(self, guild, user, event_id, key, *, abandon=False):
        def run(con):
            event = con.execute(
                "SELECT * FROM events WHERE guild=? AND id=? AND kind='hack'", (guild, event_id)
            ).fetchone()
            if not event or event["owner"] != user:
                raise DomainError("Cette opération appartient à un autre membre.")
            if event["status"] != "active":
                raise DomainError("Cette opération est déjà terminée.")
            if event["deadline"] <= self.clock():
                raise DomainError("L'opération a expiré.")
            data = json.loads(event["payload"])
            chance, prize = {"easy": (0.80, 80), "normal": (0.60, 200), "hard": (0.35, 500)}[
                data["difficulty"]
            ]
            if data["prepared"]:
                chance, prize = min(0.95, chance + 0.15), prize * 3 // 4
            win = False if abandon else self.rng.random() < chance
            fine = 0
            if win:
                prize = self.credit_prize(con, guild, user, prize, "hack-prize")
            elif not abandon:
                account = self.account(con, guild, user)
                fine = min(account["wallet"], prize // 5)
                self.money(con, guild, user, wallet=-fine, reason="hack-fine")
            result = {"win": win, "reward": prize if win else 0, "fine": fine, "abandoned": abandon}
            con.execute(
                "UPDATE events SET status='finished',result=? WHERE id=?",
                (json.dumps(result), event_id),
            )
            return result

        return self.perform(guild, user, "hack-finish", key, ["hack", "economy"], run)
