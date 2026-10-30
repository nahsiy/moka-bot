"""Préparation idempotente d'un laboratoire Discord explicitement autorisé."""

from __future__ import annotations

import discord

LAB_NAME = "Moka • Laboratoire"
PENALTY_ROLE_NAME = "☕ Café renversé"
PENALTY_ROLE_COLOUR = 0xBC8053


async def prepare(guild, bot_member, service, *, expected_name=LAB_NAME):
    service.allowed(guild.id)
    if not expected_name or guild.name != expected_name:
        raise ValueError(f"Le serveur ne correspond pas au laboratoire attendu : {expected_name}")
    if (
        not bot_member.guild_permissions.manage_channels
        or not bot_member.guild_permissions.manage_roles
    ):
        raise ValueError("Le bot doit pouvoir gérer salons et rôles dans le laboratoire")

    roles = await guild.fetch_roles()
    result = {"guild": guild.id, "roles": {}, "channels": {}}
    for name in (
        "Staff test",
        PENALTY_ROLE_NAME,
        "Lecteur",
        "MP ouverts",
        "MP sur demande",
        "MP fermés",
    ):
        role = next((r for r in roles if r.name == name and not r.managed), None)
        if role is None and name == PENALTY_ROLE_NAME:
            configured = service.get_setting(guild.id, "role:counting_failure")
            role = next((r for r in roles if r.id == configured and not r.managed), None)
            if role is None:
                role = next(
                    (
                        r
                        for r in roles
                        if r.name in {"Pas-doué", "Pas doué (test)"} and not r.managed
                    ),
                    None,
                )
        if role is None:
            role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                hoist=name == PENALTY_ROLE_NAME,
                colour=discord.Colour(PENALTY_ROLE_COLOUR if name == PENALTY_ROLE_NAME else 0),
                reason="Moka : préparation du laboratoire",
            )
            roles.append(role)
        # Même une relance ne récupère pas silencieusement un rôle privilégié.
        if role.permissions.value:
            raise ValueError(f"Le rôle de laboratoire {name} doit être sans permissions globales")
        if name == PENALTY_ROLE_NAME and (
            role.name != name or not role.hoist or role.colour.value != PENALTY_ROLE_COLOUR
        ):
            old_role = role
            role = await role.edit(
                name=name,
                colour=discord.Colour(PENALTY_ROLE_COLOUR),
                hoist=True,
                reason="Moka : pause café commune aux jeux",
            )
            roles[roles.index(old_role)] = role
        result["roles"][name] = role.id

    channels = await guild.fetch_channels()

    async def category(name, private=False):
        item = next(
            (c for c in channels if isinstance(c, discord.CategoryChannel) and c.name == name), None
        )
        if item is None:
            kwargs = {}
            if private:
                staff_role = next(r for r in roles if r.id == result["roles"]["Staff test"])
                kwargs["overwrites"] = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    staff_role: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    ),
                    bot_member: discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        manage_channels=True,
                    ),
                }
            item = await guild.create_category(name, reason="Moka : laboratoire", **kwargs)
            channels.append(item)
        return item

    public = await category("MOKA TEST")
    private = await category("MOKA STAFF TEST", True)
    voice = await category("MOKA VOCAUX TEST")
    tickets = await category("MOKA TICKETS TEST", True)
    mapping = {
        "counting": "counting",
        "words": "suite-de-mots",
        "goblin": "distractions",
        "tickets": "tickets",
        "logs": "journal-moka",
    }
    for usage, name in mapping.items():
        parent = private if usage == "logs" else public
        channel = next(
            (
                c
                for c in channels
                if isinstance(c, discord.TextChannel)
                and c.name == name
                and c.category_id == parent.id
            ),
            None,
        )
        if channel is None:
            channel = await guild.create_text_channel(
                name, category=parent, overwrites=parent.overwrites, reason="Moka : laboratoire"
            )
            channels.append(channel)
        if usage == "logs":
            # Un salon existant peut avoir des droits distincts de sa catégorie.
            staff_role = next(r for r in roles if r.id == result["roles"]["Staff test"])
            overwrite = channel.overwrites_for(staff_role)
            overwrite.view_channel = True
            overwrite.read_message_history = True
            await channel.set_permissions(
                staff_role, overwrite=overwrite, reason="Moka : accès du staff au journal"
            )
        service.set_setting(guild.id, "channel:" + usage, channel.id)
        result["channels"][usage] = channel.id

    creator = next(
        (
            c
            for c in channels
            if isinstance(c, discord.VoiceChannel)
            and c.name == "Créer mon vocal"
            and c.category_id == voice.id
        ),
        None,
    )
    if creator is None:
        creator = await guild.create_voice_channel(
            "Créer mon vocal",
            category=voice,
            overwrites=voice.overwrites,
            reason="Moka : laboratoire",
        )
    for usage, channel_id in (
        ("voice_creator", creator.id),
        ("voice_category", voice.id),
        ("ticket_category", tickets.id),
    ):
        service.set_setting(guild.id, "channel:" + usage, channel_id)
        result["channels"][usage] = channel_id
    service.set_setting(guild.id, "role:counting_failure", result["roles"][PENALTY_ROLE_NAME])
    penalty_role = next(r for r in roles if r.id == result["roles"][PENALTY_ROLE_NAME])
    for usage in ("counting", "words"):
        channel = next(c for c in channels if c.id == result["channels"][usage])
        overwrite = channel.overwrites_for(penalty_role)
        overwrite.send_messages = False
        overwrite.send_messages_in_threads = False
        await channel.set_permissions(
            penalty_role, overwrite=overwrite, reason="Moka : pause commune aux deux jeux"
        )
    service.set_setting(guild.id, "ticket_staff_roles", [result["roles"]["Staff test"]])
    service.set_setting(
        guild.id,
        "role_menu",
        {
            str(result["roles"][name]): ("MP" if name.startswith("MP ") else "")
            for name in ("Lecteur", "MP ouverts", "MP sur demande", "MP fermés")
        },
    )
    return result


async def run(config, token, *, expected_name=LAB_NAME):
    from moka.service import Service
    from moka.store import Store

    if len(config.guild_ids) != 1:
        raise ValueError("La préparation demande exactement un serveur autorisé")
    store = Store(config.data_dir / "moka.sqlite3")
    store.initialize()
    service = Service(store, config)
    async with discord.Client(intents=discord.Intents.none()) as client:
        # API bot officielle uniquement, jamais de token de compte utilisateur.
        await client.login(token)
        guild = await client.fetch_guild(config.guild_ids[0])
        me = await guild.fetch_member(client.user.id)
        return await prepare(guild, me, service, expected_name=expected_name)
