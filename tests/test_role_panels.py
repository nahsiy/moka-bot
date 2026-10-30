import itertools
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from moka.base import DomainError
from moka.cogs.community import CommunityCog, RoleSelect
from moka.role_catalog import PREFERENCES
from moka.role_panels import (
    CLEAR_ROLE_VALUE,
    CategoryClearButton,
    CategoryRoleButton,
    CategoryRoleSelect,
    RoleCategoryView,
    category_menu,
    prepare_preferences,
    publish_categories,
)


@pytest.fixture
def preferences(service):
    guild = SimpleNamespace(id=1, roles=[])
    serial = itertools.count(300)

    def role(rid, name, **kwargs):
        return discord.Role(
            guild=guild,
            state=None,
            data={
                "id": str(rid),
                "name": name,
                "permissions": str(kwargs.get("permissions", discord.Permissions.none()).value),
                "position": 100 if rid == 9999 else 1,
                "color": 0,
                "hoist": kwargs.get("hoist", False),
                "managed": False,
            },
        )

    for rid, name in enumerate(["MP ouverts", "MP sur demande", "MP fermés", "Lecteur"], 101):
        guild.roles.append(role(rid, name))
    for rid, name in enumerate(
        ["Staff test", "☕ Le Barista", "🌱 Petit grain", "☕ Café renversé"], 201
    ):
        guild.roles.append(role(rid, name))
    guild.me = SimpleNamespace(
        top_role=role(9999, "Moka"), guild_permissions=discord.Permissions(manage_roles=True)
    )
    guild.get_role = lambda rid: next((r for r in guild.roles if r.id == rid), None)
    guild.fetch_roles = AsyncMock(side_effect=lambda: list(guild.roles))

    async def create(**kwargs):
        result = role(
            next(serial), kwargs["name"], **{k: v for k, v in kwargs.items() if k != "name"}
        )
        guild.roles.append(result)
        return result

    guild.create_role = AsyncMock(side_effect=create)
    member = Mock(spec=discord.Member)
    member.id, member.guild, member.roles, member.bot = 10, guild, [], False
    member.guild_permissions = discord.Permissions.none()

    async def add(*roles, **kwargs):
        member.roles.extend(r for r in roles if r not in member.roles)

    async def remove(*roles, **kwargs):
        member.roles[:] = [r for r in member.roles if r not in roles]

    member.add_roles, member.remove_roles = (
        AsyncMock(side_effect=add),
        AsyncMock(side_effect=remove),
    )
    guild.fetch_member = AsyncMock(return_value=member)
    cog = CommunityCog(SimpleNamespace(service=service))
    client = SimpleNamespace(service=service, user=SimpleNamespace(id=9999), get_cog=lambda _: cog)
    interaction = SimpleNamespace(
        guild=guild,
        user=member,
        id=123,
        client=client,
        message=SimpleNamespace(author=client.user, edit=AsyncMock()),
        response=SimpleNamespace(
            defer=AsyncMock(), send_message=AsyncMock(), is_done=Mock(return_value=False)
        ),
        followup=SimpleNamespace(send=AsyncMock()),
        edit_original_response=AsyncMock(),
    )
    service.set_setting(1, "role_menu", {"101": "MP", "102": "MP", "103": "MP", "104": ""})
    service.set_setting(1, "ticket_staff_roles", [201])
    service.set_setting(1, "level_rewards", {"0": 203})
    service.set_setting(1, "role:counting_failure", 204)
    return SimpleNamespace(guild=guild, member=member, cog=cog, interaction=interaction)


async def setup_preferences(p, service):
    return await prepare_preferences(p.guild, p.guild.me, service)


async def test_installation_reuses_ids_and_creates_only_safe_optional_roles(preferences, service):
    p = preferences
    first = await setup_preferences(p, service)
    second = await setup_preferences(p, service)
    assert first == second and set(first) == set(PREFERENCES)
    assert p.guild.create_role.await_count == 47
    menu = service.get_setting(1, "role_menu")
    assert len(menu) == 51
    assert set(first["mp"]["roles"]) == {101, 102, 103}
    assert {201, 202, 203, 204}.isdisjoint(map(int, menu))
    assert all(len(data["roles"]) <= 25 for data in first.values())
    assert all(p.guild.get_role(int(rid)).permissions.value == 0 for rid in menu)
    assert p.member.roles == []


async def test_unsafe_existing_role_stops_before_creation(preferences, service):
    p = preferences
    p.guild.get_role(101)._permissions = discord.Permissions(manage_roles=True).value
    with pytest.raises(DomainError, match="sûr"):
        await setup_preferences(p, service)
    p.guild.create_role.assert_not_called()


async def test_category_change_and_clear_preserve_other_roles_and_money(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    p.member.roles = [p.guild.get_role(rid) for rid in (101, 104, 201, 202, 203, 204)]
    profile = service.profile(1, 10, viewer=10)
    selector = RoleSelect(p.member, category_menu(service, 1, "mp"), category="mp")
    assert selector.max_values == 1
    selector._values = ["103"]
    await selector.callback(p.interaction)
    assert {r.id for r in p.member.roles} == {103, 104, 201, 202, 203, 204}
    selector._values = []
    await selector.callback(p.interaction)
    assert {r.id for r in p.member.roles} == {104, 201, 202, 203, 204}
    assert service.profile(1, 10, viewer=10) == profile


@pytest.mark.parametrize("change", ["allowlist", "category", "module", "privilege"])
async def test_changes_during_open_menu_are_rechecked(preferences, service, change):
    p = preferences
    await setup_preferences(p, service)
    selector = RoleSelect(p.member, category_menu(service, 1, "mp"), category="mp")
    selector._values = ["101"]

    async def fetch(user):
        if change == "allowlist":
            menu = service.get_setting(1, "role_menu")
            menu.pop("101")
            service.set_setting(1, "role_menu", menu)
        elif change == "category":
            categories = service.get_setting(1, "role_categories")
            categories["mp"]["roles"].remove(101)
            service.set_setting(1, "role_categories", categories)
        elif change == "module":
            service.set_setting(1, "feature:roles", False)
        else:
            p.guild.get_role(101)._permissions = discord.Permissions(administrator=True).value
        return p.member

    p.guild.fetch_member.side_effect = fetch
    with pytest.raises(DomainError):
        await selector.callback(p.interaction)
    p.member.add_roles.assert_not_called()
    p.member.remove_roles.assert_not_called()


async def test_exclusive_category_does_not_accept_two_choices(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    selector = RoleSelect(p.member, category_menu(service, 1, "mp"), category="mp")
    selector._values = ["101", "102"]
    with pytest.raises(DomainError, match="seul rôle"):
        await selector.callback(p.interaction)
    p.member.add_roles.assert_not_called()


@pytest.mark.parametrize("rid", [201, 202, 203, 204])
async def test_staff_owner_xp_and_penalty_cannot_be_self_assigned(preferences, service, rid):
    p = preferences
    with pytest.raises(DomainError, match="pas à choisir"):
        p.cog.safe_self_role(p.guild, p.guild.get_role(rid))


async def test_dynamic_panel_after_restart_opens_private_category(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    original = CategoryRoleButton("mp")
    match = re.fullmatch(r"moka:roles:category:(?P<category>[a-z0-9-]{1,32})", original.custom_id)
    restored = await CategoryRoleButton.from_custom_id(p.interaction, original.item, match)
    await restored.callback(p.interaction)
    options = p.interaction.response.send_message.call_args.kwargs
    assert options["ephemeral"]
    assert options["view"].children[0].category == "mp"
    assert {o.value for o in options["view"].children[0].options} == {"101", "102", "103"}


async def test_publication_is_persistent_and_reuses_messages(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    serial = itertools.count(1000)
    edit = AsyncMock()
    channel = SimpleNamespace(
        id=5,
        guild=p.guild,
        send=AsyncMock(side_effect=lambda **kwargs: SimpleNamespace(id=next(serial))),
        get_partial_message=lambda mid: SimpleNamespace(edit=edit),
    )
    assert await publish_categories(channel, service) == 8
    assert await publish_categories(channel, service) == 8
    assert channel.send.await_count == 8 and edit.await_count == 8
    for call in channel.send.call_args_list:
        assert call.kwargs["view"].is_persistent()
        assert isinstance(call.kwargs["view"].children[0], CategoryRoleSelect)
        if call.kwargs["view"].children[0].item.max_values == 1:
            assert len(call.kwargs["view"].children) == 1
            assert any(
                o.value == CLEAR_ROLE_VALUE for o in call.kwargs["view"].children[0].item.options
            )
        else:
            assert call.kwargs["view"].children[1].item.label == "Tout retirer"
        assert call.kwargs["allowed_mentions"].to_dict() == {"parse": []}
        assert "facultatifs" in call.kwargs["embed"].description


async def test_install_command_checks_staff_at_runtime(preferences):
    p = preferences
    with pytest.raises(DomainError, match="permission"):
        await CommunityCog.install_roles.callback(p.cog, p.interaction)
    p.guild.fetch_roles.assert_not_called()


async def test_direct_select_and_clear_after_restart_only_confirm_privately(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    p.member.roles = [p.guild.get_role(rid) for rid in (104, 202, 203)]
    view = RoleCategoryView("mp", p.guild, service)
    original = view.children[0]
    assert original.item.max_values == 1
    assert not any(option.default for option in original.item.options)
    match = re.fullmatch(
        r"moka:roles:select:(?P<category>[a-z0-9-]{1,32})(?::[0-9a-f]{12})?", original.custom_id
    )
    restored = await CategoryRoleSelect.from_custom_id(p.interaction, original.item, match)
    restored.item._values = ["103"]
    await restored.callback(p.interaction)
    assert {r.id for r in p.member.roles} == {103, 104, 202, 203}
    p.interaction.response.defer.assert_awaited_with(ephemeral=True, thinking=True)
    confirmation = p.interaction.followup.send.call_args.kwargs
    assert confirmation["ephemeral"] and "MP fermés" in confirmation["embed"].description
    p.interaction.edit_original_response.assert_not_called()
    refreshed = p.interaction.message.edit.call_args
    assert refreshed is not None, "Le menu doit être remplacé après la sélection"
    assert set(refreshed.kwargs) == {
        "view"
    }  # Jamais de préférences personnelles dans le texte public.
    fresh_select = refreshed.kwargs["view"].children[0]
    assert fresh_select.custom_id != original.custom_id
    assert not any(option.default for option in fresh_select.item.options)
    clear = CategoryClearButton("mp")  # Les anciens boutons restent reconnus.
    match = re.fullmatch(r"moka:roles:clear:(?P<category>[a-z0-9-]{1,32})", clear.custom_id)
    restored_clear = await CategoryClearButton.from_custom_id(p.interaction, clear.item, match)
    await restored_clear.callback(p.interaction)
    assert {r.id for r in p.member.roles} == {104, 202, 203}
    assert "retirés" in p.interaction.followup.send.call_args.kwargs["embed"].description
    cleared_view = p.interaction.message.edit.call_args.kwargs["view"]
    assert cleared_view.children[0].custom_id != fresh_select.custom_id
    assert not any(option.default for option in cleared_view.children[0].item.options)
    p.interaction.edit_original_response.assert_not_called()


async def test_forged_direct_panel_does_not_change_roles(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    select = RoleCategoryView("mp", p.guild, service).children[0]
    select.item._values = ["103"]
    p.interaction.message.author = SimpleNamespace(id=888)
    await select.callback(p.interaction)
    p.member.add_roles.assert_not_called()
    assert p.interaction.response.send_message.call_args.kwargs["ephemeral"]


async def test_shared_public_menu_assigns_only_the_clicking_member(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    other = Mock(spec=discord.Member)
    other.id, other.guild, other.roles = 11, p.guild, []
    other.add_roles, other.remove_roles = AsyncMock(), AsyncMock()
    p.guild.fetch_member.side_effect = lambda user: p.member if user == 10 else other
    select = RoleCategoryView("mp", p.guild, service).children[0]
    select.item._values = ["103"]
    p.interaction.user = other
    await select.callback(p.interaction)
    other.add_roles.assert_awaited_once()
    p.member.add_roles.assert_not_called()
    p.member.remove_roles.assert_not_called()


async def test_legacy_public_select_ids_still_work_and_new_ids_are_preserved(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    options = [discord.SelectOption(label="MP fermés", value="103")]
    for custom_id in ("moka:roles:select:mp", "moka:roles:select:mp:012345abcdef"):
        item = discord.ui.Select(custom_id=custom_id, options=options, min_values=0, max_values=1)
        match = re.fullmatch(
            r"moka:roles:select:(?P<category>[a-z0-9-]{1,32})(?::[0-9a-f]{12})?", custom_id
        )
        restored = await CategoryRoleSelect.from_custom_id(p.interaction, item, match)
        assert restored.custom_id == custom_id
        restored.item._values = ["103"]
        await restored.callback(p.interaction)
        fresh = p.interaction.message.edit.call_args.kwargs["view"].children[0]
        assert fresh.custom_id != custom_id and len(fresh.custom_id) <= 100
        assert {r.id for r in p.member.roles} == {103}


async def test_clear_success_is_confirmed_even_if_discord_cannot_refresh_the_menu(
    preferences, service
):
    p = preferences
    await setup_preferences(p, service)
    p.member.roles = [p.guild.get_role(103)]
    p.interaction.message.edit.side_effect = discord.HTTPException(
        SimpleNamespace(status=503, reason="Unavailable"), "Temporary failure"
    )
    await CategoryClearButton("mp").callback(p.interaction)
    assert not p.member.roles
    payload = p.interaction.followup.send.call_args.kwargs
    assert payload["ephemeral"]
    assert "retirés" in payload["embed"].description
    assert "n'a pas pu être rafraîchie" in payload["embed"].description


async def test_role_failure_does_not_reset_the_menu_or_confirm_success(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    p.member.roles = [p.guild.get_role(103)]
    p.interaction.response.is_done.return_value = True
    p.member.remove_roles.side_effect = discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"), "Missing permission"
    )
    await CategoryClearButton("mp").callback(p.interaction)
    assert {r.id for r in p.member.roles} == {103}
    p.interaction.message.edit.assert_not_called()
    assert "retirés" not in p.interaction.followup.send.call_args.kwargs["embed"].description


async def test_single_choice_can_be_cleared_inline_without_a_button(preferences, service):
    p = preferences
    await setup_preferences(p, service)
    p.member.roles = [p.guild.get_role(103), p.guild.get_role(104)]
    view = RoleCategoryView("mp", p.guild, service)
    assert len(view.children) == 1
    select = view.children[0]
    select.item._values = [CLEAR_ROLE_VALUE]
    await select.callback(p.interaction)
    assert {r.id for r in p.member.roles} == {104}
    assert "retirés" in p.interaction.followup.send.call_args.kwargs["embed"].description
