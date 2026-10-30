from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import weakref
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from moka.base import DomainError
from moka.discord_ui import (
    CoffeeJoin,
    HackView,
    HugJoin,
    JoinView,
    card,
    event_message,
    handle_error,
)
from moka.role_panels import CategoryClearButton, CategoryRoleButton, CategoryRoleSelect
from moka.service import Service
from moka.store import Store

log = logging.getLogger(__name__)


def counting_failure_text(result):
    reason = {
        "expression": "ici, il faut écrire un nombre ou un calcul valide",
        "not_integer": "le résultat doit être un nombre entier",
        "same_user": "il faut laisser compter un autre membre entre deux essais",
        "number": f"on attendait **{result['expected']}**",
    }[result["reason"]]
    if not result["economy"]:
        fine = "Économie désactivée : aucune amende."
    elif not result["configured_fine"]:
        fine = "Amende désactivée."
    elif result["fine"]:
        fine = f"Amende : **{result['fine']} ❤️**."
        if result["fine"] < result["configured_fine"]:
            fine += " C'est tout le portefeuille !"
    else:
        fine = "Portefeuille vide : aucune amende prélevée."
    coin = (
        "🪙 **Face !** On recommence à **1**."
        if result["restart"]
        else f"🪙 **Pile !** La série continue : prochain nombre **{result['next']}**."
    )
    return f"❌ {reason}. {fine}\n{coin}" + game_penalty_text(result)


def counting_reward_card(result):
    reward, bonus = result.get("reward", 0), result.get("bonus", 0)
    if reward and bonus:
        return card(
            "☕ Palier et grain de chance !",
            f"🏅 Palier : **+{reward} ❤️**\n🍀 Bonus surprise : **+{bonus} ❤️**\n"
            f"**+{reward + bonus} ❤️** ajoutés à ton portefeuille.",
        )
    if bonus:
        return card(
            "🍀 Un grain de chance !",
            f"Moka a glissé une petite surprise dans ta tasse : **+{bonus} ❤️** !",
        )
    if reward:
        return card("🏅 Palier atteint", f"**+{reward} ❤️** ajoutés à ton portefeuille !")
    return None


def game_penalty_text(result, *, spill=True):
    if not result.get("penalty_until"):
        return ""
    if result.get("scope") == "all":
        return (
            "\n🧽 Corvée de vaisselle : pause de tous les jeux jusqu’à "
            f"<t:{int(result['penalty_until'])}:t> (<t:{int(result['penalty_until'])}:R>)."
        )
    intro = "\n☕ Oups, café renversé ! Moka passe un coup d'éponge." if spill else ""
    return intro + (
        f"\nRôle <@&{result['penalty_role']}> · pause dans les deux jeux "
        f"jusqu’à <t:{int(result['penalty_until'])}:t> "
        f"(<t:{int(result['penalty_until'])}:R>)."
    )


class Tree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        if not interaction.guild_id:
            raise DomainError("Moka s'utilise dans un serveur autorisé.")
        self.client.service.allowed(interaction.guild_id)
        from moka.admission_discord import require_access

        if getattr(interaction.command, "qualified_name", "") not in {"mes_donnees", "oublier"}:
            require_access(self.client.service, interaction.user, interaction.guild)
        return True

    async def on_error(self, interaction, error):
        await handle_error(interaction, error)


class MokaBot(commands.Bot):
    def __init__(self, config, service=None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            tree_cls=Tree,
            help_command=None,
            allowed_mentions=discord.AllowedMentions.none(),
            max_messages=100,
        )
        self.config = config
        self.store = service.store if service else Store(config.data_dir / "moka.sqlite3")
        self.service = service or Service(self.store, config)
        self._event_locks = weakref.WeakValueDictionary()
        self._level_role_locks = weakref.WeakValueDictionary()
        self.last_level_role_sync = {}
        self.last_voice_tick = None
        self.voice_eligible = set()

    def event_lock(self, event_id):
        return self._event_locks.setdefault(event_id, asyncio.Lock())

    async def load_cogs(self):
        from moka.cogs.admission import AdmissionCog
        from moka.cogs.community import CommunityCog
        from moka.cogs.members import MembersCog
        from moka.cogs.music import MusicCog
        from moka.cogs.presence import PresenceCog
        from moka.cogs.rates import RatesCog
        from moka.cogs.staff import StaffCog

        await self.add_cog(MembersCog(self))
        await self.add_cog(MusicCog(self))
        await self.add_cog(RatesCog(self))
        await self.add_cog(StaffCog(self))
        await self.add_cog(CommunityCog(self))
        await self.add_cog(AdmissionCog(self))
        await self.add_cog(PresenceCog(self))

    async def setup_hook(self):
        from moka.admission_discord import AdmissionView
        from moka.cogs.music import MusicView

        self.store.initialize()
        await self.load_cogs()
        self.add_view(MusicView())
        self.add_view(AdmissionView())
        self.add_view(JoinView())
        self.add_dynamic_items(
            CoffeeJoin, HugJoin, CategoryRoleButton, CategoryRoleSelect, CategoryClearButton
        )
        self.add_view(HackView())
        from moka.cogs.community import PhotoReviewView, RolePanelView, TicketPanelView

        self.add_view(RolePanelView())
        self.add_view(TicketPanelView())
        self.add_view(PhotoReviewView())
        if self.config.sync_commands:
            for guild_id in self.config.guild_ids:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
        self.maintenance.start()
        self.voice_rewards.start()
        self.backups.start()

    async def on_ready(self):
        log.info("Moka connecté ; %s serveurs autorisés", len(self.config.guild_ids))
        self.last_voice_tick = time.monotonic()
        self.voice_eligible.clear()  # Pas de rattrapage après une déconnexion.
        self.last_level_role_sync.clear()

    async def on_disconnect(self):
        self.last_voice_tick = None
        self.voice_eligible.clear()

    async def on_error(self, event_method, *args, **kwargs):
        log.exception("Échec événement Discord : %s", event_method)

    def channel_id(self, guild, name):
        return self.service.get_setting(guild, "channel:" + name, self.config.channels.get(name))

    def role_id(self, guild, name):
        return self.service.get_setting(guild, "role:" + name, self.config.roles.get(name))

    async def audit(self, guild, text):
        channel = guild.get_channel(self.channel_id(guild.id, "logs") or 0)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(
                    embed=card("📋 Journal Moka", text[:1900]),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                log.warning("Journal Discord inaccessible pour le serveur %s", guild.id)

    async def level_roles(self, member):
        if (
            member.bot
            or not self.service.admitted(member.guild.id, member.id)
            or not self.service.is_enabled(member.guild.id, "roles")
        ):
            return
        rewards = self.service.get_setting(member.guild.id, "level_rewards", {})
        if not rewards:
            return
        key = (member.guild.id, member.id)
        lock = self._level_role_locks.setdefault(key, asyncio.Lock())
        async with lock:
            # Relecture après le verrou : ni ancien message ni cache périmé ne rétrograde un membre.
            member = await member.guild.fetch_member(member.id)
            if not self.service.is_enabled(member.guild.id, "roles"):
                return
            rewards = self.service.get_setting(member.guild.id, "level_rewards", {})
            current = self.service.profile(member.guild.id, member.id, viewer=member.id)["level"]
            roles = {int(n): member.guild.get_role(rid) for n, rid in rewards.items()}
            earned = {n: role for n, role in roles.items() if n <= current and role is not None}
            exclusive = (
                self.service.get_setting(member.guild.id, "level_role_mode", "cumulative")
                == "exclusive"
            )
            desired = {earned[max(earned)]} if exclusive and earned else set(earned.values())
            obsolete = (
                set(member.roles).intersection(roles.values()) - desired if exclusive else set()
            )
            community = self.get_cog("CommunityCog")
            for role in desired | obsolete:
                community.safe_role(member.guild, role)
            # Ajouter avant de retirer : un refus Discord ne supprime pas le palier précédent.
            for role in desired - set(member.roles):
                await member.add_roles(role, reason="Moka : progression au comptoir")
            for role in obsolete:
                await member.remove_roles(role, reason="Moka : remplacement du palier précédent")

    async def reconcile_level_roles(self, guild):
        now = time.monotonic()
        if now - self.last_level_role_sync.get(guild.id, float("-inf")) < 60:
            return
        if not self.service.is_enabled(guild.id, "roles") or not self.service.get_setting(
            guild.id, "level_rewards", {}
        ):
            return
        self.last_level_role_sync[guild.id] = now
        for member in guild.members:
            if member.bot:
                continue
            try:
                await self.level_roles(member)
            except (discord.HTTPException, DomainError):
                log.exception("Rôle de niveau non synchronisé ; nouvel essai dans une minute")

    async def on_member_join(self, member):
        if member.guild.id in self.config.guild_ids and not member.bot:
            try:
                admission = self.get_cog("AdmissionCog")
                if admission:
                    await admission.ensure_member(member)
                await self.level_roles(member)
            except (discord.HTTPException, DomainError):
                log.exception("Premier rôle non attribué ; la maintenance réessaiera")

    async def apply_game_penalty(self, message, result):
        if not result.get("penalty_role"):
            return
        community = self.get_cog("CommunityCog")
        if not community:
            return
        with self.store.read() as con:
            grant = con.execute(
                "SELECT * FROM role_grants WHERE guild=? AND user=? AND role=?",
                (message.guild.id, message.author.id, result["penalty_role"]),
            ).fetchone()
        if grant:
            try:
                await community.apply_role_grant(message.guild, dict(grant), self.service.clock())
            except (DomainError, discord.HTTPException):
                log.exception("Rôle de jeu non attribué ; la maintenance réessaiera")

    async def on_raw_message_edit(self, payload):
        if (
            payload.guild_id not in self.config.guild_ids
            or not isinstance(payload.data.get("content"), str)
            or not payload.data.get("edited_timestamp")
        ):
            return
        author = payload.data.get("author", {}).get("id")
        try:
            result = self.service.inspect_counting_edit(
                payload.guild_id,
                payload.channel_id,
                payload.message_id,
                payload.data["content"],
                author=int(author) if author else None,
            )
            if result:
                await self.notify_counting_edit(result)
        except (discord.HTTPException, DomainError):
            log.exception("Corvée enregistrée ou contrôle à reprendre ; consulter le journal")

    async def notify_counting_edit(self, trace):
        async with self.event_lock(f"counting-edit:{trace['guild']}:{trace['message']}"):
            trace = self.service.counting_validation(
                trace["guild"], trace["channel"], trace["message"]
            )
            if not trace or trace["notified"] or trace["sanction_until"] is None:
                return
            guild = self.get_guild(trace["guild"])
            if not guild:
                raise DomainError("Serveur de comptage inaccessible.")
            community = self.get_cog("CommunityCog")
            with self.store.read() as con:
                grant = con.execute(
                    "SELECT * FROM role_grants WHERE guild=? AND user=? AND role=?",
                    (guild.id, trace["user"], trace["sanction_role"]),
                ).fetchone()
            if grant and community:
                try:
                    await community.apply_role_grant(guild, dict(grant), self.service.clock())
                except (DomainError, discord.HTTPException):
                    log.exception("Corvée persistée ; attribution du rôle à reprendre")
            channel = guild.get_channel(trace["channel"])
            if not isinstance(channel, discord.TextChannel):
                raise DomainError("Salon de comptage inaccessible.")
            next_number = self.service.counting_status(guild.id, channel.id)["next"]
            active = self.service.all_games_penalty(guild.id, trace["user"])
            end = active["penalty_until"] if active else trace["sanction_until"]
            pause = (
                f"Pause de **tous les jeux** jusqu’à <t:{int(end)}:t> (<t:{int(end)}:R>)."
                if active
                else "La corvée a déjà été levée ou est terminée."
            )
            embed = card(
                "🧽 De corvée de vaisselle",
                f"<@{trace['user']}>, le nombre **{trace['number']}** avait été validé, "
                "puis son message a changé de valeur ou est devenu invalide.\n"
                + pause
                + f"\nLa série continue : prochain nombre **{next_number}**.\n"
                "Le staff peut lever la sanction avec `/debloquer`.",
            )
            # Le lien métier sert aussi à retrouver un envoi interrompu avant l'accusé SQLite.
            embed.url = f"https://discord.com/channels/{guild.id}/{channel.id}/{trace['message']}"
            previous_notice = None
            async for old in channel.history(limit=30):
                if old.author.id == self.user.id and any(
                    e.title == embed.title and e.url == embed.url for e in old.embeds
                ):
                    previous_notice = old
                    break
            if previous_notice:
                await previous_notice.edit(
                    embed=embed, allowed_mentions=discord.AllowedMentions.none()
                )
            else:
                await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            self.service.counting_edit_notified(guild.id, trace["message"])

    async def on_message(self, message):
        if (
            not message.guild
            or message.guild.id not in self.config.guild_ids
            or message.author.bot
            or message.webhook_id
        ):
            return
        guild = message.guild.id
        if not self.service.admitted(guild, message.author.id):
            return
        try:
            activity_result = None
            game_channel = message.channel.id in {
                self.channel_id(guild, "counting"),
                self.channel_id(guild, "words"),
            }
            paused = game_channel and self.service.game_penalty(guild, message.author.id)
            if message.content.strip() and not paused and self.service.is_enabled(guild, "xp"):
                # Cooldown normal, sans polluer le salon.
                with contextlib.suppress(DomainError):
                    activity_result = self.service.activity(
                        guild, message.author.id, f"message:{message.id}"
                    )
            if message.channel.id == self.channel_id(guild, "counting") and self.service.is_enabled(
                guild, "counting"
            ):
                result = self.service.counting(
                    guild, message.channel.id, message.author.id, message.content, message.id
                )
                if result.get("blocked"):
                    if not result.get("replayed"):
                        await self.apply_game_penalty(message, result)
                        await message.reply(
                            embed=card(
                                "⏳ Pause des jeux",
                                (
                                    "🧽 Les tasses t’attendent."
                                    if result.get("scope") == "all"
                                    else "☕ Le comptoir sèche encore."
                                )
                                + game_penalty_text(result, spill=False),
                            ),
                            mention_author=False,
                        )
                    return
                if not result.get("ignored") and not result.get("replayed"):
                    await self.apply_game_penalty(message, result)
                    await message.add_reaction("✅" if result["valid"] else "❌")
                    if not result["valid"]:
                        await message.reply(
                            embed=card("🔢 Counting", counting_failure_text(result)),
                            mention_author=False,
                        )
                    elif reward_card := counting_reward_card(result):
                        await message.reply(embed=reward_card, mention_author=False)
            if message.channel.id == self.channel_id(guild, "words") and self.service.is_enabled(
                guild, "words"
            ):
                try:
                    result = self.service.word(
                        guild, message.channel.id, message.author.id, message.content, message.id
                    )
                    if result.get("blocked"):
                        if not result.get("replayed"):
                            await self.apply_game_penalty(message, result)
                            await message.reply(
                                embed=card(
                                    "⏳ Pause des jeux",
                                    (
                                        "🧽 Les tasses t’attendent."
                                        if result.get("scope") == "all"
                                        else "☕ Le comptoir sèche encore."
                                    )
                                    + game_penalty_text(result, spill=False),
                                ),
                                mention_author=False,
                            )
                        return
                    if not result.get("ignored") and not result.get("replayed"):
                        await self.apply_game_penalty(message, result)
                        await message.add_reaction("✅" if result["valid"] else "❌")
                        if not result["valid"]:
                            await message.reply(
                                embed=card(
                                    "🔗 Suite de mots", result["error"] + game_penalty_text(result)
                                ),
                                mention_author=False,
                            )
                except DomainError as error:
                    await message.reply(
                        embed=card("🔗 Suite de mots", str(error)),
                        mention_author=False,
                        delete_after=15,
                    )
            community = self.get_cog("CommunityCog")
            if message.channel.id == self.channel_id(guild, "trombi") and self.service.is_enabled(
                guild, "trombi"
            ):
                await community.submit_photo(message)
            if activity_result:
                await self.level_roles(message.author)
        except discord.HTTPException:
            log.exception("Réponse au message %s impossible", message.id)
        except DomainError:
            pass

    @tasks.loop(seconds=10)
    async def maintenance(self):
        for event in self.service.active_events():
            try:
                if event["deadline"] <= self.service.clock():
                    async with self.event_lock(event["id"]):
                        self.service.settle_event(event["guild"], event["id"])
                elif event["kind"] in {"goblin", "hug"} and event["message"]:
                    # Le compte à rebours illustré suit la boucle de maintenance.
                    async with self.event_lock(event["id"]):
                        await self.refresh_event(event["guild"], event["id"])
            except Exception:
                log.exception("Règlement événement %s impossible", event["id"])
        for event in self.service.pending_event_notifications():
            try:
                async with self.event_lock(event["id"]):
                    await self.refresh_event(event["guild"], event["id"])
                    self.service.event_notified(event["guild"], event["id"])
            except Exception:
                log.exception(
                    "Annonce événement %s impossible ; nouvelle tentative au prochain passage",
                    event["id"],
                )
        for trace in self.service.pending_counting_edits():
            try:
                await self.notify_counting_edit(trace)
            except (discord.HTTPException, DomainError):
                log.exception("Annonce de corvée différée ; nouvel essai au prochain passage")
        community = self.get_cog("CommunityCog")
        for guild in self.guilds:
            if guild.id not in self.config.guild_ids:
                continue
            try:
                await self.get_cog("AdmissionCog").reconcile(guild)
                await community.reconcile(guild)
                await self.reconcile_level_roles(guild)
                await self.auto_goblin(guild)
                await self.get_cog("PresenceCog").reconcile(guild)
            except Exception:
                log.exception("Maintenance serveur %s impossible", guild.id)

    @maintenance.before_loop
    async def before_maintenance(self):
        await self.wait_until_ready()

    async def refresh_event(self, guild_id, event_id):
        event = self.service.get_event(guild_id, event_id)
        channel = self.get_channel(event["channel"])
        if not isinstance(channel, discord.TextChannel):
            raise DomainError("Salon d'événement inaccessible.")
        if not event["message"]:
            message = await channel.send(**await event_message(event, self.service))
            self.service.bind_event(guild_id, event_id, message.id)
            return
        message = channel.get_partial_message(event["message"])
        try:
            await message.edit(
                **await event_message(event, self.service, editing=True),
            )
        except discord.NotFound:
            replacement = await channel.send(**await event_message(event, self.service))
            self.service.bind_event(guild_id, event_id, replacement.id)

    async def auto_goblin(self, guild):
        interval = self.service.rules_for(guild.id).goblin_interval_minutes * 60
        if (
            not interval
            or not self.service.is_enabled(guild.id, "goblin")
            or not self.service.is_enabled(guild.id, "economy")
        ):
            return
        channel = guild.get_channel(self.channel_id(guild.id, "goblin") or 0)
        if not isinstance(channel, discord.TextChannel):
            return
        last = self.service.get_setting(guild.id, "goblin:last_auto", 0)
        if self.service.clock() - last < interval:
            return
        result = self.service.start_event(
            guild.id, channel.id, self.user.id, "goblin", f"auto-goblin:{int(self.service.clock())}"
        )
        self.service.set_setting(guild.id, "goblin:last_auto", self.service.clock())
        event = self.service.get_event(guild.id, result["event_id"])
        message = await channel.send(**await event_message(event, self.service))
        self.service.bind_event(guild.id, event["id"], message.id)

    @tasks.loop(seconds=60)
    async def voice_rewards(self):
        now = time.monotonic()
        previous = self.last_voice_tick
        self.last_voice_tick = now
        current = set()
        if not self.is_ready():
            self.voice_eligible.clear()
            return
        presence = self.get_cog("PresenceCog")
        if presence:
            try:
                await presence.voice_tick(self.guilds)
            except Exception:
                log.exception("Suivi vocal des pauses impossible")
        for guild in self.guilds:
            if guild.id not in self.config.guild_ids or not self.service.is_enabled(guild.id, "xp"):
                continue
            for channel in [*guild.voice_channels, *guild.stage_channels]:
                if channel == guild.afk_channel or channel.id == self.channel_id(
                    guild.id, "music_voice"
                ):
                    continue
                eligible = [
                    m
                    for m in channel.members
                    if not m.bot
                    and self.service.admitted(guild.id, m.id)
                    and m.voice
                    and not (
                        m.voice.self_deaf
                        or m.voice.deaf
                        or m.voice.self_mute
                        or m.voice.mute
                        or m.voice.suppress
                    )
                ]
                if len(eligible) < 2:
                    continue
                for member in eligible:
                    identity = (guild.id, member.id, channel.id)
                    current.add(identity)
                    if (
                        previous is None
                        or not 45 <= now - previous <= 90
                        or identity not in self.voice_eligible
                    ):
                        continue
                    try:
                        self.service.activity(
                            guild.id,
                            member.id,
                            f"voice:{int(time.time() // 60)}:{member.id}",
                            "voice",
                        )
                        await self.level_roles(member)
                    except DomainError:
                        pass
                    except discord.HTTPException:
                        log.exception("Récompense de rôle vocal impossible")
        self.voice_eligible = current

    @voice_rewards.before_loop
    async def before_voice_rewards(self):
        await self.wait_until_ready()

    async def close(self):
        self.maintenance.cancel()
        self.voice_rewards.cancel()
        self.backups.cancel()
        await super().close()

    @tasks.loop(hours=1)
    async def backups(self):
        destination = self.config.data_dir / "backups"
        try:
            self.service.prune_counting_validations()
            existing = list(destination.glob("moka-*.sqlite3")) if destination.exists() else []
            if existing and time.time() - max(p.stat().st_mtime for p in existing) < 86400:
                return
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            await asyncio.to_thread(self.store.backup, destination / f"moka-{stamp}.sqlite3")
            log.info("Sauvegarde locale cohérente créée")
        except Exception:
            log.exception("ÉCHEC de sauvegarde locale ; nouvelle tentative dans une heure")

    @backups.before_loop
    async def before_backups(self):
        await self.wait_until_ready()
