"""Lecteur musical illustré : les commandes restent des composants Discord natifs."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from moka.music import duration_label
from moka.rate_cards import CREAM, MUTED, draw_name, font, wrapped

ART = Path(__file__).parent / "assets" / "music" / "moka-jukebox.png"
MINT = (114, 210, 190)


def render_music_card(queue, *, status=None):
    image = Image.new("RGBA", (1200, 900), (18, 35, 46))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, 1198, 898), radius=34, outline=(91, 119, 125), width=2)
    draw.text((60, 36), "MOKA  /  LA PAUSE EN MUSIQUE", font=font(24, 800), fill=MUTED)
    draw.text((60, 94), "Le Juke-box", font=font(66, 900), fill=CREAM)
    state = (
        "En pause"
        if queue.paused
        else "À l’écoute"
        if queue.current
        else "Une place pour ton morceau"
    )
    draw.text((60, 195), state, font=font(34, 800), fill=MINT)
    art = Image.open(ART).convert("RGBA")
    art = ImageOps.contain(art, (490, 560), Image.Resampling.LANCZOS)
    image.alpha_composite(art, (700 + (450 - art.width) // 2, 260 + (500 - art.height) // 2))
    draw = ImageDraw.Draw(image)
    if queue.current:
        title = queue.current.title
        lines = wrapped(title, font(43, 900), 635)
        for i, line in enumerate(lines[:3]):
            draw_name(image, (60, 278 + i * 52), line, 43, 635)
        draw = ImageDraw.Draw(image)
        draw.text(
            (60, 455), f"Durée {duration_label(queue.current.duration)}", font=font(29), fill=MUTED
        )
        heading = "À SUIVRE"
        lines = [f"{i + 1}. {t.title}" for i, t in enumerate(queue.pending[:3])]
        y = 555
        draw.text((60, 515), heading, font=font(23, 800), fill=MINT)
        for line in lines:
            draw_name(image, (60, y), line, 28, 625)
            y += 51
        if not lines:
            draw.text((60, y), "La file t’attend.", font=font(29), fill=CREAM)
    else:
        copy = [
            "Rejoins le vocal Le Juke-box,",
            "puis ajoute un titre ou un lien",
            "avec le bouton ci-dessous.",
        ]
        for i, line in enumerate(copy):
            draw.text((60, 305 + i * 49), line, font=font(32), fill=CREAM)
        draw.text((60, 530), "On écoute ensemble.", font=font(36, 800), fill=MINT)
        draw.text((60, 585), "Les micros restent au repos.", font=font(29), fill=MUTED)
    if status:
        draw_name(image, (60, 738), status, 25, 1080)
    draw = ImageDraw.Draw(image)
    draw.line((60, 802, 1140, 802), fill=(66, 91, 101))
    draw.text(
        (60, 831),
        f"{len(queue.pending)} morceau(s) en attente · Sans micro · Pas d’XP d’écoute",
        font=font(25),
        fill=MUTED,
    )
    out = io.BytesIO()
    image.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
