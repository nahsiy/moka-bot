from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from moka.base import DomainError
from moka.discord_ui import ForgetView, HackView, card, context, event_embed, human
from moka.economy import CATALOG


class MembersCog(commands.Cog):
    xp = app_commands.Group(name="xp", description="Progression et classement")
    argent = app_commands.Group(name="argent", description="Ton économie en cœurs")
    banque = app_commands.Group(name="banque", description="Dépôts, retraits et améliorations")

    def __init__(self, bot):
        self.bot, self.service = bot, bot.service

    async def show_profile(self, interaction, member=None):
        guild, user, _ = context(interaction)
        target = member or interaction.user
        profile = self.service.profile(guild, human(target), viewer=user)
        embed = card(
            f"☕ Profil de {target.display_name}",
            f"Niveau **{profile['level']}** · **{profile['xp']:,}/{profile['next_xp']:,} XP**",
        )
        embed.add_field(name="Portefeuille", value=f"{profile['wallet']:,} ❤️")
        embed.add_field(name="Banque", value=f"{profile['bank']:,}/{profile['capacity']:,} ❤️")
        embed.add_field(
            name="Participation comptabilisée",
            value=f"{profile['messages']} messages · {profile['voice_minutes']} minutes vocales",
            inline=False,
        )
        embed.set_footer(text="Monnaie fictive · /confidentialite pour masquer ton profil")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="Ton profil, tes niveaux et tes cœurs")
    async def profile(self, interaction: discord.Interaction, membre: discord.Member | None = None):
        await self.show_profile(interaction, membre)

    @xp.command(name="consulter", description="Consulter ta progression ou celle d'un membre")
    async def xp_show(self, interaction: discord.Interaction, membre: discord.Member | None = None):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "xp"):
            raise DomainError("Le module XP est désactivé.")
        await self.show_profile(interaction, membre)

    async def ranking(self, interaction, category):
        guild, _, _ = context(interaction)
        entries = self.service.leaderboard(guild, category)
        lines = [
            f"**{index}.** <@{row['user']}> — **{row['score']:,}** {'XP' if category == 'xp' else '❤️'}"
            for index, row in enumerate(entries, 1)
        ]
        await interaction.response.send_message(
            embed=card(
                "🏆 Classement",
                "\n".join(lines) or "Le classement attend ses premiers participants.",
            )
        )

    @xp.command(name="classement", description="Les dix premières progressions publiques")
    async def xp_ranking(self, interaction: discord.Interaction):
        await self.ranking(interaction, "xp")

    @argent.command(name="consulter", description="Consulter ton portefeuille et ta banque")
    async def money_show(self, interaction: discord.Interaction):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "economy"):
            raise DomainError("L'économie est désactivée.")
        await self.show_profile(interaction)

    @argent.command(name="classement", description="Classement public des cœurs, banque comprise")
    async def money_ranking(self, interaction: discord.Interaction):
        await self.ranking(interaction, "money")

    @argent.command(name="journalier", description="Récupérer ta récompense toutes les 24 heures")
    async def daily(self, interaction: discord.Interaction):
        guild, user, key = context(interaction)
        result = self.service.claim(guild, user, key)
        await interaction.response.send_message(
            f"Ton café du jour : **+{result['amount']} ❤️**.", ephemeral=True
        )

    @argent.command(name="hebdomadaire", description="Récupérer ta récompense tous les sept jours")
    async def weekly(self, interaction: discord.Interaction):
        guild, user, key = context(interaction)
        result = self.service.claim(guild, user, key, "weekly")
        await interaction.response.send_message(
            f"Récompense de la semaine : **+{result['amount']} ❤️**.", ephemeral=True
        )

    @banque.command(name="deposer", description="Déposer des cœurs dans ta banque")
    async def deposit(
        self, interaction: discord.Interaction, montant: app_commands.Range[int, 1, 1_000_000_000]
    ):
        guild, user, key = context(interaction)
        self.service.bank_move(guild, user, montant, key)
        await interaction.response.send_message(f"**{montant:,} ❤️** déposés.", ephemeral=True)

    @banque.command(name="retirer", description="Retirer des cœurs de ta banque")
    async def withdraw(
        self, interaction: discord.Interaction, montant: app_commands.Range[int, 1, 1_000_000_000]
    ):
        guild, user, key = context(interaction)
        self.service.bank_move(guild, user, montant, key, deposit=False)
        await interaction.response.send_message(f"**{montant:,} ❤️** retirés.", ephemeral=True)

    @banque.command(
        name="ameliorer", description="Augmenter la capacité, les intérêts ou la protection"
    )
    async def upgrade(
        self,
        interaction: discord.Interaction,
        amelioration: Literal["capacity", "interest", "protection"],
    ):
        guild, user, key = context(interaction)
        result = self.service.bank_upgrade(guild, user, key, amelioration)
        await interaction.response.send_message(
            f"Amélioration **{amelioration}**, palier **{result['tier']}** : **{result['cost']} ❤️** dépensés.",
            ephemeral=True,
        )

    @banque.command(name="interets", description="Récupérer les intérêts journaliers de ta banque")
    async def interest(self, interaction: discord.Interaction):
        guild, user, key = context(interaction)
        result = self.service.interest(guild, user, key)
        await interaction.response.send_message(
            f"Intérêts : **+{result['amount']} ❤️** ({result['rate_bps'] / 100:g} %).",
            ephemeral=True,
        )

    @app_commands.command(name="donner", description="Offrir des cœurs à un membre")
    async def give_money(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        montant: app_commands.Range[int, 1, 1_000_000_000],
    ):
        guild, user, key = context(interaction)
        self.service.transfer(guild, user, human(membre), montant, key)
        await interaction.response.send_message(
            f"Tu offres **{montant:,} ❤️** à {membre.display_name}.", ephemeral=True
        )

    @app_commands.command(
        name="parier", description="Miser des cœurs fictifs : 45 % de chance de doubler la mise"
    )
    async def bet(
        self, interaction: discord.Interaction, montant: app_commands.Range[int, 1, 1_000_000_000]
    ):
        guild, user, key = context(interaction)
        result = self.service.bet(guild, user, montant, key)
        text = f"Mise : **{montant:,} ❤️**.\n" + (
            f"Gagné ! Retour : **{result['payout']:,} ❤️** (gain net : {result['net']:,})."
            if result["win"]
            else "Cette fois, la mise est perdue."
        )
        await interaction.response.send_message(embed=card("🎲 Un petit pari", text))

    @app_commands.command(
        name="jackpot", description="Voir la cagnotte et participer au tirage actif"
    )
    async def jackpot(self, interaction: discord.Interaction):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "jackpot"):
            raise DomainError("Le jackpot est désactivé.")
        active = [
            e
            for e in self.service.active_events()
            if e["guild"] == guild and e["kind"] == "jackpot"
        ]
        text = f"Cagnotte : **{self.service.pot(guild):,} ❤️**."
        if active and active[0]["message"]:
            text += f"\n[Participer au tirage](https://discord.com/channels/{guild}/{active[0]['channel']}/{active[0]['message']})"
        else:
            text += "\nLe staff peut ouvrir un tirage avec /animation lancer."
        await interaction.response.send_message(embed=card("🎟️ Jackpot", text), ephemeral=True)

    @app_commands.command(
        name="voler", description="Tenter un vol fictif : une amende est possible"
    )
    async def rob(self, interaction: discord.Interaction, membre: discord.Member | None = None):
        guild, user, key = context(interaction)
        if membre is None:
            candidates = [
                m
                for m in interaction.guild.members
                if not m.bot
                and m.id != user
                and self.service.profile(guild, m.id, viewer=m.id)["wallet"]
                >= self.bot.config.rules.robbery_min_wallet
            ]
            if not candidates:
                raise DomainError("Aucune cible éligible dans les membres disponibles.")
            membre = self.service.rng.choice(candidates)
        result = self.service.rob(guild, user, human(membre), key)
        text = (
            f"Vol réussi sur **{membre.display_name}** : **+{result['amount']} ❤️**."
            if result["win"]
            else f"La police virtuelle t'a repéré : **{result['amount']} ❤️** d'amende."
        )
        await interaction.response.send_message(embed=card("🧤 Petites combines", text))

    @app_commands.command(name="hack", description="Ouvrir un mini-jeu de piratage fictif")
    async def hack(
        self,
        interaction: discord.Interaction,
        difficulte: Literal["easy", "normal", "hard"] = "normal",
        preparation: bool = False,
    ):
        guild, user, key = context(interaction)
        result = self.service.start_event(
            guild,
            interaction.channel_id,
            user,
            "hack",
            key,
            difficulty=difficulte,
            prepared=preparation,
        )
        event = self.service.get_event(guild, result["event_id"])
        if result["replayed"] and event["message"]:
            await interaction.response.send_message(
                "Cette opération a déjà été ouverte.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=event_embed(event, self.service), view=HackView()
        )
        message = await interaction.original_response()
        self.service.bind_event(guild, event["id"], message.id)

    @app_commands.command(
        name="boutique", description="Les petits objets disponibles en cœurs, sans gemmes"
    )
    async def shop(self, interaction: discord.Interaction):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "shop"):
            raise DomainError("La boutique est désactivée.")
        text = "\n".join(
            f"**{item['name']}** · {item['price']} ❤️ · identifiant `{key}`"
            for key, item in CATALOG.items()
        )
        await interaction.response.send_message(
            embed=card(
                "🛍️ La petite boutique",
                text
                + "\n\n/acheter pour commander, /offrir pour faire un cadeau.\nObjets décoratifs, sans effet sur les probabilités.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="acheter", description="Acheter un objet de la boutique")
    async def buy(
        self, interaction: discord.Interaction, article: Literal["cafe", "biscuit", "trophee"]
    ):
        guild, user, key = context(interaction)
        result = self.service.buy(guild, user, article, key)
        await interaction.response.send_message(
            f"**{result['name']}** ajouté à ton inventaire pour **{result['price']} ❤️**.",
            ephemeral=True,
        )

    @app_commands.command(name="inventaire", description="Voir tes objets de la boutique")
    async def inventory(self, interaction: discord.Interaction):
        guild, user, _ = context(interaction)
        rows = self.service.inventory(guild, user)
        text = "\n".join(
            f"{CATALOG.get(row['item'], {}).get('name', row['item'])} × **{row['quantity']}**"
            for row in rows
        )
        await interaction.response.send_message(
            embed=card("🎒 Ton inventaire", text or "Ton sac est encore vide."), ephemeral=True
        )

    @app_commands.command(name="offrir", description="Offrir un objet de ton inventaire")
    async def give_item(
        self,
        interaction: discord.Interaction,
        membre: discord.Member,
        article: Literal["cafe", "biscuit", "trophee"],
    ):
        guild, user, key = context(interaction)
        self.service.give_item(guild, user, human(membre), article, key)
        await interaction.response.send_message(
            f"Tu offres **{CATALOG[article]['name']}** à {membre.display_name}.", ephemeral=True
        )

    async def fun(self, interaction, member, insult):
        guild, user, key = context(interaction)
        target = member or interaction.user
        human(target)
        compliments = [
            "Tu as le talent de rendre une conversation plus agréable.",
            "Tu mérites le dernier biscuit de la boîte.",
            "Ta bonne humeur vaut toutes les réserves de café du QG.",
        ]
        taunts = [
            "Même ton café a demandé cinq minutes de pause.",
            "Tu es la mise à jour qui demande encore un redémarrage.",
            "Ton sens de l'orientation ferait hésiter une boussole.",
        ]

        def run(con):
            self.service.cooldown(con, guild, user, "fun", 15)
            return {"text": self.service.rng.choice(taunts if insult else compliments)}

        result = self.service.perform(guild, user, "fun", key, ["fun"], run)
        await interaction.response.send_message(
            embed=card(
                "🙃 Petite taquinerie" if insult else "🌟 Un compliment",
                f"**{target.display_name}**, {result['text']}",
            )
        )

    @app_commands.command(name="compliment", description="Faire un compliment à un membre")
    async def compliment(
        self, interaction: discord.Interaction, membre: discord.Member | None = None
    ):
        await self.fun(interaction, membre, False)

    @app_commands.command(
        name="insulter", description="Envoyer une taquinerie légère, sans propos haineux"
    )
    async def insult(self, interaction: discord.Interaction, membre: discord.Member | None = None):
        await self.fun(interaction, membre, True)

    @app_commands.command(
        name="horoscope", description="Une petite lecture du jour, pour le divertissement"
    )
    async def horoscope(
        self,
        interaction: discord.Interaction,
        signe: Literal[
            "Bélier",
            "Taureau",
            "Gémeaux",
            "Cancer",
            "Lion",
            "Vierge",
            "Balance",
            "Scorpion",
            "Sagittaire",
            "Capricorne",
            "Verseau",
            "Poissons",
        ],
    ):
        guild, _, _ = context(interaction)
        if not self.service.is_enabled(guild, "horoscope"):
            raise DomainError("L'horoscope est désactivé.")
        today = datetime.now(UTC).date().isoformat()
        seed = hashlib.sha256(f"{today}:{signe}".encode()).digest()
        texts = [
            "Un échange inattendu pourrait égayer ta journée.",
            "Un projet laissé de côté mérite peut-être un nouveau regard.",
            "Une pause et un café peuvent laisser place à une bonne idée.",
            "Un petit geste amical peut faire beaucoup de bien.",
        ]
        embed = card(f"✨ {signe} · {today}", texts[seed[0] % len(texts)])
        for index, name in enumerate(("Ambiance", "Rencontres", "Créativité", "Chance"), 1):
            stars = seed[index] % 5 + 1
            embed.add_field(name=name, value="★" * stars + "☆" * (5 - stars))
        embed.set_footer(text="Texte fictif de divertissement · aucune prédiction scientifique")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="confidentialite", description="Masquer ou rendre public ton profil et tes classements"
    )
    async def privacy(self, interaction: discord.Interaction, prive: bool):
        guild, user, _ = context(interaction)
        self.service.set_privacy(guild, user, prive)
        await interaction.response.send_message(
            "Ton profil est privé."
            if prive
            else "Ton profil peut apparaître dans les classements.",
            ephemeral=True,
        )

    @app_commands.command(
        name="mes_donnees", description="Exporter les données locales de ton compte"
    )
    async def export_data(self, interaction: discord.Interaction):
        guild, user, _ = context(interaction)
        await interaction.response.defer(ephemeral=True)
        content = json.dumps(
            self.service.export_user(guild, user), ensure_ascii=False, indent=2
        ).encode()
        await interaction.followup.send(
            file=discord.File(io.BytesIO(content), filename="mes-donnees-moka.json"), ephemeral=True
        )

    @app_commands.command(
        name="oublier", description="Demander l'effacement de tes données locales"
    )
    async def forget(self, interaction: discord.Interaction):
        _, user, _ = context(interaction)
        await interaction.response.send_message(
            "L'effacement retire ton XP, tes cœurs et ton inventaire. Il est définitif dans la base active. Les sauvegardes suivent leur durée de conservation. Confirmer ?",
            view=ForgetView(user),
            ephemeral=True,
        )

    @app_commands.command(name="aide", description="Les commandes et modules disponibles")
    async def help(self, interaction: discord.Interaction):
        guild, _, _ = context(interaction)
        enabled = sorted(
            name for name in self.bot.config.features if self.service.is_enabled(guild, name)
        )
        text = (
            "**Progression** : /profile · /xp consulter · /xp classement\n**Économie** : /argent · /banque · /donner\n**Distractions** : /parier · /voler · /hack · /jackpot\n**Objets** : /boutique · /acheter · /inventaire · /offrir\n**Ambiance** : /compliment · /insulter · /horoscope\n**Communauté** : /ticket · /roles · /vocal\n**Données** : /confidentialite · /mes_donnees · /oublier\n**Staff** : /config · /animation · /moderation · /diagnostic\n\nModules activés : "
            + ", ".join(enabled)
        )
        await interaction.response.send_message(
            embed=card("☕ Bienvenue chez Moka", text), ephemeral=True
        )
