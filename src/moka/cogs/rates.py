from __future__ import annotations

import asyncio
import io
import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands

from moka.base import DomainError
from moka.discord_ui import card, context
from moka.rate_cards import render_rate_card
from moka.rates import DUO_RATES, SOLO_RATES, measure_rate

log = logging.getLogger(__name__)


class RatesCog(commands.Cog):
    def __init__(self, bot):
        self.bot, self.service = bot, bot.service

    async def avatar(self, member):
        try:
            return await member.display_avatar.with_format("png").with_size(256).read()
        except (discord.HTTPException, OSError):
            return None

    async def show(self, interaction, key, members):
        guild, user, _ = context(interaction)
        self.service.require_play(guild, user)
        if not self.service.is_enabled(guild, "rates"):
            raise DomainError("Les taux du jour sont désactivés sur ce serveur.")
        if any(member.guild.id != guild for member in members):
            raise DomainError("Choisis des membres de ce serveur.")
        if any(member.bot and member.id != self.bot.user.id for member in members):
            raise DomainError("Choisis une personne, ou Moka pour jouer avec lui.")
        try:
            result = measure_rate(
                guild,
                tuple(member.id for member in members),
                key,
                datetime.fromtimestamp(self.service.clock(), tz=UTC),
                self.service.get_setting(guild, "rates:timezone", "Europe/Paris"),
            )
        except ValueError as error:
            raise DomainError(str(error)) from error
        await interaction.response.defer()
        names = tuple(member.display_name for member in members)
        avatars = tuple(await asyncio.gather(*(self.avatar(member) for member in members)))
        names_text = " et ".join(member.mention for member in members)
        embed = card(
            f"{result.rate.emoji} {result.rate.label} du jour",
            f"{names_text} : **{result.percent} %**\n{result.comment}",
        )
        embed.colour = discord.Colour(int(result.rate.color.removeprefix("#"), 16))
        zone_label = "Paris" if result.timezone == "Europe/Paris" else result.timezone
        embed.set_footer(
            text=f"Juste pour rire · Change à minuit ({zone_label})"
            + (" · Duo symétrique" if len(members) == 2 else "")
        )
        try:
            image = await asyncio.to_thread(render_rate_card, result, names, avatars)
        except (OSError, ValueError):
            log.exception("Carte de taux indisponible ; le résultat reste accessible en texte")
            await interaction.followup.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none()
            )
            return
        filename = "moka-duo.png" if len(members) == 2 else "moka-taux.png"
        await interaction.followup.send(
            file=discord.File(
                io.BytesIO(image),
                filename=filename,
                description=(
                    f"{result.rate.label} : {' et '.join(names)}, {result.percent} %. "
                    f"{result.comment} {embed.footer.text}"
                ),
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(
        name="taux", description="Ton taux du jour : choupitude, sagesse, chance…"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name=f"{rate.emoji} {rate.label}", value=rate.key)
            for rate in SOLO_RATES
        ]
    )
    @app_commands.describe(type="Le taux à découvrir", membre="Toi par défaut")
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def rate(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        membre: discord.Member | None = None,
    ):
        await self.show(interaction, type.value, (membre or interaction.user,))

    @app_commands.command(name="duo", description="Vos taux à deux : amitié, amour, complicité…")
    @app_commands.choices(
        type=[
            app_commands.Choice(name=f"{rate.emoji} {rate.label}", value=rate.key)
            for rate in DUO_RATES
        ]
    )
    @app_commands.describe(
        type="Le taux à découvrir", membre="L'autre membre", avec="Toi par défaut"
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def duo(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        membre: discord.Member,
        avec: discord.Member | None = None,
    ):
        await self.show(interaction, type.value, (avec or interaction.user, membre))
