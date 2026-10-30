"""Accès à la gestion du bot et tableau de bord permanent du staff."""

import discord

from moka.base import DomainError
from moka.discord_ui import SafeView, card, context

ADMIN_ROLES = "moka:admin_roles"


def is_moka_admin(service, member, guild=None):
    guild = guild or member.guild
    if member.guild_permissions.manage_guild:
        return True
    owner = getattr(guild, "owner_id", None)
    if owner is not None and getattr(member, "id", None) == owner:
        return True
    roles = set(service.get_setting(guild.id, ADMIN_ROLES, []))
    return bool(roles) and any(role.id in roles for role in member.roles)


async def staff_access(interaction):
    guild, user, _ = context(interaction)
    member = await interaction.guild.fetch_member(user)
    staff = set(interaction.client.service.get_setting(guild, "admission:staff_roles", []))
    staff.update(interaction.client.service.get_setting(guild, "ticket_staff_roles", []))
    if not is_moka_admin(interaction.client.service, member, interaction.guild) and not any(
        role.id in staff for role in member.roles
    ):
        raise DomainError("Ce tableau de bord est réservé à l'équipe du Comptoir.")
    return member


def short_list(lines):
    result, size = [], 0
    for line in lines:
        if size + len(line) > 920:
            result.append(f"… et {len(lines) - len(result)} autre(s).")
            break
        result.append(line)
        size += len(line) + 1
    return "\n".join(result) or "Personne actuellement."


def team_embed(guild, service, members):
    admins, welcoming, tickets, moderation = [], [], [], []
    admin_roles = set(service.get_setting(guild.id, ADMIN_ROLES, []))
    welcome_roles = set(service.get_setting(guild.id, "admission:staff_roles", []))
    ticket_roles = set(service.get_setting(guild.id, "ticket_staff_roles", []))
    for member in members:
        if member.bot:
            continue
        roles = {role.id for role in member.roles}
        native = member.id == guild.owner_id or member.guild_permissions.manage_guild
        if is_moka_admin(service, member, guild):
            reason = (
                "propriétaire du serveur"
                if member.id == guild.owner_id
                else "rôle de gestion de Moka"
                if roles & admin_roles
                else "permission Discord Gérer le serveur"
            )
            admins.append(f"{member.mention} · {reason}")
        if native or roles & welcome_roles:
            welcoming.append(member.mention)
        if native or roles & ticket_roles:
            tickets.append(member.mention)
        permissions = member.guild_permissions
        if permissions.manage_messages or permissions.moderate_members:
            rights = []
            if permissions.manage_messages:
                rights.append("messages")
            if permissions.moderate_members:
                rights.append("timeouts")
            moderation.append(f"{member.mention} · {', '.join(rights)}")
    embed = card(
        "👥 Qui gère Moka ?",
        "Les personnes et leurs accès actuels, relus sur Discord.\n"
        "La gestion de Moka est distincte des permissions de modération de Discord.",
    )
    for label, lines in (
        ("☕ Réglages de Moka", admins),
        ("🛎️ Accueil et entretiens", welcoming),
        ("🎫 Tickets", tickets),
        ("🛡️ Modération Discord", moderation),
    ):
        embed.add_field(name=label, value=short_list(lines), inline=False)
    roles = [guild.get_role(rid) for rid in admin_roles]
    names = [role.mention for role in roles if role]
    embed.add_field(
        name="Rôle de gestion du bot",
        value=" · ".join(names) if names else "Aucun rôle dédié ; les droits Discord s'appliquent.",
        inline=False,
    )
    embed.set_footer(text="Moka · Réouvre /equipe pour actualiser · Aucune notification envoyée")
    return embed


async def show_team(interaction):
    guild, _, _ = context(interaction)
    await interaction.response.defer(ephemeral=True, thinking=True)
    # fetch_guild recharge les permissions des rôles avant d'évaluer les membres.
    current = await interaction.client.fetch_guild(guild)
    members = [member async for member in current.fetch_members(limit=None)]
    await interaction.followup.send(
        embed=team_embed(current, interaction.client.service, members),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


def hub_embed():
    embed = card(
        "🔐 L'arrière-comptoir",
        "Le point de départ de l'équipe pour faire vivre le Comptoir.\n\n"
        "**☕ Baristas** · réglages de Moka : modules, économie et règles des jeux.\n"
        "**🫖 Équipe du Comptoir** · accueil, entretiens et tickets.\n\n"
        "Utilise les boutons ci-dessous : chaque réponse est privée et les droits sont vérifiés au clic. "
        "**Qui gère Moka ?** affiche les personnes qui ont réellement ces accès.\n\n"
        "La permission Discord Administrateur n'est pas donnée par ces rôles. "
        "La modération des messages et les timeouts nécessitent leurs permissions Discord propres.",
    )
    embed.set_footer(text="Moka · Une équipe, des responsabilités claires")
    return embed


def guide_embed():
    embed = card(
        "🧭 Le mémo de l'équipe",
        "**Réglages de Moka** · bouton Réglages ou `/barista`. Les modules se préparent puis s'enregistrent ; "
        "les formulaires indiquent les montants et les unités.\n\n"
        "**Qui peut faire quoi ?** · bouton Équipe ou `/equipe`. "
        "La liste reflète les rôles et les permissions réels.\n\n"
        "**Accueil** · l'entretien se passe dans le premier café privé du candidat. "
        "Le staff valide ou refuse avec les boutons de ce salon ; `/accueil etat` donne son état.\n\n"
        "**Tickets** · les membres passent par le salon d'aide. `/ticket fermer` clôt l'échange "
        "sans supprimer l'historique.\n\n"
        "**Pause des jeux** · `/debloquer` retire une sanction de Moka. "
        "Cela ne retire pas un timeout Discord.\n\n"
        "**Nettoyage** · `/messages` prépare un aperçu puis demande confirmation. "
        "La suppression est définitive ; Gérer les messages est nécessaire.\n\n"
        "**Suivi** · les actions sont consignées dans le journal, sans notification aux personnes citées.",
    )
    embed.set_footer(text="Moka · En cas de doute, vérifier avant d'agir")
    return embed


class AdminHub(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Réglages de Moka", emoji="⚙️", custom_id="moka:admin:settings", row=0)
    async def settings(self, interaction, button):
        from moka.staff_panel import open_panel

        await open_panel(interaction)

    @discord.ui.button(label="Qui gère Moka ?", emoji="👥", custom_id="moka:admin:team", row=0)
    async def team(self, interaction, button):
        await show_team(interaction)

    @discord.ui.button(label="Diagnostic", emoji="🛠️", custom_id="moka:admin:diagnostic", row=1)
    async def diagnostic(self, interaction, button):
        from moka.cogs.staff import StaffCog

        await staff_access(interaction)
        cog = interaction.client.get_cog("StaffCog")
        await StaffCog.diagnostic.callback(cog, interaction)

    @discord.ui.button(label="Guide de l'équipe", emoji="📚", custom_id="moka:admin:guide", row=1)
    async def guide(self, interaction, button):
        await staff_access(interaction)
        await interaction.response.send_message(embed=guide_embed(), ephemeral=True)
