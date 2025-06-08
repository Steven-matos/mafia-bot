import discord
from discord.ext import commands
from discord import app_commands
from db.supabase_client import get_supabase_client
from typing import Optional, List

class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.supabase = get_supabase_client()
        self.announcement_types = {
            'all': 'All announcements',
            'family': 'Family-related announcements',
            'turf': 'Turf-related announcements',
            'economy': 'Economy-related announcements',
            'hits': 'Hit-related announcements',
            'mentorship': 'Mentorship-related announcements'
        }

    @commands.group(name='channel', invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def channel(self, ctx):
        """Manage bot announcement channels."""
        await ctx.send_help(ctx.command)

    @channel.command(name='set')
    @commands.has_permissions(manage_guild=True)
    async def set_channel(self, ctx, channel: discord.TextChannel, channel_type: str, announcement_type: str = 'all', interval_minutes: int = 60):
        """Set a channel for bot announcements.
        
        Parameters:
        -----------
        channel: The text channel to set
        channel_type: The type of channel (announcements, logs, etc.)
        announcement_type: The type of announcements to send (all, family, turf, economy, hits, mentorship)
        interval_minutes: How often to send announcements (in minutes)
        """
        if announcement_type not in self.announcement_types:
            await ctx.send(f"Invalid announcement type. Available types: {', '.join(self.announcement_types.keys())}")
            return

        if interval_minutes < 1:
            await ctx.send("Interval must be at least 1 minute.")
            return

        success = await self.supabase.set_bot_channel(
            str(ctx.guild.id),
            str(channel.id),
            channel_type,
            announcement_type,
            interval_minutes
        )

        if success:
            await ctx.send(f"Channel {channel.mention} has been set for {self.announcement_types[announcement_type]} with {interval_minutes} minute interval.")
        else:
            await ctx.send("Failed to set channel. Please try again.")

    @channel.command(name='list')
    @commands.has_permissions(manage_guild=True)
    async def list_channels(self, ctx):
        """List all configured bot channels and their settings."""
        channels = await self.supabase.get_all_bot_channels(str(ctx.guild.id))
        
        if not channels:
            await ctx.send("No channels configured.")
            return

        embed = discord.Embed(title="Bot Channels", color=discord.Color.blue())
        
        for channel_data in channels:
            channel = ctx.guild.get_channel(int(channel_data['channel_id']))
            if channel:
                value = (
                    f"Type: {channel_data['channel_type']}\n"
                    f"Announcements: {self.announcement_types[channel_data['announcement_type']]}\n"
                    f"Interval: {channel_data['interval_minutes']} minutes\n"
                    f"Status: {'Enabled' if channel_data['is_enabled'] else 'Disabled'}"
                )
                embed.add_field(name=channel.mention, value=value, inline=False)

        await ctx.send(embed=embed)

    @channel.command(name='update')
    @commands.has_permissions(manage_guild=True)
    async def update_channel(self, ctx, channel: discord.TextChannel, announcement_type: str, interval_minutes: Optional[int] = None, enabled: Optional[bool] = None):
        """Update settings for a specific channel and announcement type.
        
        Parameters:
        -----------
        channel: The text channel to update
        announcement_type: The type of announcements to update
        interval_minutes: New interval in minutes (optional)
        enabled: Whether the announcement type is enabled (optional)
        """
        if announcement_type not in self.announcement_types:
            await ctx.send(f"Invalid announcement type. Available types: {', '.join(self.announcement_types.keys())}")
            return

        if interval_minutes is not None and interval_minutes < 1:
            await ctx.send("Interval must be at least 1 minute.")
            return

        update_data = {}
        if interval_minutes is not None:
            update_data['interval_minutes'] = interval_minutes
        if enabled is not None:
            update_data['is_enabled'] = enabled

        if not update_data:
            await ctx.send("No changes specified.")
            return

        success = await self.supabase.update_bot_channel_settings(
            str(ctx.guild.id),
            str(channel.id),
            announcement_type,
            **update_data
        )

        if success:
            changes = []
            if interval_minutes is not None:
                changes.append(f"interval to {interval_minutes} minutes")
            if enabled is not None:
                changes.append(f"status to {'enabled' if enabled else 'disabled'}")
            
            await ctx.send(f"Updated {self.announcement_types[announcement_type]} in {channel.mention}: {', '.join(changes)}")
        else:
            await ctx.send("Failed to update channel settings. Please try again.")

    @channel.command(name='remove')
    @commands.has_permissions(manage_guild=True)
    async def remove_channel(self, ctx, channel: discord.TextChannel, announcement_type: str):
        """Remove a specific announcement type from a channel.
        
        Parameters:
        -----------
        channel: The text channel to remove
        announcement_type: The type of announcements to remove
        """
        if announcement_type not in self.announcement_types:
            await ctx.send(f"Invalid announcement type. Available types: {', '.join(self.announcement_types.keys())}")
            return

        success = await self.supabase.delete_bot_channel(
            str(ctx.guild.id),
            str(channel.id),
            announcement_type
        )

        if success:
            await ctx.send(f"Removed {self.announcement_types[announcement_type]} from {channel.mention}")
        else:
            await ctx.send("Failed to remove channel. Please try again.")

    @channel.command(name='types')
    @commands.has_permissions(manage_guild=True)
    async def list_types(self, ctx):
        """List all available announcement types."""
        embed = discord.Embed(title="Available Announcement Types", color=discord.Color.blue())
        
        for type_id, description in self.announcement_types.items():
            embed.add_field(name=type_id, value=description, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Channels(bot)) 