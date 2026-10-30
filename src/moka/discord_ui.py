from __future__ import annotations

import asyncio
import io
import logging

import discord
from discord import app_commands

from moka.base import DomainError
from moka.coffee_round_cards import render_round_card, round_description, round_state

log = logging.getLogger(__name__)
COLOR = 0xBC8053


def card(title, text=""):
    return discord.Embed(title=title, description=text, color=COLOR)


def context(interaction, *, allow_pending=False):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        raise DomainError("Cette commande s'utilise dans un serveur autorisé.")
    interaction.client.service.allowed(interaction.guild.id)
    if not allow_pending:
        from moka.admission_discord import require_access

        require_access(interaction.client.service, interaction.user, interaction.guild)
    return interaction.guild.id, interaction.user.id, str(interaction.id)


def human(member):
    if member.bot:
        raise DomainError("Choisis une personne, pas une application.")
    return member.id


async def notify(interaction, text, *, private=True, title="☕ Moka"):
    if interaction.response.is_done():
        return await interaction.followup.send(embed=card(title, text), ephemeral=private)
    return await interaction.response.send_message(embed=card(title, text), ephemeral=private)


async def handle_error(interaction, error):
    original = getattr(error, "original", error)
    if isinstance(original, DomainError):
        text = str(original)
    elif isinstance(
        original, (app_commands.MissingPermissions, app_commands.BotMissingPermissions)
    ):
        text = "Il manque une permission pour cette action. Consulte /diagnostic."
    elif isinstance(original, app_commands.CommandOnCooldown):
        text = f"Patience : réessaie dans {original.retry_after:.0f} secondes."
    elif isinstance(original, discord.Forbidden):
        text = "Discord refuse cette action. Vérifie mes permissions et la hiérarchie des rôles."
    else:
        log.error(
            "Échec interaction %s : %s",
            interaction.id,
            type(original).__name__,
            exc_info=(type(original), original, original.__traceback__),
        )
        text = "L'action n'a pas pu aboutir. Consulte les logs avec cette référence : " + str(
            interaction.id
        )
    try:
        await notify(interaction, text, title="⚠️ Action impossible")
    except discord.HTTPException:
        log.warning("Réponse à l'interaction %s impossible", interaction.id)


class SafeView(discord.ui.View):
    async def on_error(self, interaction, error, item):
        await handle_error(interaction, error)


def event_embed(event, service):
    kind, result, data = event["kind"], event["result"], event["payload"]
    names = {
        "goblin": "☕ La tournée de Moka",
        "hug": "🤗 Câlin collectif",
        "jackpot": "🎟️ Jackpot",
        "hack": "💻 Opération virtuelle",
    }
    embed = card(names[kind])
    if kind == "hug":
        state = round_state(event, service.clock())
        embed.title = "🤗 " + state["title"]
        embed.description = round_description(event, service.clock())
        embed.set_footer(text="Moka · De la douceur, si tu en as envie")
        return embed
    if kind == "goblin":
        state = round_state(event, service.clock())
        embed.title = "☕ " + state["title"]
        if result is None:
            embed.description = (
                f"Une petite pause ensemble ? Réserve ta tasse avant <t:{int(event['deadline'])}:R>.\n"
                f"**{state['count']}/{state['maximum']}** inscrits · objectif **{state['minimum']}**.\n"
                f"**{state['reward']} ❤️** par personne si le groupe est réuni."
            )
        else:
            embed.description = round_description(event, service.clock())
        embed.set_footer(text="Moka · Un café ensemble")
        return embed
    if result:
        if kind == "jackpot":
            embed.description = (
                f"🏆 <@{result['winner']}> remporte **{result['reward']:,} ❤️** !"
                if "winner" in result
                else "Personne n'a participé. La cagnotte est conservée."
            )
            if result.get("carried"):
                embed.description += (
                    f"\nPlafond atteint : {result['carried']:,} ❤️ restent dans la cagnotte."
                )
        else:
            embed.description = (
                "Opération abandonnée."
                if result.get("abandoned")
                else (
                    f"Accès obtenu : **+{result['reward']} ❤️**."
                    if result["win"]
                    else f"Échec : **{result['fine']} ❤️** d'amende fictive."
                )
            )
    elif kind == "jackpot":
        cost = event["payload"].get("ticket_cost")
        if cost is None:
            cost = service.rules_for(event["guild"]).jackpot_ticket_cost
        embed.description = f"Un ticket par personne : **{cost} ❤️**.\nTirage <t:{int(event['deadline'])}:R> · **{len(event['participants'])}** participants.\nCagnotte : **{service.pot(event['guild']):,} ❤️**.\nMonnaie virtuelle uniquement."
    else:
        embed.description = f"Opération de <@{event['owner']}> · difficulté **{data['difficulty']}**.\nPréparation : **{'oui' if data['prepared'] else 'non'}**.\nTente l'intrusion ou abandonne avant <t:{int(event['deadline'])}:R>.\nC'est un jeu : aucun système extérieur n'est contacté."
    embed.set_footer(text="Moka · " + event["id"])
    return embed


def interaction_event(interaction, event_id=None):
    guild, _, _ = context(interaction)
    message = interaction.message
    bot = interaction.client
    if not message or not bot.user or message.author.id != bot.user.id:
        raise DomainError("Ce message n'est pas un événement de Moka.")
    if event_id is None:
        if not message.embeds:
            raise DomainError("Référence d'événement manquante.")
        footer = message.embeds[0].footer.text or ""
        if not footer.startswith("Moka · "):
            raise DomainError("Référence d'événement manquante.")
        event_id = footer.removeprefix("Moka · ")
    event = bot.service.get_event(guild, event_id)
    if event["channel"] != message.channel.id or event["message"] not in {None, message.id}:
        raise DomainError("Le message ne correspond pas à cet événement.")
    if event["message"] is None:
        bot.service.bind_event(guild, event["id"], message.id)
    return event


async def event_message(event, service, *, editing=False):
    """Même présentation au lancement, à l'inscription et après redémarrage."""
    view = (
        None
        if event["result"] is not None
        else HugView(event["id"])
        if event["kind"] == "hug"
        else CoffeeRoundView(event["id"])
        if event["kind"] == "goblin"
        else HackView()
        if event["kind"] == "hack"
        else JoinView()
    )
    options = {"view": view, "allowed_mentions": discord.AllowedMentions.none()}
    if event["kind"] in {"goblin", "hug"}:
        try:
            image = await asyncio.to_thread(render_round_card, event, service.clock())
            file = discord.File(
                io.BytesIO(image),
                filename="moka-calin.png" if event["kind"] == "hug" else "moka-tournee.png",
                description=round_description(event, service.clock()),
            )
            if editing:
                options.update(content=None, embeds=[], attachments=[file])
            else:
                options["file"] = file
            return options
        except (OSError, ValueError):
            log.exception("Carte de tournée indisponible ; repli texte avec bouton conservé")
    embed = event_embed(event, service)
    if editing:
        options.update(content=None, attachments=[], embeds=[embed])
    else:
        options["embed"] = embed
    return options


async def register_participation(interaction, event):
    guild, user, key = context(interaction)
    await interaction.response.defer(ephemeral=True)
    interaction.client.service.join_event(guild, user, event["id"], key)
    coffee = event["kind"] == "goblin"
    hug = event["kind"] == "hug"
    await interaction.followup.send(
        embed=card(
            "🤗 Une place dans le câlin"
            if hug
            else "☕ Ta tasse est réservée"
            if coffee
            else "🙋 Participation enregistrée",
            "C’est noté ! Moka te garde une place dans le cercle."
            if hug
            else "Installe-toi, Moka prépare la tournée !"
            if coffee
            else "Ta participation est enregistrée.",
        ),
        ephemeral=True,
    )
    async with interaction.client.event_lock(event["id"]):
        fresh = interaction.client.service.get_event(guild, event["id"])
        await interaction.message.edit(
            **await event_message(fresh, interaction.client.service, editing=True)
        )


class HugJoin(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"moka:hug:join:(?P<event_id>[0-9a-f]{32})",
):
    def __init__(self, event_id):
        self.event_id = event_id
        super().__init__(
            discord.ui.Button(
                label="Je rejoins le câlin",
                emoji="🤗",
                style=discord.ButtonStyle.success,
                custom_id="moka:hug:join:" + event_id,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["event_id"])

    async def callback(self, interaction):
        try:
            event = interaction_event(interaction, self.event_id)
            if event["kind"] != "hug":
                raise DomainError("Ce bouton ne correspond pas à un câlin collectif.")
            await register_participation(interaction, event)
        except Exception as error:
            await handle_error(interaction, error)


class HugView(SafeView):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        self.add_item(HugJoin(event_id))


class CoffeeJoin(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"moka:tournee:join:(?P<event_id>[0-9a-f]{32})",
):
    def __init__(self, event_id):
        self.event_id = event_id
        super().__init__(
            discord.ui.Button(
                label="Je prends un café",
                emoji="☕",
                style=discord.ButtonStyle.primary,
                custom_id="moka:tournee:join:" + event_id,
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["event_id"])

    async def callback(self, interaction):
        try:
            event = interaction_event(interaction, self.event_id)
            if event["kind"] != "goblin":
                raise DomainError("Ce bouton ne correspond pas à une tournée.")
            await register_participation(interaction, event)
        except Exception as error:
            await handle_error(interaction, error)


class CoffeeRoundView(SafeView):
    def __init__(self, event_id):
        super().__init__(timeout=None)
        self.add_item(CoffeeJoin(event_id))


class JoinView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Participer",
        emoji="🙋",
        style=discord.ButtonStyle.primary,
        custom_id="moka:event:join",
    )
    async def join(self, interaction, button):
        event = interaction_event(interaction)
        await register_participation(interaction, event)


class HackView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    async def finish(self, interaction, abandon):
        guild, user, key = context(interaction)
        event = interaction_event(interaction)
        interaction.client.service.finish_hack(guild, user, event["id"], key, abandon=abandon)
        fresh = interaction.client.service.get_event(guild, event["id"])
        await interaction.response.edit_message(
            embed=event_embed(fresh, interaction.client.service), view=None
        )
        interaction.client.service.event_notified(guild, event["id"])

    @discord.ui.button(
        label="Tenter l'intrusion", style=discord.ButtonStyle.primary, custom_id="moka:hack:attempt"
    )
    async def attempt(self, interaction, button):
        await self.finish(interaction, False)

    @discord.ui.button(
        label="Abandonner", style=discord.ButtonStyle.secondary, custom_id="moka:hack:abandon"
    )
    async def abandon(self, interaction, button):
        await self.finish(interaction, True)


class ForgetView(SafeView):
    def __init__(self, owner):
        super().__init__(timeout=60)
        self.owner = owner

    @discord.ui.button(label="Confirmer l'effacement", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        guild, user, _ = context(interaction, allow_pending=True)
        if user != self.owner:
            raise DomainError("Cette confirmation appartient à un autre membre.")
        interaction.client.service.forget_user(guild, user)
        await interaction.response.edit_message(
            content=None,
            embed=card(
                "🗑️ Données effacées",
                "Tes données de jeu ont été effacées. L’état d’accueil nécessaire aux accès est conservé tant que tu es membre. Les sauvegardes existantes suivent leur durée de conservation.",
            ),
            view=None,
        )
        self.stop()
