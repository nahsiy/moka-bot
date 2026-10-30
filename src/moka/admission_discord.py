"""Composants persistants et autorisations de l'accueil."""

import discord

from moka.base import DomainError
from moka.discord_ui import SafeView, card, handle_error


def recruiter(service, member):
    roles = service.get_setting(member.guild.id, "admission:staff_roles", [])
    return (
        member.id == member.guild.owner_id
        or member.guild_permissions.manage_guild
        or any(r.id in roles for r in member.roles)
    )


def require_access(service, member, guild=None):
    guild = guild or member.guild
    if not service.admission_enabled(guild.id):
        return
    role = service.get_setting(guild.id, "admission:member_role")
    if recruiter(service, member):
        return
    if not service.admitted(guild.id, member.id) or not any(r.id == role for r in member.roles):
        raise DomainError(
            "Ton premier café t'attend : termine l'accueil avec le staff avant de jouer."
        )


def entry_overwrites(guild, service, *, candidate=None, writable=False):
    result = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            connect=True,
            speak=True,
        ),
    }
    for rid in service.get_setting(guild.id, "admission:staff_roles", []):
        role = guild.get_role(rid)
        if role is None:
            raise DomainError("Un rôle de recrutement a disparu : fais vérifier l'accueil.")
        result[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            connect=True,
            speak=True,
        )
    if candidate:
        result[candidate] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=writable,
            read_message_history=True,
            attach_files=False,
            create_public_threads=False,
            create_private_threads=False,
            send_messages_in_threads=False,
            connect=writable,
            speak=writable,
        )
    return result


def reading_status(row):
    if row["status"] == "approved":
        return "**Bienvenue au Comptoir !** Le staff a validé ton accueil.\nCet espace reste privé et passe en lecture seule."
    if row["status"] == "refused":
        return "Le staff n'a pas validé cette arrivée. L'accès au Comptoir reste fermé.\nCet espace reste privé et passe en lecture seule ; aucun bannissement automatique."
    reading = "✅ Lecture confirmée" if row["read_at"] is not None else "📜 Lecture à confirmer"
    voice = (
        "\n🎧 Vocal souhaité : le staff peut ouvrir un espace privé."
        if row["voice_requested"]
        else ""
    )
    return (
        "Installe-toi, on prend un premier café ensemble ☕\n\n"
        "Lis la charte dans le salon dédié, puis clique sur **J'ai lu la charte**. "
        "Un mot de lecture te sera demandé dans une fenêtre privée.\n\n"
        "L'entretien se fait **à l'écrit**, à ton rythme. Tu peux demander un vocal si tu préfères. "
        "Le staff te demandera ce qui t'amène et vérifiera que tu partages l'esprit du lieu, "
        "réservé aux **21 ans et plus**. Aucune pièce d'identité n'est demandée.\n\n"
        "Les autres espaces s'ouvriront après une validation humaine.\n"
        "Pas besoin de donner ton nom civil, ta date de naissance ni d'autres informations sensibles.\n\n"
        + reading
        + voice
        + "\n\n*Les trois derniers boutons sont réservés au staff. "
        "Moka conserve l'état de l'accueil, sans exporter les échanges ni enregistrer le vocal.*"
    )


class ReadingModal(discord.ui.Modal, title="Un petit mot pour la charte"):
    keyword = discord.ui.TextInput(label="Le mot de lecture glissé dans la charte", max_length=80)

    async def on_submit(self, interaction):
        cog = interaction.client.get_cog("AdmissionCog")
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with cog.lock(interaction.guild_id, interaction.user.id):
            cog.candidate(interaction)
            valid = cog.service.confirm_reading(
                interaction.guild_id, interaction.user.id, str(self.keyword)
            )
            await cog.refresh(interaction.guild, interaction.user.id)
            if valid:
                await cog.notify_reading(interaction.guild, interaction.user.id)
        await interaction.followup.send(
            embed=card(
                "📜 Ta lecture",
                "✅ Lecture confirmée. Tu peux poursuivre l'échange avec le staff."
                if valid
                else "Ce n'est pas le mot attendu. Relis la charte tranquillement, puis réessaie.",
            ),
            ephemeral=True,
        )

    async def on_error(self, interaction, error):
        await handle_error(interaction, error)


class RefuseConfirmation(SafeView):
    def __init__(self, owner, channel):
        super().__init__(timeout=120)
        self.owner, self.channel = owner, channel

    @discord.ui.button(label="Confirmer le refus", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        if interaction.user.id != self.owner or interaction.channel_id != self.channel:
            raise DomainError("Cette confirmation appartient à un autre entretien.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.client.get_cog("AdmissionCog").decide(interaction, "refused")
        await interaction.edit_original_response(
            embed=card("🛎️ Accueil", "Décision enregistrée. Aucun bannissement."), view=None
        )


class AdmissionView(SafeView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="J'ai lu la charte", emoji="📜", custom_id="moka:admission:read", row=0
    )
    async def read(self, interaction, button):
        cog = interaction.client.get_cog("AdmissionCog")
        cog.candidate(interaction)
        await interaction.response.send_modal(ReadingModal())

    @discord.ui.button(
        label="Je préfère un vocal", emoji="🎧", custom_id="moka:admission:voice-request", row=0
    )
    async def voice_request(self, interaction, button):
        cog = interaction.client.get_cog("AdmissionCog")
        cog.candidate(interaction)
        await interaction.response.defer(ephemeral=True, thinking=True)
        cog.service.request_interview_voice(interaction.guild_id, interaction.user.id)
        await cog.refresh(interaction.guild, interaction.user.id)
        await interaction.followup.send(
            embed=card(
                "🎧 À ton rythme",
                "Demande notée. Le staff ouvrira un vocal privé lorsqu'il sera disponible.",
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Staff · ouvrir le vocal", custom_id="moka:admission:voice-open", row=1
    )
    async def open_voice(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        room = await interaction.client.get_cog("AdmissionCog").open_voice(interaction)
        await interaction.followup.send(
            embed=card(
                "🎧 Premier café en vocal",
                f"Le vocal privé est prêt : {room.mention}. Aucun enregistrement.",
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Staff · valider l'accueil",
        style=discord.ButtonStyle.success,
        custom_id="moka:admission:accept",
        row=1,
    )
    async def accept(self, interaction, button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await interaction.client.get_cog("AdmissionCog").decide(interaction, "approved")
        await interaction.followup.send(
            embed=card("☕ Accueil validé", "Décision enregistrée. Les accès sont ouverts."),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Staff · refuser",
        style=discord.ButtonStyle.danger,
        custom_id="moka:admission:refuse",
        row=1,
    )
    async def refuse(self, interaction, button):
        cog = interaction.client.get_cog("AdmissionCog")
        await cog.staff_candidate(interaction)
        await interaction.response.send_message(
            embed=card(
                "🛎️ Refuser cet accueil ?",
                "La personne restera à l'entrée, avec son entretien en lecture seule. Elle ne sera ni expulsée ni bannie.",
            ),
            view=RefuseConfirmation(interaction.user.id, interaction.channel_id),
            ephemeral=True,
        )
