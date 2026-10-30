"""Petites attentions illustrées, rares par leur texte et leur habillage."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from moka.rate_cards import CREAM, MUTED, draw_name, font, wrapped

RARITIES = {
    "classic": ("La petite attention", (114, 210, 190)),
    "rare": ("La perle du Comptoir", (244, 154, 179)),
    "epic": ("La pépite de Moka", (231, 195, 126)),
}


def render_social_card(name, result):
    label, accent = RARITIES[result.get("rarity", "classic")]
    image = Image.new("RGBA", (1200, 820), (18, 35, 46))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, 1198, 818), radius=34, outline=accent, width=3)
    draw.text((60, 36), "MOKA  /  LES PETITES ATTENTIONS", font=font(24, 800), fill=MUTED)
    title = "Petite taquinerie" if result["kind"] == "taunt" else "Un compliment pour toi"
    draw.text((60, 95), title, font=font(52, 900), fill=CREAM)
    draw_name(image, (60, 184), name, 41, 1080)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 263, 655, 312), radius=16, fill=(31, 52, 62))
    draw.text((82, 271), label, font=font(27, 800), fill=accent)
    for i, line in enumerate(wrapped(result["text"], font(37, 800), 605, lines=7)):
        draw.text((60, 353 + i * 46), line, font=font(37, 800), fill=CREAM)
    art = Image.open(
        Path(__file__).parent
        / "assets"
        / "social"
        / ("moka-taunt.png" if result["kind"] == "taunt" else "moka-compliment.png")
    ).convert("RGBA")
    art = ImageOps.contain(art, (450, 490), Image.Resampling.LANCZOS)
    image.alpha_composite(art, (710 + (430 - art.width) // 2, 249 + (490 - art.height) // 2))
    draw = ImageDraw.Draw(image)
    draw.line((60, 740, 1140, 740), fill=(66, 91, 101))
    draw.text(
        (60, 768),
        "Avec bienveillance · Juste pour sourire · Si quelqu’un dit stop, on s’arrête",
        font=font(24),
        fill=MUTED,
    )
    out = io.BytesIO()
    image.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
