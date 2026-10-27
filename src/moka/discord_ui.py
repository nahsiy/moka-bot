from __future__ import annotations

import logging

import discord
from discord import app_commands

from moka.base import DomainError

log = logging.getLogger(__name__)
COLOR = 0xBC8053


def card(title, text=""):
    return discord.Embed(title=title, description=text, color=COLOR)


def context(interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        raise DomainError("Cette commande s'utilise dans un serveur autorisé.")
    interaction.client.service.allowed(interaction.guild.id)
    return interaction.guild.id, interaction.user.id, str(interaction.id)


def human(member):
    if member.bot:
        raise DomainError("Choisis une personne, pas une application.")
    return member.id


async def notify(interaction, text, *, private=True):
    if interaction.response.is_done():
        return await interaction.followup.send(text, ephemeral=private)
    return await interaction.response.send_message(text, ephemeral=private)


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
        await notify(interaction, text)
    except discord.HTTPException:
        log.warning("Réponse à l'interaction %s impossible", interaction.id)


class SafeView(discord.ui.View):
    async def on_error(self, interaction, error, item):
        await handle_error(interaction, error)


def event_embed(event, service):
    kind, result, data = event["kind"], event["result"], event["payload"]
    names = {
        "goblin": "👺 Le gobelin du serveur",
        "jackpot": "🎟️ Jackpot",
        "hack": "💻 Opération virtuelle",
    }
    embed = card(names[kind])
    if result:
        if kind == "goblin":
            embed.description = f"{result['count']} participants. " + (
                f"Victoire ! **{result['reward']} ❤️ chacun.**"
                if result["reward"]
                else "Le gobelin s'est échappé : pas assez de participants."
            )
            if result.get("capped"):
                embed.description += "\nCertains gains sont limités par le plafond du compte."
        elif kind == "jackpot":
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
    elif kind == "goblin":
        embed.description = f"Rejoignez le groupe avant <t:{int(event['deadline'])}:R>.\n**{len(event['participants'])}/{data['maximum']}** participants · minimum **{data['minimum']}**.\nButin : **{data['reward']} ❤️** par personne en cas de victoire."
    elif kind == "jackpot":
        embed.description = f"Un ticket par personne : **{service.config.rules.jackpot_ticket_cost} ❤️**.\nTirage <t:{int(event['deadline'])}:R> · **{len(event['participants'])}** participants.\nCagnotte : **{service.pot(event['guild']):,} ❤️**.\nMonnaie virtuelle uniquement."
    else:
        embed.description = f"Opération de <@{event['owner']}> · difficulté **{data['difficulty']}**.\nPréparation : **{'oui' if data['prepared'] else 'non'}**.\nTente l'intrusion ou abandonne avant <t:{int(event['deadline'])}:R>.\nC'est un jeu : aucun système extérieur n'est contacté."
    embed.set_footer(text="Moka · " + event["id"])
    return embed


def interaction_event(interaction):
    guild, _, _ = context(interaction)
    message = interaction.message
    bot = interaction.client
    if not message or not bot.user or message.author.id != bot.user.id or not message.embeds:
        raise DomainError("Ce message n'est pas un événement de Moka.")
    footer = message.embeds[0].footer.text or ""
    if not footer.startswith("Moka · "):
        raise DomainError("Référence d'événement manquante.")
    event = bot.service.get_event(guild, footer.removeprefix("Moka · "))
    if event["channel"] != message.channel.id or event["message"] not in {None, message.id}:
        raise DomainError("Le message ne correspond pas à cet événement.")
    if event["message"] is None:
        bot.service.bind_event(guild, event["id"], message.id)
    return event


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
        guild, user, key = context(interaction)
        await interaction.response.defer(ephemeral=True)
        event = interaction_event(interaction)
        interaction.client.service.join_event(guild, user, event["id"], key)
        await interaction.followup.send("Ta participation est enregistrée.", ephemeral=True)
        # Une file par événement empêche une édition plus ancienne d'écraser
        # un compteur plus récent ; les sommes restent garanties par SQLite.
        async with interaction.client.event_lock(event["id"]):
            fresh = interaction.client.service.get_event(guild, event["id"])
            await interaction.message.edit(
                embed=event_embed(fresh, interaction.client.service),
                view=None if fresh["result"] else JoinView(),
            )


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
        guild, user, _ = context(interaction)
        if user != self.owner:
            raise DomainError("Cette confirmation appartient à un autre membre.")
        interaction.client.service.forget_user(guild, user)
        await interaction.response.edit_message(
            content="Tes données locales ont été effacées. Les sauvegardes existantes suivent leur durée de conservation.",
            view=None,
        )
        self.stop()
