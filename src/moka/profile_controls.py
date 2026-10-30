"""Propriété et durée de vie des écrans privés du profil."""

import contextlib

import discord

from moka.base import DomainError
from moka.discord_ui import SafeView, context


def owner_context(interaction, guild_id, owner):
    guild, user, key = context(interaction)
    if guild != guild_id or user != owner:
        raise DomainError("Ces boutons appartiennent à un autre profil. Ouvre /profile.")
    return guild, user, key


class ProfilePanel(SafeView):
    def __init__(self, guild, owner):
        super().__init__(timeout=180)
        self.guild_id, self.owner = guild, owner
        self.message = None
        self.expired = False

    async def interaction_check(self, interaction):
        owner_context(interaction, self.guild_id, self.owner)
        return True

    def stop(self):
        self.message = None
        super().stop()

    async def on_timeout(self):
        self.expired = True
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)
