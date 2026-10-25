from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

FEATURES = frozenset(
    {
        "xp",
        "economy",
        "bank",
        "bet",
        "jackpot",
        "robbery",
        "hack",
        "goblin",
        "counting",
        "words",
        "fun",
        "horoscope",
        "shop",
        "roles",
        "tickets",
        "temporary_voice",
        "trombi",
        "moderation",
    }
)
CHANNELS = frozenset(
    {
        "counting",
        "words",
        "announcements",
        "goblin",
        "logs",
        "tickets",
        "ticket_category",
        "voice_creator",
        "voice_category",
        "trombi",
        "trombi_review",
    }
)
ROLES = frozenset({"counting_failure", "trombi_preaccess", "trombi_access"})


@dataclass(frozen=True)
class Rules:
    message_cooldown: int = 60
    message_xp: int = 15
    message_coins: int = 3
    voice_xp: int = 10
    voice_coins: int = 2
    daily_coins: int = 200
    weekly_coins: int = 1500
    level_coins: int = 100
    bank_capacity: int = 1000
    bank_upgrade_cost: int = 500
    bank_interest_bps: int = 100
    bank_interest_max_bps: int = 500
    robbery_cooldown: int = 3600
    robbery_min_wallet: int = 100
    robbery_max_loot: int = 1000
    robbery_protection_seconds: int = 1800
    counting_reward_every: int = 100
    counting_reward: int = 100
    counting_failure_seconds: int = 10800
    words_cooldown: int = 10
    goblin_seconds: int = 60
    goblin_min_players: int = 3
    goblin_max_players: int = 20
    goblin_reward: int = 100
    goblin_interval_minutes: int = 0
    jackpot_ticket_cost: int = 100
    jackpot_seconds: int = 300
    trombi_min_level: int = 50
    max_amount: int = 1_000_000_000

    def validate(self):
        for item in fields(self):
            value = getattr(self, item.name)
            if type(value) is not int or value < 0 or value > 1_000_000_000:
                raise ValueError(f"Règle invalide : {item.name}")
        for name in (
            "message_cooldown",
            "counting_reward_every",
            "goblin_seconds",
            "goblin_min_players",
            "goblin_max_players",
            "jackpot_ticket_cost",
            "jackpot_seconds",
            "max_amount",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} doit être positif")
        if not 0 < self.bank_interest_bps <= self.bank_interest_max_bps <= 1000:
            raise ValueError("Intérêts : 0 < taux initial <= taux maximum <= 1000 points de base")
        if self.goblin_min_players > self.goblin_max_players:
            raise ValueError("Gobelin : minimum supérieur au maximum")


@dataclass(frozen=True)
class Config:
    guild_ids: tuple[int, ...] = ()
    data_dir: Path = Path("data")
    sync_commands: bool = False
    rules: Rules = field(default_factory=Rules)
    features: dict[str, bool] = field(default_factory=lambda: dict.fromkeys(FEATURES, True))
    # Pas d'identifiant privé réel dans le fichier d'exemple.
    channels: dict[str, int] = field(default_factory=dict)
    roles: dict[str, int] = field(default_factory=dict)
    word_mode: str = "free"

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        raw = {}
        location = path or os.getenv("MOKA_CONFIG")
        if location:
            with Path(location).open("rb") as stream:
                raw = tomllib.load(stream)
        unknown = set(raw) - {"rules", "features", "channels", "roles", "words"}
        if unknown:
            raise ValueError(f"Sections inconnues : {', '.join(sorted(unknown))}")
        rules = Rules(**raw.get("rules", {}))
        rules.validate()
        features = dict.fromkeys(FEATURES, True)
        for name, value in raw.get("features", {}).items():
            if name not in FEATURES or type(value) is not bool:
                raise ValueError(f"Module invalide : {name}")
            features[name] = value
        channels, roles = raw.get("channels", {}), raw.get("roles", {})
        for values, names in ((channels, CHANNELS), (roles, ROLES)):
            for name, value in values.items():
                if name not in names or type(value) is not int or value <= 0:
                    raise ValueError(f"Identifiant invalide : {name}")
        words = raw.get("words", {})
        if set(words) - {"mode"} or words.get("mode", "free") not in {"free", "last_letter"}:
            raise ValueError("Suite de mots : mode free ou last_letter attendu")
        ids = tuple(
            int(part.strip()) for part in os.getenv("MOKA_GUILD_IDS", "").split(",") if part.strip()
        )
        if any(value <= 0 for value in ids):
            raise ValueError("MOKA_GUILD_IDS doit contenir des identifiants positifs")
        sync = os.getenv("MOKA_SYNC_COMMANDS", "0")
        if sync not in {"0", "1"}:
            raise ValueError("MOKA_SYNC_COMMANDS doit valoir 0 ou 1")
        return cls(
            tuple(dict.fromkeys(ids)),
            Path(os.getenv("MOKA_DATA_DIR", "data")),
            sync == "1",
            rules,
            features,
            channels,
            roles,
            words.get("mode", "free"),
        )
