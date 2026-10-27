import io
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from PIL import Image

from moka.__main__ import check_commands
from moka.base import DomainError
from moka.cogs.rates import RatesCog
from moka.rate_cards import (
    ART,
    SIZE,
    clean_name,
    colored_illustration,
    draw_name,
    emoji_image,
    name_clusters,
    name_font,
    render_rate_card,
)
from moka.rates import DUO_RATES, SOLO_RATES, comment_for, measure_rate

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def test_stylized_greek_and_cyrillic_names_have_real_glyphs():
    face = name_font(31)
    missing = bytes(face.getmask("\U0010ffff"))
    for character in "Αlеx Élodie Анастасия":
        assert bytes(face.getmask(character)) != missing


def test_name_keeps_colored_leaves_on_both_sides():
    canvas = Image.new("RGBA", (400, 60))
    draw_name(canvas, (0, 0), "🌿 Alex 🌿", 37, 400)
    for box in [(0, 0, 40, 60), (140, 0, 185, 60)]:
        assert any(
            g > r * 1.2 and g > b * 1.2 and a > 100
            for r, g, b, a in (
                canvas.getpixel((x, y))
                for x in range(box[0], box[2])
                for y in range(box[1], box[3])
            )
        )


@pytest.mark.parametrize("emoji", ["🌿", "❤️", "👩🏽‍💻", "🇫🇷", "1️⃣"])
def test_emoji_sequences_stay_together_and_render_in_color(emoji):
    assert name_clusters(clean_name(emoji)) == [emoji]
    image = emoji_image(emoji, 37)
    assert image.size == (37, 37) and image.getbbox()
    assert any(
        a > 100 and max(r, g, b) - min(r, g, b) > 40
        for r, g, b, a in (
            image.getpixel((x, y)) for x in range(image.width) for y in range(image.height)
        )
    )


def test_rates_are_daily_stable_bounded_and_symmetric():
    for rate in SOLO_RATES:
        first = measure_rate(1, (10,), rate.key, NOW)
        assert first == measure_rate(1, (10,), rate.key, NOW.replace(hour=20))
        assert 0 <= first.percent <= 100 and first.day == "2026-10-27"
    for rate in DUO_RATES:
        assert measure_rate(1, (10, 20), rate.key, NOW) == measure_rate(1, (20, 10), rate.key, NOW)
    baseline = [measure_rate(1, (user,), "chance", NOW).percent for user in range(1, 30)]
    other = [measure_rate(2, (user,), "chance", NOW).percent for user in range(1, 30)]
    assert baseline != other and len(set(baseline)) > 10


def test_day_changes_at_paris_midnight_and_survives_dst():
    before = measure_rate(1, (10,), "sagesse", datetime(2026, 10, 27, 22, 59, tzinfo=UTC))
    after = measure_rate(1, (10,), "sagesse", datetime(2026, 10, 27, 23, 0, tzinfo=UTC))
    assert before.day == "2026-10-27" and after.day == "2026-10-28"
    assert measure_rate(
        1, (10,), "sagesse", datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    ) == measure_rate(1, (10,), "sagesse", datetime(2026, 10, 25, 1, 30, tzinfo=UTC))
    assert measure_rate(
        1, (10,), "sagesse", datetime(2026, 3, 29, 0, 30, tzinfo=UTC)
    ) == measure_rate(1, (10,), "sagesse", datetime(2026, 3, 29, 1, 30, tzinfo=UTC))


@pytest.mark.parametrize(
    ("percent", "index"),
    [(0, 0), (20, 0), (21, 1), (40, 1), (41, 2), (60, 2), (61, 3), (80, 3), (81, 4), (100, 4)],
)
def test_comment_bands_include_their_boundaries(percent, index):
    assert comment_for(SOLO_RATES[0], percent) == SOLO_RATES[0].comments[index]


@pytest.mark.parametrize(
    "users,key",
    [
        ((10, 10), "amitie"),
        ((), "chance"),
        ((0,), "chance"),
        ((True,), "chance"),
        ((10,), "amour"),
        ((10, 20), "chance"),
        ((10,), "unknown"),
    ],
)
def test_invalid_rates_and_members_are_refused(users, key):
    with pytest.raises(ValueError):
        measure_rate(1, users, key, NOW)


def test_naive_dates_and_unknown_timezones_are_refused():
    with pytest.raises(ValueError):
        measure_rate(1, (10,), "chance", datetime(2026, 10, 27))
    with pytest.raises(ValueError):
        measure_rate(1, (10,), "chance", NOW, "Missing/Zone")


def test_illustration_fill_preserves_alpha_and_handles_zero_and_hundred():
    source = Image.new("RGBA", (10, 10), (255, 0, 0, 128))
    source.putpixel((0, 0), (0, 0, 0, 0))
    gray = colored_illustration(source, 0)
    assert gray.getpixel((5, 5))[0] == gray.getpixel((5, 5))[1]
    assert gray.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert colored_illustration(source, 100).tobytes() == source.tobytes()
    half = colored_illustration(source, 50)
    assert half.getpixel((5, 9)) == source.getpixel((5, 9))
    assert half.getpixel((5, 1))[0] == half.getpixel((5, 1))[1]


@pytest.mark.parametrize("rate", SOLO_RATES + DUO_RATES, ids=lambda rate: rate.key)
def test_all_shipped_illustrations_are_square_transparent_and_render(rate):
    with Image.open(ART / (rate.key + ".png")) as art:
        assert art.width == art.height and art.width >= 512
        assert "A" in art.getbands() and art.getchannel("A").getextrema() == (0, 255)
    users = (10,) if rate in SOLO_RATES else (10, 20)
    result = measure_rate(1, users, rate.key, NOW)
    png = render_rate_card(result, tuple("Camille" for _ in users), tuple(None for _ in users))
    with Image.open(io.BytesIO(png)) as image:
        assert image.size == SIZE and image.format == "PNG"
    assert len(png) < 2_000_000


def test_bad_avatar_and_control_characters_still_produce_a_card():
    result = measure_rate(1, (10,), "choupitude", NOW)
    png = render_rate_card(result, ("\u202e" + "W" * 200 + "\n",), (b"invalid PNG",))
    with Image.open(io.BytesIO(png)) as image:
        assert image.size == SIZE


def interaction_for(service):
    guild = SimpleNamespace(id=1)
    user = Mock(spec=discord.Member)
    user.id, user.guild, user.bot, user.display_name, user.mention = (
        10,
        guild,
        False,
        "Camille",
        "<@10>",
    )
    user.display_avatar.with_format.return_value.with_size.return_value.read = AsyncMock(
        return_value=b"avatar"
    )
    bot = SimpleNamespace(service=service, user=SimpleNamespace(id=999))
    interaction = SimpleNamespace(
        guild=guild,
        user=user,
        client=bot,
        id=123,
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    return interaction, bot, user


async def test_rate_command_attaches_png_without_pings_or_economic_writes(service, monkeypatch):
    interaction, bot, user = interaction_for(service)
    content = io.BytesIO()
    Image.new("RGB", (10, 10)).save(content, format="PNG")
    monkeypatch.setattr("moka.cogs.rates.render_rate_card", lambda *args: content.getvalue())
    cog = RatesCog(bot)
    await RatesCog.rate.callback(
        cog, interaction, discord.app_commands.Choice(name="Choupitude", value="choupitude")
    )
    interaction.response.defer.assert_awaited_once()
    options = interaction.followup.send.call_args.kwargs
    assert options["file"].filename == "moka-taux.png"
    assert options["embed"].image.url == "attachment://moka-taux.png"
    assert options["allowed_mentions"].users is False
    assert options["allowed_mentions"].roles is False
    with service.store.read() as con:
        assert con.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


async def test_rates_refuse_disabled_module_wrong_guild_and_self_duo(service):
    interaction, bot, user = interaction_for(service)
    cog = RatesCog(bot)
    service.set_setting(1, "feature:rates", False)
    with pytest.raises(DomainError, match="désactivés"):
        await cog.show(interaction, "chance", (user,))
    service.set_setting(1, "feature:rates", True)
    with pytest.raises(DomainError, match="distincts"):
        await cog.show(interaction, "amitie", (user, user))
    user.guild = SimpleNamespace(id=2)
    with pytest.raises(DomainError, match="ce serveur"):
        await cog.show(interaction, "chance", (user,))
    interaction.response.defer.assert_not_awaited()


async def test_rate_choices_and_member_options_are_registered_offline(service):
    data = await check_commands(service.config)
    rate = next(c for c in data if c["name"] == "taux")
    duo = next(c for c in data if c["name"] == "duo")
    assert len(rate["options"][0]["choices"]) == 8
    assert len(duo["options"][0]["choices"]) == 6
    assert rate["options"][1]["required"] is False
    assert duo["options"][1]["required"] is True
