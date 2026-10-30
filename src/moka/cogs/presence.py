"""Suivi bienveillant des pauses ; jamais de sanction ni de message privé envoyé."""

import asyncio
import logging
import time
import weakref

import discord
from discord import app_commands
from discord.ext import commands

from moka.admission_discord import require_access
from moka.base import DomainError
from moka.discord_ui import card, context
from moka.presence import conversational_text
from moka.role_panels import protected_roles

log = logging.getLogger(__name__)


def staff_member(service, member):
    roles = set(service.get_setting(member.guild.id, "admission:staff_roles", []))
    roles.update(service.get_setting(member.guild.id, "ticket_staff_roles", []))
    return (
        member.id == member.guild.owner_id
        or member.guild_permissions.manage_guild
        or any(r.id in roles for r in member.roles)
    )


def private_staff_channel(service, channel):
    """Refuser de publier si une permission ouvre le bilan hors du staff."""
    if not isinstance(channel, discord.TextChannel):
        return False
    guild = channel.guild
    staff_roles = set(service.get_setting(guild.id, "admission:staff_roles", []))
    staff_roles.update(service.get_setting(guild.id, "ticket_staff_roles", []))
    for role in guild.roles:
        if (
            role.id in staff_roles
            or role.permissions.manage_guild
            or role.permissions.administrator
        ):
            continue
        if role.managed and role.tags and role.tags.bot_id:
            continue
        if channel.permissions_for(role).view_channel:
            return False
    for target, overwrite in channel.overwrites.items():
        if (
            isinstance(target, discord.Member)
            and overwrite.view_channel is True
            and not target.bot
            and not staff_member(service, target)
        ):
            return False
    return True


class PresenceCog(commands.Cog):
    activite = app_commands.Group(
        name="activite", description="Suivi des pauses du Comptoir (staff)"
    )

    def __init__(self, bot):
        self.bot, self.service = bot, bot.service
        self.conversations = {}
        self.voice = {}
        self.last_voice_tick = None
        self.last_reconcile = {}
        self.report_stamps = {}
        self.locks = weakref.WeakValueDictionary()

    def lock(self, guild, user):
        return self.locks.setdefault((guild, user), asyncio.Lock())

    def enabled_member(self, member):
        return (
            not member.bot
            and member.guild.id in self.bot.config.guild_ids
            and self.service.presence_enabled(member.guild.id)
            and self.service.admitted(member.guild.id, member.id)
        )

    def safe_role(self, guild):
        rid = self.service.get_setting(guild.id, "presence:role", 0)
        role = guild.get_role(rid)
        reserved = protected_roles(self.service, guild.id, include_presence=False)
        if (
            not role
            or role.id in reserved
            or role.is_default()
            or role.managed
            or role.permissions.value
            or role.name == "☕ Le Barista"
            or not guild.me
            or not guild.me.guild_permissions.manage_roles
            or role >= guild.me.top_role
        ):
            raise DomainError("Le rôle de pause doit être dédié, sans permission et sous Moka.")
        return role

    async def sync_member(self, member):
        async with self.lock(member.guild.id, member.id):
            if not self.enabled_member(member):
                return
            role = self.safe_role(member.guild)
            row = self.service.presence_member(member.guild.id, member.id)
            if row["inactive"] == (role in member.roles):
                return
            # Relire le membre et l'état après toute attente réseau.
            member = await member.guild.fetch_member(member.id)
            if not self.enabled_member(member):
                return
            role = self.safe_role(member.guild)
            row = self.service.presence_member(member.guild.id, member.id)
            if row["inactive"] and role not in member.roles:
                await member.add_roles(
                    role, reason="Moka : pause après 21 jours sans échange observé"
                )
            elif not row["inactive"] and role in member.roles:
                await member.remove_roles(role, reason="Moka : retour ou absence annoncée")

    async def participation(self, member, kind):
        async with self.lock(member.guild.id, member.id):
            if self.enabled_member(member):
                self.service.record_participation(member.guild.id, member.id, kind)
        await self.sync_member(member)

    @commands.Cog.listener()
    async def on_message(self, message):
        if (
            not message.guild
            or message.webhook_id
            or not self.enabled_member(message.author)
            or message.type not in (discord.MessageType.default, discord.MessageType.reply)
        ):
            return
        guild, channel = message.guild.id, message.channel.id
        channels = self.service.get_setting(guild, "presence:channels", [])
        if (
            channel not in channels
            or channel
            in {self.bot.channel_id(guild, "counting"), self.bot.channel_id(guild, "words")}
            or not conversational_text(message.content)
        ):
            return
        now = self.service.clock()
        key = (guild, channel)
        previous = self.conversations.get(key)
        if previous and message.id <= previous[2]:
            return
        self.conversations[key] = (message.author.id, now, message.id)
        if not previous or previous[0] == message.author.id or not 0 <= now - previous[1] <= 1800:
            return
        for uid in (previous[0], message.author.id):
            member = message.guild.get_member(uid)
            if member and self.enabled_member(member):
                try:
                    await self.participation(member, "message")
                except (DomainError, discord.HTTPException):
                    log.exception("Rôle de pause à reprendre au prochain contrôle")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Une sortie, un déplacement ou une mise en sourdine coupe la continuité.
        for identity in list(self.voice):
            if identity[:2] == (member.guild.id, member.id):
                self.voice.pop(identity, None)

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.voice.clear()
        self.conversations.clear()
        self.last_voice_tick = None

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id in self.bot.config.guild_ids:
            self.service.remove_presence(member.guild.id, member.id)
            for key, value in list(self.conversations.items()):
                if key[0] == member.guild.id and value[0] == member.id:
                    self.conversations.pop(key, None)

    async def voice_tick(self, guilds, *, now=None):
        now = time.monotonic() if now is None else now
        elapsed = None if self.last_voice_tick is None else now - self.last_voice_tick
        self.last_voice_tick = now
        current = {}
        for guild in guilds:
            if guild.id not in self.bot.config.guild_ids or not self.service.presence_enabled(
                guild.id
            ):
                continue
            for channel in [*guild.voice_channels, *guild.stage_channels]:
                if channel == guild.afk_channel or channel.id == self.bot.channel_id(
                    guild.id, "music_voice"
                ):
                    continue
                members = [
                    m
                    for m in channel.members
                    if self.enabled_member(m)
                    and m.voice
                    and not any(
                        getattr(m.voice, key)
                        for key in ("self_deaf", "deaf", "self_mute", "mute", "suppress")
                    )
                ]
                if len(members) < 2:
                    continue
                for member in members:
                    key = (guild.id, member.id, channel.id)
                    seconds = self.voice.get(key, 0)
                    if key in self.voice and elapsed is not None and 45 <= elapsed <= 90:
                        seconds += elapsed
                    else:
                        seconds = 0
                    if seconds >= 300:
                        try:
                            await self.participation(member, "voice")
                        except (DomainError, discord.HTTPException):
                            log.exception("Participation vocale à reprendre")
                        seconds = 0
                    current[key] = seconds
        self.voice = current

    def rows(self, guild):
        rows = []
        for member in guild.members:
            if self.enabled_member(member):
                rows.append(self.service.presence_member(guild.id, member.id))
        return sorted(rows, key=lambda r: (not r["inactive"], not r["announced"], r["user"]))

    def report(self, guild, rows, page=1):
        start = (page - 1) * 20
        lines = []
        for row in rows[start : start + 20]:
            if row["announced"]:
                state = f"🧳 Absence annoncée jusqu'au <t:{int(row['absent_until'])}:d>"
            elif row["inactive"]:
                state = f"🌙 En pause café · aucun échange observé depuis 21 jours (seuil <t:{int(row['due_at'])}:d>)"
            elif row["last_at"] is not None:
                state = f"☕ Dernier échange observé <t:{int(row['last_at'])}:R>"
            else:
                state = "🌱 Délai d'accueil ou de retour en cours"
            lines.append(f"<@{row['user']}> · {state}")
        result = card(
            "🌙 Les nouvelles du Comptoir",
            "**Un repère pour prendre des nouvelles, sans exclusion automatique.**\n"
            f"{sum(r['inactive'] for r in rows)} en pause · {sum(r['announced'] for r in rows)} absence(s) annoncée(s) · {len(rows)} membre(s) suivis.\n\n"
            + ("\n".join(lines) or "Aucun membre sur cette page.")
            + "\n\nÉcrit : un échange à deux, hors jeux et commandes. Vocal : 5 minutes à plusieurs. "
            "Les périodes hors ligne ne sont pas observées. Aucun texte ni audio conservé.\n"
            "`/absence` pour prévenir · `/retour` pour revenir · `/activite bilan` pour les autres pages.",
        )
        result.set_footer(
            text=f"Moka · Bilan réservé au staff · Page {page}/{max(1, (len(rows) + 19) // 20)}"
        )
        return result

    async def hide_exposed_report(self, guild, channel):
        mid = self.service.get_setting(guild.id, "presence:report", 0)
        if not mid or not isinstance(channel, discord.TextChannel):
            return
        try:
            message = await channel.fetch_message(mid)
            if message.author.id == self.bot.user.id:
                await message.delete()
            else:
                log.warning("Référence de bilan invalide ; aucun message tiers supprimé")
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.exception(
                "Bilan devenu accessible : retrait impossible ; vérifier les droits du journal"
            )
            return
        self.service.set_setting(guild.id, "presence:report", 0)
        self.report_stamps.pop(guild.id, None)

    async def publish_report(self, guild, rows):
        cid = self.service.get_setting(guild.id, "presence:journal", 0)
        channel = guild.get_channel(cid)
        if not private_staff_channel(self.service, channel):
            await self.hide_exposed_report(guild, channel)
            raise DomainError("Le journal des pauses doit rester visible uniquement par le staff.")
        payload = self.report(guild, rows).to_dict()
        if self.report_stamps.get(guild.id) == payload:
            return
        mid = self.service.get_setting(guild.id, "presence:report", 0)
        embed = discord.Embed.from_dict(payload)
        if mid:
            try:
                await channel.get_partial_message(mid).edit(
                    embed=embed, allowed_mentions=discord.AllowedMentions.none()
                )
            except discord.NotFound:
                mid = 0
        if not mid:
            message = await channel.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none()
            )
            self.service.set_setting(guild.id, "presence:report", message.id)
        self.report_stamps[guild.id] = payload

    async def reconcile(self, guild):
        now = self.service.clock()
        if (
            not self.service.presence_enabled(guild.id)
            or now - self.last_reconcile.get(guild.id, float("-inf")) < 60
        ):
            return
        self.last_reconcile[guild.id] = now
        for member in guild.members:
            if self.enabled_member(member):
                try:
                    await self.sync_member(member)
                except (DomainError, discord.HTTPException):
                    log.exception("Rôle de pause non synchronisé ; nouvel essai dans une minute")
        await self.publish_report(guild, self.rows(guild))

    async def confirm_sync(self, member):
        try:
            await self.sync_member(member)
        except (DomainError, discord.HTTPException):
            log.exception("Pause enregistrée ; rôle à reprendre au prochain contrôle")
            return "\nLa date est enregistrée ; le rôle n'a pas encore pu être actualisé. Moka réessaiera."
        return ""

    @app_commands.command(
        name="absence", description="Prévenir le Comptoir d'une absence, sans donner de motif"
    )
    async def absence(
        self, interaction: discord.Interaction, jours: app_commands.Range[int, 1, 365] = 7
    ):
        guild, user, _ = context(interaction)
        require_access(self.service, interaction.user, interaction.guild)
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.lock(guild, user):
            row = self.service.announce_absence(guild, user, jours)
        warning = await self.confirm_sync(interaction.user)
        await interaction.followup.send(
            embed=card(
                "🧳 Ta tasse t'attendra",
                f"Absence annoncée jusqu'au <t:{int(row['absent_until'])}:D>. Aucun motif demandé.\nUn échange ou `/retour` mettra fin à cette pause. Le staff voit seulement la date prévue."
                + warning,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="retour", description="Annoncer ton retour au Comptoir")
    async def retour(self, interaction: discord.Interaction):
        guild, user, _ = context(interaction)
        require_access(self.service, interaction.user, interaction.guild)
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with self.lock(guild, user):
            self.service.return_from_absence(guild, user)
        warning = await self.confirm_sync(interaction.user)
        await interaction.followup.send(
            embed=card(
                "☕ Bon retour au Comptoir",
                "Ta pause est terminée. Tu disposes à nouveau de 21 jours avant un éventuel signalement, à ton rythme."
                + warning,
            ),
            ephemeral=True,
        )

    @activite.command(name="bilan", description="Consulter le bilan privé des pauses (staff)")
    async def bilan(
        self, interaction: discord.Interaction, page: app_commands.Range[int, 1, 1000] = 1
    ):
        guild, _, _ = context(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        member = await interaction.guild.fetch_member(interaction.user.id)
        if not staff_member(self.service, member):
            raise DomainError("Ce bilan est réservé au staff du Comptoir.")
        if not self.service.presence_enabled(guild):
            raise DomainError("Le suivi des pauses n'est pas activé.")
        await interaction.followup.send(
            embed=self.report(interaction.guild, self.rows(interaction.guild), page),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
