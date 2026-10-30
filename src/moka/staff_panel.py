"""Le tableau du Barista : panneau privé, réglages compréhensibles et atomiques."""

import contextlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import discord

from moka.base import DomainError
from moka.config import FEATURES
from moka.discord_ui import SafeView, card, context, handle_error

FEATURE_LABELS = {
    "xp": "XP et niveaux",
    "economy": "Cœurs et récompenses",
    "bank": "Banque",
    "bet": "Paris",
    "jackpot": "Jackpot",
    "robbery": "Petites combines",
    "hack": "Opération virtuelle",
    "goblin": "Tournée de Moka",
    "hug": "Câlin collectif",
    "counting": "Compte les grains",
    "words": "Association de mots",
    "fun": "Compliments et taquineries",
    "rates": "Taux et duos",
    "horoscope": "Horoscope",
    "shop": "Boutique et cadeaux",
    "roles": "Rôles à choisir",
    "tickets": "Coup de main",
    "temporary_voice": "Vocaux temporaires",
    "trombi": "Trombinoscope",
    "moderation": "Modération",
    "collection": "Badges et titres",
    "music": "Le Juke-box",
}


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    unit: str = "cœurs"
    divisor: int = 1

    def display(self, value):
        return (
            format((Decimal(value) / self.divisor).normalize(), "f")
            if self.divisor != 1
            else str(value)
        )

    def parse(self, value):
        try:
            amount = (
                Decimal(value.replace(" ", "").replace("\u202f", "").replace(",", "."))
                * self.divisor
            )
            if (
                not amount.is_finite()
                or amount != amount.to_integral_value()
                or amount < 0
                or amount > 1_000_000_000
            ):
                raise ValueError
            return int(amount)
        except (InvalidOperation, ValueError) as error:
            raise DomainError(f"{self.label} : indique un nombre positif ou nul valide.") from error


GROUPS = {
    "economie": (
        "Cœurs et banque",
        [
            Field("daily_coins", "Récompense quotidienne"),
            Field("weekly_coins", "Récompense hebdomadaire"),
            Field("level_coins", "Cœurs par niveau"),
            Field("bank_capacity", "Capacité de base de la banque"),
            Field("bank_upgrade_cost", "Prix de base d’un agrandissement"),
        ],
    ),
    "xp": (
        "XP et participation",
        [
            Field("message_xp", "XP par message", "XP"),
            Field("message_coins", "Cœurs par message"),
            Field("message_cooldown", "Délai entre deux messages", "secondes"),
            Field("voice_xp", "XP par minute de vocal", "XP"),
            Field("voice_coins", "Cœurs par minute de vocal"),
        ],
    ),
    "counting": (
        "Compte les grains",
        [
            Field("counting_reward_every", "Nombres entre deux paliers", "nombres"),
            Field("counting_reward", "Cœurs par palier"),
            Field("counting_fine", "Amende maximale"),
            Field("counting_failure_seconds", "Pause après une erreur", "minutes", 60),
            Field("counting_cheat_seconds", "Corvée après une modification", "minutes", 60),
        ],
    ),
    "surprises": (
        "Surprises du counting",
        [
            Field("counting_bonus_chance_bps", "Chance d’une surprise", "%", 100),
            Field("counting_bonus_min", "Gain minimum"),
            Field("counting_bonus_max", "Gain maximum"),
        ],
    ),
    "mots": (
        "Association de mots",
        [Field("words_cooldown", "Délai entre deux propositions", "secondes")],
    ),
    "vol": (
        "Petites combines",
        [
            Field("robbery_cooldown", "Délai entre deux tentatives", "minutes", 60),
            Field("robbery_min_wallet", "Minimum dans chaque portefeuille"),
            Field("robbery_max_loot", "Butin maximum"),
            Field("robbery_protection_seconds", "Protection après un vol", "minutes", 60),
        ],
    ),
    "tournee": (
        "Tournée de Moka",
        [
            Field("goblin_seconds", "Durée des inscriptions", "secondes"),
            Field("goblin_min_players", "Participants minimum", "personnes"),
            Field("goblin_max_players", "Participants maximum", "personnes"),
            Field("goblin_reward", "Cœurs par personne"),
            Field("goblin_interval_minutes", "Apparition automatique · 0 = arrêt", "minutes"),
        ],
    ),
    "calin": (
        "Câlin collectif",
        [
            Field("hug_seconds", "Durée des inscriptions", "secondes"),
            Field("hug_max_players", "Participants maximum", "personnes"),
            Field("hug_reward", "Base par personne et participant"),
        ],
    ),
    "jackpot": (
        "Jackpot",
        [
            Field("jackpot_ticket_cost", "Prix d’un ticket"),
            Field("jackpot_seconds", "Durée des inscriptions", "secondes"),
        ],
    ),
    "interets": (
        "Intérêts de la banque",
        [
            Field("bank_interest_bps", "Taux initial", "%", 100),
            Field("bank_interest_max_bps", "Taux maximum", "%", 100),
        ],
    ),
    "photos": ("Trombinoscope", [Field("trombi_min_level", "Niveau minimum", "niveaux")]),
}


EXTRA_SECTIONS = {
    "spaces": "Salons et rôles",
    "welcome": "Accueil et pauses",
    "fun": "Petites attentions",
    "music": "Le Juke-box",
}


def feature_label(key):
    return FEATURE_LABELS.get(key, key)


async def authorize(interaction, guild_id, owner):
    guild, user, _ = context(interaction)
    if guild != guild_id or user != owner:
        raise DomainError("Ce panneau appartient à une autre personne. Ouvre /barista.")
    member = await interaction.guild.fetch_member(user)
    if not member.guild_permissions.manage_guild:
        raise DomainError("La permission Gérer le serveur est nécessaire pour ce panneau.")
    return guild, user


def panel_embed(service, guild, section, status=None):
    if section == "modules":
        text = "Choisis les fonctions proposées aux membres, puis **Enregistrer les modules**.\nLes animations déjà engagées seront réglées jusqu’au bout.\nLes accès d’accueil et les permissions du staff restent gérés séparément."
        embed = card("☕ Le tableau du Barista · Modules", text)
    elif section in GROUPS:
        title, fields = GROUPS[section]
        rules = service.rules_for(guild)
        embed = card(
            "☕ Le tableau du Barista · " + title,
            "Les valeurs s’appliquent aux prochaines actions. **Modifier les réglages** ouvre un formulaire prérempli.",
        )
        for field in fields:
            embed.add_field(
                name=field.label,
                value=f"**{field.display(getattr(rules, field.key))}** {field.unit}",
                inline=False,
            )
        if section == "economie":
            embed.description += "\nLes récompenses restent espacées de 24 heures et de 7 jours."
        if section == "calin":
            embed.description += "\nChacun reçoit la base × le nombre de participants."
        if section == "mots":
            embed.description += (
                "\nMode actuel : **"
                + (
                    "association d’idées"
                    if service.get_setting(guild, "words:mode", service.config.word_mode) == "free"
                    else "dernière lettre"
                )
                + "**."
            )
    elif section == "spaces":
        from moka.config import CHANNELS

        labels = {
            "counting": "Compte les grains",
            "words": "Association de mots",
            "goblin": "Animations",
            "logs": "Journal staff",
            "tickets": "Coup de main",
            "ticket_category": "Catégorie des tickets",
            "voice_creator": "Création des vocaux",
            "voice_category": "Catégorie des vocaux",
            "announcements": "Annonces",
            "trombi": "Trombinoscope",
            "trombi_review": "Validation des photos",
            "music_text": "Commandes musicales",
            "music_voice": "Écoute musicale",
        }
        lines = []
        for key in sorted(CHANNELS):
            cid = service.get_setting(guild, "channel:" + key, service.config.channels.get(key))
            lines.append(f"**{labels.get(key, key)}** : {f'<#{cid}>' if cid else 'non configuré'}")
        embed = card("☕ Le tableau du Barista · Salons et rôles", "\n".join(lines))
        embed.add_field(
            name="Changer un salon",
            value="`/config salon` · Choisis l’usage puis le salon dans les menus Discord.",
            inline=False,
        )
        embed.add_field(
            name="Rôles des jeux et des photos",
            value="`/config role` associe le rôle Café renversé ou la corvée. Choisis un rôle dédié, sans permission.",
            inline=False,
        )
        embed.add_field(
            name="Rôles au choix et progression",
            value="`/roles` pour les préférences et les niveaux ; `/config` pour leurs réglages. Aucun rôle de staff n’est attribué par la boutique.",
            inline=False,
        )
    elif section == "welcome":
        enabled = service.admission_enabled(guild)
        embed = card(
            "☕ Le tableau du Barista · Accueil et pauses",
            f"**Accueil : {'activé' if enabled else 'désactivé'}**\nUn premier café privé, charte séparée, entretien à l’écrit ou en vocal, puis validation par le staff.\n\n`/accueil` gère les arrivées. `/activite` consulte les pauses sans lire le contenu des échanges. `/debloquer` lève une pause des jeux ou une corvée.\n\nLes permissions d’accès restent distinctes des fonctions de divertissement.",
        )
    elif section == "fun":
        embed = card(
            "☕ Le tableau du Barista · Petites attentions",
            "**Compliments et taquineries bienveillantes**\n50 phrases originales par catégorie ; les 5 dernières sont évitées. Une action toutes les 15 secondes par personne.\n\n**Trois éditions illustrées**\nLa petite attention : 60 % · La perle du Comptoir : 30 % · La pépite de Moka : 10 %.\n\nLes éditions changent le texte et l’habillage, sans gain ni avantage. Si quelqu’un dit stop, on s’arrête.",
        )
    elif section == "music":
        text = service.get_setting(guild, "channel:music_text")
        voice = service.get_setting(guild, "channel:music_voice")
        embed = card(
            "☕ Le tableau du Barista · Le Juke-box",
            f"**Commandes et lecteur :** {f'<#{text}>' if text else 'à installer'}\n**Écoute :** {f'<#{voice}>' if voice else 'à installer'}\n\nUne file partagée ; titre ou lien YouTube ; 5 morceaux en attente par personne, 50 au total.\nPas de messages libres, pas de micros ni d’XP d’écoute. Les accès d’accueil sont conservés.\n\n`/config jukebox` crée ou vérifie les deux salons. `/jukebox arreter` arrête la lecture et vide la file.\nLa file reste en mémoire : après un redémarrage, chacun choisit de nouveaux morceaux.",
        )
    else:
        state = service.staff_overview(guild)
        active = sum(service.is_enabled(guild, key) for key in FEATURES)
        embed = card(
            "☕ Le tableau du Barista",
            "Tout pour régler la vie du Comptoir, au même endroit.\nChoisis une rubrique dans le menu ci-dessous.",
        )
        embed.add_field(name="Fonctions proposées", value=f"**{active}/{len(FEATURES)}** actives")
        embed.add_field(name="Profils enregistrés", value=str(state["members"]))
        embed.add_field(
            name="Cœurs en circulation", value=f"{state['circulation']:,} ❤️".replace(",", "\u202f")
        )
        embed.add_field(name="Animations en cours", value=str(state["events"]))
        embed.add_field(name="Accueils en attente", value=str(state["admissions"]))
        embed.add_field(name="Pauses des jeux", value=str(state["penalties"]))
    if status:
        embed.add_field(name="Dernière action", value=status, inline=False)
    embed.set_footer(
        text="Moka · Réservé au staff · Le panneau se ferme après 5 minutes sans action"
    )
    return embed


class RulesModal(discord.ui.Modal):
    def __init__(self, view, rules, revision):
        title, fields = GROUPS[view.section]
        super().__init__(title=title, timeout=180)
        self.panel, self.revision = view, revision
        self.inputs = []
        for field in fields:
            item = discord.ui.TextInput(
                label=f"{field.label} ({field.unit})"[:45],
                default=field.display(getattr(rules, field.key)),
                min_length=1,
                max_length=20,
            )
            self.add_item(item)
            self.inputs.append((field, item))

    async def on_error(self, interaction, error):
        await handle_error(interaction, error)

    async def on_submit(self, interaction):
        guild, _ = await authorize(interaction, self.panel.guild_id, self.panel.owner)
        if self.panel.is_finished():
            raise DomainError("Ce panneau a été fermé. Ouvre /barista pour recommencer.")
        changes = {field.key: field.parse(item.value) for field, item in self.inputs}
        await interaction.response.defer()
        interaction.client.service.update_rules(guild, changes, revision=self.revision)
        await interaction.client.audit(
            interaction.guild,
            "Réglages du panneau Barista modifiés : "
            + ", ".join(changes)
            + f" par {interaction.user.id}.",
        )
        await render_panel(
            interaction, self.panel.section, status="✅ Réglages enregistrés.", previous=self.panel
        )


class SectionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Vue d’ensemble", value="home", emoji="☕"),
            discord.SelectOption(label="Fonctions actives", value="modules", emoji="🎛️"),
        ]
        options.extend(
            discord.SelectOption(label=title, value=key) for key, (title, _) in GROUPS.items()
        )
        options.extend(
            discord.SelectOption(label=title, value=key) for key, title in EXTRA_SECTIONS.items()
        )
        super().__init__(placeholder="Que souhaites-tu régler ?", options=options, row=0)

    async def callback(self, interaction):
        view = self.view
        await authorize(interaction, view.guild_id, view.owner)
        await interaction.response.defer()
        await render_panel(interaction, self.values[0], previous=view)


class ModulesSelect(discord.ui.Select):
    def __init__(self, selected):
        options = [
            discord.SelectOption(label=feature_label(key), value=key, default=key in selected)
            for key in sorted(FEATURES)
        ]
        super().__init__(
            placeholder="Choisir les fonctions actives",
            options=options,
            min_values=0,
            max_values=len(options),
            row=1,
        )

    async def callback(self, interaction):
        view = self.view
        await authorize(interaction, view.guild_id, view.owner)
        await interaction.response.defer()
        await render_panel(
            interaction,
            "modules",
            pending=set(self.values),
            expected=view.expected_modules,
            status="Sélection préparée. Clique sur Enregistrer les modules pour l’appliquer.",
            previous=view,
        )


class StaffPanel(SafeView):
    def __init__(self, service, guild, owner, section="home", pending=None, expected=None):
        super().__init__(timeout=300)
        self.guild_id, self.owner, self.section = guild, owner, section
        self.expected_modules = (
            {key for key in FEATURES if service.is_enabled(guild, key)}
            if expected is None
            else set(expected)
        )
        self.pending_modules = self.expected_modules if pending is None else set(pending)
        self.message = None
        self.add_item(SectionSelect())
        if section == "modules":
            self.add_item(ModulesSelect(self.pending_modules))
            self.remove_item(self.edit_rules)
        else:
            self.remove_item(self.save_modules)
            if section not in GROUPS:
                self.remove_item(self.edit_rules)

    async def interaction_check(self, interaction):
        await authorize(interaction, self.guild_id, self.owner)
        return True

    async def on_timeout(self):
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)

    @discord.ui.button(
        label="Modifier les réglages", emoji="✏️", style=discord.ButtonStyle.primary, row=2
    )
    async def edit_rules(self, interaction, button):
        guild, _ = await authorize(interaction, self.guild_id, self.owner)
        rules, revision = interaction.client.service.rules_snapshot(guild)
        await interaction.response.send_modal(RulesModal(self, rules, revision))

    @discord.ui.button(
        label="Enregistrer les modules", emoji="💾", style=discord.ButtonStyle.success, row=2
    )
    async def save_modules(self, interaction, button):
        guild, _ = await authorize(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        interaction.client.service.update_modules(
            guild, self.pending_modules, expected=self.expected_modules
        )
        await interaction.client.audit(
            interaction.guild, f"Modules du panneau Barista enregistrés par {interaction.user.id}."
        )
        await render_panel(
            interaction, "modules", status="✅ Fonctions enregistrées.", previous=self
        )

    @discord.ui.button(label="Actualiser", emoji="🔄", row=2)
    async def refresh(self, interaction, button):
        await authorize(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        await render_panel(interaction, self.section, previous=self)

    @discord.ui.button(label="Fermer", row=2)
    async def close_panel(self, interaction, button):
        await authorize(interaction, self.guild_id, self.owner)
        self.stop()
        await interaction.response.edit_message(
            embed=card(
                "☕ Le tableau du Barista", "Panneau fermé. `/barista` permet de le rouvrir."
            ),
            view=None,
        )


async def render_panel(
    interaction, section="home", *, status=None, pending=None, expected=None, previous=None
):
    guild, user = context(interaction)[:2]
    await authorize(interaction, guild, user)
    view = StaffPanel(interaction.client.service, guild, user, section, pending, expected)
    if previous:
        previous.stop()
    view.message = await interaction.edit_original_response(
        embed=panel_embed(interaction.client.service, guild, section, status),
        attachments=[],
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )
