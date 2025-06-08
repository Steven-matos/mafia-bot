import discord
from discord.ext import commands
import logging
from typing import Optional
from db.supabase_client import supabase

logger = logging.getLogger('mafia-bot')

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = None

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.command(name="prefix")
    async def prefix_command(self, ctx):
        """Show the bot's command prefix."""
        try:
            # Get server settings
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            prefix = settings.get("prefix", "!") if settings else "!"

            embed = discord.Embed(
                title="🤖 Bot Prefix",
                description=f"Use `{prefix}` before commands to interact with this bot.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Example",
                value=f"`{prefix}help` - Show help menu\n`{prefix}balance` - Check your balance",
                inline=False
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="help")
    async def help_command(self, ctx, command: Optional[str] = None):
        """Show help for commands."""
        try:
            # Get server settings for prefix
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            prefix = settings.get("prefix", "!") if settings else "!"

            if command is None:
                # Show main help menu
                embed = discord.Embed(
                    title="🤖 GTA V Crime Family Bot Help",
                    description=f"Here are all the available command categories. Use `{prefix}help <category>` for more details.",
                    color=discord.Color.blue()
                )

                # Add categories
                categories = {
                    "Economy": "💰 Manage your money and bank account",
                    "Family": "👨‍👩‍👧‍👦 Manage your crime family",
                    "Turf": "🗺️ Control and manage territories",
                    "Roleplay": "🎮 Participate in roleplay events",
                    "Hit System": "🎯 Manage hit contracts",
                    "Family Relationships": "🤝 Manage family alliances and KOS",
                    "Family Ranks": "👑 Manage family hierarchy",
                    "Mentorship": "👨‍🏫 Manage mentor-mentee relationships",
                    "Recruitment": "📝 Manage family recruitment process"
                }

                # Add moderator commands if user has permissions
                if ctx.author.guild_permissions.manage_guild:
                    categories["Moderator"] = "⚙️ Server management commands"
                    categories["Bot Channels"] = "📢 Configure bot announcement channels"

                for category, description in categories.items():
                    embed.add_field(
                        name=category,
                        value=description,
                        inline=False
                    )

                embed.set_footer(text=f"Use {prefix}help <command> for detailed information about a specific command")
                await ctx.send(embed=embed)
                return

            # Show help for specific command
            cmd = self.bot.get_command(command.lower())
            if cmd is None:
                await ctx.send(f"Command '{command}' not found.")
                return

            embed = discord.Embed(
                title=f"Command: {cmd.name}",
                description=cmd.help or "No description available",
                color=discord.Color.blue()
            )

            # Add usage information
            if isinstance(cmd, commands.Group):
                subcommands = [f"`{prefix}{cmd.name} {sub.name}` - {sub.help or 'No description'}" 
                             for sub in cmd.commands]
                if subcommands:
                    embed.add_field(
                        name="Subcommands",
                        value="\n".join(subcommands),
                        inline=False
                    )
            else:
                # Get command signature
                params = []
                for param in cmd.clean_params.values():
                    if param.required:
                        params.append(f"<{param.name}>")
                    else:
                        params.append(f"[{param.name}]")
                
                usage = f"`{prefix}{cmd.name} {' '.join(params)}`"
                embed.add_field(name="Usage", value=usage, inline=False)

            # Add permissions if any
            if hasattr(cmd, "checks"):
                for check in cmd.checks:
                    if hasattr(check, "__qualname__"):
                        if "is_family_leader" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Family Leader (Don)", inline=False)
                        elif "is_server_moderator" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Server Moderator", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Help(bot)) 