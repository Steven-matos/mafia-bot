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

                # Add categories with more detailed descriptions
                categories = {
                    "Economy": "💰 Manage your money and bank account\n`balance`, `daily`, `transfer`, `rob`, `leaderboard`",
                    "Family": "👨‍👩‍👧‍👦 Manage your crime family\n`family create`, `family join`, `family leave`, `family info`",
                    "Turf": "🗺️ Control and manage territories\n`turf capture`, `turf defend`, `turf list`, `turf income`",
                    "Roleplay": "🎮 Participate in roleplay events\n`rp start`, `rp join`, `rp leave`, `rp status`",
                    "Hit System": "🎯 Manage hit contracts\n`hit request`, `hit list`, `hit complete`, `hit stats`",
                    "Family Relationships": "🤝 Manage family alliances and KOS\n`relationship alliance`, `relationship kos`, `relationship list`",
                    "Family Ranks": "👑 Manage family hierarchy\n`rank create`, `rank set`, `rank list`, `rank delete`",
                    "Mentorship": "👨‍🏫 Manage mentor-mentee relationships\n`mentor assign`, `mentor list`, `mentor end`, `mentor my`",
                    "Recruitment": "📝 Manage family recruitment process\n`recruitment addstep`, `recruitment remove`"
                }

                # Add moderator commands if user has permissions
                if ctx.author.guild_permissions.manage_guild:
                    categories["Moderator"] = "⚙️ Server management commands\n`mod settings`, `mod setprefix`, `mod setdaily`, `mod setcooldown`"
                    categories["Bot Channels"] = "📢 Configure bot announcement channels\n`channel set`, `channel list`, `channel update`, `channel remove`"

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
                        if hasattr(param, "description"):
                            param_descriptions.append(f"`{param.name}`: {param.description}")
                    if param_descriptions:
                        embed.add_field(name="Parameters", value="\n".join(param_descriptions), inline=False)

            # Add permissions if any
            if hasattr(cmd, "checks"):
                for check in cmd.checks:
                    if hasattr(check, "__qualname__"):
                        if "is_family_leader" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Family Leader (Don)", inline=False)
                        elif "is_server_moderator" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Server Moderator", inline=False)
                        elif "is_eligible_for_hits" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Made Men or higher", inline=False)
                        elif "is_eligible_mentor" in check.__qualname__:
                            embed.add_field(name="Required Role", value="Made Men or Capo", inline=False)

            # Add examples if available
            if hasattr(cmd, "examples"):
                examples = cmd.examples
                if isinstance(examples, list):
                    examples = "\n".join(f"`{prefix}{ex}`" for ex in examples)
                embed.add_field(name="Examples", value=examples, inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Help(bot)) 