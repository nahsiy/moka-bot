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
from moka.discord_ui import HackView, JoinView, event_embed, handle_error
from moka.service import Service
from moka.store import Store

log = logging.getLogger(__name__)


class Tree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        if not interaction.guild_id:
            raise DomainError("Moka s'utilise dans un serveur autorisé.")
        self.client.service.allowed(interaction.guild_id)
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
        self.last_voice_tick = None
        self.voice_eligible = set()

    def event_lock(self, event_id):
        return self._event_locks.setdefault(event_id, asyncio.Lock())

    async def setup_hook(self):
        from moka.cogs.community import CommunityCog
        from moka.cogs.members import MembersCog
        from moka.cogs.staff import StaffCog

        self.store.initialize()
        await self.add_cog(MembersCog(self))
        await self.add_cog(StaffCog(self))
        await self.add_cog(CommunityCog(self))
        self.add_view(JoinView())
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
                await channel.send(text[:1900], allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                log.warning("Journal Discord inaccessible pour le serveur %s", guild.id)

    async def level_roles(self, member, result):
        if not self.service.is_enabled(member.guild.id, "roles"):
            return
        if result.get("level", 0) == result.get("previous_level", 0):
            return
        rewards = self.service.get_setting(member.guild.id, "level_rewards", {})
        community = self.get_cog("CommunityCog")
        for threshold, role_id in rewards.items():
            if int(threshold) <= result["level"]:
                role = member.guild.get_role(role_id)
                if role and role not in member.roles:
                    community.safe_role(member.guild, role)
                    await member.add_roles(role, reason="Moka : récompense de niveau")

    async def on_message(self, message):
        if (
            not message.guild
            or message.guild.id not in self.config.guild_ids
            or message.author.bot
            or message.webhook_id
        ):
            return
        guild = message.guild.id
        try:
            activity_result = None
            if message.content.strip() and self.service.is_enabled(guild, "xp"):
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
                if not result.get("ignored") and not result.get("replayed"):
                    await message.add_reaction("✅" if result["valid"] else "❌")
                    if not result["valid"]:
                        await message.reply(
                            f"Oups ! On attendait **{result['expected']}**, avec un autre membre que le précédent. On repart à **1**.",
                            mention_author=False,
                        )
                    elif result["reward"]:
                        await message.reply(
                            f"Palier atteint : **+{result['reward']} ❤️** !", mention_author=False
                        )
            if message.channel.id == self.channel_id(guild, "words") and self.service.is_enabled(
                guild, "words"
            ):
                try:
                    result = self.service.word(
                        guild, message.channel.id, message.author.id, message.content, message.id
                    )
                    if not result.get("ignored") and not result.get("replayed"):
                        await message.add_reaction("✅")
                except DomainError as error:
                    await message.reply(str(error), mention_author=False, delete_after=15)
            community = self.get_cog("CommunityCog")
            if message.channel.id == self.channel_id(guild, "trombi") and self.service.is_enabled(
                guild, "trombi"
            ):
                await community.submit_photo(message)
            if activity_result:
                await self.level_roles(message.author, activity_result)
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
        community = self.get_cog("CommunityCog")
        for guild in self.guilds:
            if guild.id not in self.config.guild_ids:
                continue
            try:
                await community.reconcile(guild)
                await self.auto_goblin(guild)
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
            message = await channel.send(embed=event_embed(event, self.service))
            self.service.bind_event(guild_id, event_id, message.id)
            return
        message = channel.get_partial_message(event["message"])
        try:
            await message.edit(
                embed=event_embed(event, self.service),
                view=None
                if event["result"]
                else (HackView() if event["kind"] == "hack" else JoinView()),
            )
        except discord.NotFound:
            replacement = await channel.send(embed=event_embed(event, self.service))
            self.service.bind_event(guild_id, event_id, replacement.id)

    async def auto_goblin(self, guild):
        interval = self.config.rules.goblin_interval_minutes * 60
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
        message = await channel.send(embed=event_embed(event, self.service), view=JoinView())
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
        for guild in self.guilds:
            if guild.id not in self.config.guild_ids or not self.service.is_enabled(guild.id, "xp"):
                continue
            for channel in [*guild.voice_channels, *guild.stage_channels]:
                if channel == guild.afk_channel:
                    continue
                eligible = [
                    m
                    for m in channel.members
                    if not m.bot
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
                        result = self.service.activity(
                            guild.id,
                            member.id,
                            f"voice:{int(time.time() // 60)}:{member.id}",
                            "voice",
                        )
                        await self.level_roles(member, result)
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
