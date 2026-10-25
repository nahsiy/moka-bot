from __future__ import annotations

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from moka.base import DomainError
from moka.config import CHANNELS, FEATURES, ROLES
from moka.discord_ui import JoinView, card, context, event_embed


def staff(interaction, permission="manage_guild"):
    values = context(interaction)
    if not getattr(interaction.user.guild_permissions, permission, False):
        raise DomainError(f"La permission {permission} est nécessaire.")
    return values


class StaffCog(commands.Cog):
    config = app_commands.Group(
        name="config",
        description="Configuration de Moka",
        default_permissions=discord.Permissions(manage_guild=True),
    )
    animation = app_commands.Group(
        name="animation",
        description="Lancer les animations collectives",
        default_permissions=discord.Permissions(manage_guild=True),
    )
    moderation = app_commands.Group(
        name="moderation",
        description="Modération manuelle et journalisée",
        default_permissions=discord.Permissions(moderate_members=True),
    )

    def __init__(self, bot):
        self.bot, self.service = bot, bot.service

    @config.command(name="module", description="Activer ou désactiver un module")
    async def module(self, interaction: discord.Interaction, nom: str, actif: bool):
        guild, _, _ = staff(interaction)
        if nom not in FEATURES:
            raise DomainError("Modules : " + ", ".join(sorted(FEATURES)))
        self.service.set_setting(guild, "feature:" + nom, actif)
        await interaction.response.send_message(
            f"Module **{nom}** {'activé' if actif else 'désactivé'}. Les événements déjà ouverts sont réglés jusqu'au bout.",
            ephemeral=True,
        )
        await self.bot.audit(
            interaction.guild, f"Configuration : {nom}={actif} par {interaction.user.id}."
        )

    @module.autocomplete("nom")
    async def feature_names(self, interaction, current):
        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(FEATURES)
            if current.casefold() in name
        ][:25]

    @config.command(
        name="salon", description="Choisir un salon textuel, une catégorie ou le vocal créateur"
    )
    async def channel(
        self,
        interaction: discord.Interaction,
        usage: str,
        salon: discord.TextChannel | discord.VoiceChannel | discord.CategoryChannel,
    ):
        guild, _, _ = staff(interaction)
        if usage not in CHANNELS:
            raise DomainError("Usage de salon inconnu.")
        expected = (
            discord.VoiceChannel
            if usage == "voice_creator"
            else discord.CategoryChannel
            if usage in {"voice_category", "ticket_category"}
            else discord.TextChannel
        )
        if salon.guild.id != guild or not isinstance(salon, expected):
            raise DomainError("Le type de salon ne correspond pas à cet usage.")
        # Deux moteurs de jeux dans un même salon donneraient des règles ambiguës.
        if usage in {"counting", "words"}:
            other = "words" if usage == "counting" else "counting"
            if self.bot.channel_id(guild, other) == salon.id:
                raise DomainError("Choisis deux salons distincts pour counting et suite de mots.")
        self.service.set_setting(guild, "channel:" + usage, salon.id)
        await interaction.response.send_message(
            f"Usage **{usage}** affecté à {salon.mention}.", ephemeral=True
        )

    @channel.autocomplete("usage")
    async def channel_names(self, interaction, current):
        return [
            app_commands.Choice(name=name, value=name)
            for name in sorted(CHANNELS)
            if current.casefold() in name
        ][:25]

    @config.command(name="role", description="Définir un rôle temporaire ou du trombinoscope")
    async def role(
        self,
        interaction: discord.Interaction,
        usage: Literal["counting_failure", "trombi_preaccess", "trombi_access"],
        role: discord.Role,
    ):
        guild, _, _ = staff(interaction)
        if usage not in ROLES:
            raise DomainError("Usage de rôle inconnu.")
        self.bot.get_cog("CommunityCog").safe_role(interaction.guild, role)
        self.service.set_setting(guild, "role:" + usage, role.id)
        await interaction.response.send_message(
            f"Rôle **{role.name}** affecté à **{usage}**.", ephemeral=True
        )

    @config.command(name="role_choix", description="Ajouter ou retirer un rôle du menu des membres")
    async def role_choice(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        actif: bool,
        groupe_exclusif: str = "",
    ):
        guild, _, _ = staff(interaction)
        self.bot.get_cog("CommunityCog").safe_role(interaction.guild, role)
        menu = self.service.get_setting(guild, "role_menu", {})
        if actif:
            if len(menu) >= 25 and str(role.id) not in menu:
                raise DomainError("Ce premier menu est limité à 25 rôles.")
            if len(groupe_exclusif) > 30:
                raise DomainError("Nom de groupe trop long.")
            menu[str(role.id)] = groupe_exclusif.strip()
        else:
            menu.pop(str(role.id), None)
        self.service.set_setting(guild, "role_menu", menu)
        await interaction.response.send_message(
            "Menu des rôles mis à jour. Un groupe non vide impose un seul choix dans ce groupe.",
            ephemeral=True,
        )

    @config.command(name="niveau_role", description="Associer un rôle à un niveau atteint")
    async def level_role(
        self,
        interaction: discord.Interaction,
        niveau: app_commands.Range[int, 1, 10000],
        role: discord.Role,
    ):
        guild, _, _ = staff(interaction)
        self.bot.get_cog("CommunityCog").safe_role(interaction.guild, role)
        rewards = self.service.get_setting(guild, "level_rewards", {})
        rewards[str(niveau)] = role.id
        self.service.set_setting(guild, "level_rewards", rewards)
        await interaction.response.send_message(
            f"Le niveau **{niveau}** donne le rôle **{role.name}**. Les membres peuvent utiliser /roles niveaux pour rattraper leurs récompenses.",
            ephemeral=True,
        )

    @config.command(
        name="equipe_tickets", description="Choisir les rôles du staff autorisés à lire les tickets"
    )
    async def ticket_staff(self, interaction: discord.Interaction, role: discord.Role, actif: bool):
        guild, _, _ = staff(interaction)
        if role.guild.id != guild or role.is_default() or role.managed:
            raise DomainError("Choisis un rôle de staff explicite.")
        roles = set(self.service.get_setting(guild, "ticket_staff_roles", []))
        roles.add(role.id) if actif else roles.discard(role.id)
        self.service.set_setting(guild, "ticket_staff_roles", sorted(roles))
        await interaction.response.send_message(
            "Accès appliqué aux prochains tickets. Les salons existants conservent leurs permissions actuelles.",
            ephemeral=True,
        )

    @config.command(name="suite_mots", description="Choisir les règles de la suite de mots")
    async def word_mode(
        self, interaction: discord.Interaction, mode: Literal["free", "last_letter"]
    ):
        guild, _, _ = staff(interaction)
        self.service.set_setting(guild, "words:mode", mode)
        await interaction.response.send_message(
            "Mode **association libre** : un mot inédit par membre à tour de rôle."
            if mode == "free"
            else "Mode **dernière lettre** : le mot commence par la dernière lettre du précédent, sans répétition.",
            ephemeral=True,
        )

    @config.command(
        name="reinitialiser_jeu", description="Recommencer une partie en conservant son record"
    )
    async def reset_game(self, interaction: discord.Interaction, jeu: Literal["counting", "words"]):
        guild, _, _ = staff(interaction)
        channel = self.bot.channel_id(guild, jeu)
        if not channel:
            raise DomainError("Configure d'abord le salon de ce jeu.")
        self.service.reset_game(guild, channel, jeu)
        await interaction.response.send_message(
            "Nouvelle partie initialisée. Le record est conservé.", ephemeral=True
        )

    @config.command(
        name="ajuster_coeurs", description="Correction manuelle d'un solde fictif, journalisée"
    )
    async def adjust(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: app_commands.Range[int, -1_000_000_000, 1_000_000_000],
        motif: app_commands.Range[str, 3, 200],
    ):
        guild, _, key = staff(interaction)
        if membre.bot:
            raise DomainError("Choisis une personne.")
        self.service.adjust(guild, membre.id, montant, key)
        await self.bot.audit(
            interaction.guild,
            f"Ajustement {montant:+} ❤️ pour {membre.id} par {interaction.user.id}. Motif : {motif}",
        )
        await interaction.response.send_message(
            "Solde corrigé. L'ajustement figure dans le journal économique local.", ephemeral=True
        )

    @animation.command(name="lancer", description="Ouvrir un gobelin ou un tirage de jackpot")
    async def start_event(
        self, interaction: discord.Interaction, jeu: Literal["goblin", "jackpot"]
    ):
        guild, user, key = staff(interaction)
        if not isinstance(interaction.channel, discord.TextChannel):
            raise DomainError("Lance cette animation dans un salon textuel.")
        result = self.service.start_event(guild, interaction.channel_id, user, jeu, key)
        event = self.service.get_event(guild, result["event_id"])
        if result["replayed"] and event["message"]:
            await interaction.response.send_message(
                "Cet événement a déjà été ouvert.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=event_embed(event, self.service), view=JoinView()
        )
        message = await interaction.original_response()
        self.service.bind_event(guild, event["id"], message.id)

    @app_commands.command(
        name="diagnostic", description="Vérifier la configuration et les permissions de Moka"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def diagnostic(self, interaction: discord.Interaction):
        guild, _, _ = staff(interaction)
        await interaction.response.defer(ephemeral=True)
        me = interaction.guild.me
        permissions = me.guild_permissions
        lines = [
            f"Base SQLite : **{'OK' if self.service.check_integrity() else 'ERREUR'}**",
            f"Serveur autorisé : **{guild}**",
            f"Message Content : **{self.bot.intents.message_content}** · membres : **{self.bot.intents.members}**",
        ]
        for permission in (
            "view_channel",
            "send_messages",
            "embed_links",
            "add_reactions",
            "read_message_history",
            "manage_roles",
            "manage_channels",
            "move_members",
            "create_public_threads",
        ):
            lines.append(f"{'✅' if getattr(permissions, permission) else '⚠️'} {permission}")
        for name in sorted(CHANNELS):
            channel_id = self.bot.channel_id(guild, name)
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                lines.append(f"{name} : {'✅' if channel else '❌'} {channel_id}")
                if isinstance(channel, discord.TextChannel):
                    local = channel.permissions_for(me)
                    if not all((local.view_channel, local.send_messages, local.embed_links)):
                        lines.append(f"⚠️ Permissions locales insuffisantes : {name}")
        await interaction.followup.send(
            embed=card("🔎 Diagnostic Moka", "\n".join(lines)), ephemeral=True
        )

    def moderation_target(self, interaction, member, permission):
        guild, _, _ = staff(interaction, permission)
        if not self.service.is_enabled(guild, "moderation"):
            raise DomainError("Le module de modération est désactivé.")
        if (
            member.id in {interaction.user.id, interaction.guild.owner_id, self.bot.user.id}
            or member.bot
        ):
            raise DomainError("Cette cible ne peut pas être modérée avec cette commande.")
        if member.top_role >= interaction.guild.me.top_role:
            raise DomainError("Ce membre est au-dessus de mon rôle.")
        if (
            interaction.user.id != interaction.guild.owner_id
            and member.top_role >= interaction.user.top_role
        ):
            raise DomainError("Ce membre est au-dessus de ton rôle.")

    @moderation.command(name="pause", description="Mettre temporairement un membre en timeout")
    async def timeout(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        motif: app_commands.Range[str, 3, 200],
    ):
        from datetime import timedelta

        self.moderation_target(interaction, membre, "moderate_members")
        await interaction.response.defer(ephemeral=True)
        await membre.timeout(timedelta(minutes=minutes), reason=f"{interaction.user.id} : {motif}")
        await self.bot.audit(
            interaction.guild,
            f"Timeout {minutes} min pour {membre.id} par {interaction.user.id}. Motif : {motif}",
        )
        await interaction.followup.send("Pause appliquée.", ephemeral=True)

    @moderation.command(name="reprendre", description="Retirer le timeout d'un membre")
    async def untimeout(self, interaction: discord.Interaction, membre: discord.Member):
        self.moderation_target(interaction, membre, "moderate_members")
        await interaction.response.defer(ephemeral=True)
        await membre.timeout(None, reason=f"Moka : {interaction.user.id}")
        await self.bot.audit(
            interaction.guild, f"Timeout retiré pour {membre.id} par {interaction.user.id}."
        )
        await interaction.followup.send("Pause levée.", ephemeral=True)
