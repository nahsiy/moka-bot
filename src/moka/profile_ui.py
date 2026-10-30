"""Actions bancaires du profil : toujours sur le compte de l'auteur."""

import asyncio
import contextlib
import io
import logging
import re

import discord

from moka.base import DomainError
from moka.discord_ui import card, context, handle_error, human
from moka.profile_cards import number, render_profile_card
from moka.profile_controls import ProfilePanel, owner_context

log = logging.getLogger(__name__)


def parse_amount(text):
    cleaned = str(text).strip().translate(str.maketrans("", "", " \u00a0\u202f"))
    if not re.fullmatch(r"[0-9]{1,10}", cleaned) or int(cleaned) < 1:
        raise DomainError("Indique un nombre entier de cœurs supérieur à zéro.")
    return int(cleaned)


async def update_profile(interaction, target, *, profile=None, status=None, previous=None):
    guild, user, key = context(interaction)
    service = interaction.client.service
    profile = profile or service.profile(guild, human(target), viewer=user)
    enabled = service.is_enabled(guild, "economy") and service.is_enabled(guild, "bank")
    cost = service.rules_for(guild).bank_upgrade_cost * (profile["bank_tier"] + 1)
    avatar = None
    with contextlib.suppress(discord.HTTPException, OSError):
        avatar = await target.display_avatar.with_format("png").with_size(256).read()
    view = (
        ProfileView(guild, user, profile, key, enabled, cost, service=service)
        if target.id == user
        else None
    )
    attachments, embeds = [], []
    description = (
        f"Profil de {target.display_name}. Niveau {profile['level']}, "
        f"{profile['xp']} sur {profile['next_xp']} XP. "
        f"Portefeuille {profile['wallet']} cœurs. "
        f"Banque {profile['bank']} sur {profile['capacity']} cœurs."
    )
    if enabled and profile["bank_tier"] < 20:
        next_capacity = profile["capacity"] + profile["capacity"] // (profile["bank_tier"] + 1)
        description += f" Prochain palier {next_capacity} cœurs, prix {cost} cœurs."
    if status:
        description += " " + status.replace("**", "")
    try:
        image = await asyncio.to_thread(
            render_profile_card,
            profile,
            target.display_name,
            avatar,
            bank_enabled=enabled,
            upgrade_cost=cost,
            status=status,
        )
        attachments.append(
            discord.File(
                io.BytesIO(image),
                filename="moka-profile.png",
                description=description,
            )
        )
    except (OSError, ValueError):
        log.exception("Image du profil indisponible ; repli sur le texte")
        embed = card(
            f"☕ Profil de {discord.utils.escape_markdown(target.display_name)}",
            f"Niveau **{profile['level']}** · **{number(profile['xp'])}/{number(profile['next_xp'])} XP**",
        )
        embed.add_field(name="Portefeuille", value=f"{number(profile['wallet'])} ❤️")
        embed.add_field(
            name="Banque", value=f"{number(profile['bank'])}/{number(profile['capacity'])} ❤️"
        )
        if status:
            embed.add_field(name="Dernière action", value=status, inline=False)
        embeds.append(embed)
    if previous:
        previous.stop()
    message = await interaction.edit_original_response(
        content=None,
        attachments=attachments,
        embeds=embeds,
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    if view:
        view.message = message


async def send_profile(interaction, target=None):
    guild, user, _ = context(interaction)
    target = target or interaction.user
    if target.guild.id != guild:
        raise DomainError("Choisis un membre de ce serveur.")
    profile = interaction.client.service.profile(guild, human(target), viewer=user)
    await interaction.response.defer(ephemeral=True)
    await update_profile(interaction, target, profile=profile)


class BankAmountModal(discord.ui.Modal):
    def __init__(self, guild, owner, key, deposit, *, previous=None):
        super().__init__(
            title="Déposer en banque" if deposit else "Retirer de la banque", timeout=180
        )
        self.guild_id, self.owner, self.receipt, self.deposit = guild, owner, key, deposit
        self.previous = previous
        self.amount = discord.ui.TextInput(
            label="Montant en cœurs", placeholder="Exemple : 250", min_length=1, max_length=20
        )
        self.add_item(self.amount)

    async def on_error(self, interaction, error):
        await handle_error(interaction, error)

    async def on_submit(self, interaction):
        guild, user, _ = owner_context(interaction, self.guild_id, self.owner)
        if self.previous and self.previous.expired:
            raise DomainError("Ce profil a expiré. Rouvre /profile avant une nouvelle opération.")
        amount = parse_amount(self.amount.value)
        await interaction.response.defer()
        result = interaction.client.service.bank_move(
            guild, user, amount, self.receipt, deposit=self.deposit
        )
        action = "Dépôt en banque" if result["deposit"] else "Retrait vers ton portefeuille"
        if result["replayed"]:
            action += " déjà pris en compte"
        await update_profile(
            interaction,
            interaction.user,
            status=f"✅ {action} : **{number(result['amount'])} ❤️**.",
            previous=self.previous,
        )


class ProfileView(ProfilePanel):
    def __init__(self, guild, owner, profile, key, bank_enabled, upgrade_cost, *, service=None):
        super().__init__(guild, owner)
        if service:
            from moka.profile_hub import HubSelect, RewardButton

            self.add_item(HubSelect(service, guild))
            if service.is_enabled(guild, "economy"):
                rewards = service.reward_status(guild, owner)
                self.add_item(
                    RewardButton("daily", rewards["daily"], service.rules_for(guild).daily_coins)
                )
                self.add_item(
                    RewardButton("weekly", rewards["weekly"], service.rules_for(guild).weekly_coins)
                )
        self.receipt = "profile-upgrade:" + key
        self.tier = profile["bank_tier"]
        self.deposit.disabled = (
            not bank_enabled or profile["wallet"] == 0 or profile["bank"] >= profile["capacity"]
        )
        self.withdraw.disabled = not bank_enabled or profile["bank"] == 0
        self.upgrade.label = (
            "Capacité maximale" if self.tier >= 20 else f"Agrandir · {number(upgrade_cost)} ❤️"
        )
        self.upgrade.disabled = (
            not bank_enabled or self.tier >= 20 or profile["wallet"] < upgrade_cost
        )

    async def open_amount(self, interaction, deposit):
        guild, user, key = owner_context(interaction, self.guild_id, self.owner)
        service = interaction.client.service
        if not service.is_enabled(guild, "economy") or not service.is_enabled(guild, "bank"):
            raise DomainError("La banque est désactivée sur ce serveur.")
        await interaction.response.send_modal(
            BankAmountModal(guild, user, "profile-bank:" + key, deposit, previous=self)
        )

    @discord.ui.button(label="Déposer", emoji="📥", style=discord.ButtonStyle.primary, row=0)
    async def deposit(self, interaction, button):
        await self.open_amount(interaction, True)

    @discord.ui.button(label="Retirer", emoji="📤", style=discord.ButtonStyle.secondary, row=0)
    async def withdraw(self, interaction, button):
        await self.open_amount(interaction, False)

    @discord.ui.button(label="Agrandir", emoji="🏦", style=discord.ButtonStyle.secondary, row=1)
    async def upgrade(self, interaction, button):
        guild, user, _ = owner_context(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        result = interaction.client.service.bank_upgrade(
            guild, user, self.receipt, expected_tier=self.tier
        )
        await update_profile(
            interaction,
            interaction.user,
            previous=self,
            status=(
                "✅ Agrandissement déjà pris en compte."
                if result["replayed"]
                else f"✅ Banque agrandie · **{number(result['cost'])} ❤️** prélevés sur le portefeuille."
            ),
        )

    @discord.ui.button(label="Actualiser", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, interaction, button):
        owner_context(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        await update_profile(interaction, interaction.user, previous=self)
