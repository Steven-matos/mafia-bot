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
            settings = supabase.get_server_settings(str(ctx.guild.id))
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
            settings = supabase.get_server_settings(str(ctx.guild.id))
            prefix = settings.get("prefix", "!") if settings else "!"

            if command is None:
                # Show main help menu
                embed = discord.Embed(
                    title="🤖 GTA V Crime Family Bot Help",
                    description=f"Here are all the available command categories. Use `{prefix}help <category>` for more details.",
                    color=discord.Color.blue()
                )

                # Add categories with more detailed descriptions
                categories = {
                    "Economy": "💰 Manage your money and bank account\nMain command: `balance`\n`balance`, `daily`, `transfer`, `rob`, `leaderboard`",
                    "Family": "👨‍👩‍👧‍👦 Manage your crime family\nMain command: `family`\n`family create`, `family join`, `family leave`, `family info`",
                    "Turf": "🗺️ Control and manage territories\nMain command: `turf`\n`turf capture`, `turf defend`, `turf list`, `turf income`",
                    "Hit System": "🎯 Manage hit contracts\nMain command: `hit`\n`hit request`, `hit list`, `hit complete`, `hit stats`",
                    "Family Relationships": "🤝 Manage family alliances and KOS\nMain command: `relationship`\n`relationship alliance`, `relationship kos`, `relationship list`",
                    "Family Ranks": "👑 Manage family hierarchy\nMain command: `rank`\n`rank create`, `rank set`, `rank list`, `rank delete`",
                    "Mentorship": "👨‍🏫 Manage mentor-mentee relationships\nMain command: `mentor`\n`mentor assign`, `mentor list`, `mentor end`, `mentor my`",
                    "Recruitment": "📝 Manage family recruitment process\nMain command: `recruitment`\n`recruitment addstep`, `recruitment remove`",
                    "Regime": "👥 Manage family regimes\nMain command: `regime`\n`regime create`, `regime list`, `regime assign`, `regime distribution`",
                    "Assignment": "📋 Manage regime assignments\nMain command: `assignment`\n`assignment create`, `assignment list`, `assignment complete`"
                }

                # Add moderator commands if user has permissions
                if ctx.author.guild_permissions.manage_guild:
                    categories["Moderator"] = "⚙️ Server management commands\nMain command: `mod`\n`mod settings`, `mod setprefix`, `mod setdaily`, `mod setcooldown`, `mod ban`, `mod unban`, `mod banned`, `mod userinfo`, `mod serverstats`, `mod resetuser`, `mod resetfamily`, `mod cleanup`, `mod backup`, `mod audit`"
                    categories["Bot Channels"] = "📢 Configure bot announcement channels\nMain command: `channel`\n`channel set`, `channel list`, `channel update`, `channel remove`, `channel types`"

                for category, description in categories.items():
                    embed.add_field(
                        name=category,
                        value=description,
                        inline=False
                    )

                embed.set_footer(text=f"Use {prefix}help <command> for detailed information about a specific command")
                await ctx.send(embed=embed)
                return

            # Show help for specific command or category
            command = command.lower()
            
            # Special handling for mod category
            if command == "mod" and ctx.author.guild_permissions.manage_guild:
                embed = discord.Embed(
                    title="⚙️ Moderator Commands",
                    description="Server management commands for moderators and administrators.",
                    color=discord.Color.blue()
                )
                
                mod_commands = {
                    "settings": "View current server settings",
                    "setprefix": "Set the server's command prefix",
                    "setdaily": "Set the daily reward amount",
                    "setcooldown": "Set cooldown for turf capture",
                    "createturfs": "Create all GTA V turfs for the server",
                    "ban": "Ban a user from using the bot in this server",
                    "unban": "Unban a user from using the bot in this server",
                    "banned": "List all banned users",
                    "userinfo": "Get detailed information about a user",
                    "serverstats": "View detailed server statistics",
                    "resetuser": "Reset a user's data (removes from family, resets balance)",
                    "resetfamily": "Reset a family's data (removes all members, resets balance)",
                    "cleanup": "Clean up database entries for users who have left the server",
                    "backup": "Create a backup of important server data",
                    "audit": "View recent server activity audit log",
                    "createuser": "Manually create a user in the database"
                }
                
                for cmd, desc in mod_commands.items():
                    embed.add_field(
                        name=f"{prefix}mod {cmd}",
                        value=desc,
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return

            # Handle other commands
            cmd = self.bot.get_command(command)
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
                subcommands = []
                for sub in cmd.commands:
                    # Get subcommand signature
                    params = []
                    for param in sub.clean_params.values():
                        if param.required:
                            params.append(f"<{param.name}>")
                        else:
                            params.append(f"[{param.name}]")
                    
                    usage = f"`{prefix}{cmd.name} {sub.name} {' '.join(params)}`"
                    subcommands.append(f"{usage}\n{sub.help or 'No description'}")
                
                if subcommands:
                    embed.add_field(
                        name="Subcommands",
                        value="\n\n".join(subcommands),
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

                # Add parameter descriptions if available
                if hasattr(cmd, "clean_params"):
                    param_descriptions = []
                    for param in cmd.clean_params.values():
                        desc = param.description if hasattr(param, "description") else "No description"
                        param_descriptions.append(f"`{param.name}`: {desc}")
                    
                    if param_descriptions:
                        embed.add_field(
                            name="Parameters",
                            value="\n".join(param_descriptions),
                            inline=False
                        )

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in help_command: {str(e)}")
            await ctx.send("An error occurred while showing help.")

async def setup(bot):
    await bot.add_cog(Help(bot)) 