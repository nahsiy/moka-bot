import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest
from PIL import Image

from moka.base import DomainError
from moka.cogs.music import MusicCog, Player
from moka.music import Queue, Track, music_query, resolve_track
from moka.music_cards import render_music_card
from moka.music_setup import music_overwrites


def track(user=10):
    return Track("Un morceau", "https://www.youtube.com/watch?v=jNQXAC9IVRw", 19, user)


@pytest.mark.parametrize(
    "query",
    [
        "http://youtube.com/x",
        "https://youtube.com.evil.example/x",
        "https://127.0.0.1/a",
        "file:///tmp/a",
        "https://user:pass@youtube.com/x",
        "//localhost/a",
        "https://youtu.be:80/a",
    ],
)
def test_only_youtube_https_or_plain_search_is_accepted(query):
    with pytest.raises(DomainError):
        music_query(query)


def test_search_is_not_shell_code_and_queue_is_bounded_owned_and_duplicate_safe():
    assert music_query("café acoustique") == "ytsearch1:café acoustique"
    queue = Queue()
    for i in range(5):
        assert queue.add(track(), str(i))
    assert not queue.add(track(), "0")
    with pytest.raises(DomainError, match="pleine"):
        queue.add(track(), "6")
    with pytest.raises(DomainError, match="propres"):
        queue.remove(1, 20)
    assert queue.remove(1, 10).requester == 10
    queue.advance()
    assert not queue.vote_skip(20, [10, 20, 30])
    assert not queue.vote_skip(20, [10, 20, 30])
    assert queue.vote_skip(30, [10, 20, 30])
    queue.advance()
    assert not queue.votes
    assert queue.vote_skip(10, [10, 20, 30])


async def test_resolver_timeout_terminates_the_child_process():
    proc = SimpleNamespace(
        communicate=AsyncMock(side_effect=TimeoutError), kill=Mock(), wait=AsyncMock()
    )
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        pytest.raises(TimeoutError),
    ):
        await resolve_track("un titre", 10)
    proc.kill.assert_called_once()
    proc.wait.assert_awaited_once()


async def test_music_controls_recheck_channel_voice_and_staff(service):
    member = Mock(spec=discord.Member, id=10, bot=False)
    member.voice = SimpleNamespace(channel=SimpleNamespace(id=200))
    member.guild_permissions = SimpleNamespace(manage_guild=False)
    guild = SimpleNamespace(id=1, fetch_member=AsyncMock(return_value=member))
    interaction = SimpleNamespace(
        guild=guild, user=member, id=1, channel_id=100, client=SimpleNamespace(service=service)
    )
    bot = SimpleNamespace(
        service=service, channel_id=lambda g, name: 100 if name == "music_text" else 200
    )
    cog = MusicCog(bot)
    await cog.authorize(interaction)
    interaction.channel_id = 101
    with pytest.raises(DomainError, match="commandes musicales"):
        await cog.authorize(interaction)
    interaction.channel_id = 100
    member.voice = None
    with pytest.raises(DomainError, match="Rejoins"):
        await cog.authorize(interaction)
    with pytest.raises(DomainError, match="staff"):
        await cog.authorize(interaction, listening=False, staff_only=True)
    await cog.authorize(interaction, listening=False)
    service.set_setting(1, "moka:admin_roles", [500])
    member.roles = [SimpleNamespace(id=500)]
    await cog.authorize(interaction, listening=False, staff_only=True)
    member.roles = []
    with pytest.raises(DomainError, match="staff"):
        await cog.authorize(interaction, listening=False, staff_only=True)


def test_music_channel_overwrites_keep_admission_and_disable_chat_and_mics(service):
    everyone = Mock(id=1)
    member_role = Mock(id=12)
    staff_role = Mock(id=13)
    bot = Mock(id=99)
    guild = SimpleNamespace(
        id=1,
        default_role=everyone,
        me=bot,
        get_role=lambda rid: {12: member_role, 13: staff_role}.get(rid),
    )
    service.set_setting(1, "admission:enabled", True)
    service.set_setting(1, "admission:member_role", 12)
    service.set_setting(1, "admission:staff_roles", [13])
    text = music_overwrites(guild, service)
    assert text[everyone].view_channel is False
    assert text[member_role].view_channel and not text[member_role].send_messages
    assert text[member_role].use_application_commands
    voice = music_overwrites(guild, service, voice=True)
    assert voice[member_role].connect and not voice[member_role].speak
    assert not voice[staff_role].speak and voice[bot].speak
    assert not voice[member_role].use_application_commands


async def test_worker_cleans_up_and_next_add_can_restart(service):
    guild = SimpleNamespace(id=1, voice_client=None)
    player = Player(SimpleNamespace(bot=SimpleNamespace(service=service)), guild)
    player.render = AsyncMock()
    player.listeners = Mock(return_value=[])
    player.queue.add(track(), "a")
    player.task = asyncio.create_task(player.run())
    await player.task
    assert player.task is None and player.queue.current is None


def test_music_card_handles_long_titles_and_keeps_a_large_readable_format():
    queue = Queue()
    queue.add(
        Track("🌿 Un très long titre avec des caractères variés " * 6, track().url, 120, 10), "1"
    )
    queue.advance()
    with Image.open(io.BytesIO(render_music_card(queue))) as image:
        assert image.size == (1200, 900)


async def test_installer_never_rewrites_an_unrelated_existing_channel(service):
    from moka.music_setup import prepare_music

    service.set_setting(1, "channel:music_text", 99)
    existing = Mock(spec=discord.TextChannel)
    guild = SimpleNamespace(
        id=1,
        me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_channels=True)),
        get_channel=lambda cid: existing if cid == 99 else None,
        create_text_channel=AsyncMock(),
    )
    with pytest.raises(DomainError, match="n’a pas été créé"):
        await prepare_music(guild, service)
    guild.create_text_channel.assert_not_awaited()


async def test_reader_disables_controls_that_have_no_current_action():
    from moka.cogs.music import MusicView

    queue = Queue()
    idle = MusicView(queue)
    assert idle.pause.disabled and idle.resume.disabled and idle.skip.disabled
    queue.add(track(), "1")
    queue.advance()
    active = MusicView(queue)
    assert not active.pause.disabled and active.resume.disabled and not active.skip.disabled
    queue.paused = True
    paused = MusicView(queue)
    assert paused.pause.disabled and not paused.resume.disabled


async def test_duplicate_or_busy_search_does_not_spawn_more_resolvers(service):
    cog = MusicCog(SimpleNamespace(service=service))
    member = SimpleNamespace(id=10)
    cog.authorize = AsyncMock(return_value=(member, SimpleNamespace()))
    interaction = SimpleNamespace(
        guild=SimpleNamespace(id=1), response=SimpleNamespace(defer=AsyncMock())
    )
    cog.searching.add((1, 10))
    with (
        patch("moka.cogs.music.resolve_track", AsyncMock()) as resolver,
        pytest.raises(DomainError, match="recherche"),
    ):
        await cog.add_track(interaction, "un titre")
    resolver.assert_not_awaited()


def test_total_queue_capacity_is_shared_but_cannot_exceed_fifty():
    queue = Queue()
    for i in range(50):
        queue.add(track(100 + i), str(i))
    with pytest.raises(DomainError, match="pleine"):
        queue.add(track(999), "51")
    assert len(queue.pending) == 50


def test_real_ffmpeg_opus_source_discards_stderr_without_a_broken_reader_thread():
    import shutil

    from moka.cogs.music import opus_source

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg est nécessaire uniquement pour la lecture musicale réelle")
    source = opus_source("sine=frequency=440:duration=0.1", before_options="-nostdin -f lavfi")
    try:
        while source.read():
            pass
        assert source.frames >= 5
        assert source._pipe_reader_thread is None
    finally:
        source.cleanup()
