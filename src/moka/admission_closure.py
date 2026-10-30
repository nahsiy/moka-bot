"""Clôture des premiers cafés validés, sans copie de l'entretien."""

from contextlib import suppress
from datetime import UTC, datetime, timedelta

import discord

from moka.admission_discord import entry_overwrites
from moka.base import DomainError
from moka.discord_ui import card

CLOSED_CATEGORY = "📁 Les premiers cafés · terminés"
CLOSING_TITLE = "☕ Bienvenue au Comptoir !"


async def fetch_room(guild, channel, cls):
    if not channel:
        return None
    try:
        room = await guild.fetch_channel(channel)
    except discord.NotFound:
        return None
    if not isinstance(room, cls):
        raise DomainError("Le salon suivi pour cet accueil a un type inattendu.")
    return room


def check_private(room, guild, service, candidate):
    expected = entry_overwrites(guild, service, candidate=candidate, writable=False)
    if room.overwrites != expected:
        raise DomainError("Les permissions privées de l'entretien doivent être resynchronisées.")
    if isinstance(room, discord.TextChannel) and room.topic != f"moka-admission:{candidate.id}":
        raise DomainError("Le marqueur du salon d'entretien ne correspond pas au candidat.")


async def closed_category(cog, guild):
    async with cog.lock(guild.id, 0):
        service = cog.service
        expected = entry_overwrites(guild, service)
        category_id = service.get_setting(guild.id, "admission:closed_category", 0)
        category = await fetch_room(guild, category_id, discord.CategoryChannel)
        if category is not None and category.name != CLOSED_CATEGORY:
            raise DomainError("La catégorie de clôture configurée correspond à un autre espace.")
        if category is None:
            # Retrouver une création réussie avant une interruption de sa liaison SQLite.
            category = next(
                (
                    c
                    for c in await guild.fetch_channels()
                    if isinstance(c, discord.CategoryChannel)
                    and c.name == CLOSED_CATEGORY
                    and c.overwrites == expected
                ),
                None,
            )
        if category is None:
            category = await guild.create_category(
                CLOSED_CATEGORY, overwrites=expected, reason="Moka : premiers cafés terminés"
            )
        elif category.overwrites != expected:
            await category.edit(overwrites=expected, reason="Moka : archives d'accueil privées")
        service.set_setting(guild.id, "admission:closed_category", category.id)
        return category


def closing_embed(service, guild, candidate, closure):
    links = []
    if isinstance(candidate, discord.Member):
        for key, label in (
            ("general_channel", "Rejoindre le Comptoir"),
            ("roles_channel", "Choisir mes rôles"),
        ):
            room = guild.get_channel(service.get_setting(guild.id, "admission:" + key, 0))
            if (
                isinstance(room, discord.TextChannel)
                and room.permissions_for(candidate).view_channel
            ):
                links.append(f"[{label}](https://discord.com/channels/{guild.id}/{room.id})")
    deadline = int(closure["delete_at"])
    embed = card(
        CLOSING_TITLE,
        "Ton accueil est terminé, bienvenue au Comptoir ! Installe-toi ☕\n\n"
        + (" · ".join(links) + "\n\n" if links else "")
        + "Cet entretien reste privé, accessible à toi et au staff. Tu peux encore le relire.\n"
        + f"**Ce salon et son éventuel vocal seront supprimés le <t:{deadline}:F> "
        f"(<t:{deadline}:R>).** Aucun échange ne sera recopié ou exporté.",
    )
    embed.timestamp = datetime.fromtimestamp(closure["created"], UTC)
    embed.set_footer(text="Moka · Premier café terminé · Conservation : 7 jours")
    return embed


async def close_approved(cog, guild, user):
    """Sous le verrou du candidat ; chaque étape reprend après un échec Discord."""
    service = cog.service
    row = service.admission(guild.id, user)
    if not row or row["status"] != "approved":
        return
    closure = service.admission_closure(guild.id, user)
    if not closure and not row["channel"]:
        return
    # Le rôle membre vient parfois d'être attribué : ne pas décider des liens sur
    # un cache Gateway encore en retard. Un départ n'annule pas la conservation.
    try:
        candidate = await guild.fetch_member(user)
    except discord.NotFound:
        candidate = discord.Object(id=user)
    room = await fetch_room(guild, row["channel"], discord.TextChannel)
    voice = await fetch_room(guild, row["voice"], discord.VoiceChannel)
    for bound in (room, voice):
        if bound:
            check_private(bound, guild, service, candidate)
    if closure is None:
        if room is None:
            # Salon supprimé manuellement : ne pas supprimer un vocal sans annonce.
            return
        closure = service.plan_admission_closure(guild.id, user)
    if (row["channel"] and row["channel"] != closure["channel"]) or (
        row["voice"] and row["voice"] != closure["voice"]
    ):
        raise DomainError("La liaison de cet accueil a changé ; clôture suspendue.")
    if not closure["notice"]:
        if room is None:
            return
        category = await closed_category(cog, guild)
        expected = entry_overwrites(guild, service, candidate=candidate, writable=False)
        for bound in (room, voice):
            if bound and bound.category_id != category.id:
                await bound.edit(
                    category=category,
                    sync_permissions=False,
                    overwrites=expected,
                    reason="Moka : entretien validé et privé",
                )
        stamp = datetime.fromtimestamp(closure["created"], UTC)
        notice = None
        async for message in room.history(limit=None, after=stamp - timedelta(seconds=1)):
            if message.author.id == guild.me.id and any(
                embed.title == CLOSING_TITLE and embed.timestamp == stamp
                for embed in message.embeds
            ):
                notice = message
                break
        if notice is None:
            closure = service.arm_admission_closure(guild.id, user)
            notice = await room.send(
                embed=closing_embed(service, guild, candidate, closure),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        service.acknowledge_admission_closure(guild.id, user, notice.id)
        closure = service.admission_closure(guild.id, user)
    if closure["delete_at"] is None or service.clock() < closure["delete_at"]:
        return
    # Seuls les deux identifiants liés à cet accueil validé sont concernés.
    # Les erreurs 403/réseau n'effacent pas les liaisons et sont réessayées.
    for field, bound in (("channel", room), ("voice", voice)):
        if not row[field]:
            continue
        if bound is not None:
            if isinstance(bound, discord.VoiceChannel) and bound.members:
                continue
            with suppress(discord.NotFound):
                await bound.delete(reason="Moka : entretien validé supprimé après sept jours")
        service.clear_closed_room(guild.id, user, field, row[field])
    remaining = service.admission(guild.id, user)
    if remaining["channel"] is None and remaining["voice"] is None:
        await cog.bot.audit(
            guild,
            f"Entretien de <@{user}> supprimé après son délai de conservation. "
            "La validation reste acquise ; aucun échange n'a été recopié.",
        )
        service.finish_admission_closure(guild.id, user)
        cog.rendered.pop((guild.id, user), None)
