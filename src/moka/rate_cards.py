"""Cartes Discord : illustrations ImageGen, avatars et données du jour."""

from __future__ import annotations

import io
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from moka.rates import DailyRate

ASSETS = Path(__file__).parent / "assets"
ART = ASSETS / "rates"
FONT = ASSETS / "fonts" / "Nunito.ttf"
NAME_FONT = ASSETS / "fonts" / "NotoSans.ttf"
EMOJI_FONT = ASSETS / "fonts" / "NotoColorEmoji.ttf"
SIZE = (1360, 600)
CREAM = (255, 244, 219)
MUTED = (164, 185, 193)


def font(size, weight=600):
    face = ImageFont.truetype(str(FONT), size)
    face.set_variation_by_axes([weight])
    return face


def name_font(size, weight=800):
    # Les pseudos mêlent souvent latin, grec et cyrillique ; Nunito est trop limitée.
    face = ImageFont.truetype(str(NAME_FONT), size)
    axes = face.get_variation_axes()
    face.set_variation_by_axes(
        [weight if axis["name"] == b"Weight" else axis["default"] for axis in axes]
    )
    return face


def name_clusters(text):
    """Garde ensemble accents, variantes, teintes, drapeaux et séquences ZWJ."""
    clusters = []
    for char in text:
        code = ord(char)
        regional = 0x1F1E6 <= code <= 0x1F1FF
        previous_flag = bool(
            clusters and len(clusters[-1]) == 1 and 0x1F1E6 <= ord(clusters[-1]) <= 0x1F1FF
        )
        if clusters and (
            unicodedata.category(char).startswith("M")
            or char == "\u200d"
            or clusters[-1].endswith("\u200d")
            or 0x1F3FB <= code <= 0x1F3FF
            or (regional and previous_flag)
        ):
            clusters[-1] += char
        else:
            clusters.append(char)
    return clusters


@lru_cache(maxsize=256)
def emoji_image(text, size):
    # Cette police couleur utilise une taille bitmap fixe, puis est réduite localement.
    face = ImageFont.truetype(str(EMOJI_FONT), 109)
    image = Image.new("RGBA", (max(136, round(face.getlength(text))), 128))
    ImageDraw.Draw(image).text((0, 0), text, font=face, embedded_color=True, anchor="lt")
    return image.resize((size, size), Image.Resampling.LANCZOS)


def name_parts(text, size):
    face = name_font(size)
    parts = []
    for cluster in name_clusters(text):
        emoji = any(
            0x1F000 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF or c in "\ufe0f\u20e3"
            for c in cluster
        )
        if not emoji and parts and not parts[-1][0]:
            parts[-1] = (False, parts[-1][1] + cluster)
        else:
            parts.append((emoji, cluster))
    return [(emoji, value, size + 3 if emoji else face.getlength(value)) for emoji, value in parts]


def draw_name(canvas, xy, text, size, width):
    clusters = name_clusters(text)
    display = text
    while sum(part[2] for part in name_parts(display, size)) > width and clusters:
        clusters.pop()
        display = "".join(clusters).rstrip() + "…"
    x, y = xy
    face = name_font(size)
    for emoji, value, advance in name_parts(display, size):
        if emoji:
            canvas.alpha_composite(emoji_image(value, size), (round(x), y + round(size * 0.15)))
        else:
            ImageDraw.Draw(canvas).text((x, y), value, font=face, fill=CREAM)
        x += advance


def clean_name(name):
    return (
        " ".join(
            "".join(
                c for c in str(name) if c == "\u200d" or not unicodedata.category(c).startswith("C")
            ).split()
        )[:80]
        or "Un camarade"
    )


def fit_text(text, face, width):
    if face.getlength(text) <= width:
        return text
    while text and face.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def wrapped(text, face, width, lines=2):
    result, current = [], ""
    for word in text.split():
        attempt = (current + " " + word).strip()
        if current and face.getlength(attempt) > width:
            result.append(current)
            current = word
        else:
            current = attempt
    if current:
        result.append(current)
    if len(result) > lines:
        result = result[:lines]
        result[-1] = fit_text(result[-1] + "…", face, width)
    return result


def colored_illustration(image, percent):
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError("Pourcentage invalide")
    original = image.convert("RGBA")
    gray = ImageOps.grayscale(original).convert("RGBA")
    gray.putalpha(original.getchannel("A"))
    height = round(original.height * percent / 100)
    if height:
        # Copie RGBA sans double application de l'alpha sur les contours.
        region = original.crop((0, original.height - height, original.width, original.height))
        gray.paste(region, (0, original.height - height))
    return gray


def avatar_image(data, name, size, accent):
    image = None
    if data and len(data) <= 4_000_000:
        try:
            with Image.open(io.BytesIO(data)) as source:
                if source.width <= 4096 and source.height <= 4096:
                    image = ImageOps.fit(
                        source.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS
                    )
        except (OSError, ValueError, Image.DecompressionBombError):
            pass
    if image is None:
        image = Image.new("RGBA", (size, size), (36, 59, 70))
        draw = ImageDraw.Draw(image)
        initial = next((c.upper() for c in clean_name(name) if c.isalpha()), "M")
        draw.text((size / 2, size / 2), initial, font=name_font(size // 2), fill=CREAM, anchor="mm")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    image.putalpha(mask)
    ring = Image.new("RGBA", (size + 12, size + 12))
    ImageDraw.Draw(ring).ellipse((0, 0, size + 11, size + 11), fill=accent)
    ring.alpha_composite(image, (6, 6))
    return ring


def render_rate_card(
    result: DailyRate,
    names: tuple[str, ...],
    avatars: tuple[bytes | None, ...],
    *,
    art_dir: Path = ART,
) -> bytes:
    if len(names) not in (1, 2) or len(avatars) != len(names):
        raise ValueError("Une carte demande un ou deux avatars")
    names = tuple(clean_name(name) for name in names)
    accent = tuple(bytes.fromhex(result.rate.color.removeprefix("#")))
    canvas = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(canvas)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        draw.line(
            (0, y, SIZE[0], y), fill=(int(17 + 7 * t), int(32 + 10 * t), int(43 + 9 * t), 255)
        )
    glow = Image.new("RGBA", SIZE)
    ImageDraw.Draw(glow).ellipse((850, 60, 1330, 540), fill=accent + (40,))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(65)))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((1, 1, 1358, 598), radius=34, outline=(91, 119, 125), width=2)
    draw.text((66, 40), "MOKA  /  LES TAUX DU JOUR", font=font(24, 800), fill=MUTED)
    day = date.fromisoformat(result.day).strftime("%d.%m.%Y")
    draw.text((1292, 40), day, font=font(24), fill=MUTED, anchor="ra")
    duo = len(names) == 2
    if duo:
        joined = names[0] + "  &  " + names[1]
        draw_name(canvas, (66, 88), joined, 37, 1220)
        canvas.alpha_composite(avatar_image(avatars[0], names[0], 158, accent), (63, 181))
        canvas.alpha_composite(avatar_image(avatars[1], names[1], 158, accent), (153, 310))
    else:
        canvas.alpha_composite(avatar_image(avatars[0], names[0], 202, accent), (67, 168))
        draw_name(canvas, (66, 402), names[0], 31, 255)
    draw = ImageDraw.Draw(canvas)
    left = 350
    draw.text((left, 149), result.rate.label, font=font(43, 800), fill=accent)
    draw.text((left - 5, 204), f"{result.percent} %", font=font(112, 900), fill=CREAM)
    bar = (left, 352, left + 496, 374)
    draw.rounded_rectangle(bar, radius=11, fill=(55, 76, 86))
    if result.percent:
        width = max(1, round(496 * result.percent / 100))
        draw.rounded_rectangle(
            (left, 352, left + width, 374), radius=min(11, width // 2), fill=accent
        )
    for index, line in enumerate(wrapped(result.comment, font(30), 535)):
        draw.text((left, 406 + index * 39), line, font=font(30), fill=CREAM)
    with Image.open(art_dir / (result.rate.key + ".png")) as source:
        source = source.convert("RGBA")
        visible = source.getchannel("A").getbbox()
        if visible:
            source = source.crop(visible)
        illustration = colored_illustration(source, result.percent)
    illustration = ImageOps.contain(illustration, (395, 415), method=Image.Resampling.LANCZOS)
    canvas.alpha_composite(
        illustration,
        (935 + (395 - illustration.width) // 2, 111 + (415 - illustration.height) // 2),
    )
    draw = ImageDraw.Draw(canvas)
    draw.line((66, 516, 1292, 516), fill=(66, 91, 101), width=1)
    draw.text((66, 539), "Juste pour rire. Le taux change à minuit.", font=font(25), fill=MUTED)
    if duo:
        draw.text((1292, 539), "Même duo, même résultat.", font=font(25), fill=MUTED, anchor="ra")
    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
