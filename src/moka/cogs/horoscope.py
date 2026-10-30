"""Le café des astres : menu commun, lecture personnelle et source visible."""

import logging
import uuid
from pathlib import Path
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from moka.admission_discord import require_access
from moka.base import DomainError
from moka.discord_ui import SafeView, card, context, handle_error
from moka.horoscope import (
    RUBRICS,
    SIGNS,
    SOURCE,
    HoroscopeReader,
    SourceUnavailable,
    sign_for_member,
    source_url,
)

log = logging.getLogger(__name__)
ART = Path(__file__).parents[1] / "assets" / "horoscope" / "moka-cafe-astres.png"
HOME_TITLE = "✨ Le café des astres"


class HoroscopeSelect(
    discord.ui.DynamicItem[discord.ui.Select], template=r"moka:horoscope:sign:[0-9a-f]{8}"
):
    def __init__(self, custom_id=None):
        super().__init__(
            discord.ui.Select(
                placeholder="Quel signe souhaites-tu lire ?",
                min_values=1,
                max_values=1,
                row=0,
                custom_id=custom_id or "moka:horoscope:sign:" + uuid.uuid4().hex[:8],
                options=[
                    discord.SelectOption(label=name, value=key, emoji=emoji)
                    for key, (emoji, name) in SIGNS.items()
                ],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(item.custom_id)

    async def callback(self, interaction):
        try:
            await interaction.client.get_cog("HoroscopeCog").show(
                interaction, self.item.values[0], panel=True
            )
        except Exception as error:
            await handle_error(interaction, error)


class HoroscopeView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HoroscopeSelect())

    @discord.ui.button(
        label="Mon signe enregistré",
        emoji="☕",
        style=discord.ButtonStyle.secondary,
        custom_id="moka:horoscope:mine",
        row=1,
    )
    async def mine(self, interaction, button):
        await interaction.client.get_cog("HoroscopeCog").show(interaction, panel=True)


def source_view(sign):
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(label="Lire l'horoscope complet", emoji="📖", url=source_url(sign))
    )
    return view


def edition_embed(edition):
    emoji, name = SIGNS[edition.sign]
    day, month, year = edition.day.split("-")[::-1]
    preview = discord.utils.escape_mentions(discord.utils.escape_markdown(edition.preview))
    embed = card(
        f"{emoji} {name} · {day}/{month}/{year}",
        f"**L'aperçu du jour**\n> {preview}\n\n"
        f"[Source : {SOURCE}]({edition.url})\n"
        "Retrouve la lecture détaillée — dont amour en couple et célibataire — avec le bouton ci-dessous.",
    )
    for rubric in RUBRICS:
        value = edition.scores[rubric]
        embed.add_field(
            name=rubric, value="★" * value + "☆" * (5 - value) + f" · {value}/5", inline=True
        )
    embed.set_footer(text="Aperçu RSS et notes de l'éditeur · Astrologie de divertissement")
    return embed


def home_embed(reader):
    day = reader.today().strftime("%d/%m/%Y")
    embed = card(
        HOME_TITLE,
        "**Un café, ton signe et la lecture du jour.**\n\n"
        "Choisis un signe directement dans la liste. Si tu as choisi le tien dans les rôles, "
        "**Mon signe enregistré** le retrouve pour toi.\n\n"
        "**Au menu**\nAperçu quotidien et notes de l'éditeur : humeur, amour, argent, travail et loisirs. "
        "Un bouton donne accès au texte complet gratuit, sur le site de la source.\n\n"
        f"**Source : [{SOURCE}](https://www.mon-horoscope-du-jour.com/)**\n"
        "Ta lecture s'ouvre uniquement pour toi ; le menu reste disponible pour tout le monde.",
    )
    embed.set_image(url="attachment://moka-cafe-astres.png")
    embed.set_footer(text=f"Moka · Nous sommes le {day} à Paris · Astrologie de divertissement")
    return embed


class HoroscopeCog(commands.Cog):
    def __init__(self, bot):
        self.bot, self.service = bot, bot.service
        self.reader = HoroscopeReader(self.service)
        self.rendered = {}

    async def show(self, interaction, sign=None, *, panel=False):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "horoscope"):
            raise DomainError("L'horoscope est désactivé.")
        channel = self.service.get_setting(guild, "channel:horoscope", 0)
        if not channel:
            raise DomainError("Le café des astres n'est pas encore installé sur ce serveur.")
        if interaction.channel_id != channel:
            await interaction.response.send_message(
                embed=card(HOME_TITLE, f"Retrouve le menu et les horoscopes dans <#{channel}>."),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if panel and (
            not interaction.message
            or interaction.message.author.id != self.bot.user.id
            or interaction.message.id != self.service.get_setting(guild, "horoscope:message", 0)
        ):
            raise DomainError("Utilise le menu actuel du café des astres.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        member = await interaction.guild.fetch_member(interaction.user.id)
        require_access(self.service, member)
        sign = sign or sign_for_member(self.service, member)
        if not sign:
            await interaction.followup.send(
                embed=card(
                    "✨ Quel est ton signe ?",
                    "Aucun signe unique n'est enregistré dans tes rôles. Choisis simplement un signe dans la liste du salon. Il n'est pas nécessaire de donner ta date de naissance.",
                ),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        source_url(sign)
        try:
            edition = await self.reader.read(guild, sign)
            embed = edition_embed(edition)
        except SourceUnavailable as error:
            embed = card("🌙 L'édition du jour se fait attendre", str(error))
            embed.add_field(name="Source", value=SOURCE)
        await interaction.followup.send(
            embed=embed,
            view=source_view(sign),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        if panel:
            # Une nouvelle identité de composant efface la sélection visuelle commune.
            try:
                await interaction.message.edit(view=HoroscopeView())
            except discord.HTTPException:
                log.warning("Menu des astres non réinitialisé ; la lecture a été envoyée")

    async def refresh_home(self, guild):
        if not self.service.is_enabled(guild.id, "horoscope"):
            return
        channel_id = self.service.get_setting(guild.id, "channel:horoscope", 0)
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        stamp = (channel_id, self.reader.today())
        if self.rendered.get(guild.id) == stamp:
            return
        mid = self.service.get_setting(guild.id, "horoscope:message", 0)
        if mid:
            try:
                await channel.get_partial_message(mid).edit(
                    embed=home_embed(self.reader),
                    view=HoroscopeView(),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                self.rendered[guild.id] = stamp
                return
            except discord.NotFound:
                pass
        # Retrouver un panneau envoyé avant l'enregistrement de son identifiant.
        async for message in channel.history(limit=50):
            if (
                message.author.id == guild.me.id
                and message.embeds
                and message.embeds[0].title == HOME_TITLE
            ):
                self.service.set_setting(guild.id, "horoscope:message", message.id)
                await message.edit(
                    embed=home_embed(self.reader),
                    view=HoroscopeView(),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                self.rendered[guild.id] = stamp
                return
        message = await channel.send(
            embed=home_embed(self.reader),
            view=HoroscopeView(),
            file=discord.File(
                ART,
                filename="moka-cafe-astres.png",
                description="Moka observe les étoiles depuis le comptoir, avec un télescope en laiton et un atlas céleste.",
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.service.set_setting(guild.id, "horoscope:message", message.id)
        self.rendered[guild.id] = stamp

    @app_commands.command(
        name="horoscope", description="L'horoscope publié du jour, dans le café des astres"
    )
    @app_commands.checks.cooldown(1, 3, key=lambda i: (i.guild_id, i.user.id))
    async def horoscope(
        self,
        interaction: discord.Interaction,
        signe: Literal[
            "Bélier",
            "Taureau",
            "Gémeaux",
            "Cancer",
            "Lion",
            "Vierge",
            "Balance",
            "Scorpion",
            "Sagittaire",
            "Capricorne",
            "Verseau",
            "Poissons",
        ]
        | None = None,
    ):
        sign = next((key for key, (_, name) in SIGNS.items() if name == signe), None)
        await self.show(interaction, sign)
