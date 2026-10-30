"""Installation explicite de l'accueil ; jamais lancée automatiquement au démarrage."""

import discord

from moka.admission import keyword_hash
from moka.admission_discord import entry_overwrites
from moka.base import DomainError
from moka.discord_ui import card


def charter(keyword):
    return card(
        "📜 La charte du Comptoir",
        (
            "**Bienvenue dans notre petit café, réservé aux 21 ans et plus.**\n"
            "On vient ici pour discuter, rire et partager une pause dans une ambiance bienveillante.\n\n"
            "**☕ Une place pour chacun**\n"
            "Respecte les personnes, leurs convictions et leurs limites. Les désaccords sont possibles ; "
            "les attaques personnelles, discriminations, menaces et harcèlement ne le sont pas.\n\n"
            "**🍪 L'humour se partage**\n"
            "Les taquineries restent légères et consenties. Si quelqu'un dit stop, on s'arrête. "
            "Pas de contenu sexuel explicite, choquant ou violent. Les jeux et les cœurs restent fictifs.\n\n"
            "**🔒 Ce qui se dit au café mérite du respect**\n"
            "Ne partage ni informations personnelles, ni captures de conversations privées, ni photos "
            "d'autrui sans son accord. Respecte les préférences de messages privés. Aucun enregistrement "
            "vocal sans l'accord de toutes les personnes concernées.\n\n"
            "**🛎️ Un comptoir agréable**\n"
            "Évite le spam, la publicité non sollicitée et les mentions répétées. Utilise les salons "
            "adaptés et respecte aussi les règles de Discord. En cas de malaise, parle au staff. "
            "Il peut intervenir pour protéger l'ambiance du lieu et t'expliquer sa décision.\n\n"
            "**🌱 Ton premier café**\n"
            "L'accueil se fait dans ton salon privé avec le staff, à l'écrit par défaut, en vocal si tu "
            "le souhaites. Confirme simplement que tu as au moins 21 ans : pas de pièce d'identité ni "
            "de date de naissance à transmettre. Pour montrer que tu as repéré cette consigne, "
            f"retiens le mot **{keyword}** et saisis-le avec le bouton *J'ai lu la charte*, dans ton salon. "
            "Ce mot ne remplace pas notre échange.\n\n"
            "**Prends ton temps : une bonne rencontre vaut mieux qu'un accueil à toute vitesse.**"
        ),
    ).set_footer(text="Moka · Un premier café, puis une place au Comptoir")


def gate_overwrites(channel, guild, member_role, staff_roles, *, public=None):
    """Fermer @everyone, ouvrir aux membres seulement si le salon était public."""
    if public is None:
        public = channel.permissions_for(guild.default_role).view_channel
    bot_visible = channel.permissions_for(guild.me).view_channel
    overwrites = channel.overwrites
    base = overwrites.get(guild.default_role, discord.PermissionOverwrite())
    base.view_channel = False
    overwrites[guild.default_role] = base
    if public:
        for role in (member_role, *staff_roles):
            overwrite = overwrites.get(role, discord.PermissionOverwrite())
            overwrite.view_channel = True
            overwrites[role] = overwrite
    if bot_visible:
        bot_overwrite = overwrites.get(guild.me, discord.PermissionOverwrite())
        bot_overwrite.view_channel = True
        overwrites[guild.me] = bot_overwrite
    return overwrites


async def prepare_admission(guild, service, *, keyword):
    service.allowed(guild.id)
    if service.admission_enabled(guild.id):
        raise DomainError(
            "L'accueil est déjà activé : ne pas recalculer les anciens accès publics."
        )
    if not keyword.strip() or len(keyword) > 40:
        raise DomainError("Choisis un mot de lecture court.")
    if (
        not guild.me.guild_permissions.manage_channels
        or not guild.me.guild_permissions.manage_roles
    ):
        raise DomainError("Moka doit pouvoir gérer les salons et les rôles.")
    if any(
        getattr(guild.default_role.permissions, p)
        for p in ("administrator", "manage_guild", "manage_roles", "manage_channels")
    ):
        raise DomainError("Les permissions de base permettraient de contourner l'accueil.")
    staff_ids = service.get_setting(
        guild.id, "admission:staff_roles", service.get_setting(guild.id, "ticket_staff_roles", [])
    )
    staff_roles = [guild.get_role(rid) for rid in staff_ids]
    if not staff_roles or any(r is None or r.is_default() for r in staff_roles):
        raise DomainError("Configure au moins un rôle de staff précis avant l'installation.")
    members = [m async for m in guild.fetch_members(limit=None)]
    established = {m.id for m in members}
    original_members = service.get_setting(guild.id, "admission:established_members")
    if original_members is None:
        original_members = [m.id for m in members if not m.bot]
        service.set_setting(guild.id, "admission:established_members", original_members)
    bot_roles = {r.id for m in members if m.bot for r in m.roles if not r.is_default()}
    plan = service.get_setting(guild.id, "admission:original_public_channels")
    if plan is None:
        plan = {
            str(c.id): c.permissions_for(guild.default_role).view_channel for c in guild.channels
        }
        service.set_setting(guild.id, "admission:original_public_channels", plan)
    channels = [c for c in guild.channels if str(c.id) in plan]
    # Un rôle XP/préférence ne doit pas servir de passe-droit, même dans un salon privé.
    for channel in channels:
        for target, overwrite in channel.overwrites.items():
            if overwrite.view_channel is not True or target.id == guild.id:
                continue
            if isinstance(target, discord.Role):
                if target.id not in set(staff_ids) | bot_roles | {
                    service.get_setting(guild.id, "admission:member_role")
                }:
                    raise DomainError(
                        "Un rôle non staff ouvre un salon. Vérifier cette exception avant d'activer l'accueil."
                    )
            elif target.id not in established:
                raise DomainError(
                    "Un ancien membre conserve un accès nominatif : vérifier cette exception."
                )
    prepared_roles = {}
    for key, name, color in (
        ("member_role", "☕ Membre du Comptoir", 0xBC8053),
        ("waiting_role", "🛎️ En attente", 0xA8A29E),
    ):
        role = guild.get_role(service.get_setting(guild.id, "admission:" + key, 0))
        if role is None:
            if any(r.name == name for r in guild.roles):
                raise DomainError(
                    "Un rôle homonyme existe : vérifier son usage avant l'installation."
                )
            role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                colour=discord.Colour(color),
                hoist=key == "waiting_role",
                mentionable=False,
                reason="Moka : accès au Comptoir",
            )
        if role.managed or role.permissions.value or role >= guild.me.top_role:
            raise DomainError("Rôle d'accueil non sûr ou hiérarchie insuffisante.")
        service.set_setting(guild.id, "admission:" + key, role.id)
        prepared_roles[key] = role
    member_role = prepared_roles["member_role"]
    service.set_setting(guild.id, "admission:staff_roles", staff_ids)
    service.set_setting(guild.id, "admission:keyword_hash", keyword_hash(keyword))
    for member in members:
        if member.bot or member.id not in original_members:
            continue
        row = service.begin_admission(guild.id, member.id, established=True)
        if row["status"] != "approved":
            continue
        if member_role not in member.roles:
            await member.add_roles(
                member_role, reason="Moka : conserver l'accès des membres déjà présents"
            )
    category = guild.get_channel(service.get_setting(guild.id, "admission:category", 0))
    if category is None:
        category = await guild.create_category(
            "🛎️ L’ENTRÉE DU COMPTOIR",
            overwrites=entry_overwrites(guild, service),
            reason="Moka : premier café",
        )
        service.set_setting(guild.id, "admission:category", category.id)
    rules = guild.get_channel(service.get_setting(guild.id, "admission:rules", 0))
    if rules is None:
        overwrites = entry_overwrites(guild, service)
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True,
            add_reactions=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
        )
        rules = await guild.create_text_channel(
            "📜・la-charte-du-comptoir",
            category=category,
            overwrites=overwrites,
            reason="Moka : charte en lecture seule",
        )
        service.set_setting(guild.id, "admission:rules", rules.id)
    msg_id = service.get_setting(guild.id, "admission:charter_message")
    if msg_id:
        await rules.get_partial_message(msg_id).edit(
            embed=charter(keyword), allowed_mentions=discord.AllowedMentions.none()
        )
    else:
        msg = await rules.send(
            embed=charter(keyword), allowed_mentions=discord.AllowedMentions.none()
        )
        service.set_setting(guild.id, "admission:charter_message", msg.id)
    # Les catégories ET chaque enfant sont fermés, y compris les salons désynchronisés.
    # En cas d'échec partiel, l'accueil reste désactivé et les anciens membres gardent leur rôle.
    for channel in channels:
        await channel.edit(
            overwrites=gate_overwrites(
                channel, guild, member_role, staff_roles, public=plan[str(channel.id)]
            ),
            reason="Moka : accès communautaire après entretien",
        )
    return {
        "category": category.id,
        "rules": rules.id,
        "channels_gated": len(channels),
        "established_members": sum(not m.bot for m in members),
    }
