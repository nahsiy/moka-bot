"""Rendez-vous collectifs de Moka, sans donnée de membre sur les cartes."""

import io
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from moka.profile_cards import number
from moka.rate_cards import CREAM, MUTED, font, wrapped

ART = Path(__file__).parent / "assets" / "events" / "moka-tournee.png"
HUG_ART = ART.with_name("moka-calin.png")
SIZE = (1200, 900)
GOLD = (231, 195, 126)
MINT = (114, 210, 190)
ROSE = (244, 154, 179)


def round_state(event, now):
    data, result = event["payload"], event["result"]
    count = len(event["participants"]) if result is None else result["count"]
    served = result is not None and count >= data["minimum"]
    hug = event["kind"] == "hug"
    return {
        "count": count,
        "minimum": data["minimum"],
        "maximum": data["maximum"],
        "finished": result is not None,
        "served": served,
        "remaining": max(0, math.ceil(event["deadline"] - now)),
        "reward": (data["reward"] * (count if hug else 1)) if result is None else result["reward"],
        "title": (
            (
                "Le câlin collectif de Moka"
                if result is None
                else "Câlin collectif terminé !"
                if served
                else "Les bras restent ouverts"
            )
            if hug
            else "La tournée de Moka"
            if result is None
            else "La tournée est servie !"
            if served
            else "À la prochaine pause !"
        ),
    }


def round_description(event, now):
    state = round_state(event, now)
    people = f"{state['count']} personne{'s' if state['count'] != 1 else ''}"
    if event["kind"] == "hug":
        if state["served"]:
            text = f"{people} dans le câlin · {number(state['reward'])} cœurs par personne ({number(event['payload']['reward'])} × {state['count']})."
            if event["result"].get("capped"):
                text += " Certains gains sont limités par le plafond du compte."
        elif state["finished"]:
            text = "Pas de participant cette fois. Moka garde une place pour la prochaine pause."
        else:
            closing = datetime.fromtimestamp(event["deadline"], ZoneInfo("Europe/Paris"))
            text = (
                f"{state['remaining']} secondes restantes. {people}, {state['maximum']} places. "
                f"{number(event['payload']['reward'])} cœurs × le nombre de participants, pour chacun. "
                f"Fermeture à {closing:%H:%M:%S}, heure de Paris."
            )
        return state["title"] + " " + text

    if state["served"]:
        text = f"{people} au comptoir · {state['reward']} cœurs par personne."
        if event["result"].get("capped"):
            text += " Certains gains sont limités par le plafond du compte."
    elif state["finished"]:
        text = f"Pas assez de monde au comptoir : {people}, objectif {state['minimum']}."
    else:
        closing = datetime.fromtimestamp(event["deadline"], ZoneInfo("Europe/Paris"))
        text = (
            f"{state['remaining']} secondes restantes. {people} au comptoir, "
            f"objectif {state['minimum']}, {state['maximum']} places. "
            f"{state['reward']} cœurs par personne si le groupe est réuni. "
            f"Fermeture à {closing:%H:%M:%S}, heure de Paris."
        )
    separator = " " if state["title"].endswith("!") else ". "
    return state["title"] + separator + text


def render_round_card(event, now, *, art_path=None):
    state = round_state(event, now)
    hug = event["kind"] == "hug"
    accent = ROSE if hug else GOLD
    art_path = art_path or (HUG_ART if hug else ART)
    canvas = Image.new("RGBA", SIZE, (18, 35, 46))
    glow = Image.new("RGBA", SIZE)
    ImageDraw.Draw(glow).ellipse((550, 190, 1170, 765), fill=accent + (35,))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(70)))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((1, 1, 1198, 898), radius=34, outline=(91, 119, 125), width=2)
    draw.text((60, 35), "MOKA  /  LES RENDEZ-VOUS", font=font(24, 800), fill=MUTED)
    draw.text((60, 90), state["title"], font=font(56, 900), fill=accent)
    subtitle = (
        "Un café, quelques sourires, et des cœurs."
        if state["served"]
        else "On se retrouvera au comptoir."
        if state["finished"]
        else "Une petite pause ensemble ?"
    )
    if hug:
        subtitle = (
            "De la douceur et des sourires partagés."
            if state["served"]
            else "Une autre occasion viendra, tout simplement."
            if state["finished"]
            else "Moka ouvre les bras. Tu viens ?"
        )
    draw.text((60, 171), subtitle, font=font(31), fill=CREAM)
    label = "LE COMPTOIR A FERMÉ" if state["finished"] else "LE COMPTOIR FERME DANS"
    if hug:
        label = "LE CÂLIN EST TERMINÉ" if state["finished"] else "LE CÂLIN COMMENCE DANS"
    value = (
        "Partagé !"
        if hug and state["served"]
        else "Servie !"
        if state["served"]
        else "À bientôt"
        if state["finished"]
        else f"{state['remaining']} s"
    )
    draw.text((60, 258), label, font=font(24, 800), fill=MUTED)
    draw.text((55, 292), value, font=font(89, 900), fill=CREAM)
    cups = (
        ("participant" if state["count"] == 1 else "participants")
        if hug
        else ("café réservé" if state["count"] == 1 else "cafés réservés")
    )
    draw.text((60, 430), f"{state['count']} {cups}", font=font(39, 800), fill=MINT)
    draw.text(
        (60, 487),
        (
            f"{state['maximum']} places · chacun à son rythme"
            if hug
            else f"{state['maximum']} places · objectif {state['minimum']}"
        ),
        font=font(28),
        fill=MUTED,
    )
    reward_text = f"{number(state['reward'])} cœurs"
    reward_size = 62
    while reward_size > 28 and font(reward_size, 900).getlength(reward_text) > 475:
        reward_size -= 2
    draw.text((60, 548), reward_text, font=font(reward_size, 900), fill=accent)
    reward_label = (
        "par personne · santé, l'équipe !"
        if state["served"]
        else "Cette fois, aucune récompense."
        if state["finished"]
        else "par personne si le groupe est réuni"
    )
    if hug:
        reward_label = (
            f"par personne · {number(event['payload']['reward'])} × {state['count']}"
            if state["served"]
            else "Pas de gain, juste une prochaine fois."
            if state["finished"]
            else f"par personne · {number(event['payload']['reward'])} × participants"
        )
    for i, line in enumerate(wrapped(reward_label, font(30), 455)):
        draw.text((60, 635 + i * 37), line, font=font(30), fill=CREAM)
    with Image.open(art_path) as source:
        art = source.convert("RGBA")
        if box := art.getchannel("A").getbbox():
            art = art.crop(box)
        art = ImageOps.contain(art, (590, 555), Image.Resampling.LANCZOS)
    canvas.alpha_composite(art, (555 + (590 - art.width) // 2, 210 + (555 - art.height) // 2))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((60, 765, 1140, 789), radius=12, fill=(49, 72, 82))
    progress = min(1, state["count"] / max(1, state["maximum"] if hug else state["minimum"]))
    if progress:
        width = max(1, round(progress * 1080))
        draw.rounded_rectangle((60, 765, 60 + width, 789), radius=min(12, width // 2), fill=MINT)
    missing = max(0, state["minimum"] - state["count"])
    goal = (
        "Le groupe est réuni !"
        if not missing
        else f"Il manque encore {missing} personne{'s' if missing > 1 else ''}."
    )
    if hug:
        goal = (
            "Un clic pour partager un peu de douceur."
            if not state["finished"]
            else "Merci pour ce moment ensemble !"
            if state["served"]
            else "À bientôt pour une nouvelle pause ensemble."
        )
    draw.text((60, 807), goal, font=font(27, 800), fill=MINT if not missing else MUTED)
    footer = "Moka prépare le plateau. Réserve ta tasse avec le bouton."
    if state["finished"]:
        footer = "Merci d'être passés au comptoir. À la prochaine tournée !"
        if state["served"] and event["result"].get("capped"):
            footer = "Certains gains sont limités par le plafond du compte."
    if hug:
        footer = "Un câlin virtuel et facultatif. Participe seulement si tu en as envie."
        if state["finished"] and state["served"] and event["result"].get("capped"):
            footer = "Certains gains sont limités par le plafond du compte."
    draw.text((60, 853), footer, font=font(23), fill=MUTED)
    output = io.BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
