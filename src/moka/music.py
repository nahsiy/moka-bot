"""Sources YouTube et état d'une file : aucun cookie ni contenu de message conservé."""

import asyncio
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from moka.base import DomainError

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "music.youtube.com", "m.youtube.com", "youtu.be"}


def music_query(value):
    value = value.strip()
    if not 1 <= len(value) <= 300 or any(ord(c) < 32 for c in value):
        raise DomainError("Indique un titre ou un lien YouTube, jusqu’à 300 caractères.")
    parsed = urlparse(value)
    if (
        "://" in value
        or value.startswith("//")
        or parsed.scheme in {"file", "data", "javascript", "http", "https", "ftp"}
    ):
        try:
            port = parsed.port
        except ValueError as error:
            raise DomainError("Le lien YouTube est invalide.") from error
        if (
            parsed.scheme != "https"
            or parsed.hostname not in YOUTUBE_HOSTS
            or parsed.username
            or parsed.password
            or port not in (None, 443)
        ):
            raise DomainError("Utilise un lien https:// YouTube ou saisis simplement un titre.")
        if parsed.path == "/playlist":
            raise DomainError(
                "Ajoute un morceau individuel : les listes de lecture ne sont pas importées."
            )
        return value
    if re.match(r"^(www\.|youtu\.be|youtube\.com)", value):
        raise DomainError("Ajoute https:// devant le lien YouTube.")
    return "ytsearch1:" + value


@dataclass
class Track:
    title: str
    url: str
    duration: int
    requester: int
    stream: str = field(default="", repr=False)
    resolved_at: float = field(default=0, repr=False)


async def resolve_track(query, requester):
    source = music_query(query)
    deno = shutil.which("deno")
    if not deno and Path("/opt/homebrew/bin/deno").is_file():
        deno = "/opt/homebrew/bin/deno"
    runtime = ["--js-runtimes", "deno:" + deno] if deno else []
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "yt_dlp",
        "--dump-single-json",
        "--no-playlist",
        "--no-warnings",
        "--no-cache-dir",
        "--socket-timeout",
        "12",
        "--retries",
        "1",
        "--format",
        "bestaudio/best",
        *runtime,
        "--",
        source,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        limit=4 * 1024 * 1024,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=45)
    except (TimeoutError, asyncio.CancelledError):
        process.kill()
        await process.wait()
        raise
    if process.returncode:
        raise DomainError(
            "Ce morceau est indisponible. Essaie un autre lien ou un titre plus précis."
        )
    try:
        data = json.loads(output)
        if "entries" in data:
            data = next(item for item in data["entries"] if item)
        duration = int(data.get("duration") or 0)
        if data.get("is_live") or not 1 <= duration <= 1800:
            raise DomainError(
                "Choisis un morceau de 30 minutes maximum. Les directs ne sont pas pris en charge."
            )
        stream = data.get("url", "")
        host = urlparse(stream).hostname or ""
        if urlparse(stream).scheme != "https" or not host.endswith(".googlevideo.com"):
            raise DomainError("Le flux audio YouTube n’est pas disponible pour ce morceau.")
        video_id = data["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError
        return Track(
            str(data["title"])[:200],
            f"https://www.youtube.com/watch?v={video_id}",
            duration,
            requester,
            stream,
            time.monotonic(),
        )
    except (ValueError, KeyError, StopIteration, TypeError) as error:
        raise DomainError(
            "La source n’a pas renvoyé de morceau lisible. Essaie un autre lien."
        ) from error


def duration_label(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


class Queue:
    def __init__(self):
        self.pending = []
        self.current = None
        self.paused = False
        self.votes = set()
        self.receipts = set()

    def add(self, track, key):
        if key in self.receipts:
            return False
        if (
            len(self.pending) >= 50
            or sum(t.requester == track.requester for t in self.pending) >= 5
        ):
            raise DomainError(
                "La file est pleine pour toi : 5 morceaux en attente par personne, 50 au total."
            )
        self.pending.append(track)
        self.receipts.add(key)
        if len(self.receipts) > 500:
            # La file n'est jamais rejouée automatiquement après redémarrage.
            self.receipts = {key}
        return True

    def advance(self):
        self.current = self.pending.pop(0) if self.pending else None
        self.paused = False
        self.votes.clear()
        return self.current

    def remove(self, index, user, staff=False):
        if not 1 <= index <= len(self.pending):
            raise DomainError("Ce numéro n’est plus dans la file. Consulte /jukebox file.")
        track = self.pending[index - 1]
        if not staff and track.requester != user:
            raise DomainError(
                "Tu peux retirer tes propres morceaux. Le staff peut gérer toute la file."
            )
        return self.pending.pop(index - 1)

    def vote_skip(self, user, listeners, staff=False):
        if not self.current:
            raise DomainError("Aucun morceau en cours.")
        if staff or self.current.requester == user:
            return True
        active = set(listeners)
        self.votes.intersection_update(active)
        self.votes.add(user)
        return len(self.votes) >= max(1, len(active) // 2 + 1)
