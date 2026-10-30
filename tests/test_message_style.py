from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.members import MembersCog
from moka.discord_ui import COLOR, handle_error, notify


def interaction_for(service, *, done=False):
    member = Mock(spec=discord.Member)
    member.id, member.bot = 10, False
    return SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=member,
        id=123,
        client=SimpleNamespace(service=service),
        response=SimpleNamespace(
            is_done=Mock(return_value=done),
            send_message=AsyncMock(),
            defer=AsyncMock(),
        ),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.mark.parametrize("done", [False, True])
async def test_notifications_keep_frames_and_privacy_before_or_after_defer(service, done):
    interaction = interaction_for(service, done=done)
    await notify(interaction, "Confirmation de test.")
    sender = interaction.followup.send if done else interaction.response.send_message
    sent = sender.call_args
    assert not sent.args and sent.kwargs["ephemeral"] is True
    assert sent.kwargs["embed"].title == "☕ Moka"
    assert sent.kwargs["embed"].description == "Confirmation de test."
    assert sent.kwargs["embed"].colour.value == COLOR


async def test_errors_are_framed_and_stay_private(service):
    interaction = interaction_for(service)
    await handle_error(interaction, DomainError("Solde insuffisant."))
    sent = interaction.response.send_message.call_args.kwargs
    assert sent["ephemeral"] is True
    assert sent["embed"].title == "⚠️ Action impossible"
    assert sent["embed"].description == "Solde insuffisant."


async def test_daily_reward_has_a_private_frame_and_credits_only_once(service):
    interaction = interaction_for(service)
    cog = MembersCog(interaction.client)
    await MembersCog.daily.callback(cog, interaction)
    await MembersCog.daily.callback(cog, interaction)
    sent = interaction.response.send_message.call_args.kwargs
    assert sent["ephemeral"] is True and sent["embed"].colour.value == COLOR
    assert "200" in sent["embed"].description
    assert service.profile(1, 10, viewer=10)["wallet"] == 200


async def test_personal_export_keeps_private_json_attachment_with_frame(service):
    interaction = interaction_for(service)
    await MembersCog.export_data.callback(MembersCog(interaction.client), interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    sent = interaction.followup.send.call_args.kwargs
    assert sent["ephemeral"] is True and sent["embed"].title == "📦 Tes données"
    assert sent["file"].filename == "mes-donnees-moka.json"
