from __future__ import annotations

import contextlib
import os
import sqlite3
import tempfile
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
 guild INTEGER NOT NULL, user INTEGER NOT NULL,
 wallet INTEGER NOT NULL DEFAULT 0 CHECK(wallet >= 0),
 bank INTEGER NOT NULL DEFAULT 0 CHECK(bank >= 0),
 bank_tier INTEGER NOT NULL DEFAULT 0 CHECK(bank_tier >= 0),
 interest_tier INTEGER NOT NULL DEFAULT 0 CHECK(interest_tier >= 0),
 protection_tier INTEGER NOT NULL DEFAULT 0 CHECK(protection_tier >= 0),
 xp INTEGER NOT NULL DEFAULT 0 CHECK(xp >= 0), private_profile INTEGER NOT NULL DEFAULT 0,
 messages INTEGER NOT NULL DEFAULT 0, voice_minutes INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY (guild, user)
);
CREATE TABLE IF NOT EXISTS receipts (
 guild INTEGER NOT NULL, key TEXT NOT NULL, user INTEGER NOT NULL,
 action TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL,
 PRIMARY KEY(guild,key)
);
CREATE TABLE IF NOT EXISTS cooldowns (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, action TEXT NOT NULL,
 until REAL NOT NULL, PRIMARY KEY(guild,user,action)
);
CREATE TABLE IF NOT EXISTS ledger (
 id INTEGER PRIMARY KEY, guild INTEGER NOT NULL, user INTEGER NOT NULL,
 wallet_delta INTEGER NOT NULL, bank_delta INTEGER NOT NULL,
 reason TEXT NOT NULL, created REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ledger_user ON ledger(guild,user,id);
CREATE TABLE IF NOT EXISTS settings (
 guild INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
 PRIMARY KEY(guild,key)
);
CREATE TABLE IF NOT EXISTS games (
 guild INTEGER NOT NULL, channel INTEGER NOT NULL, kind TEXT NOT NULL,
 value TEXT NOT NULL DEFAULT '', last_user INTEGER NOT NULL DEFAULT 0,
 score INTEGER NOT NULL DEFAULT 0, record INTEGER NOT NULL DEFAULT 0,
 round INTEGER NOT NULL DEFAULT 0, last_message INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(guild,channel,kind)
);
CREATE TABLE IF NOT EXISTS words (
 guild INTEGER NOT NULL, channel INTEGER NOT NULL, round INTEGER NOT NULL,
 word TEXT NOT NULL, PRIMARY KEY(guild,channel,round,word)
);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, guild INTEGER NOT NULL, channel INTEGER NOT NULL,
 message INTEGER, kind TEXT NOT NULL, owner INTEGER NOT NULL,
 deadline REAL NOT NULL, status TEXT NOT NULL DEFAULT 'active',
 payload TEXT NOT NULL, result TEXT, notified INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS events_active ON events(status,deadline);
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_goblin ON events(guild,kind) WHERE status='active' AND kind='goblin';
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_hug ON events(guild,kind) WHERE status='active' AND kind='hug';
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_jackpot ON events(guild,kind) WHERE status='active' AND kind='jackpot';
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_hack ON events(guild,owner,kind) WHERE status='active' AND kind='hack';
CREATE TABLE IF NOT EXISTS participants (
 event TEXT NOT NULL REFERENCES events(id), user INTEGER NOT NULL,
 PRIMARY KEY(event,user)
);
CREATE TABLE IF NOT EXISTS pots (
 guild INTEGER PRIMARY KEY, amount INTEGER NOT NULL DEFAULT 0 CHECK(amount>=0)
);
CREATE TABLE IF NOT EXISTS inventory (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, item TEXT NOT NULL,
 quantity INTEGER NOT NULL CHECK(quantity>=0), PRIMARY KEY(guild,user,item)
);
CREATE TABLE IF NOT EXISTS role_grants (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, role INTEGER NOT NULL,
 reason TEXT NOT NULL, until REAL NOT NULL, applied INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(guild,user,role)
);
CREATE TABLE IF NOT EXISTS tickets (
 id TEXT PRIMARY KEY, guild INTEGER NOT NULL, user INTEGER NOT NULL,
 channel INTEGER UNIQUE, status TEXT NOT NULL DEFAULT 'creating', created REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_open_ticket ON tickets(guild,user) WHERE status IN ('creating','open');
CREATE TABLE IF NOT EXISTS voice_rooms (
 guild INTEGER NOT NULL, channel INTEGER PRIMARY KEY, owner INTEGER NOT NULL, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS photos (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, message INTEGER PRIMARY KEY,
 review_message INTEGER UNIQUE, status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS admissions (
 guild INTEGER NOT NULL, user INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','refused')),
 channel INTEGER UNIQUE, message INTEGER, voice INTEGER UNIQUE,
 read_at REAL, attempt_at REAL, voice_requested INTEGER NOT NULL DEFAULT 0,
 decided_by INTEGER, created REAL NOT NULL, updated REAL NOT NULL,
 PRIMARY KEY(guild,user)
);
CREATE TABLE IF NOT EXISTS presence (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, started REAL NOT NULL,
 last_at REAL, last_kind TEXT CHECK(last_kind IN ('message','voice')),
 absent_until REAL, PRIMARY KEY(guild,user)
);
CREATE TABLE IF NOT EXISTS counting_validations (
 guild INTEGER NOT NULL, channel INTEGER NOT NULL, message INTEGER NOT NULL,
 user INTEGER NOT NULL, number INTEGER NOT NULL, created REAL NOT NULL,
 sanction_until REAL, sanction_role INTEGER, notified INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(guild,message)
);
CREATE INDEX IF NOT EXISTS counting_validations_age ON counting_validations(guild,created);
CREATE TABLE IF NOT EXISTS collections (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, kind TEXT NOT NULL,
 item TEXT NOT NULL, earned REAL NOT NULL, PRIMARY KEY(guild,user,kind,item)
);
CREATE TABLE IF NOT EXISTS profile_titles (
 guild INTEGER NOT NULL, user INTEGER NOT NULL, title TEXT,
 PRIMARY KEY(guild,user)
);
PRAGMA user_version=1;
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(self.connect()) as con:
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise ValueError("Cette base utilise une version plus récente de Moka")
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript(SCHEMA)
        os.chmod(self.path, 0o600)

    @contextlib.contextmanager
    def transaction(self):
        with contextlib.closing(self.connect()) as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    @contextlib.contextmanager
    def read(self):
        with contextlib.closing(self.connect()) as con:
            yield con

    def backup(self, destination: str | Path):
        target = Path(destination)
        if target.resolve() == self.path.resolve() or target.exists():
            raise ValueError("Choisir un nouveau fichier de sauvegarde")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Le nom final n'apparaît qu'après vérification : une copie interrompue
        # ne peut pas être prise pour la dernière sauvegarde saine.
        fd, temporary = tempfile.mkstemp(
            prefix=".moka-backup-", suffix=".partial", dir=target.parent
        )
        os.close(fd)
        try:
            with (
                contextlib.closing(self.connect()) as source,
                contextlib.closing(sqlite3.connect(temporary)) as dest,
            ):
                source.backup(dest)
                if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Sauvegarde incohérente")
            # link refuse tout écrasement, même si un autre processus crée la cible.
            os.link(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return target
