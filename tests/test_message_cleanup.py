from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka import message_cleanup as cleanup
from moka.__main__ import check_commands
from moka.base import DomainError


def message(days=0, *, pinned=False, panel=False, bot=False):
    created = datetime.now(UTC) - timedelta(days=days)
    return SimpleNamespace(
        id=discord.utils.time_snowflake(created),
        created_at=created,
        author=SimpleNamespace(id=99 if bot else 10),
        pinned=pinned,
        components=[object()] if panel else [],
        delete=AsyncMock(),
    )


def channel(messages):
    async def history(**kwargs):
        for msg in sorted(messages, key=lambda m: m.id, reverse=True):
            if msg.id >= kwargs["before"].id:
                continue
            if kwargs["after"] and msg.id <= kwargs["after"].id:
                continue
            yield msg

    result = Mock(spec=discord.TextChannel)
    result.guild, result.id = SimpleNamespace(id=1), 2
    result.history = Mock(side_effect=history)
    result.fetch_message = AsyncMock(
        side_effect=lambda ident: next(m for m in messages if m.id == ident)
    )
    result.delete_messages = AsyncMock()
    return result


def snapshot():
    return discord.utils.time_snowflake(datetime.now(UTC) + timedelta(seconds=1))


async def test_selection_is_frozen_and_protects_pins_and_bot_panels():
    now = snapshot()
    plain, pin, panel = message(1), message(2, pinned=True), message(3, panel=True, bot=True)
    human_components = message(4, panel=True)
    later = message(-1)
    room = channel([plain, pin, panel, human_components, later])
    selected = await cleanup.select_messages(room, now, 99)
    assert set(selected.ids) == {plain.id, human_components.id}
    assert (selected.pinned, selected.panels) == (1, 1)
    assert (selected.first, selected.last) == (human_components.id, plain.id)
    room.delete_messages.assert_not_awaited()
    selected = await cleanup.select_messages(room, now, 99, keep_pinned=False)
    assert pin.id in selected.ids and panel.id not in selected.ids


async def test_date_and_since_boundaries_include_anchor_only_in_target_channel():
    old, anchor, recent = message(8), message(5), message(1)
    room = channel([old, anchor, recent])
    selected = await cleanup.select_messages(room, snapshot(), 99, since=anchor.id)
    assert set(selected.ids) == {anchor.id, recent.id}
    selected = await cleanup.select_messages(room, snapshot(), 99, before=anchor.created_at)
    assert selected.ids == (old.id,)
    single = await cleanup.select_messages(room, snapshot(), 99, single=anchor.id)
    assert single.ids == (anchor.id,)


async def test_overflow_refuses_without_any_deletion(monkeypatch):
    monkeypatch.setattr(cleanup, "MAX_MESSAGES", 2)
    room = channel([message(1), message(2), message(3)])
    with pytest.raises(DomainError, match="Aucun message supprimé"):
        await cleanup.select_messages(room, snapshot(), 99)
    room.delete_messages.assert_not_awaited()


@pytest.mark.parametrize("value", ["2026-02-30", "demain", "2026-10-30T12:00"])
def test_invalid_dates(value):
    with pytest.raises(DomainError):
        cleanup.date_boundary(value)


def test_paris_midnight_handles_summer_and_winter():
    assert cleanup.date_boundary("2026-07-01").astimezone(UTC).hour == 22
    assert cleanup.date_boundary("2026-12-01").astimezone(UTC).hour == 23


@pytest.mark.parametrize(
    "value", ["abc", "-123456789012345", "１２３４５６７８９０１２３４５", "18446744073709551616"]
)
def test_invalid_snowflakes(value):
    with pytest.raises(DomainError):
        cleanup.message_id(value)


async def execute(messages, *, missing=None):
    room = channel([msg for msg in messages if msg.id != missing])
    selection = cleanup.Selection(tuple(m.id for m in messages), None, None, 0, 0)
    result = cleanup.Result()
    refresh = AsyncMock(return_value=room)
    await cleanup.delete_selection(selection, refresh, True, 99, "test", AsyncMock(), result)
    return room, result, refresh


async def test_recent_batches_never_exceed_100_and_old_messages_use_single_delete():
    recent = [message(i / 1000) for i in range(102)]
    old = message(15)
    room, result, refresh = await execute([*recent, old])
    assert result.deleted == 103 and not result.stopped
    assert [len(call.args[0]) for call in room.delete_messages.await_args_list] == [100, 2]
    old.delete.assert_awaited_once_with()
    assert all(not m.delete.await_count for m in recent)
    assert refresh.await_count == 2


async def test_new_pins_and_panels_are_rechecked_and_missing_not_counted_deleted():
    plain, pin, panel, gone = (
        message(1),
        message(2, pinned=True),
        message(3, panel=True, bot=True),
        message(4),
    )
    room, result, _ = await execute([plain, pin, panel, gone], missing=gone.id)
    assert (result.deleted, result.protected, result.missing) == (1, 2, 1)
    room.delete_messages.assert_not_awaited()
    plain.delete.assert_awaited_once_with()
    pin.delete.assert_not_awaited()


async def test_individual_failure_preserves_partial_count():
    first, second = message(15), message(16)
    second.delete.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="refus"), "refus"
    )
    result = cleanup.Result()
    room = channel([first, second])
    with pytest.raises(discord.Forbidden):
        await cleanup.delete_selection(
            cleanup.Selection((first.id, second.id), None, None, 0, 0),
            AsyncMock(return_value=room),
            True,
            99,
            "test",
            AsyncMock(),
            result,
        )
    assert result.deleted == 1


async def test_permission_loss_between_batches_stops_before_next_delete():
    messages = [message(i / 1000) for i in range(101)]
    room = channel(messages)
    refresh = AsyncMock(side_effect=[room, DomainError("Permission retirée")])
    result = cleanup.Result()
    with pytest.raises(DomainError):
        await cleanup.delete_selection(
            cleanup.Selection(tuple(m.id for m in messages), None, None, 0, 0),
            refresh,
            True,
            99,
            "test",
            AsyncMock(),
            result,
        )
    assert result.deleted == 100
    messages[-1].delete.assert_not_awaited()


async def test_deadline_stops_without_deleting(monkeypatch):
    monkeypatch.setattr(cleanup, "RUN_SECONDS", 0)
    msg = message(1)
    _, result, refresh = await execute([msg])
    assert result.stopped and result.deleted == 0
    refresh.assert_not_awaited()


async def test_bulk_revalidation_reports_progress_before_first_delete(monkeypatch):
    messages = [message(i / 1000) for i in range(100)]
    room = channel(messages)
    clock = [0]
    fetch = room.fetch_message.side_effect
    history = room.history.side_effect

    async def slow_fetch(ident):
        clock[0] += 1
        return fetch(ident)

    async def paginated_history(**kwargs):
        async for value in history(**kwargs):
            clock[0] += 1
            yield value

    room.fetch_message.side_effect = slow_fetch
    room.history.side_effect = paginated_history
    monkeypatch.setattr(cleanup.time, "monotonic", lambda: clock[0])
    observations = []

    async def progress(result):
        observations.append((getattr(result, "checked", 0), result.deleted))

    result = cleanup.Result()
    await cleanup.delete_selection(
        cleanup.Selection(tuple(m.id for m in messages), None, None, 0, 0),
        AsyncMock(return_value=room),
        True,
        99,
        "test",
        progress,
        result,
    )
    assert any(checked >= 5 and deleted == 0 for checked, deleted in observations)
    room.fetch_message.assert_not_awaited()


async def test_history_recheck_deletes_only_confirmed_ids():
    first, inserted, last = message(3), message(2), message(1)
    room = channel([first, inserted, last])
    result = cleanup.Result()
    await cleanup.delete_selection(
        cleanup.Selection((first.id, last.id), first.id, last.id, 0, 0),
        AsyncMock(return_value=room),
        True,
        99,
        "test",
        AsyncMock(),
        result,
    )
    deleted = room.delete_messages.call_args.args[0]
    assert {msg.id for msg in deleted} == {first.id, last.id}
    inserted.delete.assert_not_awaited()
    assert (result.checked, result.total, result.deleted) == (2, 2, 2)


def interaction(service):
    return SimpleNamespace(
        guild=SimpleNamespace(id=1),
        user=SimpleNamespace(id=10),
        client=SimpleNamespace(
            service=service, user=SimpleNamespace(id=99), fetch_guild=AsyncMock(), audit=AsyncMock()
        ),
        response=SimpleNamespace(defer=AsyncMock(), edit_message=AsyncMock()),
        edit_original_response=AsyncMock(),
    )


async def test_authorization_uses_fresh_guild_roles_and_channel_permissions(service, monkeypatch):
    monkeypatch.setattr(cleanup, "context", lambda i: (1, i.user.id, "command"))
    i = interaction(service)
    room = channel([])
    room.permissions_for.return_value = discord.Permissions(
        view_channel=True, read_message_history=True, manage_messages=True
    )
    fresh = SimpleNamespace(fetch_channel=AsyncMock(return_value=room), fetch_member=AsyncMock())
    i.client.fetch_guild.return_value = fresh
    assert await cleanup.authorize(i, 2, 10) is room
    i.client.fetch_guild.assert_awaited_once_with(1)
    assert fresh.fetch_member.await_count == 2
    room.permissions_for.return_value = discord.Permissions(
        view_channel=True, read_message_history=True
    )
    with pytest.raises(DomainError, match="Gérer les messages"):
        await cleanup.authorize(i, 2, 10)
    i.user.id = 11
    with pytest.raises(DomainError, match="autre personne"):
        await cleanup.authorize(i, 2, 10)


async def test_cancel_expiry_and_wrong_owner_never_delete(service, monkeypatch):
    monkeypatch.setattr(cleanup, "context", lambda i: (i.guild.id, i.user.id, "command"))
    i = interaction(service)
    selected = cleanup.Selection((123,), 123, 123, 0, 0)
    view = cleanup.CleanupView(10, 1, 2, selected, True)
    i.user.id = 11
    with pytest.raises(DomainError):
        await view.confirm.callback(i)
    i.user.id = 10
    await view.cancel.callback(i)
    with pytest.raises(DomainError):
        await view.confirm.callback(i)
    view = cleanup.CleanupView(10, 1, 2, selected, True)
    await view.on_timeout()
    with pytest.raises(DomainError):
        await view.confirm.callback(i)
    i.client.fetch_guild.assert_not_awaited()


async def test_confirmation_double_click_and_failed_permission_report_honestly(
    service, monkeypatch
):
    monkeypatch.setattr(cleanup, "context", lambda i: (1, i.user.id, "command"))
    auth = AsyncMock(side_effect=DomainError("Permission retirée"))
    monkeypatch.setattr(cleanup, "authorize", auth)
    i = interaction(service)
    view = cleanup.CleanupView(10, 1, 2, cleanup.Selection((123,), 123, 123, 0, 0), True)
    await view.confirm.callback(i)
    embed = i.edit_original_response.call_args.kwargs["embed"]
    assert "interrompu" in embed.title and "Permission retirée" in embed.description
    with pytest.raises(DomainError, match="déjà utilisée"):
        await view.confirm.callback(i)
    auth.assert_awaited_once()
    i.client.audit.assert_awaited_once()


async def test_commands_are_registered_with_correct_default_permission(service):
    commands = await check_commands(service.config)
    group = next(command for command in commands if command["name"] == "messages")
    assert (
        int(group["default_member_permissions"]) == discord.Permissions(manage_messages=True).value
    )
    assert {option["name"] for option in group["options"]} == {
        "vider",
        "avant",
        "depuis",
        "anciens",
        "supprimer",
    }


async def test_concurrent_confirmations_cannot_delete_twice(service, monkeypatch):
    import asyncio

    monkeypatch.setattr(cleanup, "context", lambda i: (1, i.user.id, "command"))
    monkeypatch.setattr(cleanup, "authorize", AsyncMock(return_value=channel([])))
    started, finish = asyncio.Event(), asyncio.Event()

    async def delete(*args):
        started.set()
        await finish.wait()
        args[-1].deleted = 1

    deleting = AsyncMock(side_effect=delete)
    monkeypatch.setattr(cleanup, "delete_selection", deleting)
    i = interaction(service)
    selected = cleanup.Selection((123,), 123, 123, 0, 0)
    first = cleanup.CleanupView(10, 1, 2, selected, True)
    second = cleanup.CleanupView(10, 1, 2, selected, True)
    running = asyncio.create_task(first.confirm.callback(i))
    await started.wait()
    try:
        with pytest.raises(DomainError, match="déjà utilisée"):
            await first.confirm.callback(i)
        with pytest.raises(DomainError, match="déjà en cours"):
            await second.confirm.callback(i)
    finally:
        finish.set()
        await running
    deleting.assert_awaited_once()
    assert "**1**" in i.edit_original_response.call_args.kwargs["embed"].description
