from __future__ import annotations

import asyncio
import logging
import weakref

import discord
from discord import app_commands
from discord.ext import commands

from moka.admission_discord import require_access
from moka.base import DomainError
from moka.cogs.staff import staff
from moka.discord_ui import SafeView, card, context
from moka.role_panels import (
    CategoryPicker,
    category_menu,
    prepare_preferences,
    protected_roles,
    publish_categories,
    selected_channel_links,
    validate_choices,
)

log = logging.getLogger(__name__)
PRIVILEGES = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_messages",
    "manage_threads",
    "manage_nicknames",
    "kick_members",
    "ban_members",
    "moderate_members",
    "move_members",
    "mute_members",
    "deafen_members",
    "mention_everyone",
    "view_audit_log",
    "manage_events",
    "manage_expressions",
)


class RoleSelect(discord.ui.Select):
    def __init__(self, member, menu, *, category=None):
        self.category = category
        options = []
        for role_id, group in menu.items():
            role = member.guild.get_role(int(role_id))
            if role:
                options.append(
                    discord.SelectOption(
                        label=role.name[:100],
                        value=str(role.id),
                        default=role in member.roles,
                        description=(f"Un seul choix : {group}" if group else "Choix libre")[:100],
                    )
                )
        if not options:
            raise DomainError("Aucun rôle disponible. Le staff doit configurer /config role_choix.")
        exclusive = len(set(menu.values())) == 1 and all(menu.values())
        super().__init__(
            placeholder="Choisir mes rôles",
            min_values=0,
            max_values=1 if exclusive else len(options),
            options=options,
        )
        self.owner = member.id

    async def callback(self, interaction):
        guild, user, _ = context(interaction)
        if user != self.owner:
            raise DomainError("Ce menu appartient à un autre membre.")
        cog = interaction.client.get_cog("CommunityCog")
        selected = set(self.values)
        validate_choices(cog.service, guild, self.category, selected)
        await interaction.response.defer(ephemeral=True)
        await cog.apply_role_preferences(interaction, self.category, selected)
        text = "Tes rôles sont mis à jour." + selected_channel_links(
            cog.service, interaction.guild, selected
        )
        await interaction.edit_original_response(
            content=None, embed=card("☕ Tes préférences", text), view=None
        )


class RolePanelView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Choisir mes rôles",
        emoji="🎭",
        style=discord.ButtonStyle.primary,
        custom_id="moka:roles:open",
    )
    async def open_roles(self, interaction, button):
        await interaction.client.get_cog("CommunityCog").choose_roles(interaction)


class TicketPanelView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Contacter le staff",
        emoji="📬",
        style=discord.ButtonStyle.primary,
        custom_id="moka:tickets:open",
    )
    async def open_ticket(self, interaction, button):
        await interaction.client.get_cog("CommunityCog").open_ticket(interaction)


class PhotoReviewView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    async def review(self, interaction, approve):
        guild, _, _ = staff(interaction)
        cog = interaction.client.get_cog("CommunityCog")
        if not interaction.message or interaction.message.author.id != interaction.client.user.id:
            raise DomainError("Ce panneau n'appartient pas à Moka.")
        with cog.bot.store.read() as con:
            row = con.execute(
                "SELECT * FROM photos WHERE guild=? AND review_message=?",
                (guild, interaction.message.id),
            ).fetchone()
        if not row:
            raise DomainError("Photo introuvable.")
        await interaction.response.defer(ephemeral=True)
        channel = interaction.guild.get_channel(cog.bot.channel_id(guild, "trombi") or 0)
        if not isinstance(channel, discord.TextChannel):
            raise DomainError("Salon trombinoscope introuvable.")
        try:
            original = await channel.fetch_message(row["message"])
        except discord.NotFound as error:
            cog.service.delete_photo(guild, row["message"])
            raise DomainError("La photo a été supprimée par son auteur.") from error
        if not any(
            a.content_type and a.content_type.startswith("image/") for a in original.attachments
        ):
            cog.service.delete_photo(guild, row["message"])
            raise DomainError("Ce message ne contient plus de photo.")
        user = cog.service.review_photo(guild, row["message"], approve=approve)
        await cog.sync_photo_role(interaction.guild, user)
        await interaction.message.edit(
            content=None,
            embed=card(
                "📸 Trombinoscope",
                "Photo approuvée." if approve else "Photo refusée : aucun accès accordé.",
            ),
            view=None,
        )
        await interaction.followup.send(
            embed=card("📸 Trombinoscope", "Décision enregistrée."), ephemeral=True
        )

    @discord.ui.button(
        label="Approuver", style=discord.ButtonStyle.success, custom_id="moka:photo:approve"
    )
    async def approve(self, interaction, button):
        await self.review(interaction, True)

    @discord.ui.button(
        label="Refuser", style=discord.ButtonStyle.secondary, custom_id="moka:photo:reject"
    )
    async def reject(self, interaction, button):
        await self.review(interaction, False)


class CommunityCog(commands.Cog):
    roles = app_commands.Group(name="roles", description="Choix et récompenses de rôles")
    ticket_group = app_commands.Group(name="ticket", description="Contacter le staff")
    vocal = app_commands.Group(name="vocal", description="Ton salon vocal temporaire")

    def __init__(self, bot):
        self.bot, self.service = bot, bot.service
        self.ticket_lock = asyncio.Lock()
        self.voice_lock = asyncio.Lock()
        self.last_reconcile = {}
        self.role_locks = weakref.WeakValueDictionary()

    @staticmethod
    def safe_role(guild, role):
        if not role or role.guild.id != guild.id or role.is_default() or role.managed:
            raise DomainError("Ce rôle ne peut pas être attribué automatiquement.")
        if any(getattr(role.permissions, p, False) for p in PRIVILEGES):
            raise DomainError(
                "Un rôle doté de permissions de modération ou d'administration est interdit ici."
            )
        if not guild.me or role >= guild.me.top_role:
            raise DomainError("Place le rôle de Moka au-dessus du rôle à attribuer.")

    def safe_self_role(self, guild, role):
        self.safe_role(guild, role)
        if role.id in protected_roles(self.service, guild.id) or role.name == "☕ Le Barista":
            raise DomainError(
                "Les rôles du staff, de progression et de pause ne sont pas à choisir."
            )

    async def apply_role_preferences(self, interaction, category, selected):
        guild, user, _ = context(interaction)
        validate_choices(self.service, guild, category, selected)
        admission = getattr(self.bot, "get_cog", lambda _: None)("AdmissionCog")
        lock = (
            admission.lock(guild, user)
            if admission
            else self.role_locks.setdefault((guild, user), asyncio.Lock())
        )
        async with lock:
            member = await interaction.guild.fetch_member(user)
            require_access(self.service, member, interaction.guild)
            # Même contrôle après l'attente : une fenêtre ancienne ne rétablit aucun choix retiré.
            menu = validate_choices(self.service, guild, category, selected)
            roles = [interaction.guild.get_role(int(key)) for key in menu]
            for role in roles:
                if role:
                    self.safe_self_role(interaction.guild, role)
            add = [r for r in roles if r and str(r.id) in selected and r not in member.roles]
            remove = [r for r in roles if r and str(r.id) not in selected and r in member.roles]
            if add:
                await member.add_roles(*add, reason="Moka : choix des rôles")
            if remove:
                await member.remove_roles(*remove, reason="Moka : choix des rôles")
            return [r.name for r in roles if r and str(r.id) in selected]

    async def choose_roles(self, interaction, category=None):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "roles"):
            raise DomainError("Le choix de rôles est désactivé.")
        view = SafeView(timeout=120)
        categories = self.service.get_setting(guild, "role_categories", {})
        if category is None and categories:
            view.add_item(CategoryPicker(interaction.user.id, categories))
            text = "Choisis une rubrique. Tu pourras ajouter ou retirer tes préférences."
        else:
            menu = category_menu(self.service, guild, category)
            view.add_item(RoleSelect(interaction.user, menu, category=category))
            text = "Sélectionne tes préférences. Pour tout retirer dans cette rubrique, valide sans sélection."
        await interaction.response.send_message(
            embed=card(
                "☕ Fais comme chez toi",
                text,
            ),
            view=view,
            ephemeral=True,
        )

    @roles.command(
        name="choisir", description="Choisir tes rôles parmi ceux autorisés par le staff"
    )
    async def roles_choose(self, interaction: discord.Interaction):
        await self.choose_roles(interaction)

    @roles.command(name="publier", description="Publier le panneau permanent des rôles")
    @app_commands.default_permissions(manage_guild=True)
    async def roles_publish(self, interaction: discord.Interaction):
        guild, _, _ = staff(interaction)
        if not self.service.is_enabled(guild, "roles"):
            raise DomainError("Le module de rôles est désactivé.")
        if self.service.get_setting(guild, "role_categories", {}):
            if not isinstance(interaction.channel, discord.TextChannel):
                raise DomainError("Publie le panneau dans un salon textuel.")
            await interaction.response.defer(ephemeral=True)
            count = await publish_categories(interaction.channel, self.service)
            await interaction.followup.send(
                embed=card("☕ Le coin des rôles", f"{count} rubriques publiées ou actualisées."),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=card(
                "🎭 À chacun ses préférences",
                "Genre, région, centres d'intérêt, MP ou notifications : les choix sont définis par le staff.",
            ),
            view=RolePanelView(),
        )

    @roles.command(
        name="installer", description="Préparer les préférences facultatives du Comptoir"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def install_roles(self, interaction: discord.Interaction):
        guild, _, _ = staff(interaction)
        if not self.service.is_enabled(guild, "roles"):
            raise DomainError("Le module de rôles est désactivé.")
        await interaction.response.defer(ephemeral=True)
        categories = await prepare_preferences(
            interaction.guild, interaction.guild.me, self.service
        )
        await interaction.followup.send(
            embed=card(
                "☕ Le coin des rôles",
                f"{len(categories)} rubriques prêtes. Utilise /roles publier dans le salon de ton choix.",
            ),
            ephemeral=True,
        )

    @roles.command(name="niveaux", description="Récupérer les rôles de niveau déjà mérités")
    async def level_roles(self, interaction: discord.Interaction):
        guild, user, _ = context(interaction)
        if not self.service.is_enabled(guild, "roles"):
            raise DomainError("Le module de rôles est désactivé.")
        await interaction.response.defer(ephemeral=True)
        await self.bot.level_roles(interaction.user)
        await interaction.followup.send(
            embed=card("🏅 Récompenses de niveau", "Tes récompenses de rôle ont été vérifiées."),
            ephemeral=True,
        )

    async def open_ticket(self, interaction):
        guild_id, user, key = context(interaction)
        if not self.service.is_enabled(guild_id, "tickets"):
            raise DomainError("Les tickets sont désactivés.")
        staff_roles = [
            interaction.guild.get_role(i)
            for i in self.service.get_setting(guild_id, "ticket_staff_roles", [])
        ]
        staff_roles = [r for r in staff_roles if r and not r.is_default()]
        if not staff_roles:
            raise DomainError("Le staff doit d'abord configurer /config equipe_tickets.")
        await interaction.response.defer(ephemeral=True)
        async with self.ticket_lock:
            ticket = self.service.reserve_ticket(guild_id, user, key)
            ticket = self.service.ticket_by_id(guild_id, ticket["id"])
            if ticket["status"] not in {"creating", "open"}:
                raise DomainError(
                    "Cette demande est terminée. Relance /ticket ouvrir pour une nouvelle demande."
                )
            existing = interaction.guild.get_channel(ticket["channel"] or 0)
            if existing:
                await interaction.followup.send(
                    embed=card("📬 Ton ticket", f"Ton ticket est déjà ouvert : {existing.mention}"),
                    ephemeral=True,
                )
                return
            # Récupération d'une création interrompue juste avant l'écriture SQLite.
            existing = next(
                (
                    c
                    for c in interaction.guild.text_channels
                    if c.topic == "moka-ticket:" + ticket["id"]
                ),
                None,
            )
            if existing:
                self.service.bind_ticket(guild_id, ticket["id"], existing.id)
                await interaction.followup.send(
                    embed=card("📬 Ton ticket", f"Ton ticket : {existing.mention}"), ephemeral=True
                )
                return
            if ticket["status"] == "open":
                self.service.close_ticket(guild_id, ticket["channel"])
                raise DomainError(
                    "L'ancien salon a disparu. Relance /ticket ouvrir pour en créer un nouveau."
                )
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True,
                ),
            }
            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )
            category = interaction.guild.get_channel(
                self.bot.channel_id(guild_id, "ticket_category") or 0
            )
            try:
                channel = await interaction.guild.create_text_channel(
                    f"ticket-{ticket['id'][:8]}",
                    topic="moka-ticket:" + ticket["id"],
                    category=category if isinstance(category, discord.CategoryChannel) else None,
                    overwrites=overwrites,
                    reason="Moka : demande de ticket",
                )
            except discord.HTTPException:
                self.service.fail_ticket(guild_id, ticket["id"])
                raise
            self.service.bind_ticket(guild_id, ticket["id"], channel.id)
            await channel.send(
                embed=card(
                    "📬 Ton ticket",
                    "📬 Ton ticket est ouvert. Explique ta demande au staff.\nUn seul ticket ouvert par personne. /ticket fermer termine l'échange sans supprimer les messages.",
                )
            )
            await interaction.followup.send(
                embed=card("📬 Ton ticket", f"Ton ticket : {channel.mention}"), ephemeral=True
            )

    @ticket_group.command(name="ouvrir", description="Ouvrir un ticket privé avec le staff")
    async def ticket_open(self, interaction: discord.Interaction):
        await self.open_ticket(interaction)

    @ticket_group.command(
        name="publier", description="Publier un bouton permanent de contact du staff"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def ticket_publish(self, interaction: discord.Interaction):
        guild, _, _ = staff(interaction)
        if not self.service.is_enabled(guild, "tickets"):
            raise DomainError("Les tickets sont désactivés.")
        await interaction.response.send_message(
            embed=card(
                "📬 Un mot au staff ?",
                "Ouvre un ticket privé pour une demande, une suggestion ou un signalement.",
            ),
            view=TicketPanelView(),
        )

    @ticket_group.command(
        name="fermer", description="Fermer ce ticket sans supprimer son historique"
    )
    async def ticket_close(self, interaction: discord.Interaction):
        guild, user, _ = context(interaction)
        ticket = self.service.ticket(guild, interaction.channel_id)
        staff_role_ids = set(self.service.get_setting(guild, "ticket_staff_roles", []))
        if (
            user != ticket["user"]
            and not interaction.user.guild_permissions.manage_guild
            and not staff_role_ids.intersection(r.id for r in interaction.user.roles)
        ):
            raise DomainError("Seuls l'auteur et le staff peuvent fermer ce ticket.")
        await interaction.response.defer(ephemeral=True)
        member = interaction.guild.get_member(ticket["user"])
        if member:
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                reason="Moka : fermeture ticket",
            )
        await interaction.channel.edit(
            name="ferme-" + interaction.channel.name.removeprefix("ferme-"),
            topic="moka-ticket-closed:" + ticket["id"],
        )
        self.service.close_ticket(guild, interaction.channel_id)
        await interaction.followup.send(
            embed=card(
                "📬 Ticket fermé",
                "L'historique reste dans ce salon ; aucun transcript n'est exporté.",
            ),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.guild.id not in self.bot.config.guild_ids or member.bot:
            return
        self.bot.voice_eligible = {
            v for v in self.bot.voice_eligible if v[:2] != (member.guild.id, member.id)
        }
        if not self.service.admitted(member.guild.id, member.id) or not self.service.is_enabled(
            member.guild.id, "temporary_voice"
        ):
            return
        creator = self.bot.channel_id(member.guild.id, "voice_creator")
        if after.channel and after.channel.id == creator and before.channel != after.channel:
            async with self.voice_lock:
                # Le membre peut avoir quitté le créateur pendant un appel réseau.
                if (
                    not member.voice
                    or not member.voice.channel
                    or member.voice.channel.id != creator
                ):
                    return
                with self.bot.store.read() as con:
                    row = con.execute(
                        "SELECT channel FROM voice_rooms WHERE guild=? AND owner=?",
                        (member.guild.id, member.id),
                    ).fetchone()
                room = member.guild.get_channel(row[0]) if row else None
                if room is None:
                    category = member.guild.get_channel(
                        self.bot.channel_id(member.guild.id, "voice_category") or 0
                    )
                    if not isinstance(category, discord.CategoryChannel):
                        return
                    # Copie explicite des droits de la catégorie : aucune visibilité supplémentaire.
                    room = await member.guild.create_voice_channel(
                        f"Salon de {member.display_name}"[:100],
                        category=category,
                        overwrites=category.overwrites,
                        reason="Moka : salon temporaire",
                    )
                    with self.bot.store.transaction() as con:
                        con.execute(
                            "INSERT INTO voice_rooms VALUES(?,?,?,?)",
                            (member.guild.id, room.id, member.id, self.service.clock()),
                        )
                try:
                    await member.move_to(room, reason="Moka : salon personnel")
                except discord.HTTPException:
                    log.warning("Déplacement vocal impossible pour %s", member.id)

    async def owned_room(self, interaction):
        guild, user, _ = context(interaction)
        if not self.service.is_enabled(guild, "temporary_voice"):
            raise DomainError("Les salons temporaires sont désactivés.")
        with self.bot.store.read() as con:
            row = con.execute(
                "SELECT channel FROM voice_rooms WHERE guild=? AND owner=?", (guild, user)
            ).fetchone()
        room = interaction.guild.get_channel(row[0]) if row else None
        if not isinstance(room, discord.VoiceChannel):
            raise DomainError("Rejoins le vocal créateur pour obtenir ton salon.")
        return room

    @vocal.command(name="renommer", description="Renommer ton salon vocal temporaire")
    async def voice_name(
        self, interaction: discord.Interaction, nom: app_commands.Range[str, 1, 80]
    ):
        room = await self.owned_room(interaction)
        await interaction.response.defer(ephemeral=True)
        await room.edit(name=nom, reason="Moka : demande du propriétaire")
        await interaction.followup.send(
            embed=card("🔊 Ton salon vocal", "Salon renommé."), ephemeral=True
        )

    @vocal.command(
        name="limite", description="Définir la capacité de ton salon, 0 signifie sans limite"
    )
    async def voice_limit(
        self, interaction: discord.Interaction, places: app_commands.Range[int, 0, 99]
    ):
        room = await self.owned_room(interaction)
        await interaction.response.defer(ephemeral=True)
        await room.edit(user_limit=places, reason="Moka : capacité demandée par le propriétaire")
        await interaction.followup.send(
            embed=card("🔊 Ton salon vocal", "Capacité mise à jour."), ephemeral=True
        )

    async def submit_photo(self, message):
        guild, user = message.guild.id, message.author.id
        preaccess = self.bot.role_id(guild, "trombi_preaccess")
        access = self.bot.role_id(guild, "trombi_access")
        if not {preaccess, access}.intersection(role.id for role in message.author.roles):
            await message.reply(
                embed=card("📸 Trombinoscope", "Demande d'abord le pré-accès au staff par ticket."),
                mention_author=False,
            )
            return
        if not any(
            a.content_type and a.content_type.startswith("image/") for a in message.attachments
        ):
            await message.reply(
                embed=card(
                    "📸 Trombinoscope",
                    "Chaque publication doit contenir une image. Les échanges peuvent se faire dans un fil.",
                ),
                mention_author=False,
            )
            return
        self.service.add_photo(guild, user, message.id)
        review = message.guild.get_channel(self.bot.channel_id(guild, "trombi_review") or 0)
        if not isinstance(review, discord.TextChannel):
            raise DomainError("Le salon de validation du trombinoscope n'est pas configuré.")
        # Le panneau ne recopie ni ne télécharge l'image.
        response = await review.send(
            embed=card(
                "📸 Trombinoscope",
                f"Photo à vérifier de <@{user}> : [ouvrir l'original]({message.jump_url})",
            ),
            view=PhotoReviewView(),
        )
        with self.bot.store.transaction() as con:
            con.execute(
                "UPDATE photos SET review_message=? WHERE guild=? AND message=?",
                (response.id, guild, message.id),
            )
        try:
            await message.create_thread(
                name=f"Photo de {message.author.display_name}"[:100], auto_archive_duration=1440
            )
        except discord.HTTPException:
            log.warning("Fil photo impossible pour %s", message.id)

    async def sync_photo_role(self, guild, user):
        member = guild.get_member(user)
        if not member:
            return
        role = guild.get_role(self.bot.role_id(guild.id, "trombi_access") or 0)
        if not role:
            return
        count = self.service.approved_photos(guild.id, user)
        if count and role not in member.roles:
            self.safe_role(guild, role)
            await member.add_roles(role, reason="Moka : photo approuvée")
        elif not count and role in member.roles:
            await member.remove_roles(role, reason="Moka : plus de photo approuvée")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.guild_id not in self.bot.config.guild_ids:
            return
        user = self.service.delete_photo(payload.guild_id, payload.message_id)
        guild = self.bot.get_guild(payload.guild_id)
        if user and guild:
            await self.sync_photo_role(guild, user)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        if payload.guild_id not in self.bot.config.guild_ids:
            return
        users = {
            self.service.delete_photo(payload.guild_id, message) for message in payload.message_ids
        }
        guild = self.bot.get_guild(payload.guild_id)
        if guild:
            for user in users - {None}:
                await self.sync_photo_role(guild, user)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.guild_id not in self.bot.config.guild_ids or "attachments" not in payload.data:
            return
        if any(a.get("content_type", "").startswith("image/") for a in payload.data["attachments"]):
            return
        user = self.service.delete_photo(payload.guild_id, payload.message_id)
        guild = self.bot.get_guild(payload.guild_id)
        if user and guild:
            await self.sync_photo_role(guild, user)

    def safe_game_role(self, guild, role, usage):
        self.safe_role(guild, role)
        if role.permissions.value or role.id in protected_roles(
            self.service, guild.id, exclude_usage=usage
        ):
            raise DomainError(
                "Choisis un rôle de pause dédié, sans permission et distinct des autres usages."
            )

    async def configure_game_role(self, guild, role, *, usage="counting_failure"):
        self.safe_game_role(guild, role, usage)
        if not role.hoist:
            await role.edit(hoist=True, reason="Moka : afficher séparément le rôle de pause")
        for usage in ("counting", "words"):
            channel_id = self.bot.channel_id(guild.id, usage)
            if not channel_id:
                continue
            channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                raise DomainError("Le salon de jeu doit être un salon textuel.")
            overwrite = channel.overwrites_for(role)
            overwrite.send_messages = False
            overwrite.send_messages_in_threads = False
            await channel.set_permissions(
                role, overwrite=overwrite, reason="Moka : pause commune aux deux jeux"
            )

    async def apply_role_grant(self, guild, grant, now):
        lock = self.role_locks.setdefault((guild.id, grant["user"]), asyncio.Lock())
        async with lock:
            # Une ancienne capture de maintenance ne peut pas réactiver une sanction levée.
            with self.bot.store.read() as con:
                current = con.execute(
                    "SELECT * FROM role_grants WHERE guild=? AND user=? AND role=?",
                    (guild.id, grant["user"], grant["role"]),
                ).fetchone()
            if current:
                await self._apply_role_grant(guild, dict(current), max(now, self.service.clock()))

    async def release_game_roles(self, guild, user, roles):
        for role_id in roles:
            with self.bot.store.read() as con:
                grant = con.execute(
                    "SELECT * FROM role_grants WHERE guild=? AND user=? AND role=? AND reason IN ('counting','words','counting-edit') AND until<=?",
                    (guild.id, user, role_id, self.service.clock()),
                ).fetchone()
            if grant:
                try:
                    await self.apply_role_grant(guild, dict(grant), self.service.clock())
                except (DomainError, discord.HTTPException):
                    log.exception("Retrait du rôle de jeu différé ; la maintenance réessaiera")
        with self.bot.store.read() as con:
            pending = con.execute(
                "SELECT 1 FROM role_grants WHERE guild=? AND user=? AND reason IN ('counting','words','counting-edit') AND until<=?",
                (guild.id, user, self.service.clock()),
            ).fetchone()
        return bool(pending)

    async def _apply_role_grant(self, guild, grant, now):
        role = guild.get_role(grant["role"])
        member = guild.get_member(grant["user"])
        if not member:
            try:
                member = await guild.fetch_member(grant["user"])
            except discord.NotFound:
                # Conserver une pause active : elle s'applique aussi après un retour.
                if grant["until"] > now:
                    return
        if not role and grant["until"] > now:
            # Un rôle supprimé ne doit pas lever la pause métier avant son terme.
            return
        if grant["until"] <= now:
            # Le retrait d'un rôle expiré reste possible même si ses droits ont changé.
            if member and role and role in member.roles:
                await member.remove_roles(role, reason="Moka : rôle temporaire expiré")
            with self.bot.store.transaction() as con:
                con.execute(
                    "DELETE FROM role_grants WHERE guild=? AND user=? AND role=? AND until<=?",
                    (guild.id, grant["user"], grant["role"], now),
                )
        elif not grant["applied"] or role not in member.roles:
            if grant["reason"] == "counting-edit":
                self.safe_game_role(guild, role, "counting_cheat")
            else:
                self.safe_role(guild, role)
            await member.add_roles(
                role,
                reason="Moka : modification après validation"
                if grant["reason"] == "counting-edit"
                else "Moka : erreur dans un jeu",
            )
            with self.bot.store.transaction() as con:
                con.execute(
                    "UPDATE role_grants SET applied=1 WHERE guild=? AND user=? AND role=?",
                    (guild.id, member.id, role.id),
                )

    async def reconcile(self, guild):
        now = self.service.clock()
        # Les expirations sont traitées même si le module vient d'être désactivé.
        with self.bot.store.read() as con:
            grants = [
                dict(row)
                for row in con.execute("SELECT * FROM role_grants WHERE guild=?", (guild.id,))
            ]
        for grant in grants:
            try:
                await self.apply_role_grant(guild, grant, now)
            except (DomainError, discord.HTTPException):
                log.exception(
                    "Rôle temporaire non réconcilié ; nouvelle tentative au prochain passage"
                )
        if now - self.last_reconcile.get(guild.id, 0) < 60:
            return
        self.last_reconcile[guild.id] = now
        # Aucun scan du contenu des conversations. Seulement les salons suivis.
        for ticket in self.service.pending_tickets(guild.id):
            channel = next(
                (c for c in guild.text_channels if c.topic == "moka-ticket:" + ticket["id"]), None
            )
            if channel:
                self.service.bind_ticket(guild.id, ticket["id"], channel.id)
            elif now - ticket["created"] > 120:
                self.service.fail_ticket(guild.id, ticket["id"])
        with self.bot.store.read() as con:
            rooms = [
                dict(row)
                for row in con.execute("SELECT * FROM voice_rooms WHERE guild=?", (guild.id,))
            ]
        for row in rooms:
            room = guild.get_channel(row["channel"])
            if (
                isinstance(room, discord.VoiceChannel)
                and not room.members
                and now - row["created"] >= 30
            ):
                await room.delete(reason="Moka : salon temporaire vide")
                room = None
            if room is None:
                with self.bot.store.transaction() as con:
                    con.execute("DELETE FROM voice_rooms WHERE channel=?", (row["channel"],))
        # Contrôle de disparition des photos après une période hors ligne.
        photo_channel = guild.get_channel(self.bot.channel_id(guild.id, "trombi") or 0)
        if isinstance(photo_channel, discord.TextChannel):
            with self.bot.store.read() as con:
                photos = [
                    dict(row)
                    for row in con.execute(
                        "SELECT * FROM photos WHERE guild=? AND status IN ('pending','approved') ORDER BY message",
                        (guild.id,),
                    )
                ]
            cursor = self.service.get_setting(guild.id, "photo:cursor", 0)
            batch = [p for p in photos if p["message"] > cursor][:10]
            if not batch:
                batch = photos[:10]
            for photo in batch:
                try:
                    original = await photo_channel.fetch_message(photo["message"])
                    if not any(
                        a.content_type and a.content_type.startswith("image/")
                        for a in original.attachments
                    ):
                        self.service.delete_photo(guild.id, photo["message"])
                except discord.NotFound:
                    self.service.delete_photo(guild.id, photo["message"])
                await self.sync_photo_role(guild, photo["user"])
            if batch:
                self.service.set_setting(guild.id, "photo:cursor", batch[-1]["message"])
