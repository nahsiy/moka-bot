from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
import weakref
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from moka.admission_closure import close_approved
from moka.admission_discord import AdmissionView, entry_overwrites, reading_status, recruiter
from moka.base import DomainError
from moka.discord_ui import card

log = logging.getLogger(__name__)


class AdmissionCog(commands.Cog):
    accueil = app_commands.Group(
        name="accueil", description="Suivi des premiers cafés par le staff"
    )

    def __init__(self, bot):
        self.bot, self.service = bot, bot.service
        self.locks = weakref.WeakValueDictionary()
        self.last_reconcile = {}
        self.rendered = {}

    def lock(self, guild, user):
        return self.locks.setdefault((guild, user), asyncio.Lock())

    def candidate(self, interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise DomainError("Cet accueil s'utilise dans un serveur.")
        self.service.allowed(interaction.guild_id)
        if not self.service.admission_enabled(interaction.guild_id):
            raise DomainError("L'accueil n'est pas activé.")
        row = self.service.admission(interaction.guild_id, interaction.user.id)
        if not row or row["status"] != "pending" or row["channel"] != interaction.channel_id:
            raise DomainError("Utilise les boutons de ton propre premier café, encore en attente.")
        return row

    async def staff_candidate(self, interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise DomainError("L'accueil s'utilise dans un serveur.")
        self.service.allowed(interaction.guild_id)
        if not self.service.admission_enabled(interaction.guild_id):
            raise DomainError("L'accueil n'est pas activé.")
        actor = await interaction.guild.fetch_member(interaction.user.id)
        if not recruiter(self.service, actor):
            raise DomainError("Cette action est réservée au staff chargé de l'accueil.")
        row = self.service.admission(interaction.guild_id, channel=interaction.channel_id)
        if not row or row["user"] == actor.id:
            raise DomainError("Aucun autre candidat à accueillir dans ce salon.")
        return row

    def safe_roles(self, guild):
        approved = guild.get_role(self.service.get_setting(guild.id, "admission:member_role", 0))
        waiting = guild.get_role(self.service.get_setting(guild.id, "admission:waiting_role", 0))
        if not approved or not waiting or approved == waiting:
            raise DomainError("Les rôles d'accueil doivent être réparés par le responsable.")
        for role in (approved, waiting):
            if (
                role.managed
                or role.is_default()
                or role.permissions.value
                or role >= guild.me.top_role
            ):
                raise DomainError("Les rôles d'accueil doivent être sans privilège et sous Moka.")
        return approved, waiting

    async def sync(self, member):
        guild = member.guild
        row = self.service.admission(guild.id, member.id)
        approved, waiting = self.safe_roles(guild)
        desired, obsolete = (
            (approved, waiting) if row["status"] == "approved" else (waiting, approved)
        )
        remove = [obsolete] if obsolete in member.roles else []
        if row["status"] != "approved":
            linked = self.service.get_setting(guild.id, "role_channels", {})
            remove.extend(
                role
                for role in member.roles
                if str(role.id) in linked and role not in remove and role != desired
            )
        if remove:
            await member.remove_roles(*remove, reason="Moka : accès au Comptoir")
        if desired not in member.roles:
            await member.add_roles(desired, reason="Moka : accueil au Comptoir")
        room = guild.get_channel(row["channel"] or 0)
        room_overwrites = entry_overwrites(
            guild, self.service, candidate=member, writable=row["status"] == "pending"
        )
        if room and room.overwrites != room_overwrites:
            await room.edit(
                overwrites=room_overwrites,
                reason="Moka : confidentialité du premier café",
            )
        voice = guild.get_channel(row["voice"] or 0)
        if voice and row["status"] != "pending" and member.voice and member.voice.channel == voice:
            await member.move_to(None, reason="Moka : entretien terminé")
        if voice and voice.overwrites != room_overwrites:
            await voice.edit(
                overwrites=room_overwrites,
                reason="Moka : confidentialité du vocal d'accueil",
            )
        await self.refresh(guild, member.id)
        await self.notify_reading(guild, member.id)
        await close_approved(self, guild, member.id)

    async def notify_reading(self, guild, user, *, include_closed=False, ping=True):
        """Appelé sous le verrou du candidat ; reçu durable et reprise après envoi."""
        row = self.service.admission(guild.id, user)
        if (
            not row
            or row["read_at"] is None
            or not row["channel"]
            or (row["status"] != "pending" and not include_closed)
        ):
            return False
        key = f"admission:reading_notice:{user}"
        receipt = self.service.get_setting(guild.id, key, {})
        if receipt.get("read_at") == row["read_at"] and receipt.get("channel") == row["channel"]:
            return False
        try:
            channel = guild.get_channel(row["channel"])
            if not isinstance(channel, discord.TextChannel):
                raise DomainError("Le salon privé de cet accueil est introuvable.")
            candidate = await guild.fetch_member(user)
            expected = entry_overwrites(
                guild, self.service, candidate=candidate, writable=row["status"] == "pending"
            )
            if channel.overwrites != expected:
                raise DomainError(
                    "Les permissions privées de cet accueil doivent être resynchronisées."
                )
            stamp = datetime.fromtimestamp(row["read_at"], UTC)
            stamp = stamp.replace(microsecond=stamp.microsecond // 1000 * 1000)
            # Retrouver un envoi Discord réussi avant une interruption de l'accusé SQLite.
            async for message in channel.history(limit=None, after=stamp - timedelta(seconds=1)):
                if message.author.id == guild.me.id and any(
                    embed.title == "✅ Charte confirmée" and embed.timestamp == stamp
                    for embed in message.embeds
                ):
                    self.service.set_setting(
                        guild.id,
                        key,
                        {"read_at": row["read_at"], "channel": channel.id, "message": message.id},
                    )
                    return False
            members = [member async for member in guild.fetch_members(limit=None)]
            staff = (
                sorted(
                    (
                        member
                        for member in members
                        if not member.bot
                        and member.id != user
                        and recruiter(self.service, member)
                        and channel.permissions_for(member).view_channel
                    ),
                    key=lambda member: member.id,
                )
                if ping
                else []
            )
            state = (
                "L'équipe peut poursuivre l'entretien. **L'accès au Comptoir attend toujours sa validation humaine.**"
                if row["status"] == "pending"
                else "**Cet accueil a déjà été validé.**"
                if row["status"] == "approved"
                else "Cet accueil est déjà clôturé."
            )
            embed = card(
                "✅ Charte confirmée",
                f"<@{user}> a confirmé la lecture de la charte avec le mot attendu.\n\n" + state,
            )
            embed.timestamp = stamp
            if row["message"]:
                embed.url = f"https://discord.com/channels/{guild.id}/{channel.id}/{row['message']}"
            embed.set_footer(text="Moka · Le mot de lecture n'est pas affiché")
            message = await channel.send(
                content="🔔 " + " ".join(member.mention for member in staff) if staff else None,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, roles=False, users=staff, replied_user=False
                ),
            )
            self.service.set_setting(
                guild.id,
                key,
                {"read_at": row["read_at"], "channel": channel.id, "message": message.id},
            )
            return True
        except (discord.HTTPException, DomainError):
            log.warning(
                "Notification de lecture à reprendre pour l'accueil %s/%s",
                guild.id,
                user,
                exc_info=True,
            )
            return False

    async def ensure_member(self, member):
        if member.bot or not self.service.admission_enabled(member.guild.id):
            return
        async with self.lock(member.guild.id, member.id):
            member = await member.guild.fetch_member(member.id)
            row = self.service.begin_admission(member.guild.id, member.id)
            if row["status"] == "pending":
                category = member.guild.get_channel(
                    self.service.get_setting(member.guild.id, "admission:category", 0)
                )
                if not isinstance(category, discord.CategoryChannel):
                    raise DomainError("L'entrée du Comptoir est introuvable.")
                room = member.guild.get_channel(row["channel"] or 0)
                marker = f"moka-admission:{member.id}"
                if room is None:
                    room = next((c for c in category.text_channels if c.topic == marker), None)
                if room is None:
                    slug = (
                        unicodedata.normalize("NFKD", member.display_name)
                        .encode("ascii", "ignore")
                        .decode()
                        .lower()
                    )
                    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:40] or "bienvenue"
                    room = await member.guild.create_text_channel(
                        f"☕・premier-café-{slug}",
                        category=category,
                        topic=marker,
                        overwrites=entry_overwrites(
                            member.guild, self.service, candidate=member, writable=True
                        ),
                        reason="Moka : premier café privé",
                    )
                self.service.bind_admission(member.guild.id, member.id, channel=room.id)
            await self.sync(member)

    async def refresh(self, guild, user):
        row = self.service.admission(guild.id, user)
        if not row or not row["channel"]:
            return
        stamp = (
            row["channel"],
            row["message"],
            row["status"],
            row["read_at"],
            row["voice_requested"],
        )
        if self.rendered.get((guild.id, user)) == stamp:
            return
        channel = guild.get_channel(row["channel"])
        if not channel:
            return
        payload = dict(
            embed=card("☕ Ton premier café", reading_status(row)),
            view=AdmissionView() if row["status"] == "pending" else None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if row["message"]:
            try:
                await channel.get_partial_message(row["message"]).edit(**payload)
                self.rendered[(guild.id, user)] = stamp
                return
            except discord.NotFound:
                pass
        else:
            # Reprise après envoi réussi mais liaison SQLite interrompue.
            async for old in channel.history(limit=50, oldest_first=True):
                if (
                    old.author.id == guild.me.id
                    and old.embeds
                    and old.embeds[0].title == "☕ Ton premier café"
                ):
                    await old.edit(**payload)
                    self.service.bind_admission(guild.id, user, message=old.id)
                    return
        msg = await channel.send(**payload)
        self.service.bind_admission(guild.id, user, message=msg.id)

    async def decide(self, interaction, decision):
        row = await self.staff_candidate(interaction)
        async with self.lock(interaction.guild_id, row["user"]):
            # Contrôle renouvelé après le verrou, pas seulement à l'affichage du bouton.
            row = await self.staff_candidate(interaction)
            member = await interaction.guild.fetch_member(row["user"])
            self.safe_roles(interaction.guild)
            changed = self.service.decide_admission(
                interaction.guild_id, member.id, interaction.user.id, decision
            )
            if changed:
                await self.bot.audit(
                    interaction.guild,
                    f"Accueil de <@{member.id}> : {'validé' if decision == 'approved' else 'refusé'} par <@{interaction.user.id}>. Aucun contenu d'entretien conservé par Moka.",
                )
            await self.sync(member)
            if decision == "approved":
                await self.bot.level_roles(member)

    async def open_voice(self, interaction):
        row = await self.staff_candidate(interaction)
        async with self.lock(interaction.guild_id, row["user"]):
            row = await self.staff_candidate(interaction)
            if row["status"] != "pending" or not row["voice_requested"]:
                raise DomainError("Le candidat doit d'abord demander un entretien vocal.")
            member = await interaction.guild.fetch_member(row["user"])
            category = interaction.guild.get_channel(
                self.service.get_setting(interaction.guild_id, "admission:category", 0)
            )
            if not isinstance(category, discord.CategoryChannel):
                raise DomainError("L'entrée du Comptoir est introuvable.")
            voice = interaction.guild.get_channel(row["voice"] or 0)
            name = f"☕ Premier café · {member.display_name[:40]}"
            if voice is None:
                voice = next(
                    (
                        c
                        for c in category.voice_channels
                        if c.overwrites_for(member).view_channel is True
                    ),
                    None,
                )
            if voice is None:
                voice = await interaction.guild.create_voice_channel(
                    name,
                    category=category,
                    overwrites=entry_overwrites(
                        interaction.guild, self.service, candidate=member, writable=True
                    ),
                    reason="Moka : entretien vocal demandé par le candidat",
                )
            self.service.bind_admission(interaction.guild_id, member.id, voice=voice.id)
            return voice

    async def reconcile(self, guild):
        now = self.service.clock()
        if (
            not self.service.admission_enabled(guild.id)
            or now - self.last_reconcile.get(guild.id, 0) < 60
        ):
            return
        self.last_reconcile[guild.id] = now
        reconciled = set()
        for member in guild.members:
            if member.bot:
                continue
            try:
                await self.ensure_member(member)
                reconciled.add(member.id)
            except (DomainError, discord.HTTPException):
                log.exception("Accueil à reprendre ; nouvel essai dans une minute")
        # Le délai continue aussi pour les personnes ayant quitté le serveur.
        for row in self.service.approved_interviews(guild.id):
            if row["user"] in reconciled:
                continue  # sync a déjà repris cette clôture sous le verrou du candidat.
            try:
                async with self.lock(guild.id, row["user"]):
                    await close_approved(self, guild, row["user"])
            except (DomainError, discord.HTTPException):
                log.exception("Clôture d'accueil à reprendre ; nouvel essai dans une minute")

    @accueil.command(name="etat", description="Voir l'état du premier café de ce salon (staff)")
    async def status(self, interaction: discord.Interaction):
        row = await self.staff_candidate(interaction)
        await interaction.response.send_message(
            embed=card(
                "🛎️ Suivi de l'accueil",
                f"État : **{row['status']}** · Lecture : **{'confirmée' if row['read_at'] is not None else 'à confirmer'}**.\nLes boutons du premier message permettent de poursuivre l'accueil.",
            ),
            ephemeral=True,
        )

    @accueil.command(
        name="reprendre", description="Rouvrir un accueil refusé dans ce salon (staff)"
    )
    async def reopen(self, interaction: discord.Interaction):
        row = await self.staff_candidate(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.lock(interaction.guild_id, row["user"]):
            await self.staff_candidate(interaction)
            self.service.reopen_admission(interaction.guild_id, row["user"])
            await self.sync(await interaction.guild.fetch_member(row["user"]))
        await interaction.followup.send(
            embed=card(
                "☕ On reprend un café",
                "L'accueil est rouvert. La charte est à confirmer à nouveau.",
            ),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.guild_id not in self.bot.config.guild_ids:
            return
        row = self.service.admission(payload.guild_id, channel=payload.channel_id)
        if row and row["message"] == payload.message_id:
            self.rendered.pop((payload.guild_id, row["user"]), None)
