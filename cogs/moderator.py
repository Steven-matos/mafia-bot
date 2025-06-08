import discord
from discord.ext import commands
from db.supabase_client import supabase
from typing import Optional
from datetime import datetime, timezone

class Moderator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_mod():
        """Check if user has moderator permissions."""
        async def predicate(ctx):
            return ctx.author.guild_permissions.manage_guild
        return commands.check(predicate)

    @commands.group(invoke_without_command=True)
    @is_mod()
    async def mod(self, ctx):
        """Moderator commands for server management."""
        await ctx.send_help(ctx.command)

    @mod.command(name="settings")
    @is_mod()
    async def view_settings(self, ctx):
        """View current server settings."""
        try:
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found! Please contact an administrator.")
                return

            embed = discord.Embed(
                title="⚙️ Server Settings",
                color=discord.Color.blue()
            )

            embed.add_field(name="Command Prefix", value=settings["prefix"], inline=True)
            embed.add_field(name="Daily Reward", value=f"${settings['daily_amount']:,}", inline=True)
            embed.add_field(name="Turf Capture Cooldown", value=f"{settings['turf_capture_cooldown']} hours", inline=True)
            embed.add_field(name="Heist Cooldown", value=f"{settings['heist_cooldown']} hours", inline=True)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="setprefix")
    @is_mod()
    async def set_prefix(self, ctx, new_prefix: str):
        """Set the server's command prefix."""
        try:
            if len(new_prefix) > 5:
                await ctx.send("Prefix must be 5 characters or less!")
                return

            success = await supabase.update_server_settings(
                str(ctx.guild.id),
                {"prefix": new_prefix}
            )

            if success:
                await ctx.send(f"Command prefix updated to: `{new_prefix}`")
            else:
                await ctx.send("Failed to update prefix. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="setdaily")
    @is_mod()
    async def set_daily(self, ctx, amount: int):
        """Set the daily reward amount."""
        try:
            if amount < 0:
                await ctx.send("Amount must be positive!")
                return

            success = await supabase.update_server_settings(
                str(ctx.guild.id),
                {"daily_amount": amount}
            )

            if success:
                await ctx.send(f"Daily reward amount updated to: ${amount:,}")
            else:
                await ctx.send("Failed to update daily amount. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="setcooldown")
    @is_mod()
    async def set_cooldown(self, ctx, type: str, hours: int):
        """Set cooldown for turf capture or heists."""
        try:
            if hours < 1:
                await ctx.send("Cooldown must be at least 1 hour!")
                return

            if type.lower() not in ["turf", "heist"]:
                await ctx.send("Invalid type! Use 'turf' or 'heist'.")
                return

            setting = "turf_capture_cooldown" if type.lower() == "turf" else "heist_cooldown"
            success = await supabase.update_server_settings(
                str(ctx.guild.id),
                {setting: hours}
            )

            if success:
                await ctx.send(f"{type.title()} cooldown updated to {hours} hours.")
            else:
                await ctx.send("Failed to update cooldown. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="resetuser")
    @is_mod()
    async def reset_user(self, ctx, member: discord.Member):
        """Reset a user's progress (money, family, etc.)."""
        try:
            # Get user data
            user = await supabase.get_user(str(member.id))
            if not user:
                await ctx.send("User not found!")
                return

            # Confirm reset
            confirm_embed = discord.Embed(
                title="⚠️ Confirm User Reset",
                description=f"Are you sure you want to reset {member.mention}'s progress?",
                color=discord.Color.red()
            )
            confirm_embed.add_field(name="Current Money", value=f"${user['money']:,}")
            confirm_embed.add_field(name="Current Bank", value=f"${user['bank']:,}")
            
            confirm_msg = await ctx.send(embed=confirm_embed)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except TimeoutError:
                await ctx.send("Reset cancelled - no response received.")
                return

            if str(reaction.emoji) == "❌":
                await ctx.send("Reset cancelled.")
                return

            # Reset user data
            success = await supabase.reset_user(str(member.id))
            if success:
                await ctx.send(f"{member.mention}'s progress has been reset.")
            else:
                await ctx.send("Failed to reset user. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="resetfamily")
    @is_mod()
    async def reset_family(self, ctx, family_name: str):
        """Reset a family's progress."""
        try:
            # Get family data
            family = await supabase.get_family_by_name(family_name)
            if not family:
                await ctx.send("Family not found!")
                return

            # Confirm reset
            confirm_embed = discord.Embed(
                title="⚠️ Confirm Family Reset",
                description=f"Are you sure you want to reset the {family_name} family?",
                color=discord.Color.red()
            )
            confirm_embed.add_field(name="Current Money", value=f"${family['family_money']:,}")
            confirm_embed.add_field(name="Current Reputation", value=str(family["reputation"]))
            
            confirm_msg = await ctx.send(embed=confirm_embed)
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except TimeoutError:
                await ctx.send("Reset cancelled - no response received.")
                return

            if str(reaction.emoji) == "❌":
                await ctx.send("Reset cancelled.")
                return

            # Reset family data
            success = await supabase.reset_family(family["id"])
            if success:
                await ctx.send(f"The {family_name} family has been reset.")
            else:
                await ctx.send("Failed to reset family. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="activity")
    @is_mod()
    async def view_activity(self, ctx, days: Optional[int] = 7):
        """View server activity for the past X days."""
        try:
            if days < 1 or days > 30:
                await ctx.send("Days must be between 1 and 30!")
                return

            # Get server transactions
            transactions = await supabase.get_server_transactions(str(ctx.guild.id), days)
            if not transactions:
                await ctx.send("No activity found for the specified period.")
                return

            # Group transactions by type
            transaction_types = {}
            for transaction in transactions:
                t_type = transaction["type"]
                if t_type not in transaction_types:
                    transaction_types[t_type] = 0
                transaction_types[t_type] += 1

            # Create embed
            embed = discord.Embed(
                title=f"📊 Server Activity (Last {days} days)",
                color=discord.Color.blue()
            )

            for t_type, count in transaction_types.items():
                embed.add_field(
                    name=t_type.replace("_", " ").title(),
                    value=str(count),
                    inline=True
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="ban")
    @is_mod()
    async def ban_user(self, ctx, member: discord.Member, *, reason: Optional[str] = None):
        """Ban a user from using the bot in this server."""
        try:
            # Check if user is already banned in this server
            banned_users = await supabase.get_banned_users(str(ctx.guild.id))
            if any(ban["user_id"] == str(member.id) for ban in banned_users):
                await ctx.send(f"{member.mention} is already banned in this server.")
                return

            # Ban user
            success = await supabase.ban_user(str(member.id), str(ctx.guild.id), reason)
            if success:
                embed = discord.Embed(
                    title="🚫 User Banned",
                    description=f"{member.mention} has been banned from using the bot in this server.",
                    color=discord.Color.red()
                )
                if reason:
                    embed.add_field(name="Reason", value=reason)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to ban user. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="unban")
    @is_mod()
    async def unban_user(self, ctx, member: discord.Member):
        """Unban a user from using the bot in this server."""
        try:
            # Check if user is banned in this server
            banned_users = await supabase.get_banned_users(str(ctx.guild.id))
            if not any(ban["user_id"] == str(member.id) for ban in banned_users):
                await ctx.send(f"{member.mention} is not banned in this server.")
                return

            # Unban user
            success = await supabase.unban_user(str(member.id), str(ctx.guild.id))
            if success:
                await ctx.send(f"{member.mention} has been unbanned from using the bot in this server.")
            else:
                await ctx.send("Failed to unban user. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="banned")
    @is_mod()
    async def list_banned(self, ctx):
        """List all banned users in this server."""
        try:
            banned_users = await supabase.get_banned_users(str(ctx.guild.id))
            if not banned_users:
                await ctx.send("No banned users found in this server.")
                return

            embed = discord.Embed(
                title="🚫 Banned Users",
                description="Users banned from using the bot in this server:",
                color=discord.Color.red()
            )

            for ban in banned_users:
                user = self.bot.get_user(int(ban["user_id"]))
                name = user.name if user else "Unknown"
                embed.add_field(
                    name=name,
                    value=f"Reason: {ban['reason'] or 'No reason provided'}\nBanned at: {ban['banned_at']}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mod.command(name="createturfs")
    @is_mod()
    async def create_turfs(self, ctx):
        """Create GTA V turfs for the server."""
        try:
            # Define GTA V turfs with their locations and base income
            turfs = [
                # Los Santos City Center
                {
                    "name": "Vinewood Hills",
                    "description": "Luxury residential area with high-end properties and celebrity homes",
                    "income": 5000,
                    "gta_coordinates": "Vinewood Hills"
                },
                {
                    "name": "Downtown Los Santos",
                    "description": "Business district with corporate offices and financial institutions",
                    "income": 4500,
                    "gta_coordinates": "Downtown LS"
                },
                {
                    "name": "Vinewood Boulevard",
                    "description": "Entertainment district with clubs, theaters, and tourist attractions",
                    "income": 4000,
                    "gta_coordinates": "Vinewood Blvd"
                },
                {
                    "name": "Rockford Hills",
                    "description": "Upscale shopping district with luxury boutiques",
                    "income": 4200,
                    "gta_coordinates": "Rockford Hills"
                },
                
                # Beach and Port Areas
                {
                    "name": "Vespucci Beach",
                    "description": "Popular beach area with tourist attractions and nightlife",
                    "income": 3500,
                    "gta_coordinates": "Vespucci Beach"
                },
                {
                    "name": "Del Perro Beach",
                    "description": "Coastal area with beachfront properties and pier",
                    "income": 3200,
                    "gta_coordinates": "Del Perro Beach"
                },
                {
                    "name": "Terminal",
                    "description": "Port area with shipping facilities and warehouses",
                    "income": 3800,
                    "gta_coordinates": "Terminal"
                },
                
                # South Los Santos
                {
                    "name": "Strawberry",
                    "description": "Working-class neighborhood with local businesses",
                    "income": 3000,
                    "gta_coordinates": "Strawberry"
                },
                {
                    "name": "Grove Street",
                    "description": "Historic gang territory with street influence",
                    "income": 2800,
                    "gta_coordinates": "Grove Street"
                },
                {
                    "name": "Davis",
                    "description": "Urban neighborhood with street markets",
                    "income": 2500,
                    "gta_coordinates": "Davis"
                },
                
                # East Los Santos
                {
                    "name": "La Mesa",
                    "description": "Industrial area with warehouses and factories",
                    "income": 3200,
                    "gta_coordinates": "La Mesa"
                },
                {
                    "name": "El Burro Heights",
                    "description": "Residential area with local businesses",
                    "income": 2200,
                    "gta_coordinates": "El Burro Heights"
                },
                
                # North Los Santos
                {
                    "name": "Mirror Park",
                    "description": "Hipster neighborhood with art galleries and cafes",
                    "income": 2800,
                    "gta_coordinates": "Mirror Park"
                },
                {
                    "name": "Burton",
                    "description": "Residential area with shopping centers",
                    "income": 2600,
                    "gta_coordinates": "Burton"
                },
                
                # Blaine County
                {
                    "name": "Sandy Shores",
                    "description": "Desert town with local businesses and airfield",
                    "income": 2000,
                    "gta_coordinates": "Sandy Shores"
                },
                {
                    "name": "Paleto Bay",
                    "description": "Coastal town with fishing industry and small businesses",
                    "income": 2200,
                    "gta_coordinates": "Paleto Bay"
                },
                {
                    "name": "Grapeseed",
                    "description": "Agricultural area with farms and rural businesses",
                    "income": 1800,
                    "gta_coordinates": "Grapeseed"
                },
                
                # Special Areas
                {
                    "name": "Fort Zancudo",
                    "description": "Military base with restricted access",
                    "income": 4800,
                    "gta_coordinates": "Fort Zancudo"
                },
                {
                    "name": "Los Santos International Airport",
                    "description": "Major transportation hub with cargo facilities",
                    "income": 4600,
                    "gta_coordinates": "LSIA"
                },
                {
                    "name": "Maze Bank Tower",
                    "description": "Financial district with corporate headquarters",
                    "income": 5200,
                    "gta_coordinates": "Maze Bank"
                },
                
                # Arena and Entertainment
                {
                    "name": "Arena Complex",
                    "description": "Massive entertainment complex hosting deathmatches and vehicle battles",
                    "income": 5500,
                    "gta_coordinates": "Arena War"
                },
                {
                    "name": "Diamond Casino",
                    "description": "Luxury casino and resort with high-stakes gambling",
                    "income": 6000,
                    "gta_coordinates": "Diamond Casino"
                },
                {
                    "name": "Maze Bank Arena",
                    "description": "Sports and entertainment venue for major events",
                    "income": 4800,
                    "gta_coordinates": "Maze Bank Arena"
                },
                {
                    "name": "Galileo Observatory",
                    "description": "Historic landmark with tourist attractions",
                    "income": 2800,
                    "gta_coordinates": "Galileo"
                },
                
                # Industrial and Manufacturing
                {
                    "name": "Humane Labs",
                    "description": "Research facility with valuable technology",
                    "income": 4500,
                    "gta_coordinates": "Humane Labs"
                },
                {
                    "name": "Bolingbroke Penitentiary",
                    "description": "Maximum security prison with restricted access",
                    "income": 4200,
                    "gta_coordinates": "Bolingbroke"
                },
                {
                    "name": "Palmer-Taylor Power Station",
                    "description": "Major power generation facility",
                    "income": 3800,
                    "gta_coordinates": "Power Station"
                },
                
                # Additional Areas
                {
                    "name": "Mount Chiliad",
                    "description": "Mountain area with tourist attractions and hiking trails",
                    "income": 2200,
                    "gta_coordinates": "Mount Chiliad"
                },
                {
                    "name": "Alamo Sea",
                    "description": "Large lake area with recreational activities",
                    "income": 2000,
                    "gta_coordinates": "Alamo Sea"
                },
                {
                    "name": "Great Chaparral",
                    "description": "Rural area with ranches and farms",
                    "income": 1800,
                    "gta_coordinates": "Great Chaparral"
                }
            ]

            # Create turfs
            success = await supabase.create_server_turfs(str(ctx.guild.id), turfs)
            
            if success:
                embed = discord.Embed(
                    title="🏢 Turfs Created",
                    description="Successfully created GTA V turfs for the server!",
                    color=discord.Color.green()
                )
                
                # Group turfs by region for better organization
                regions = {
                    "Los Santos City Center": [],
                    "Beach and Port Areas": [],
                    "South Los Santos": [],
                    "East Los Santos": [],
                    "North Los Santos": [],
                    "Blaine County": [],
                    "Special Areas": [],
                    "Arena and Entertainment": [],
                    "Industrial and Manufacturing": [],
                    "Additional Areas": []
                }
                
                for turf in turfs:
                    if "Vinewood" in turf["name"] or "Downtown" in turf["name"] or "Rockford" in turf["name"]:
                        regions["Los Santos City Center"].append(turf)
                    elif "Beach" in turf["name"] or "Terminal" in turf["name"]:
                        regions["Beach and Port Areas"].append(turf)
                    elif turf["name"] in ["Strawberry", "Grove Street", "Davis"]:
                        regions["South Los Santos"].append(turf)
                    elif "La Mesa" in turf["name"] or "El Burro" in turf["name"]:
                        regions["East Los Santos"].append(turf)
                    elif "Mirror" in turf["name"] or "Burton" in turf["name"]:
                        regions["North Los Santos"].append(turf)
                    elif turf["name"] in ["Sandy Shores", "Paleto Bay", "Grapeseed"]:
                        regions["Blaine County"].append(turf)
                    elif turf["name"] in ["Fort Zancudo", "Los Santos International Airport", "Maze Bank Tower"]:
                        regions["Special Areas"].append(turf)
                    elif "Arena" in turf["name"] or "Casino" in turf["name"] or "Observatory" in turf["name"]:
                        regions["Arena and Entertainment"].append(turf)
                    elif "Labs" in turf["name"] or "Penitentiary" in turf["name"] or "Power" in turf["name"]:
                        regions["Industrial and Manufacturing"].append(turf)
                    else:
                        regions["Additional Areas"].append(turf)
                
                # Add fields for each region
                for region, region_turfs in regions.items():
                    if region_turfs:
                        value = "\n".join([f"• {turf['name']} (${turf['income']:,}/hour)" for turf in region_turfs])
                        embed.add_field(name=region, value=value, inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to create turfs. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Moderator(bot)) 