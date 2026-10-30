"""Le Juke-box : file partagée et contrôles autorisés à chaque action."""

import asyncio
import contextlib
import io
import logging
import os
import shutil
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from moka.admin_space import is_moka_admin
from moka.admission_discord import require_access
from moka.base import DomainError
from moka.cogs.staff import staff
from moka.discord_ui import SafeView, card, context, handle_error
from moka.music import Queue, duration_label, resolve_track
from moka.music_cards import render_music_card
from moka.music_setup import prepare_music

log = logging.getLogger(__name__)


class MeasuredOpus(discord.FFmpegOpusAudio):
    """Compteur technique sans audio enregistré ni identité de membre."""

    def __init__(self, *args, **kwargs):
        self.frames = 0
        super().__init__(*args, **kwargs)

    def read(self):
        data = super().read()
        self.frames += bool(data)
        return data


def opus_source(
    source,
    *,
    before_options="-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -protocol_whitelist https,tls,tcp,crypto",
):
    # discord.py attend un fichier, pas la constante entière subprocess.DEVNULL.
    # Popen duplique le descripteur dans le processus enfant avant la fermeture.
    with open(os.devnull, "wb") as quiet:
        return MeasuredOpus(
            source,
            executable=shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg",
            before_options=before_options,
            options="-vn -af volume=0.35",
            stderr=quiet,
        )


class Player:
    def __init__(self, cog, guild):
        self.cog, self.guild = cog, guild
        self.queue = Queue()
        self.lock = asyncio.Lock()
        self.render_lock = asyncio.Lock()
        self.task = None
        self.idle_at = time.monotonic()
        self.status = None
        self.skipping = False

    async def render(self, status=None):
        async with self.render_lock:
            channel = self.guild.get_channel(self.cog.bot.channel_id(self.guild.id, "music_text"))
            if not isinstance(channel, discord.TextChannel):
                return
            if status is not None:
                self.status = status
            data = await asyncio.to_thread(render_music_card, self.queue, status=self.status)
            text = "Le Juke-box. " + ("En pause. " if self.queue.paused else "")
            text += (
                f"{self.queue.current.title}, durée {duration_label(self.queue.current.duration)}. "
                if self.queue.current
                else "Rejoins le vocal Le Juke-box puis ajoute un morceau."
            )
            text += " À suivre : " + ", ".join(t.title for t in self.queue.pending[:3])
            file = discord.File(
                io.BytesIO(data), filename="moka-jukebox.png", description=text[:1024]
            )
            mid = self.cog.bot.service.get_setting(self.guild.id, "music:message", 0)
            if mid:
                try:
                    await channel.get_partial_message(mid).edit(
                        content=None,
                        embeds=[],
                        attachments=[file],
                        view=MusicView(self.queue),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    return
                except discord.NotFound:
                    file.reset()
            message = await channel.send(
                file=file,
                view=MusicView(self.queue),
                allowed_mentions=discord.AllowedMentions.none(),
            )
            self.cog.bot.service.set_setting(self.guild.id, "music:message", message.id)

    def listeners(self):
        channel = self.guild.get_channel(self.cog.bot.channel_id(self.guild.id, "music_voice"))
        return (
            [
                m.id
                for m in channel.members
                if not m.bot and self.cog.bot.service.admitted(self.guild.id, m.id)
            ]
            if channel
            else []
        )

    async def run(self):
        worker = asyncio.current_task()
        try:
            while True:
                async with self.lock:
                    track = self.queue.advance()
                    self.skipping = False
                    if track is None:
                        self.task = None
                if track is None:
                    break
                if not self.listeners() or not self.cog.bot.service.is_enabled(
                    self.guild.id, "music"
                ):
                    break
                try:
                    if time.monotonic() - track.resolved_at > 60:
                        fresh = await resolve_track(track.url, track.requester)
                        track.stream, track.resolved_at = fresh.stream, fresh.resolved_at
                    async with self.lock:
                        channel = self.guild.get_channel(
                            self.cog.bot.channel_id(self.guild.id, "music_voice")
                        )
                        if not self.listeners():
                            break
                        voice = self.guild.voice_client
                        if not voice:
                            voice = await channel.connect(timeout=25, self_deaf=True)
                        elif voice.channel.id != channel.id:
                            raise DomainError("Moka est déjà dans un autre vocal.")
                        done = asyncio.Event()
                        loop = asyncio.get_running_loop()
                        audio = opus_source(track.stream)

                        def finished(error, loop=loop, done=done, audio=audio):
                            if error:
                                log.warning("Lecture audio interrompue (%s)", type(error).__name__)
                            log.info(
                                "Juke-box : lecture terminée, %s paquets Opus lus", audio.frames
                            )
                            loop.call_soon_threadsafe(done.set)

                        try:
                            voice.play(audio, after=finished)
                        except Exception:
                            audio.cleanup()
                            raise
                    await self.render("Bonne écoute · Volume doux")
                    await done.wait()
                except (DomainError, discord.DiscordException, OSError, TimeoutError):
                    log.warning("Un morceau du Juke-box ne peut pas être lu")
                    await self.render("Ce morceau est indisponible. Moka essaie le suivant.")
        finally:
            async with self.lock:
                if self.task is worker or self.task is None:
                    self.queue.current = None
                    self.queue.paused = False
                    self.idle_at = time.monotonic()
                    self.task = None
            with contextlib.suppress(discord.HTTPException):
                await self.render("Ajoute un morceau pour prolonger la pause.")

    async def stop(self):
        task = self.task
        if task:
            task.cancel()
        if voice := self.guild.voice_client:
            voice.stop()
            await voice.disconnect(force=True)
        if task:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        async with self.lock:
            self.queue.pending.clear()
            self.queue.current = None
            self.queue.paused = False
            self.task = None
            self.skipping = False
        await self.render("Lecteur arrêté · Tu peux ajouter un nouveau morceau.")


class AddTrackModal(discord.ui.Modal, title="Ajouter un morceau au Juke-box"):
    query = discord.ui.TextInput(
        label="Titre, artiste ou lien YouTube",
        placeholder="Un titre et son artiste, ou https://youtu.be/…",
        min_length=1,
        max_length=300,
    )

    async def on_submit(self, interaction):
        await interaction.client.get_cog("MusicCog").add_track(interaction, self.query.value)

    async def on_error(self, interaction, error):
        await handle_error(interaction, error)


class MusicView(SafeView):
    def __init__(self, queue=None):
        super().__init__(timeout=None)
        if queue is not None:
            self.pause.disabled = queue.current is None or queue.paused
            self.resume.disabled = queue.current is None or not queue.paused
            self.skip.disabled = queue.current is None

    @discord.ui.button(
        label="Ajouter un morceau",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="moka:music:add",
        row=0,
    )
    async def add(self, interaction, button):
        await interaction.client.get_cog("MusicCog").authorize(interaction)
        await interaction.response.send_modal(AddTrackModal())

    @discord.ui.button(label="Pause", emoji="⏸️", custom_id="moka:music:pause", row=0)
    async def pause(self, interaction, button):
        await interaction.client.get_cog("MusicCog").control(interaction, "pause")

    @discord.ui.button(label="Reprendre", emoji="▶️", custom_id="moka:music:resume", row=0)
    async def resume(self, interaction, button):
        await interaction.client.get_cog("MusicCog").control(interaction, "resume")

    @discord.ui.button(label="Passer / voter", emoji="⏭️", custom_id="moka:music:skip", row=1)
    async def skip(self, interaction, button):
        await interaction.client.get_cog("MusicCog").control(interaction, "skip")

    @discord.ui.button(label="Voir la file", emoji="📜", custom_id="moka:music:queue", row=1)
    async def queue(self, interaction, button):
        await interaction.client.get_cog("MusicCog").show_queue(interaction)


class MusicCog(commands.Cog):
    jukebox = app_commands.Group(name="jukebox", description="La pause musicale du Comptoir")

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.searching = set()
        self.last_search = {}

    def player(self, guild):
        if guild.id not in self.players:
            self.players[guild.id] = Player(self, guild)
        return self.players[guild.id]

    async def authorize(self, interaction, *, listening=True, staff_only=False):
        guild, user, _ = context(interaction)
        service = self.bot.service
        if not service.is_enabled(guild, "music"):
            raise DomainError("Le Juke-box est désactivé sur ce serveur.")
        text = self.bot.channel_id(guild, "music_text")
        if not text:
            raise DomainError("Le staff peut installer Le Juke-box avec /config jukebox.")
        if interaction.channel_id != text:
            raise DomainError(f"Les commandes musicales se passent dans <#{text}>.")
        member = await interaction.guild.fetch_member(user)
        require_access(service, member, interaction.guild)
        if staff_only and not is_moka_admin(service, member, interaction.guild):
            raise DomainError("Seul le staff de gestion de Moka peut arrêter toute la file.")
        voice = self.bot.channel_id(guild, "music_voice")
        if listening and (
            not member.voice or not member.voice.channel or member.voice.channel.id != voice
        ):
            raise DomainError(f"Rejoins d’abord le vocal <#{voice}> pour agir sur la musique.")
        return member, self.player(interaction.guild)

    async def add_track(self, interaction, query):
        member, player = await self.authorize(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        identity = (interaction.guild.id, member.id)
        now = time.monotonic()
        if identity in self.searching or now - self.last_search.get(identity, 0) < 5:
            raise DomainError(
                "Une recherche est déjà en cours ou vient d’aboutir. Patiente quelques secondes."
            )
        if len(self.searching) >= 3:
            raise DomainError("Trois recherches sont déjà en cours. Réessaie dans un instant.")
        self.searching.add(identity)
        self.last_search[identity] = now
        try:
            track = await resolve_track(query, member.id)
        except TimeoutError as error:
            raise DomainError(
                "La recherche prend trop de temps. Réessaie dans un instant."
            ) from error
        finally:
            self.searching.discard(identity)
        await self.authorize(interaction)
        async with player.lock:
            player.queue.add(track, str(interaction.id))
            position = len(player.queue.pending)
            if player.task is None:
                player.task = asyncio.create_task(player.run(), name="moka-music")
        await interaction.followup.send(
            embed=card(
                "🎵 Morceau ajouté",
                f"**{discord.utils.escape_markdown(track.title)}** · {duration_label(track.duration)}\nPosition dans la file : **{position}**.",
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await player.render()

    @jukebox.command(
        name="jouer", description="Ajouter un titre ou un lien YouTube à la file partagée"
    )
    async def play(self, interaction: discord.Interaction, recherche: str):
        await self.add_track(interaction, recherche)

    async def control(self, interaction, action):
        member, player = await self.authorize(
            interaction, staff_only=action == "stop", listening=action != "stop"
        )
        await interaction.response.defer(ephemeral=True)
        if action == "stop":
            await player.stop()
            text = "Lecteur arrêté et file vidée."
        else:
            async with player.lock:
                voice = interaction.guild.voice_client
                if not voice or not player.queue.current:
                    raise DomainError("Aucun morceau en cours. Ajoute un morceau pour commencer.")
                if action == "pause":
                    voice.pause()
                    player.queue.paused = True
                    text = "Lecture en pause."
                elif action == "resume":
                    voice.resume()
                    player.queue.paused = False
                    text = "Lecture reprise."
                elif player.queue.vote_skip(
                    member.id,
                    player.listeners(),
                    is_moka_admin(self.bot.service, member, interaction.guild),
                ):
                    if not player.skipping:
                        voice.stop()
                        player.skipping = True
                    text = "Morceau passé."
                else:
                    text = f"Vote enregistré : {len(player.queue.votes)}/{len(player.listeners()) // 2 + 1}. La majorité des personnes à l’écoute décide."
            await player.render(text)
        await interaction.followup.send(embed=card("🎵 Le Juke-box", text), ephemeral=True)

    @jukebox.command(name="pause", description="Mettre la lecture en pause")
    async def pause(self, interaction: discord.Interaction):
        await self.control(interaction, "pause")

    @jukebox.command(name="reprendre", description="Reprendre la lecture en pause")
    async def resume(self, interaction: discord.Interaction):
        await self.control(interaction, "resume")

    @jukebox.command(
        name="passer", description="Passer ton morceau ou voter pour passer le morceau en cours"
    )
    async def skip(self, interaction: discord.Interaction):
        await self.control(interaction, "skip")

    @jukebox.command(name="arreter", description="Staff · arrêter la lecture et vider la file")
    async def stop_player(self, interaction: discord.Interaction):
        await self.control(interaction, "stop")

    async def show_queue(self, interaction, page=1):
        _, player = await self.authorize(interaction, listening=False)
        start = (page - 1) * 8
        async with player.lock:
            current = player.queue.current
            rows = list(player.queue.pending[start : start + 8])
            total = len(player.queue.pending)
        if page > 1 and not rows:
            raise DomainError("Cette page est vide. Consulte la première page de la file.")
        lines = [
            f"**{start + i + 1}.** {discord.utils.escape_markdown(t.title)} · {duration_label(t.duration)}"
            for i, t in enumerate(rows)
        ]
        text = (
            "**En cours :** " + discord.utils.escape_markdown(current.title) + "\n\n"
            if current
            else ""
        ) + (
            "\n".join(lines)
            or "La file est vide. Ajoute le prochain morceau avec le bouton du lecteur."
        )
        text += f"\n\n{total}/50 morceaux en attente · Page {page}\n5 ajouts en attente par personne · 30 minutes maximum par morceau."
        await interaction.response.send_message(
            embed=card("📜 À suivre au Juke-box", text), ephemeral=True
        )

    @jukebox.command(name="file", description="Voir les morceaux en attente")
    async def queue(
        self, interaction: discord.Interaction, page: app_commands.Range[int, 1, 7] = 1
    ):
        await self.show_queue(interaction, page)

    @jukebox.command(
        name="retirer",
        description="Retirer un de tes morceaux en attente, par son numéro dans la file",
    )
    async def remove(
        self, interaction: discord.Interaction, numero: app_commands.Range[int, 1, 50]
    ):
        member, player = await self.authorize(interaction)
        async with player.lock:
            track = player.queue.remove(
                numero, member.id, is_moka_admin(self.bot.service, member, interaction.guild)
            )
        await interaction.response.send_message(
            embed=card("🎵 Morceau retiré", discord.utils.escape_markdown(track.title)),
            ephemeral=True,
        )
        await player.render()

    async def install(self, interaction: discord.Interaction):
        staff(interaction)
        member = await interaction.guild.fetch_member(interaction.user.id)
        if not is_moka_admin(self.bot.service, member, interaction.guild):
            raise DomainError("Un rôle de gestion de Moka ou Gérer le serveur est nécessaire.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        spaces = await prepare_music(interaction.guild, self.bot.service)
        await self.player(interaction.guild).render()
        await interaction.followup.send(
            embed=card(
                "🎵 Le Juke-box est installé",
                f"Commandes et lecteur : {spaces['music_text'].mention}\nÉcoute sans micro : {spaces['music_voice'].mention}\nLes membres accueillis peuvent écouter et ajouter des morceaux.",
            ),
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if guild.id in self.bot.config.guild_ids and self.bot.channel_id(
                guild.id, "music_text"
            ):
                try:
                    await self.player(guild).render()
                except discord.HTTPException:
                    log.warning("Lecteur musical à republier")
        if not self.watch.is_running():
            self.watch.start()

    @tasks.loop(seconds=30)
    async def watch(self):
        for player in list(self.players.values()):
            if player.guild.voice_client and (
                not player.listeners()
                or not self.bot.service.is_enabled(player.guild.id, "music")
                or (not player.queue.current and time.monotonic() - player.idle_at >= 120)
            ):
                try:
                    await player.stop()
                except discord.HTTPException:
                    log.warning("Déconnexion du lecteur à reprendre")

    async def cog_unload(self):
        self.watch.cancel()
        for player in self.players.values():
            if player.task:
                player.task.cancel()
            if voice := player.guild.voice_client:
                await voice.disconnect(force=True)
