import asyncio
from dataclasses import asdict
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.horoscope import HoroscopeCog, HoroscopeView, edition_embed
from moka.horoscope import (
    RUBRICS,
    SIGNS,
    HoroscopeReader,
    SourceUnavailable,
    fetch_text,
    parse_edition,
    sign_for_member,
    source_url,
)

DAY = date(2026, 10, 30)


def rss(*, day="Fri, 30 Oct 2026 06:00:00 +0000", link=None, words=40):
    # Textes originaux de test, aucun article d'un tiers embarqué.
    text = " ".join(f"mot{i}" for i in range(words))
    return f"""<rss><channel><item><title>Autre actualité</title><link>https://example.test</link>
    <pubDate>{day}</pubDate><description>Texte sans rapport</description></item>
    <item><title>Lecture du jour</title><link>{link or source_url("belier")}</link>
    <pubDate>{day}</pubDate><description><![CDATA[<b>B&eacute;lier:</b> {text}<script>secret</script>]]></description>
    </item></channel></rss>"""


def html(day=30, *, sign="Bélier", rubrics=RUBRICS, score=3):
    return f"<h1>Horoscope du {sign} aujourd'hui, {day} Octobre 2026</h1>" + "".join(
        f'<div class="summary-card"><div class="summary-title">{r}</div>'
        f'<div class="summary-star"><span class="staron">{"★" * score}</span>'
        f'<span class="staroff">{"★" * (5 - score)}</span></div></div>'
        for r in rubrics
    )


def edition(day=DAY):
    return parse_edition("belier", day, rss(), html())


def test_editorial_reading_keeps_published_scores_and_short_attributed_preview():
    e = edition()
    assert e.scores == {key: 3 for key in RUBRICS}
    assert len(e.preview.split()) == 25 and e.preview.endswith("…")
    assert "Bélier:" not in e.preview and "secret" not in e.preview
    assert e.day == "2026-10-30" and e.url == source_url("belier")
    card = edition_embed(e)
    assert len(card.fields) == 5
    assert all("3/5" in f.value for f in card.fields)
    assert "Mon Horoscope du Jour" in card.description
    assert "30/10/2026" in card.title


@pytest.mark.parametrize(
    "bad_rss,bad_html",
    [
        (rss(day="Thu, 29 Oct 2026 06:00:00 +0000"), html()),
        (rss(), html(29)),
        (rss(), html(sign="Taureau")),
        (rss(), html(rubrics=RUBRICS[:-1])),
        (rss(link="https://evil.test/horoscopes/quotidien/belier.htm"), html()),
        (rss(day="bad date"), html()),
        (rss(words=0), html()),
        ("<!DOCTYPE rss [<!ENTITY xx 'boom'>]>" + rss(), html()),
        ("not xml", html()),
    ],
)
def test_bad_date_wrong_source_or_incomplete_scores_never_become_today(bad_rss, bad_html):
    with pytest.raises(SourceUnavailable):
        parse_edition("belier", DAY, bad_rss, bad_html)


def test_single_day_heading_does_not_match_eleventh_day():
    with pytest.raises(SourceUnavailable):
        parse_edition(
            "belier", date(2026, 10, 1), rss(day="Thu, 01 Oct 2026 06:00:00 +0000"), html(11)
        )


def test_named_html_entities_and_utm_links_from_official_rss_are_supported():
    data = rss(link=source_url("belier") + "?utm_source=feed")
    data = data.replace("<title>Lecture du jour</title>", "<title>Lecture r&eacute;elle</title>")
    assert parse_edition("belier", DAY, data, html()).scores["Amour"] == 3


async def test_same_day_cache_survives_restart_and_coalesces_parallel_clicks(service):
    service.clock.now = datetime(2026, 10, 30, 12, tzinfo=UTC).timestamp()
    fetch = AsyncMock(return_value=edition())
    reader = HoroscopeReader(service, fetch)
    a, b = await asyncio.gather(reader.read(1, "belier"), reader.read(1, "belier"))
    assert a == b and fetch.await_count == 1
    restarted = HoroscopeReader(service, AsyncMock(side_effect=AssertionError("pas de réseau")))
    assert await restarted.read(1, "belier") == a
    assert service.get_setting(2, "horoscope:edition:belier") is None
    assert set(service.get_setting(1, "horoscope:edition:belier")) == set(asdict(a))
    assert "user" not in asdict(a)


async def test_paris_midnight_refuses_yesterday_even_when_source_is_unavailable(service):
    service.clock.now = datetime(2026, 10, 30, 22, 59, tzinfo=UTC).timestamp()
    fetch = AsyncMock(return_value=edition())
    reader = HoroscopeReader(service, fetch)
    assert (await reader.read(1, "belier")).day == "2026-10-30"
    service.clock.advance(60)  # Minuit à Paris ; encore le 30 en UTC.
    fetch.side_effect = SourceUnavailable()
    with pytest.raises(SourceUnavailable):
        await reader.read(1, "belier")
    assert fetch.await_args.args[1] == date(2026, 10, 31)
    with pytest.raises(SourceUnavailable):
        await reader.read(1, "belier")
    assert fetch.await_count == 2  # Les erreurs sont aussi temporisées.
    service.clock.advance(61)
    with pytest.raises(SourceUnavailable):
        await reader.read(1, "belier")
    assert fetch.await_count == 3


async def test_midnight_during_request_requires_new_edition(service):
    service.clock.now = datetime(2026, 10, 30, 22, 59, 59, tzinfo=UTC).timestamp()

    async def fetch(*args):
        service.clock.advance(2)
        return edition()

    reader = HoroscopeReader(service, fetch)
    with pytest.raises(SourceUnavailable):
        await reader.read(1, "belier")
    assert service.get_setting(1, "horoscope:edition:belier") is None


async def test_invalid_sign_and_other_guild_never_trigger_network(service):
    fetch = AsyncMock()
    reader = HoroscopeReader(service, fetch)
    for guild, sign in ((3, "belier"), (1, "https://evil.test"), (1, "../")):
        with pytest.raises(DomainError):
            await reader.read(guild, sign)
    fetch.assert_not_awaited()


@pytest.mark.parametrize("status,body", [(302, b""), (200, b"x" * 11)])
async def test_network_redirects_and_excessive_payloads_are_rejected(status, body):
    content = SimpleNamespace(read=AsyncMock(return_value=body), at_eof=lambda: True)
    response = MagicMock()
    response.__aenter__ = AsyncMock(return_value=SimpleNamespace(status=status, content=content))
    session = SimpleNamespace(get=MagicMock(return_value=response))
    with pytest.raises(SourceUnavailable):
        await fetch_text(session, source_url("belier"), 10)
    assert session.get.call_args.kwargs["allow_redirects"] is False


def test_registered_sign_is_optional_unique_and_limited_to_preference_roles(service):
    guild = SimpleNamespace(id=1, owner_id=90)
    member = SimpleNamespace(guild=guild, roles=[SimpleNamespace(id=10, name="♈ Bélier")])
    assert sign_for_member(service, member) is None
    service.set_setting(1, "role_categories", {"signe": {"roles": [10, 11]}})
    assert sign_for_member(service, member) == "belier"
    member.roles.append(SimpleNamespace(id=11, name="♉ Taureau"))
    assert sign_for_member(service, member) is None


@pytest.fixture
def horoscope_ui(service):
    service.clock.now = datetime(2026, 10, 30, 12, tzinfo=UTC).timestamp()
    service.set_setting(1, "channel:horoscope", 500)
    service.set_setting(1, "horoscope:message", 600)
    guild = SimpleNamespace(id=1, owner_id=90)
    member = MagicMock(spec=discord.Member)
    member.guild = guild
    member.id = 10
    member.roles = []
    member.guild_permissions = discord.Permissions.none()
    guild.fetch_member = AsyncMock(return_value=member)
    bot = SimpleNamespace(service=service, user=SimpleNamespace(id=999))
    c = HoroscopeCog(bot)
    c.reader.fetch = AsyncMock(return_value=edition())
    i = SimpleNamespace(
        guild=guild,
        guild_id=1,
        id=123,
        channel_id=500,
        user=member,
        client=bot,
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        message=SimpleNamespace(id=600, author=bot.user, edit=AsyncMock()),
    )
    return SimpleNamespace(cog=c, interaction=i, service=service)


async def test_menu_returns_private_reading_without_changing_member_roles(horoscope_ui):
    p = horoscope_ui
    i = p.interaction
    await p.cog.show(i, "belier", panel=True)
    assert i.response.defer.call_args.kwargs["ephemeral"] is True
    kwargs = i.followup.send.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert kwargs["view"].children[0].url == source_url("belier")
    i.message.edit.assert_awaited_once()
    assert p.service.get_setting(1, "role_categories") is None


async def test_wrong_channel_routes_to_cafe_without_loading_source(horoscope_ui):
    p = horoscope_ui
    p.interaction.channel_id = 501
    await p.cog.show(p.interaction, "belier")
    p.cog.reader.fetch.assert_not_awaited()
    assert "<#500>" in p.interaction.response.send_message.call_args.kwargs["embed"].description


async def test_missing_sign_gives_clear_choice_without_requesting_birth_date(horoscope_ui):
    p = horoscope_ui
    await p.cog.show(p.interaction, panel=True)
    p.cog.reader.fetch.assert_not_awaited()
    assert "Choisis" in p.interaction.followup.send.call_args.kwargs["embed"].description


async def test_source_error_keeps_complete_reading_link_and_never_sends_old_preview(horoscope_ui):
    p = horoscope_ui
    p.cog.reader.fetch.side_effect = SourceUnavailable()
    await p.cog.show(p.interaction, "belier")
    kwargs = p.interaction.followup.send.call_args.kwargs
    assert "attendre" in kwargs["embed"].title
    assert kwargs["view"].children[0].url == source_url("belier")
    assert "mot0" not in kwargs["embed"].description


@pytest.mark.parametrize("fault", ["module", "admission", "panel"])
async def test_callbacks_recheck_access_and_panel_binding(horoscope_ui, fault):
    p = horoscope_ui
    if fault == "module":
        p.service.set_setting(1, "feature:horoscope", False)
    elif fault == "admission":
        p.service.set_setting(1, "admission:enabled", True)
    else:
        p.interaction.message.id = 601
    with pytest.raises(DomainError):
        await p.cog.show(p.interaction, "belier", panel=True)
    p.cog.reader.fetch.assert_not_awaited()


async def test_menu_is_persistent_and_its_selection_identity_resets():
    a, b = HoroscopeView(), HoroscopeView()
    assert a.is_persistent() and b.is_persistent()
    sa = next(c for c in a.children if hasattr(c, "item"))
    sb = next(c for c in b.children if hasattr(c, "item"))
    assert len(sa.item.options) == len(SIGNS) == 12
    assert sa.item.row == 0
    assert sa.custom_id != sb.custom_id
    assert all(not option.default for option in sa.item.options)


async def test_fresh_admission_check_after_defer_blocks_a_new_pending_member(horoscope_ui):
    p = horoscope_ui

    async def fetch(uid):
        p.service.set_setting(1, "admission:enabled", True)
        return p.interaction.user

    p.interaction.guild.fetch_member.side_effect = fetch
    with pytest.raises(DomainError, match="premier café"):
        await p.cog.show(p.interaction, "belier")
    p.cog.reader.fetch.assert_not_awaited()
    p.interaction.followup.send.assert_not_awaited()
