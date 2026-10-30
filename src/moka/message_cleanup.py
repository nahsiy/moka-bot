"""Nettoyage manuel : sélection figée, confirmation privée, aucun transcript."""

import asyncio
import contextlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import discord

from moka.base import DomainError
from moka.discord_ui import SafeView, card, context

MAX_MESSAGES = 5000
CONFIRM_SECONDS = 60
RUN_SECONDS = 600


def date_boundary(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=ZoneInfo("Europe/Paris"))
    except ValueError as error:
        raise DomainError("Date attendue : AAAA-MM-JJ, à minuit (heure de Paris).") from error


def message_id(value):
    if not value.isascii() or not value.isdecimal() or not 15 <= len(value) <= 20:
        raise DomainError("Copie l'identifiant du message, composé de 15 à 20 chiffres.")
    result = int(value)
    if not 0 < result < 2**64:
        raise DomainError("Identifiant de message invalide.")
    return result


async def authorize(interaction, channel_id, owner):
    guild_id, user, _ = context(interaction)
    if user != owner:
        raise DomainError("Cette confirmation appartient à une autre personne.")
    if not interaction.client.service.is_enabled(guild_id, "moderation"):
        raise DomainError("Le module de modération est désactivé.")
    # Un nouveau Guild recharge aussi les rôles : fetch_member seul les garderait en cache.
    guild = await interaction.client.fetch_guild(guild_id)
    channel = await guild.fetch_channel(channel_id)
    if not isinstance(channel, discord.TextChannel) or channel.guild.id != guild_id:
        raise DomainError("Choisis un salon textuel de ce serveur.")
    actor = await guild.fetch_member(owner)
    me = await guild.fetch_member(interaction.client.user.id)
    for member, label in ((actor, "Il te faut"), (me, "Il me faut")):
        permissions = channel.permissions_for(member)
        if not all(
            getattr(permissions, name)
            for name in ("view_channel", "read_message_history", "manage_messages")
        ):
            raise DomainError(
                f"{label} Voir le salon, Lire l'historique et Gérer les messages dans ce salon."
            )
    return channel


@dataclass(frozen=True)
class Selection:
    ids: tuple[int, ...]
    first: int | None
    last: int | None
    pinned: int
    panels: int


def protected(message, keep_pinned, bot_id):
    # Préserver les panneaux persistants, même si leurs messages ne sont pas épinglés.
    return (keep_pinned and message.pinned) or (
        message.author.id == bot_id and bool(message.components)
    )


async def select_messages(
    channel, snapshot, bot_id, *, keep_pinned=True, before=None, since=None, single=None
):
    ids, pinned, panels = [], 0, 0
    before = min(snapshot, discord.utils.time_snowflake(before, high=False)) if before else snapshot
    if single is not None:
        if single >= before:
            raise DomainError("Ce message est postérieur à la demande.")
        messages = [await channel.fetch_message(single)]
    else:
        messages = [
            message
            async for message in channel.history(
                limit=MAX_MESSAGES + 1,
                before=discord.Object(before),
                after=discord.Object(since - 1) if since else None,
                oldest_first=False,
            )
        ]
        if len(messages) > MAX_MESSAGES:
            raise DomainError(
                f"Plus de {MAX_MESSAGES} messages à examiner. Réduis la période avec /messages avant ou depuis. Aucun message supprimé."
            )
    for message in messages:
        if keep_pinned and message.pinned:
            pinned += 1
        elif message.author.id == bot_id and message.components:
            panels += 1
        else:
            ids.append(message.id)
    return Selection(tuple(ids), min(ids, default=None), max(ids, default=None), pinned, panels)


@dataclass
class Result:
    deleted: int = 0
    missing: int = 0
    protected: int = 0
    stopped: bool = False
    error: str = ""
    checked: int = 0
    total: int = 0

    def description(self):
        return (
            (f"**{self.checked}/{self.total}** message(s) vérifié(s).\n" if self.total else "")
            + f"**{self.deleted}** message(s) supprimé(s) · **{self.missing}** déjà absent(s) · "
            f"**{self.protected}** désormais protégé(s)."
            + (
                "\n**Nettoyage interrompu.** Les autres messages ont été conservés. Relance un aperçu pour continuer."
                if self.stopped
                else ""
            )
            + (f"\n{self.error}" if self.error else "")
        )


async def delete_selection(
    selection, refresh_channel, keep_pinned, bot_id, reason, progress, result
):
    deadline = time.monotonic() + RUN_SECONDS
    reported = time.monotonic()
    result.total = len(selection.ids)
    for offset in range(0, len(selection.ids), 100):
        if time.monotonic() >= deadline:
            result.stopped = True
            break
        channel = await refresh_channel()
        recent, old = [], []
        targets = set(selection.ids[offset : offset + 100])
        found = set()
        # Relire une page d'historique plutôt que faire cent requêtes unitaires.
        # Les bornes et l'intersection préservent exactement la sélection confirmée.
        async for message in channel.history(
            limit=None,
            before=discord.Object(max(targets) + 1),
            after=discord.Object(min(targets) - 1),
            oldest_first=False,
        ):
            if time.monotonic() >= deadline:
                result.stopped = True
                break
            if message.id not in targets or message.id in found:
                continue
            found.add(message.id)
            result.checked += 1
            if protected(message, keep_pinned, bot_id):
                result.protected += 1
            else:
                # Marge de 24 h sous la limite de deux semaines de Discord.
                cutoff = datetime.now(UTC) - timedelta(days=13)
                (recent if message.created_at > cutoff else old).append(message)
            if time.monotonic() - reported >= 5:
                await progress(result)
                reported = time.monotonic()
        if result.stopped:
            break
        absent = len(targets - found)
        result.checked += absent
        result.missing += absent
        if len(recent) > 1:
            await channel.delete_messages(recent, reason=reason)
            result.deleted += len(recent)
        else:
            old.extend(recent)
        for message in old:
            if time.monotonic() >= deadline:
                result.stopped = True
                break
            try:
                await message.delete()
                result.deleted += 1
            except discord.NotFound:
                result.missing += 1
            if time.monotonic() - reported >= 5:
                await progress(result)
                reported = time.monotonic()
        if time.monotonic() - reported >= 5:
            await progress(result)
            reported = time.monotonic()


class CleanupView(SafeView):
    def __init__(self, owner, guild_id, channel_id, selection, keep_pinned):
        super().__init__(timeout=CONFIRM_SECONDS)
        self.owner, self.guild_id, self.channel_id = owner, guild_id, channel_id
        self.selection, self.keep_pinned = selection, keep_pinned
        self.expires = time.monotonic() + CONFIRM_SECONDS
        self.used = False
        self.message = None

    async def interaction_check(self, interaction):
        guild, owner, _ = context(interaction)
        if (guild, owner) != (self.guild_id, self.owner):
            raise DomainError("Cette confirmation appartient à une autre personne.")
        return True

    async def on_timeout(self):
        self.used = True
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(
                    embed=card("☕ Nettoyage expiré", "Aucun nettoyage lancé. Relance /messages."),
                    view=None,
                )

    @discord.ui.button(
        label="Supprimer définitivement", style=discord.ButtonStyle.danger, emoji="🗑️"
    )
    async def confirm(self, interaction, button):
        await self.interaction_check(interaction)
        if self.used or time.monotonic() >= self.expires:
            raise DomainError("Confirmation déjà utilisée ou expirée. Relance /messages.")
        # Consommer avant le premier await : deux clics ne lancent jamais deux travaux.
        self.used = True
        self.stop()
        await interaction.response.defer(ephemeral=True)
        bot = interaction.client
        locks = getattr(bot, "message_cleanup_locks", None)
        if locks is None:
            bot.message_cleanup_locks = locks = {}
        lock = locks.setdefault((self.guild_id, self.channel_id), asyncio.Lock())
        if lock.locked():
            raise DomainError(
                "Un nettoyage est déjà en cours dans ce salon. Relance ensuite /messages."
            )
        result = Result(total=len(self.selection.ids))

        async def refresh():
            return await authorize(interaction, self.channel_id, self.owner)

        async def progress(state):
            await interaction.edit_original_response(
                embed=card("🧽 Nettoyage en cours", state.description()), view=None
            )

        async with lock:
            try:
                await refresh()
                await progress(result)
                await delete_selection(
                    self.selection,
                    refresh,
                    self.keep_pinned,
                    bot.user.id,
                    f"Moka : nettoyage confirmé par {self.owner}",
                    progress,
                    result,
                )
            except (discord.HTTPException, DomainError) as error:
                result.stopped = True
                result.error = (
                    str(error)
                    if isinstance(error, DomainError)
                    else "Discord n'a pas terminé la demande. Vérifie les permissions avant de réessayer."
                )
            except (Exception, asyncio.CancelledError):
                result.stopped = True
                raise
            finally:
                await bot.audit(
                    interaction.guild,
                    f"Nettoyage par <@{self.owner}> dans <#{self.channel_id}> : {result.description()}",
                )
                await interaction.edit_original_response(
                    embed=card(
                        "☕ Nettoyage interrompu" if result.stopped else "☕ Comptoir nettoyé",
                        result.description(),
                    ),
                    view=None,
                )

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await self.interaction_check(interaction)
        if self.used:
            raise DomainError("Cette confirmation n'est plus active.")
        self.used = True
        self.stop()
        await interaction.response.edit_message(
            embed=card("☕ Nettoyage annulé", "Aucun message supprimé."), view=None
        )


async def preview(
    interaction,
    salon,
    *,
    keep_pinned=True,
    before=None,
    since=None,
    single=None,
    label="Tous les messages",
):
    guild_id, owner, _ = context(interaction)
    channel = salon or interaction.channel
    if not isinstance(channel, discord.TextChannel) or channel.guild.id != guild_id:
        raise DomainError("Choisis un salon textuel de ce serveur.")
    await interaction.response.defer(ephemeral=True, thinking=True)
    channel = await authorize(interaction, channel.id, owner)
    if since is not None:
        await channel.fetch_message(since)  # L'ancre doit appartenir à ce salon.
    selection = await select_messages(
        channel,
        interaction.id,
        interaction.client.user.id,
        keep_pinned=keep_pinned,
        before=before,
        since=since,
        single=single,
    )
    text = (
        f"**Salon :** {channel.mention}\n**Périmètre :** {label}\n"
        f"**{len(selection.ids)} message(s)** sélectionné(s).\n"
        f"{selection.pinned} épinglé(s) conservé(s) · {selection.panels} panneau(x) Moka conservé(s).\n"
    )
    view = None
    if selection.ids:
        first = int(discord.utils.snowflake_time(selection.first).timestamp())
        last = int(discord.utils.snowflake_time(selection.last).timestamp())
        old = sum(
            discord.utils.snowflake_time(ident) <= datetime.now(UTC) - timedelta(days=13)
            for ident in selection.ids
        )
        text += (
            f"Du <t:{first}:F> au <t:{last}:F>.\n"
            f"{old} message(s) ancien(s) traité(s) individuellement ; cela peut prendre du temps.\n\n"
            "**Suppression irréversible pour tout le monde, pièces jointes comprises.** "
            "Les nouveaux messages seront conservés. Aucun contenu n'est sauvegardé.\n"
            "Confirme dans la minute ou annule."
        )
        view = CleanupView(owner, guild_id, channel.id, selection, keep_pinned)
    message = await interaction.followup.send(
        embed=card("🧽 Un coup de propre", text), view=view, ephemeral=True, wait=True
    )
    if view:
        view.message = message
