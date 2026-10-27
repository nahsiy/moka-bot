"""Taux ludiques stables sur une journée, sans profilage ni écriture en base."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Rate:
    key: str
    label: str
    of: str
    emoji: str
    color: str
    comments: tuple[str, str, str, str, str]


SOLO_RATES = (
    Rate(
        "chance",
        "Chance",
        "chance",
        "🍀",
        "#68CB99",
        (
            "Même la tartine hésite à tomber du bon côté.",
            "Garde un biscuit de secours, au cas où.",
            "Une chance sur deux. Le suspense est entier.",
            "La dernière place libre est juste pour toi.",
            "Tu trouves le biscuit caché au fond de la boîte.",
        ),
    ),
    Rate(
        "choupitude",
        "Choupitude",
        "choupitude",
        "🧸",
        "#F69CB4",
        (
            "Petit hérisson aujourd'hui. Câlins avec précaution.",
            "Un peu grognon, mais on te garde quand même.",
            "Dose de douceur tout à fait réglementaire.",
            "Même ton café te dessine un cœur.",
            "Le nounours demande où tu prends tes cours.",
        ),
    ),
    Rate(
        "suspicion",
        "Suspicion",
        "suspicion",
        "🕵️",
        "#BB9CEB",
        (
            "Aucune miette suspecte. Pour le moment.",
            "Tu sais quelque chose sur le dernier biscuit.",
            "Moka a ouvert un petit carnet à ton nom.",
            "Ce sourire mérite une enquête de proximité.",
            "La boîte est vide et tu as du chocolat aux doigts.",
        ),
    ),
    Rate(
        "criminalite",
        "Criminalité fictive",
        "criminalité fictive",
        "🚔",
        "#EC9878",
        (
            "Même les biscuits te font confiance.",
            "Un sucre emprunté, jamais rendu.",
            "Le vol de plaid commence à se voir.",
            "Recherché pour disparition de goûter.",
            "Le gang des biscuits a trouvé son chef.",
        ),
    ),
    Rate(
        "loutritude",
        "Loutritude",
        "loutritude",
        "🦦",
        "#78C4DC",
        (
            "Tu flottes surtout entre deux idées.",
            "Les moustaches poussent, doucement.",
            "Première baignade validée. Serviette recommandée.",
            "Tu gardes ton goûter sur le ventre en nageant.",
            "La rivière vient de te remettre les clés.",
        ),
    ),
    Rate(
        "flemme",
        "Flemme",
        "flemme",
        "🛋️",
        "#B7ABE5",
        (
            "Le canapé ne t'a même pas vu passer.",
            "Une petite pause. Une vraie petite, cette fois.",
            "Tu négocies encore avec ton réveil.",
            "Le plaid a demandé la garde partagée.",
            "Même la télécommande est trop loin.",
        ),
    ),
    Rate(
        "sagesse",
        "Sagesse",
        "sagesse",
        "🦉",
        "#D9B777",
        (
            "Tu as cherché tes lunettes. Sur ton nez.",
            "La bonne idée arrive juste après le clic.",
            "Tu lis la notice avant de tout démonter.",
            "On te demande conseil avant de toucher au bouton.",
            "Même Moka vient prendre des notes.",
        ),
    ),
    Rate(
        "chaos",
        "Chaos",
        "chaos",
        "🌪️",
        "#81AEEA",
        (
            "La cuillère est rangée. Le monde respire.",
            "Une petite éclaboussure, rien de plus.",
            "Tu retrouves tes clés dans le frigo.",
            "Moka met un couvercle sur son café.",
            "Les meubles ont demandé une ceinture de sécurité.",
        ),
    ),
)

DUO_RATES = (
    Rate(
        "amour",
        "Amour",
        "amour",
        "❤️",
        "#F48F9A",
        (
            "Le café est chaud. Le flirt attendra.",
            "Un sucre, un sourire, et on verra.",
            "Le rendez-vous manque juste d'une date.",
            "Vous oubliez le café à force de vous regarder.",
            "Deux tasses, un plaid. Moka vous laisse la table.",
        ),
    ),
    Rate(
        "amitie",
        "Amitié",
        "amitié",
        "🤝",
        "#E7C577",
        (
            "Vous vous croisez au comptoir, c'est un début.",
            "Le deuxième café est encore à proposer.",
            "Vous avez déjà une bonne blague en commun.",
            "Tu connais sa commande avant qu'il la passe.",
            "La dernière part de gâteau se partage sans débat.",
        ),
    ),
    Rate(
        "complicite",
        "Complicité",
        "complicité",
        "😏",
        "#BF9BE1",
        (
            "La blague privée est encore en préparation.",
            "Un regard. Deux interprétations différentes.",
            "Vous riez des mêmes petites bêtises.",
            "Un sourcil levé et tout le monde se méfie.",
            "Moka vous sépare avant le prochain fou rire.",
        ),
    ),
    Rate(
        "rivalite",
        "Rivalité",
        "rivalité",
        "⚔️",
        "#EA9C87",
        (
            "Même le dernier biscuit ne vous divise pas.",
            "Un petit défi pour choisir la musique.",
            "La revanche est déjà dans le calendrier.",
            "Les cuillères sont sorties. Duel au comptoir.",
            "Moka a prévu une table chacun.",
        ),
    ),
    Rate(
        "equipe",
        "Esprit d'équipe",
        "synergie",
        "🧩",
        "#79CBB5",
        (
            "Vous portez le plateau dans deux directions.",
            "Le plan est bon. Il manque le même plan.",
            "Un café pour réfléchir, et ça repart.",
            "L'un prépare, l'autre pense aux biscuits.",
            "Service parfait. Même la mousse est coordonnée.",
        ),
    ),
    Rate(
        "chaos_duo",
        "Chaos à deux",
        "chaos combiné",
        "💥",
        "#F0B270",
        (
            "À deux, vous remettez les livres à leur place.",
            "Une blague, une éclaboussure, ça va encore.",
            "Vous aviez pourtant promis de rester sages.",
            "Moka range les objets fragiles avant votre arrivée.",
            "Le café vole. Les biscuits aussi. Vous rigolez.",
        ),
    ),
)


@dataclass(frozen=True)
class DailyRate:
    rate: Rate
    percent: int
    day: str
    comment: str
    timezone: str


def comment_for(rate: Rate, percent: int) -> str:
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError("Pourcentage invalide")
    return rate.comments[max(0, (percent - 1) // 20)]


def measure_rate(
    guild: int, users: tuple[int, ...], key: str, now: datetime, timezone: str = "Europe/Paris"
) -> DailyRate:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("La date doit comporter un fuseau horaire")
    if type(guild) is not int or guild <= 0 or len(users) not in (1, 2):
        raise ValueError("Serveur ou nombre de membres invalide")
    if any(type(user) is not int or user <= 0 for user in users) or len(set(users)) != len(users):
        raise ValueError("Choisis des membres distincts")
    catalog = SOLO_RATES if len(users) == 1 else DUO_RATES
    rate = next((rate for rate in catalog if rate.key == key), None)
    if rate is None:
        raise ValueError("Type de taux inconnu")
    try:
        day = now.astimezone(ZoneInfo(timezone)).date().isoformat()
    except (ZoneInfoNotFoundError, ValueError, TypeError) as error:
        raise ValueError("Fuseau horaire des taux invalide") from error
    identities = "+".join(sorted(str(user) for user in users))
    digest = hashlib.sha256(f"{guild}:{identities}:{key}:{day}".encode()).digest()
    percent = int.from_bytes(digest[:2], "big") % 101
    return DailyRate(rate, percent, day, comment_for(rate, percent), timezone)
