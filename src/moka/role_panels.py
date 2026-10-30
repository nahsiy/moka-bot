"""Rubriques de préférences facultatives et panneaux persistants de Moka."""

import logging
import re
import unicodedata
from uuid import uuid4

import discord

from moka.base import DomainError
from moka.discord_ui import SafeView, card, context, handle_error
from moka.role_catalog import PREFERENCES

log = logging.getLogger(__name__)
CLEAR_ROLE_VALUE = "__clear__"


def protected_roles(service, guild, *, include_presence=True, exclude_usage=None):
    reserved = set(service.get_setting(guild, "level_rewards", {}).values())
    reserved.update(service.get_setting(guild, "ticket_staff_roles", []))
    reserved.update(service.get_setting(guild, "admission:staff_roles", []))
    reserved.update(
        service.get_setting(guild, key)
        for key in ("admission:member_role", "admission:waiting_role")
        if service.get_setting(guild, key)
    )
    for usage in (
        "counting_failure",
        "counting_cheat",
        "trombi_preaccess",
        "trombi_access",
        "owner",
    ):
        if usage == exclude_usage:
            continue
        role = service.get_setting(guild, "role:" + usage, service.config.roles.get(usage))
        if role:
            reserved.add(role)
    if include_presence and (role := service.get_setting(guild, "presence:role")):
        reserved.add(role)
    return reserved


async def prepare_preferences(guild, bot_member, service):
    service.allowed(guild.id)
    if not service.is_enabled(guild.id, "roles"):
        raise DomainError("Le module de rôles est désactivé.")
    if not bot_member or not bot_member.guild_permissions.manage_roles:
        raise DomainError("Moka a besoin de Gérer les rôles pour préparer les préférences.")
    roles = await guild.fetch_roles()
    reserved = protected_roles(service, guild.id)
    menu = service.get_setting(guild.id, "role_menu", {})
    categories = service.get_setting(guild.id, "role_categories", {})
    if len(set(categories) | set(PREFERENCES)) > 25:
        raise DomainError("Le panneau est limité à 25 rubriques.")
    # Valider tous les rôles existants avant la première création.
    for _, _, _, names in PREFERENCES.values():
        for name in names:
            role = next((r for r in roles if r.name == name), None)
            if role and (
                role.managed
                or role.permissions.value
                or role.id in reserved
                or role >= bot_member.top_role
            ):
                raise DomainError(f"Le rôle {name} n'est pas un rôle de préférence sûr.")
    for key, (title, description, exclusive, names) in PREFERENCES.items():
        data = categories.setdefault(key, {"title": title, "description": description, "roles": []})
        matching = {r.id for r in roles if r.name in names}
        missing = sum(not any(r.name == name for r in roles) for name in names)
        if len(set(data["roles"]) | matching) + missing > 25:
            raise DomainError("Une rubrique est limitée à 25 rôles.")
        for name in names:
            role = next((r for r in roles if r.name == name), None)
            if role is None:
                role = await guild.create_role(
                    name=name,
                    permissions=discord.Permissions.none(),
                    colour=discord.Colour.default(),
                    hoist=False,
                    mentionable=False,
                    reason="Moka : préférences facultatives du Comptoir",
                )
                roles.append(role)
            if role >= bot_member.top_role:
                raise DomainError("Place Moka au-dessus des rôles de préférences.")
            menu[str(role.id)] = key if exclusive else ""
            if role.id not in data["roles"]:
                if len(data["roles"]) >= 25:
                    raise DomainError("Une rubrique est limitée à 25 rôles.")
                data["roles"].append(role.id)
        service.set_setting(guild.id, "role_menu", menu)
        service.set_setting(guild.id, "role_categories", categories)
    return categories


def category_key(title):
    plain = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    key = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")
    if not key or len(key) > 32:
        raise DomainError("Choisis un nom court pour cette rubrique.")
    return key


def category_menu(service, guild, category=None):
    menu = service.get_setting(guild, "role_menu", {})
    categories = service.get_setting(guild, "role_categories", {})
    if category is not None:
        if category not in categories:
            raise DomainError("Cette rubrique a changé. Rouvre le choix des rôles.")
        ids = {str(rid) for rid in categories[category]["roles"]}
        menu = {rid: group for rid, group in menu.items() if rid in ids}
    elif categories:
        raise DomainError("Le menu a changé. Choisis maintenant une rubrique.")
    if len(menu) > 25:
        raise DomainError("Cette rubrique dépasse 25 choix.")
    return menu


def validate_choices(service, guild, category, selected):
    if not service.is_enabled(guild, "roles"):
        raise DomainError("Les rôles à choisir sont désactivés.")
    menu = category_menu(service, guild, category)
    if not selected <= menu.keys():
        raise DomainError("Le menu a changé. Rouvre le choix des rôles.")
    groups = [menu[key] for key in selected if menu[key]]
    if len(groups) != len(set(groups)):
        raise DomainError("Choisis un seul rôle dans chaque groupe exclusif.")
    return menu


def require_own_panel(interaction):
    context(interaction)
    if (
        not interaction.message
        or not interaction.client.user
        or interaction.message.author.id != interaction.client.user.id
    ):
        raise DomainError("Ce panneau n'appartient pas à Moka.")


async def apply_public_choice(interaction, category, selected):
    require_own_panel(interaction)
    await interaction.response.defer(ephemeral=True, thinking=True)
    names = await interaction.client.get_cog("CommunityCog").apply_role_preferences(
        interaction, category, selected
    )
    text = (
        "Tes choix pour cette rubrique : **" + ", ".join(names) + "**."
        if names
        else "Tes choix pour cette rubrique sont retirés."
    )
    try:
        # Nouvelle référence : Discord abandonne ses cases cochées locales.
        # Le panneau reste commun, sans pré-cocher les rôles d'une personne.
        await interaction.message.edit(
            view=RoleCategoryView(category, interaction.guild, interaction.client.service)
        )
    except (discord.HTTPException, DomainError):
        log.warning("Liste de préférences non rafraîchie après une attribution réussie")
        text += "\nTes rôles sont à jour, mais la liste n'a pas pu être rafraîchie. Rouvre le salon pour l'actualiser."
    await interaction.followup.send(embed=card("☕ Tes préférences", text), ephemeral=True)


class CategoryRoleSelect(
    discord.ui.DynamicItem[discord.ui.Select],
    template=r"moka:roles:select:(?P<category>[a-z0-9-]{1,32})(?::[0-9a-f]{12})?",
):
    def __init__(
        self, category, options, maximum, placeholder="Choisir mes rôles", *, custom_id=None
    ):
        self.category = category
        super().__init__(
            discord.ui.Select(
                custom_id=custom_id or f"moka:roles:select:{category}:{uuid4().hex[:12]}",
                placeholder=placeholder,
                min_values=0,
                max_values=maximum,
                options=options,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(
            match["category"],
            item.options,
            item.max_values,
            item.placeholder,
            custom_id=item.custom_id,
        )

    async def callback(self, interaction):
        try:
            selected = set(self.item.values)
            if CLEAR_ROLE_VALUE in selected:
                if selected != {CLEAR_ROLE_VALUE} or not any(
                    option.value == CLEAR_ROLE_VALUE for option in self.item.options
                ):
                    raise DomainError("Choisis un rôle ou Aucun choix, pas les deux.")
                selected = set()
            await apply_public_choice(interaction, self.category, selected)
        except Exception as error:
            await handle_error(interaction, error)


class CategoryClearButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"moka:roles:clear:(?P<category>[a-z0-9-]{1,32})",
):
    def __init__(self, category):
        self.category = category
        super().__init__(
            discord.ui.Button(
                label="Tout retirer",
                style=discord.ButtonStyle.secondary,
                custom_id="moka:roles:clear:" + category,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["category"])

    async def callback(self, interaction):
        try:
            await apply_public_choice(interaction, self.category, set())
        except Exception as error:
            await handle_error(interaction, error)


class CategoryPicker(discord.ui.Select):
    def __init__(self, owner, categories):
        self.owner = owner
        super().__init__(
            placeholder="Quelle rubrique souhaites-tu personnaliser ?",
            options=[
                discord.SelectOption(label=data["title"][:100], value=key)
                for key, data in categories.items()
                if data["roles"]
            ],
        )

    async def callback(self, interaction):
        _, user, _ = context(interaction)
        if user != self.owner:
            raise DomainError("Ce menu appartient à un autre membre.")
        await interaction.client.get_cog("CommunityCog").choose_roles(interaction, self.values[0])


class CategoryRoleButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"moka:roles:category:(?P<category>[a-z0-9-]{1,32})",
):
    """Compatibilité des anciens panneaux déjà publiés, conservée après redémarrage."""

    def __init__(self, category):
        self.category = category
        super().__init__(
            discord.ui.Button(
                label="Personnaliser mes rôles",
                emoji="☕",
                style=discord.ButtonStyle.primary,
                custom_id="moka:roles:category:" + category,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["category"])

    async def callback(self, interaction):
        try:
            context(interaction)
            if (
                not interaction.message
                or not interaction.client.user
                or interaction.message.author.id != interaction.client.user.id
            ):
                raise DomainError("Ce panneau n'appartient pas à Moka.")
            await interaction.client.get_cog("CommunityCog").choose_roles(
                interaction, self.category
            )
        except Exception as error:
            await handle_error(interaction, error)


class RoleCategoryView(SafeView):
    def __init__(self, category, guild, service):
        super().__init__(timeout=None)
        menu = category_menu(service, guild.id, category)
        roles = [guild.get_role(int(rid)) for rid in menu]
        options = [
            discord.SelectOption(label=role.name[:100], value=str(role.id))
            for role in roles
            if role
        ]
        if not options:
            raise DomainError("Aucun rôle disponible dans cette rubrique.")
        exclusive = len(set(menu.values())) == 1 and all(menu.values())
        placeholders = {
            "genre": "Mes pronoms…",
            "presence": "Mon rythme de présence…",
            "signe": "Mon signe…",
            "mp": "Mes préférences de MP…",
            "entraide": "Mon envie d'aider…",
            "region": "Mon coin du monde…",
            "interets": "Mes centres d'intérêt…",
            "notifications": "Mes notifications…",
        }
        maximum = 1 if exclusive else len(options)
        inline_clear = maximum == 1 and len(options) < 25
        if inline_clear:
            options.append(
                discord.SelectOption(
                    label="Aucun choix",
                    value=CLEAR_ROLE_VALUE,
                    description="Retirer le rôle de cette rubrique.",
                )
            )
        self.add_item(
            CategoryRoleSelect(
                category,
                options,
                maximum,
                placeholders.get(category, "Choisir mes rôles…"),
            )
        )
        # À 25 options, conserver un retrait accessible sans dépasser la limite Discord.
        if maximum > 1 or not inline_clear:
            self.add_item(CategoryClearButton(category))


def category_embed(data):
    embed = card(
        data["title"],
        data["description"]
        + "\n\n**Choix facultatifs.** Sélectionne toutes tes préférences pour cette rubrique dans la liste ci-dessous. "
        "Ta sélection remplace les choix de cette rubrique. La liste se remet à zéro après validation. "
        "La confirmation privée et ton profil indiquent tes rôles actifs.",
    )
    embed.set_footer(text="Moka · Installe-toi comme tu aimes")
    return embed


async def publish_categories(channel, service):
    guild = channel.guild.id
    service.allowed(guild)
    if not service.is_enabled(guild, "roles"):
        raise DomainError("Le module de rôles est désactivé.")
    categories = service.get_setting(guild, "role_categories", {})
    if not categories or len(categories) > 25:
        raise DomainError("Configure entre une et 25 rubriques avant de publier le panneau.")
    for key in categories:
        category_menu(service, guild, key)
    setting = "role_panels:" + str(channel.id)
    messages = service.get_setting(guild, setting, {})
    for key, data in categories.items():
        options = {
            "embed": category_embed(data),
            "view": RoleCategoryView(key, channel.guild, service),
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if key in messages:
            try:
                await channel.get_partial_message(messages[key]).edit(**options)
                continue
            except discord.NotFound:
                pass
        message = await channel.send(**options)
        messages[key] = message.id
        service.set_setting(guild, setting, messages)
    return len(categories)
