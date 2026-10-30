"""Installation explicite des espaces du Juke-box, accueil préservé."""

import discord

from moka.base import DomainError


def music_overwrites(guild, service, *, voice=False):
    gated = service.admission_enabled(guild.id)
    base = discord.PermissionOverwrite(
        view_channel=not gated,
        read_message_history=True,
        send_messages=False,
        send_messages_in_threads=False,
        create_public_threads=False,
        create_private_threads=False,
        add_reactions=False,
        use_application_commands=not voice,
        connect=voice,
        speak=False,
        stream=False,
        use_soundboard=False,
        use_external_sounds=False,
    )
    result = {guild.default_role: base}
    roles = service.get_setting(guild.id, "admission:staff_roles", [])
    if gated:
        roles = [service.get_setting(guild.id, "admission:member_role"), *roles]
    for rid in roles:
        role = guild.get_role(rid)
        if role is None:
            raise DomainError(
                "Un rôle d’accueil a disparu. Fais vérifier l’accueil avant l’installation."
            )
        overwrite = discord.PermissionOverwrite.from_pair(*base.pair())
        overwrite.view_channel = True
        result[role] = overwrite
    result[guild.me] = discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        use_application_commands=True,
        connect=True,
        speak=True,
        stream=False,
    )
    return result


async def prepare_music(guild, service):
    service.allowed(guild.id)
    if not guild.me.guild_permissions.manage_channels:
        raise DomainError("Moka doit pouvoir gérer les salons pour installer Le Juke-box.")
    result = {}
    installed = service.get_setting(guild.id, "music:installed_channels", [])
    for usage in ("music_text", "music_voice"):
        configured = service.get_setting(guild.id, "channel:" + usage, 0)
        if configured and guild.get_channel(configured) and configured not in installed:
            raise DomainError(
                "Ce salon n’a pas été créé par Le Juke-box. L’installation ne réécrit pas les accès d’un salon existant."
            )
    for usage, name, voice in [
        ("music_text", "🎵・le-juke-box", False),
        ("music_voice", "🎵 Le Juke-box", True),
    ]:
        cid = service.get_setting(guild.id, "channel:" + usage, 0)
        channel = guild.get_channel(cid)
        if channel and not isinstance(
            channel, discord.VoiceChannel if voice else discord.TextChannel
        ):
            raise DomainError("Un espace musical est d’un type inattendu. Vérifie /config salon.")
        overwrites = music_overwrites(guild, service, voice=voice)
        if channel is None:
            creator = guild.create_voice_channel if voice else guild.create_text_channel
            kwargs = (
                {}
                if voice
                else {
                    "topic": "Le Juke-box de Moka · Ajoute un morceau avec le bouton du lecteur ou /jukebox jouer. Rejoins le vocal pour écouter. Ici, seuls les commandes et le lecteur prennent la parole."
                }
            )
            channel = await creator(
                name, overwrites=overwrites, reason="Moka : installer Le Juke-box demandé", **kwargs
            )
            service.set_setting(guild.id, "channel:" + usage, channel.id)
            installed.append(channel.id)
            service.set_setting(guild.id, "music:installed_channels", installed)
        else:
            await channel.edit(
                overwrites=overwrites, reason="Moka : vérifier les accès du Juke-box"
            )
        result[usage] = channel
    return result
