"""Profil privé lisible dans Discord, rendu localement sans données embarquées."""

import io

from PIL import Image, ImageDraw

from moka.rate_cards import CREAM, MUTED, avatar_image, draw_name, font

PROFILE_SIZE = (1200, 900)
TEAL = (114, 210, 190)


def number(value):
    return f"{value:,}".replace(",", "\u202f")


def level_progress(profile):
    floor = 100 * profile["level"] ** 2
    return max(0, min(1, (profile["xp"] - floor) / (profile["next_xp"] - floor)))


def draw_balance(draw, xy, value, width):
    text = number(value)
    size = 78
    while size > 28 and font(size, 900).getlength(text) > width:
        size -= 2
    draw.text(xy, text, font=font(size, 900), fill=CREAM)


def render_profile_card(profile, name, avatar, *, bank_enabled=True, upgrade_cost=500, status=None):
    image = Image.new("RGBA", PROFILE_SIZE, (18, 35, 46))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1, 1, 1198, 898), radius=34, outline=(91, 119, 125), width=2)
    draw.text((60, 36), "MOKA  /  PROFIL", font=font(25, 800), fill=MUTED)
    image.alpha_composite(avatar_image(avatar, name, 128, TEAL), (60, 103))
    draw_name(image, (235, 115), name, 48, 905)
    draw = ImageDraw.Draw(image)
    draw.text((235, 186), f"Niveau {profile['level']}", font=font(34, 800), fill=TEAL)
    if profile.get("title"):
        draw.text((235, 236), profile["title"], font=font(25, 800), fill=CREAM)
    draw.text((60, 283), "PROGRESSION", font=font(24, 800), fill=MUTED)
    draw.text(
        (1140, 278),
        f"{number(profile['xp'])} / {number(profile['next_xp'])} XP",
        font=font(32, 800),
        fill=CREAM,
        anchor="ra",
    )
    draw.rounded_rectangle((60, 340, 1140, 364), radius=12, fill=(48, 72, 83))
    progress = level_progress(profile)
    if progress:
        width = max(1, round(1080 * progress))
        draw.rounded_rectangle((60, 340, 60 + width, 364), radius=min(12, width // 2), fill=TEAL)
    for x, label in [(60, "PORTEFEUILLE"), (630, "BANQUE")]:
        draw.rounded_rectangle((x, 414, x + 510, 610), radius=24, fill=(27, 49, 62))
        draw.text((x + 30, 438), label, font=font(25, 800), fill=MUTED)
    draw_balance(draw, (90, 470), profile["wallet"], 450)
    draw_balance(draw, (660, 470), profile["bank"], 450)
    draw.text((90, 566), "cœurs disponibles", font=font(29), fill=MUTED)
    draw.text((660, 566), f"sur {number(profile['capacity'])} cœurs", font=font(29), fill=MUTED)
    if not bank_enabled:
        bank_text = "Banque désactivée sur ce serveur"
    elif profile["bank_tier"] >= 20:
        bank_text = "Banque au palier maximal"
    else:
        capacity = profile["capacity"] // (profile["bank_tier"] + 1)
        bank_text = (
            f"Prochain palier : {number(profile['capacity'] + capacity)} cœurs"
            f"  ·  coût {number(upgrade_cost)}"
        )
    draw.text((60, 660), bank_text, font=font(31, 800), fill=TEAL)
    draw.text(
        (60, 721),
        f"{number(profile['messages'])} messages  ·  {number(profile['voice_minutes'])} minutes vocales",
        font=font(30),
        fill=CREAM,
    )
    if status:
        draw_name(image, (60, 767), status.replace("**", ""), 24, 1080)
        draw = ImageDraw.Draw(image)
    draw.line((60, 810, 1140, 810), fill=(66, 91, 101))
    draw.text(
        (60, 839),
        "Réponse privée · Monnaie fictive · /confidentialite",
        font=font(25),
        fill=MUTED,
    )
    out = io.BytesIO()
    image.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
