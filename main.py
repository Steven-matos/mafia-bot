import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from db.supabase_client import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mafia-bot')

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Default prefix for the bot
DEFAULT_PREFIX = '!'

bot = commands.Bot(
    command_prefix=DEFAULT_PREFIX,
    intents=intents,
    help_command=None  # We'll implement a custom help command
)

# List of cogs to load
INITIAL_EXTENSIONS = [
    'cogs.economy',
    'cogs.family',
    'cogs.turf',
    'cogs.moderator',
    'cogs.hits',
    'cogs.relationships',
    'cogs.ranks',
    'cogs.channels',
    'cogs.mentorship',
    'cogs.recruitment',
    'cogs.assignments',
    'cogs.meetings',
    'cogs.help'
]

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    await bot.change_presence(
        activity=discord.Game(name="GTA V Crime Family RP | !help")
    )
    # Register all servers the bot is in
    for guild in bot.guilds:
        await register_server(guild)

@bot.event
async def on_guild_join(guild):
    """Handle when the bot joins a new server."""
    await register_server(guild)

@bot.event
async def on_member_join(member):
    """Handle when a new member joins a server."""
    try:
        # Add user to server in database
        await supabase.add_user_to_server(
            user_id=str(member.id),
            server_id=str(member.guild.id)
        )
    except Exception as e:
        print(f"Error adding user to server: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        logger.error(f"Command not found: {ctx.message.content}")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        logger.error(f"Command error: {error}")
        logger.error(f"Command context: {ctx.message.content}")
        logger.error(f"User: {ctx.author} (ID: {ctx.author.id})")
        logger.error(f"Channel: {ctx.channel} (ID: {ctx.channel.id})")
        logger.error(f"Guild: {ctx.guild} (ID: {ctx.guild.id})")
        await ctx.send("An error occurred while processing the command.")

@bot.event
async def on_command(ctx):
    """Check if user is banned in the server before executing command."""
    try:
        # Skip check for moderator commands
        if ctx.command.cog_name == "Moderator":
            return

        # Check if user is banned in this server
        banned_users = supabase.get_banned_users(str(ctx.guild.id))
        if any(ban["user_id"] == str(ctx.author.id) for ban in banned_users):
            await ctx.send("You are banned from using the bot in this server.")
            ctx.command_failed = True
    except Exception as e:
        print(f"Error checking user ban status: {str(e)}")

async def register_server(guild):
    """Register a server in the database."""
    try:
        # Check if server is already registered
        settings = supabase.get_server_settings(str(guild.id))
        if not settings:
            # Register new server
            await supabase.register_server(
                server_id=str(guild.id),
                name=guild.name
            )
            logger.info(f"Registered new server: {guild.name}")
    except Exception as e:
        logger.error(f"Error registering server {guild.name}: {e}")

async def load_extensions():
    """Load all bot extensions."""
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension}: {e}")

async def main():
    """Main entry point for the bot."""
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 