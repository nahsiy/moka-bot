from __future__ import annotations

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from moka.base import DomainError
from moka.config import CHANNELS, FEATURES, ROLES
from moka.discord_ui import card, context, event_message
from moka.role_panels import category_key


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

    @app_commands.command(name="barista", description="Ouvrir le panneau privé de réglages de Moka")
    @app_commands.default_permissions(manage_guild=True)
    async def panel(self, interaction: discord.Interaction):
        from moka.staff_panel import authorize, render_panel

        guild, owner, _ = context(interaction)
        await authorize(interaction, guild, owner)
        await interaction.response.defer(ephemeral=True, thinking=True)
        await render_panel(interaction)

    @config.command(
        name="jukebox", description="Installer ou vérifier les espaces et le lecteur du Juke-box"
    )
    async def music_setup(self, interaction: discord.Interaction):
        await self.bot.get_cog("MusicCog").install(interaction)

    @config.command(name="module", description="Activer ou désactiver un module")
    async def module(self, interaction: discord.Interaction, nom: str, actif: bool):
        guild, _, _ = staff(interaction)
        nom = {"tournee": "goblin", "tournée": "goblin", "calin": "hug", "câlin": "hug"}.get(
            nom.casefold(), nom
        )
        if nom not in FEATURES:
            raise DomainError("Modules : " + ", ".join(sorted(FEATURES)))
        self.service.set_setting(guild, "feature:" + nom, actif)
        label = {"goblin": "tournée de Moka", "hug": "câlin collectif"}.get(nom, nom)
        await interaction.response.send_message(
            embed=card(
                "⚙️ Configuration",
                f"Module **{label}** {'activé' if actif else 'désactivé'}. Les événements déjà ouverts sont réglés jusqu'au bout.",
            ),
            ephemeral=True,
        )
        await self.bot.audit(
            interaction.guild, f"Configuration : {nom}={actif} par {interaction.user.id}."
        )

    @module.autocomplete("nom")
    async def feature_names(self, interaction, current):
        return [
            app_commands.Choice(
                name={"goblin": "☕ Tournée de Moka", "hug": "🤗 Câlin collectif"}.get(name, name),
                value=name,
            )
            for name in sorted(FEATURES)
            if current.casefold()
            in {"goblin": "tournee tournée goblin", "hug": "calin câlin hug"}.get(name, name)
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
            if usage in {"voice_creator", "music_voice"}
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
        await interaction.response.defer(ephemeral=True)
        self.service.set_setting(guild, "channel:" + usage, salon.id)
        if usage in {"counting", "words"}:
            for penalty_usage in ("counting_failure", "counting_cheat"):
                role_id = self.bot.role_id(guild, penalty_usage)
                if role := interaction.guild.get_role(role_id) if role_id else None:
                    await self.bot.get_cog("CommunityCog").configure_game_role(
                        interaction.guild, role, usage=penalty_usage
                    )
        await interaction.followup.send(
            embed=card("⚙️ Configuration", f"Usage **{usage}** affecté à {salon.mention}."),
            ephemeral=True,
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
        usage: Literal["counting_failure", "counting_cheat", "trombi_preaccess", "trombi_access"],
        role: discord.Role,
    ):
        guild, _, _ = staff(interaction)
        if usage not in ROLES:
            raise DomainError("Usage de rôle inconnu.")
        self.bot.get_cog("CommunityCog").safe_role(interaction.guild, role)
        await interaction.response.defer(ephemeral=True)
        if usage in {"counting_failure", "counting_cheat"}:
            await self.bot.get_cog("CommunityCog").configure_game_role(
                interaction.guild, role, usage=usage
            )
        self.service.set_setting(guild, "role:" + usage, role.id)
        await interaction.followup.send(
            embed=card("⚙️ Configuration", f"Rôle **{role.name}** affecté à **{usage}**."),
            ephemeral=True,
        )

    @config.command(name="role_choix", description="Ajouter ou retirer un rôle du menu des membres")
    async def role_choice(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        actif: bool,
        groupe_exclusif: str = "",
        rubrique: str = "",
    ):
        guild, _, _ = staff(interaction)
        self.bot.get_cog("CommunityCog").safe_self_role(interaction.guild, role)
        menu = self.service.get_setting(guild, "role_menu", {})
        categories = self.service.get_setting(guild, "role_categories", {})
        key = category_key(rubrique) if rubrique else None
        if actif:
            if not categories and not key and len(menu) >= 25 and str(role.id) not in menu:
                raise DomainError("Ce premier menu est limité à 25 rôles.")
            if (
                categories
                and not key
                and not any(role.id in c["roles"] for c in categories.values())
            ):
                raise DomainError("Choisis une rubrique pour ce nouveau rôle.")
            if len(groupe_exclusif) > 30:
                raise DomainError("Nom de groupe trop long.")
            if key:
                if key not in categories and len(categories) >= 25:
                    raise DomainError("Le panneau est limité à 25 rubriques.")
                data = categories.setdefault(
                    key,
                    {
                        "title": rubrique[:100],
                        "description": "Tes préférences au Comptoir.",
                        "roles": [],
                    },
                )
                if role.id not in data["roles"] and len(data["roles"]) >= 25:
                    raise DomainError("Une rubrique est limitée à 25 rôles.")
                for value in categories.values():
                    if value is not data:
                        value["roles"] = [rid for rid in value["roles"] if rid != role.id]
                if role.id not in data["roles"]:
                    data["roles"].append(role.id)
            menu[str(role.id)] = groupe_exclusif.strip()
        else:
            menu.pop(str(role.id), None)
            for data in categories.values():
                data["roles"] = [rid for rid in data["roles"] if rid != role.id]
        self.service.set_setting(guild, "role_menu", menu)
        if categories:
            self.service.set_setting(guild, "role_categories", categories)
        await interaction.response.send_message(
            embed=card(
                "⚙️ Configuration",
                "Menu des rôles mis à jour. Un groupe non vide impose un seul choix dans ce groupe.",
            ),
            ephemeral=True,
        )

    @config.command(name="niveau_role", description="Associer un rôle à un niveau atteint")
    async def level_role(
        self,
        interaction: discord.Interaction,
        niveau: app_commands.Range[int, 0, 10000],
        role: discord.Role,
    ):
        guild, _, _ = staff(interaction)
        self.bot.get_cog("CommunityCog").safe_role(interaction.guild, role)
        rewards = self.service.get_setting(guild, "level_rewards", {})
        rewards[str(niveau)] = role.id
        self.service.set_setting(guild, "level_rewards", rewards)
        await interaction.response.send_message(
            embed=card(
                "⚙️ Configuration",
                f"Le niveau **{niveau}** donne le rôle **{role.name}**. Les membres peuvent utiliser /roles niveaux pour rattraper leurs récompenses.",
            ),
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
            embed=card(
                "⚙️ Configuration",
                "Accès appliqué aux prochains tickets. Les salons existants conservent leurs permissions actuelles.",
            ),
            ephemeral=True,
        )

    @config.command(name="suite_mots", description="Choisir les règles de la suite de mots")
    async def word_mode(
        self, interaction: discord.Interaction, mode: Literal["free", "last_letter"]
    ):
        guild, _, _ = staff(interaction)
        self.service.set_setting(guild, "words:mode", mode)
        await interaction.response.send_message(
            embed=card(
                "⚙️ Configuration",
                "Mode **association libre** : un mot inédit par membre à tour de rôle."
                if mode == "free"
                else "Mode **dernière lettre** : le mot commence par la dernière lettre du précédent, sans répétition.",
            ),
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
            embed=card("⚙️ Configuration", "Nouvelle partie initialisée. Le record est conservé."),
            ephemeral=True,
        )

    @config.command(
        name="comptage", description="Consulter les règles du counting ou régler son amende"
    )
    async def counting_rules(
        self,
        interaction: discord.Interaction,
        amende: app_commands.Range[int, 0, 1_000_000] | None = None,
    ):
        guild, _, _ = staff(interaction)
        if amende is not None:
            self.service.update_rules(guild, {"counting_fine": amende})
        channel = self.bot.channel_id(guild, "counting")
        state = self.service.counting_status(guild, channel)
        chance = f"{state['bonus_chance_bps'] / 100:g}".replace(".", ",")
        bonus = (
            f"{chance} % par bon nombre · {state['bonus_min']} à {state['bonus_max']} ❤️"
            if state["bonus_chance_bps"]
            else "désactivé"
        )
        await interaction.response.send_message(
            embed=card(
                "⚙️ Configuration",
                f"**Salon :** {f'<#{channel}>' if channel else 'non configuré'}\n"
                f"**Prochain nombre :** {state['next']} · **Record :** {state['record']}\n"
                f"**Bonus surprise :** {bonus}\n"
                f"**Amende :** {state['fine']} ❤️ (portefeuille uniquement)\n"
                "Calculs acceptés · auteurs alternés · texte = erreur · pile ou face à chaque erreur.",
            ),
            ephemeral=True,
        )

    @config.command(
        name="corvee", description="Régler la pause de tous les jeux après modification du counting"
    )
    async def corvee(
        self, interaction: discord.Interaction, minutes: app_commands.Range[int, 0, 1440]
    ):
        guild, _, _ = staff(interaction)
        self.service.update_rules(guild, {"counting_cheat_seconds": minutes * 60})
        await interaction.response.send_message(
            embed=card(
                "🧽 Corvée de vaisselle",
                f"Durée des nouvelles corvées : **{minutes} minute(s)**. "
                "Zéro désactive les nouvelles sanctions. Les corvées en cours gardent leur échéance ; `/debloquer` permet de les lever.",
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="debloquer",
        description="Lever une pause des jeux, Café renversé ou corvée de vaisselle",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def unpause(self, interaction: discord.Interaction, membre: discord.Member):
        guild, actor, key = staff(interaction)
        if membre.bot or membre.guild.id != guild:
            raise DomainError("Choisis une personne de ce serveur.")
        await interaction.response.defer(ephemeral=True)
        result = self.service.release_game_penalty(guild, membre.id, key)
        pending = await self.bot.get_cog("CommunityCog").release_game_roles(
            interaction.guild, membre.id, result["roles"]
        )
        if self.service.game_penalty(guild, membre.id):
            text = "Une nouvelle sanction est active ; elle n'a pas été annulée par cette demande."
        elif pending:
            text = "La pause est levée, mais Discord n'a pas encore retiré le rôle. Moka réessaie automatiquement ; le rôle peut encore empêcher l'écriture."
        else:
            games = "à tous les jeux" if result.get("all_games") else "aux deux jeux"
            text = f"✅ Sanction levée pour {membre.mention} : accès {games} rétabli."
        await interaction.followup.send(embed=card("☕ Retour au comptoir", text), ephemeral=True)
        if not result["replayed"]:
            await self.bot.audit(
                interaction.guild, f"Pause des jeux levée pour {membre.id} par {actor}."
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
            embed=card(
                "🪙 Ajustement des cœurs",
                "Solde corrigé. L'ajustement figure dans le journal économique local.",
            ),
            ephemeral=True,
        )

    @animation.command(
        name="lancer", description="Ouvrir une tournée de Moka, un câlin collectif ou un jackpot"
    )
    @app_commands.choices(
        jeu=[
            app_commands.Choice(name="☕ Tournée de Moka", value="goblin"),
            app_commands.Choice(name="🤗 Câlin collectif", value="hug"),
            app_commands.Choice(name="🎟️ Jackpot", value="jackpot"),
        ]
    )
    async def start_event(self, interaction: discord.Interaction, jeu: app_commands.Choice[str]):
        guild, user, key = staff(interaction)
        if not isinstance(interaction.channel, discord.TextChannel):
            raise DomainError("Lance cette animation dans un salon textuel.")
        result = self.service.start_event(guild, interaction.channel_id, user, jeu.value, key)
        event = self.service.get_event(guild, result["event_id"])
        if result["replayed"] and event["message"]:
            await interaction.response.send_message(
                embed=card("🎲 Animation", "Cet événement a déjà été ouvert."), ephemeral=True
            )
            return
        await interaction.response.defer()
        # L'image et le bouton portent la même référence, conservée au redémarrage.
        options = await event_message(event, self.service, editing=True)
        message = await interaction.edit_original_response(**options)
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
        await interaction.followup.send(
            embed=card("🛡️ Modération", "Pause appliquée."), ephemeral=True
        )

    @moderation.command(name="reprendre", description="Retirer le timeout d'un membre")
    async def untimeout(self, interaction: discord.Interaction, membre: discord.Member):
        self.moderation_target(interaction, membre, "moderate_members")
        await interaction.response.defer(ephemeral=True)
        await membre.timeout(None, reason=f"Moka : {interaction.user.id}")
        await self.bot.audit(
            interaction.guild, f"Timeout retiré pour {membre.id} par {interaction.user.id}."
        )
        await interaction.followup.send(embed=card("🛡️ Modération", "Pause levée."), ephemeral=True)
