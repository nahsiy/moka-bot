"""Lecteur de l'édition publiée : aperçu RSS court et notes de l'éditeur."""

from __future__ import annotations

import asyncio
import re
import unicodedata
import weakref
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.entities import name2codepoint
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import aiohttp

from moka import __version__
from moka.base import DomainError

SOURCE = "Mon Horoscope du Jour"
HOST = "www.mon-horoscope-du-jour.com"
ZONE = ZoneInfo("Europe/Paris")
RUBRICS = ("Humeur", "Amour", "Argent", "Travail", "Loisirs")
SIGNS = {
    "belier": ("♈", "Bélier"),
    "taureau": ("♉", "Taureau"),
    "gemeaux": ("♊", "Gémeaux"),
    "cancer": ("♋", "Cancer"),
    "lion": ("♌", "Lion"),
    "vierge": ("♍", "Vierge"),
    "balance": ("♎", "Balance"),
    "scorpion": ("♏", "Scorpion"),
    "sagittaire": ("♐", "Sagittaire"),
    "capricorne": ("♑", "Capricorne"),
    "verseau": ("♒", "Verseau"),
    "poissons": ("♓", "Poissons"),
}
MONTHS = [
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
]


def plain(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    ).casefold()


def source_url(sign):
    if sign not in SIGNS:
        raise DomainError("Choisis l'un des douze signes proposés.")
    return f"https://{HOST}/horoscopes/quotidien/{sign}.htm"


class SourceUnavailable(DomainError):
    def __init__(self):
        super().__init__(
            "L'édition du jour n'est pas encore vérifiable chez l'éditeur. Réessaie un peu plus tard ; le bouton de lecture complète reste disponible."
        )


@dataclass(frozen=True)
class Edition:
    sign: str
    day: str
    preview: str
    scores: dict[str, int]
    url: str


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignore += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore - 1)

    def handle_data(self, value):
        if not self.ignore:
            self.parts.append(value)


def clean_text(value):
    parser = Text()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


class Page(HTMLParser):
    """Ne lit que le titre daté et les cinq cartes de notation, jamais les articles."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = []
        self.h1 = False
        self.depth = 0
        self.card_depth = None
        self.capture = None
        self.label, self.on, self.off = "", "", ""
        self.scores = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "h1":
            self.h1 = True
        if tag == "div":
            self.depth += 1
            if "summary-card" in classes:
                self.card_depth = self.depth
                self.label, self.on, self.off = "", "", ""
        if self.card_depth is not None:
            for css, target in (("summary-title", "label"), ("staron", "on"), ("staroff", "off")):
                if css in classes:
                    self.capture = (tag, target)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.h1 = False
        if self.capture and self.capture[0] == tag:
            self.capture = None
        if tag == "div":
            if self.card_depth == self.depth:
                label = self.label.strip()
                on, off = self.on.count("★"), self.off.count("★")
                if label in RUBRICS and on + off == 5 and label not in self.scores:
                    self.scores[label] = on
                self.card_depth = None
            self.depth -= 1

    def handle_data(self, value):
        if self.h1:
            self.heading.append(value)
        if self.capture:
            field = self.capture[1]
            setattr(self, field, getattr(self, field) + value)


def parse_edition(sign, day, rss, html):
    url = source_url(sign)
    if "<!DOCTYPE" in rss.upper() or "<!ENTITY" in rss.upper():
        raise SourceUnavailable()
    # Le flux officiel utilise aussi des entités HTML nommées hors CDATA.
    rss = re.sub(
        r"&([A-Za-z][A-Za-z0-9]+);",
        lambda m: (
            f"&#{name2codepoint[m[1]]};"
            if m[1] in name2codepoint and m[1] not in {"amp", "lt", "gt", "apos", "quot"}
            else m[0]
        ),
        rss,
    )
    try:
        root = ET.fromstring(rss)
    except ET.ParseError as error:
        raise SourceUnavailable() from error
    preview = None
    for item in root.findall("./channel/item"):
        link = item.findtext("link", "").split("?", 1)[0]
        if link != url:
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate", ""))
            if published.tzinfo is None or published.astimezone(ZONE).date() != day:
                continue
        except (ValueError, TypeError, OverflowError):
            continue
        text = clean_text(item.findtext("description", ""))
        text = re.sub(r"^" + re.escape(SIGNS[sign][1]) + r"\s*:\s*", "", text)
        words = text.split()
        if words:
            preview = " ".join(words[:25])[:700] + (
                "…" if len(words) > 25 or len(text) > 700 else ""
            )
            break
    page = Page()
    page.feed(html)
    heading = plain(" ".join(page.heading))
    expected = rf"\b0?{day.day}\s+{MONTHS[day.month - 1]}\s+{day.year}\b"
    if not preview or not re.search(expected, heading) or plain(SIGNS[sign][1]) not in heading:
        raise SourceUnavailable()
    if set(page.scores) != set(RUBRICS):
        raise SourceUnavailable()
    return Edition(sign, day.isoformat(), preview, page.scores, url)


async def fetch_text(session, url, limit):
    async with session.get(url, allow_redirects=False) as response:
        if response.status != 200:
            raise SourceUnavailable()
        data = await response.content.read(limit + 1)
        # StreamReader.read(n) peut rendre moins de n octets avant EOF.
        while len(data) <= limit and not response.content.at_eof():
            data += await response.content.read(min(65536, limit + 1 - len(data)))
        if len(data) > limit:
            raise SourceUnavailable()
        return data.decode("utf-8")


async def fetch_edition(sign, day):
    url = source_url(sign)
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=12),
            headers={"User-Agent": f"Moka/{__version__} (horoscope RSS reader)"},
            trust_env=False,
        ) as session:
            rss, html = await asyncio.gather(
                fetch_text(session, f"https://{HOST}/rss/rss_{sign}.php", 256 * 1024),
                fetch_text(session, url, 1024 * 1024),
            )
        return parse_edition(sign, day, rss, html)
    except (aiohttp.ClientError, TimeoutError, UnicodeError, ValueError) as error:
        raise SourceUnavailable() from error


class HoroscopeReader:
    def __init__(self, service, fetch=fetch_edition):
        self.service, self.fetch = service, fetch
        self.locks = weakref.WeakValueDictionary()
        self.failures = {}

    def today(self):
        return datetime.fromtimestamp(self.service.clock(), UTC).astimezone(ZONE).date()

    async def read(self, guild, sign):
        self.service.allowed(guild)
        source_url(sign)
        async with self.locks.setdefault((guild, sign), asyncio.Lock()):
            day = self.today()
            key = "horoscope:edition:" + sign
            cached = self.service.get_setting(guild, key)
            if cached and cached.get("day") == day.isoformat():
                return Edition(**cached)
            if self.failures.get((guild, sign), 0) > self.service.clock():
                raise SourceUnavailable()
            try:
                edition = await self.fetch(sign, day)
                if edition.day != day.isoformat() or edition.url != source_url(sign):
                    raise SourceUnavailable()
                # Un passage de minuit pendant la requête exige une nouvelle lecture.
                if self.today() != day:
                    raise SourceUnavailable()
            except SourceUnavailable:
                self.failures[(guild, sign)] = self.service.clock() + 60
                raise
            self.service.set_setting(guild, key, asdict(edition))
            self.failures.pop((guild, sign), None)
            return edition


def sign_for_member(service, member):
    category = service.get_setting(member.guild.id, "role_categories", {}).get("signe", {})
    ids = set(category.get("roles", []))
    matching = {
        key
        for role in member.roles
        if role.id in ids
        for key, (emoji, name) in SIGNS.items()
        if role.name == f"{emoji} {name}"
    }
    return next(iter(matching)) if len(matching) == 1 else None
