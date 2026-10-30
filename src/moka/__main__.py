from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from moka.config import Config
from moka.service import Service
from moka.store import Store


def demo():
    """Scénario reproductible dans une base jetable, sans token ni connexion."""
    with tempfile.TemporaryDirectory(prefix="moka-demo-") as tmp:
        config = Config(guild_ids=(1,), data_dir=Path(tmp))
        store = Store(Path(tmp) / "demo.sqlite3")
        store.initialize()
        now = [1_800_000_000.0]
        service = Service(store, config, clock=lambda: now[0], rng=random.Random(7))
        service.claim(1, 101, "daily-101")
        service.claim(1, 102, "daily-102")
        service.bank_move(1, 101, 100, "deposit")
        service.buy(1, 101, "cafe", "purchase")
        service.give_item(1, 101, 102, "cafe", "gift")
        service.activity(1, 101, "message-1")
        count = service.counting(1, 10, 101, "1", 1001)
        count2 = service.counting(1, 10, 102, "2", 1002)
        event = service.start_event(1, 20, 101, "goblin", "spawn")
        for user in (101, 102, 103):
            service.join_event(1, user, event["event_id"], f"join-{user}")
        now[0] += config.rules.goblin_seconds + 1
        goblin = service.settle_event(1, event["event_id"])
        backup = store.backup(Path(tmp) / "demo-backup.sqlite3")
        return {
            "mode": "offline-demo",
            "discord_connected": False,
            "profile": service.profile(1, 101, viewer=101),
            "inventory_recipient": service.inventory(1, 102),
            "counting": [count["score"], count2["score"]],
            "goblin": goblin,
            "backup_created": backup.is_file(),
            "database_integrity": service.check_integrity(),
        }


async def check_commands(config):
    from moka.bot import MokaBot

    # Pas de setup_hook (ni tâches ni synchronisation ni base utilisateur).
    with tempfile.TemporaryDirectory(prefix="moka-check-") as tmp:
        config = replace(config, data_dir=Path(tmp), sync_commands=False)
        bot = MokaBot(config)
        await bot.load_cogs()
        commands = [command.to_dict(bot.tree) for command in bot.tree.get_commands()]
        await bot.close()
        return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description="Moka, compagnon Discord en Python")
    parser.add_argument("--config", type=Path, help="Configuration TOML")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Valider configuration et commandes sans connexion Discord")
    sub.add_parser("demo", help="Jouer un scénario local sans token, sans données réelles")
    sub.add_parser("run", help="Démarrer le bot (token et serveurs autorisés requis)")
    laboratory = sub.add_parser(
        "prepare-test",
        help="Préparer les salons/rôles dans le seul serveur Moka • Laboratoire autorisé",
    )
    laboratory.add_argument(
        "--expected-name", default="Moka • Laboratoire", help="Nom exact du serveur de test attendu"
    )
    backup = sub.add_parser("backup", help="Créer une sauvegarde cohérente sans écraser un fichier")
    backup.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            print(json.dumps(demo(), ensure_ascii=False, indent=2))
            return 0
        config = Config.load(args.config)
        if args.command == "check":
            commands = asyncio.run(check_commands(config))
            print(
                json.dumps(
                    {
                        "configuration": "ok",
                        "discord_connected": False,
                        "guilds_configured": len(config.guild_ids),
                        "slash_roots": len(commands),
                        "commands": [c["name"] for c in commands],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        store = Store(config.data_dir / "moka.sqlite3")
        if args.command == "backup":
            if not store.path.is_file():
                raise ValueError("Aucune base à sauvegarder")
            print(store.backup(args.destination))
            return 0
        if not config.guild_ids:
            raise ValueError("Définis MOKA_GUILD_IDS avant de connecter le bot")
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise ValueError("Définis DISCORD_TOKEN dans l'environnement")
        if args.command == "prepare-test":
            from moka.laboratory import run

            print(
                json.dumps(
                    asyncio.run(run(config, token, expected_name=args.expected_name)),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        # Une instance par base : évite les doublons d'événements Discord.
        import fcntl

        from moka.bot import MokaBot

        config.data_dir.mkdir(parents=True, exist_ok=True)
        os.umask(0o077)
        with (config.data_dir / "moka.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError("Une instance de Moka utilise déjà cette base") from error
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
            )
            bot = MokaBot(config)
            bot.run(token, log_handler=None)
        return 0
    except (ValueError, TypeError, OSError) as error:
        print(f"Moka : {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
