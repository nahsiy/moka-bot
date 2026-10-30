"""Navigation privée du profil, achats explicites et collection décorative."""

import math

import discord

from moka.base import DomainError
from moka.collection import BADGES, TITLES
from moka.discord_ui import card, context
from moka.economy import CATALOG
from moka.profile_cards import number
from moka.profile_controls import ProfilePanel, owner_context
from moka.profile_ui import update_profile

PAGES = {
    "profile": ("Mon profil", "☕"),
    "history": ("Mes mouvements de cœurs", "🧾"),
    "shop": ("La petite boutique", "🛍️"),
    "inventory": ("Mon inventaire", "🎒"),
    "badges": ("Mes badges", "🏅"),
    "titles": ("Mes titres", "🎀"),
    "guide": ("Comment ça marche ?", "💡"),
}
REASONS = {
    "daily": "Récompense quotidienne",
    "weekly": "Récompense hebdomadaire",
    "message": "Discussion",
    "voice": "Vocal",
    "level": "Passage de niveau",
    "deposit": "Dépôt en banque",
    "withdraw": "Retrait de la banque",
    "bank-upgrade": "Agrandissement de banque",
    "interest": "Intérêts",
    "gift-out": "Cœurs offerts",
    "gift-in": "Cœurs reçus",
    "robbery-loss": "Petite combine · perte",
    "robbery-gain": "Petite combine · gain",
    "robbery-fine": "Petite combine · amende",
    "counting": "Palier du counting",
    "counting-bonus": "Surprise du counting",
    "counting-fine": "Erreur au counting",
    "staff-adjustment": "Ajustement du staff",
    "bet-stake": "Mise",
    "bet-prize": "Gain du pari",
}


class HubSelect(discord.ui.Select):
    def __init__(self, service, guild, page="profile"):
        keys = [
            k
            for k in PAGES
            if k not in {"badges", "titles"} or service.is_enabled(guild, "collection")
        ]
        keys = [
            k for k in keys if k not in {"shop", "inventory"} or service.is_enabled(guild, "shop")
        ]
        super().__init__(
            placeholder="Explorer mon profil",
            row=2,
            options=[
                discord.SelectOption(
                    label=PAGES[k][0], emoji=PAGES[k][1], value=k, default=k == page
                )
                for k in keys
            ],
        )

    async def callback(self, interaction):
        view = self.view
        owner_context(interaction, view.guild_id, view.owner)
        await interaction.response.defer()
        await show_hub(interaction, self.values[0])
        view.stop()


class RewardButton(discord.ui.Button):
    def __init__(self, period, wait, amount):
        label = "Quotidienne" if period == "daily" else "Hebdomadaire"
        suffix = (
            (
                f"dans {math.ceil(wait / 60)} min"
                if wait < 3600
                else f"dans {math.ceil(wait / 3600)} h"
            )
            if wait
            else f"+{number(amount)} ❤️"
        )
        super().__init__(
            label=f"{label} · {suffix}",
            emoji="🎁",
            row=3,
            disabled=bool(wait),
            style=discord.ButtonStyle.secondary,
        )
        self.period = period

    async def callback(self, interaction):
        guild, user, key = owner_context(interaction, self.view.guild_id, self.view.owner)
        await interaction.response.defer()
        result = interaction.client.service.claim(guild, user, "profile-claim:" + key, self.period)
        await update_profile(
            interaction,
            interaction.user,
            status=f"✅ Récompense reçue : {number(result['amount'])} ❤️.",
        )
        self.view.stop()


class PurchaseSelect(discord.ui.Select):
    def __init__(self, service, guild, owned):
        options = [
            discord.SelectOption(
                label=f"{v['name']} · {v['price']} ❤️",
                value="object:" + k,
                description="Objet à conserver ou à offrir",
            )
            for k, v in CATALOG.items()
        ]
        if service.is_enabled(guild, "collection"):
            options += [
                discord.SelectOption(
                    label=f"{v['name']} · {v['price']} ❤️",
                    value="title:" + k,
                    description="Titre décoratif pour ton profil",
                )
                for k, v in TITLES.items()
                if k not in owned
            ]
        super().__init__(placeholder="Choisir un objet ou un titre", options=options, row=1)

    async def callback(self, interaction):
        owner_context(interaction, self.view.guild_id, self.view.owner)
        self.view.selection = self.values[0]
        kind, key = self.values[0].split(":", 1)
        item = (TITLES if kind == "title" else CATALOG)[key]
        self.view.purchase.label = f"Acheter · {item['price']} ❤️"
        self.view.purchase.disabled = False
        for opt in self.options:
            opt.default = opt.value == self.values[0]
        await interaction.response.edit_message(view=self.view)


class TitleSelect(discord.ui.Select):
    def __init__(self, owned, current):
        options = [discord.SelectOption(label="Aucun titre", value="none", default=current is None)]
        options += [
            discord.SelectOption(label=v["name"], value=k, default=k == current)
            for k, v in TITLES.items()
            if k in owned
        ]
        super().__init__(
            placeholder="Choisir le titre affiché sur mon profil", options=options, row=1
        )

    async def callback(self, interaction):
        guild, user, key = owner_context(interaction, self.view.guild_id, self.view.owner)
        title = None if self.values[0] == "none" else self.values[0]
        await interaction.response.defer()
        interaction.client.service.equip_title(guild, user, title, "profile-title:" + key)
        await show_hub(
            interaction,
            "titles",
            status="✅ Titre retiré." if title is None else "✅ Titre affiché sur ton profil.",
        )
        self.view.stop()


class HubView(ProfilePanel):
    def __init__(self, service, guild, owner, page, *, more=False, index=0, owned=(), current=None):
        super().__init__(guild, owner)
        self.page, self.index = page, index
        self.selection = None
        navigation = HubSelect(service, guild, page)
        navigation.row = 0
        self.add_item(navigation)
        self.previous.disabled = index == 0
        self.next_page.disabled = not more
        if page != "history":
            self.remove_item(self.previous)
            self.remove_item(self.next_page)
        if page == "shop":
            self.add_item(PurchaseSelect(service, guild, owned))
        else:
            self.remove_item(self.purchase)
        if page == "titles":
            self.add_item(TitleSelect(owned, current))

    @discord.ui.button(label="Retour au profil", emoji="☕", row=4)
    async def back(self, interaction, button):
        owner_context(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        await update_profile(interaction, interaction.user)
        self.stop()

    @discord.ui.button(
        label="Choisis un article",
        emoji="🛍️",
        disabled=True,
        style=discord.ButtonStyle.primary,
        row=3,
    )
    async def purchase(self, interaction, button):
        guild, user, key = owner_context(interaction, self.guild_id, self.owner)
        if not self.selection:
            return
        kind, item = self.selection.split(":", 1)
        await interaction.response.defer()
        service = interaction.client.service
        result = (
            service.buy_title(guild, user, item, "hub-buy:" + key)
            if kind == "title"
            else service.buy(guild, user, item, "hub-buy:" + key)
        )
        await show_hub(
            interaction, "shop", status=f"✅ {result['name']} acheté pour {result['price']} ❤️."
        )
        self.stop()

    @discord.ui.button(label="Page précédente", row=3)
    async def previous(self, interaction, button):
        owner_context(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        await show_hub(interaction, "history", index=max(0, self.index - 1))
        self.stop()

    @discord.ui.button(label="Page suivante", row=3)
    async def next_page(self, interaction, button):
        owner_context(interaction, self.guild_id, self.owner)
        await interaction.response.defer()
        await show_hub(interaction, "history", index=self.index + 1)
        self.stop()


async def show_hub(interaction, page, *, index=0, status=None):
    guild, user, _ = context(interaction)
    service = interaction.client.service
    if page in {"shop", "inventory"} and not service.is_enabled(guild, "shop"):
        raise DomainError("La boutique est désactivée sur ce serveur.")
    if page in {"badges", "titles"} and not service.is_enabled(guild, "collection"):
        raise DomainError("Les badges et titres sont désactivés sur ce serveur.")
    if page == "profile":
        return await update_profile(interaction, interaction.user, status=status)
    owned, current, more = (), None, False
    title, emoji = PAGES[page]
    embed = card(f"{emoji} {title}")
    if page == "history":
        history = service.heart_history(guild, user, index)
        more = history["more"]
        lines = []
        for row in history["rows"]:
            reason = row["reason"]
            label = REASONS.get(
                reason,
                "Achat en boutique"
                if reason.startswith(("shop:", "title:"))
                else "Animation"
                if reason in {"goblin", "hug", "jackpot", "hack"}
                else "Autre mouvement",
            )
            deltas = " · ".join(
                f"{name} **{row[col]:+d}**"
                for name, col in [("Portefeuille", "wallet_delta"), ("Banque", "bank_delta")]
                if row[col]
            )
            lines.append(f"<t:{int(row['created'])}:d> · {label}\n{deltas} ❤️")
        embed.description = (
            "\n\n".join(lines)
            or "Aucun mouvement pour le moment. Les cœurs gagnés et dépensés apparaîtront ici."
        )
    elif page in {"badges", "titles", "shop"}:
        collection = (
            service.collection(guild, user)
            if service.is_enabled(guild, "collection")
            else {"owned": [], "title": None}
        )
        owned = {r["item"] for r in collection["owned"] if r["kind"] == "title"}
        current = collection["title"]
        if page == "badges":
            badges = {r["item"] for r in collection["owned"] if r["kind"] == "badge"}
            embed.description = f"**{len(badges)}/{len(BADGES)} souvenirs recueillis** · À ton rythme, sans série quotidienne obligatoire.\nLes badges restent acquis. Ils ne donnent aucun privilège."
            for key, b in BADGES.items():
                embed.add_field(
                    name=f"{'✅' if key in badges else b['emoji']} {b['name']}",
                    value=b["description"] + f"\n{collection['progress'][key]}/{b['goal']}",
                    inline=False,
                )
        elif page == "titles":
            embed.description = (
                "Choisis ton titre ci-dessous. Le changement est gratuit et visible sur ta carte de profil."
                if owned
                else "Tu n’as pas encore de titre. La petite boutique en propose, contre des cœurs fictifs."
            ) + "\nLes titres sont décoratifs, sans rôle ni permission Discord."
        else:
            balance = service.profile(guild, user, viewer=user)["wallet"]
            embed.description = (
                f"**Ton portefeuille : {number(balance)} ❤️**\nChoisis un article, puis clique sur **Acheter**. Un achat prélève tes cœurs fictifs.\n\n**Objets à offrir**\n"
                + "\n".join(f"{v['name']} · **{v['price']} ❤️**" for v in CATALOG.values())
            )
            if service.is_enabled(guild, "collection"):
                embed.description += "\n\n**Titres pour ton profil**\n" + "\n".join(
                    f"{v['name']} · **{'déjà acquis' if k in owned else str(v['price']) + ' ❤️'}**"
                    for k, v in TITLES.items()
                )
    elif page == "inventory":
        rows = service.inventory(guild, user)
        embed.description = (
            "\n".join(
                f"{CATALOG.get(r['item'], {}).get('name', 'Objet')} × **{r['quantity']}**"
                for r in rows
            )
            or "Ton sac est encore vide. Découvre les petits cadeaux dans la boutique."
        )
        embed.description += "\n\n`/offrir` permet de faire un cadeau à un membre. Le cadeau est annoncé publiquement ; tes achats restent privés."
    else:
        rules = service.rules_for(guild)
        embed.description = f"**Discuter**\nUn message peut rapporter {rules.message_xp} XP et {rules.message_coins} ❤️, au plus une fois toutes les {rules.message_cooldown} secondes.\n\n**Passer en vocal**\nUne minute éligible rapporte {rules.voice_xp} XP et {rules.voice_coins} ❤️. Il faut au moins deux humains actifs, hors AFK, sans sourdine ni écoute passive du Juke-box.\n\n**Garder des cœurs**\nLe portefeuille sert aux achats et aux jeux. La banque protège tes dépôts des petites combines ; tu peux l’agrandir depuis Mon profil.\n\n**Revenir quand tu veux**\nLa quotidienne se réclame toutes les 24 h, l’hebdomadaire tous les 7 jours. Il n’y a pas de série à conserver.\n\n**Choisir ce que tu montres**\n`/confidentialite` masque ton profil et te retire des classements. `/mes_donnees` exporte tes données ; `/oublier` demande leur effacement."
    if status:
        embed.add_field(name="Dernière action", value=status, inline=False)
    embed.set_footer(
        text="Moka · Réponse privée" + (f" · Page {index + 1}" if page == "history" else "")
    )
    view = HubView(service, guild, user, page, more=more, index=index, owned=owned, current=current)
    view.message = await interaction.edit_original_response(
        content=None,
        attachments=[],
        embeds=[embed],
        view=view,
        allowed_mentions=discord.AllowedMentions.none(),
    )
