import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union
from datetime import datetime, timedelta, timezone
import pytz
import logging
from utils.checks import is_family_don, is_family_member
from db.supabase_client import supabase

logger = logging.getLogger('mafia-bot')

# Security constants
MAX_PREFIX_LENGTH = 5
MAX_DAILY_AMOUNT = 1000000  # $1M max daily
MIN_COOLDOWN = 1  # Minimum cooldown in hours
MAX_COOLDOWN = 168  # Maximum cooldown in hours (1 week)
MAX_AUDIT_DAYS = 30  # Maximum days for audit log
MAX_BAN_REASON_LENGTH = 1000  # Maximum length for ban reason

class CreateUserModal(discord.ui.Modal, title='Create New User'):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member
        
        # Add form fields
        self.initial_money = discord.ui.TextInput(
            label='Initial Money',
            placeholder='Enter starting money amount (default: 0)',
            required=False,
            default='0'
        )
        self.initial_bank = discord.ui.TextInput(
            label='Initial Bank Balance',
            placeholder='Enter starting bank balance (default: 0)',
            required=False,
            default='0'
        )
        self.psn = discord.ui.TextInput(
            label='PlayStation Network ID',
            placeholder='Enter PSN ID (optional)',
            required=False
        )
        self.notes = discord.ui.TextInput(
            label='Notes',
            placeholder='Any additional notes about this user',
            required=False,
            style=discord.TextStyle.paragraph
        )
        
        # Add fields to modal
        self.add_item(self.initial_money)
        self.add_item(self.initial_bank)
        self.add_item(self.psn)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate money inputs
            try:
                money = int(self.initial_money.value) if self.initial_money.value else 0
                bank = int(self.initial_bank.value) if self.initial_bank.value else 0
                if money < 0 or bank < 0:
                    await interaction.response.send_message("❌ Money and bank values cannot be negative!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Money and bank values must be valid numbers!", ephemeral=True)
                return

            # Check if user already exists
            user = await supabase.get_user(str(self.member.id))
            if user:
                await interaction.response.send_message(f"❌ User {self.member.mention} already exists in the database!", ephemeral=True)
                return

            # Create user data
            user_data = {
                "id": str(self.member.id),
                "username": self.member.name,
                "money": money,
                "bank": bank,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # Add PSN if provided
            if self.psn.value:
                # Check if PSN is already taken
                existing_user = supabase.table('users').select('id').eq('psn', self.psn.value).execute()
                if existing_user.data:
                    await interaction.response.send_message("❌ This PSN is already registered to another user!", ephemeral=True)
                    return
                user_data["psn"] = self.psn.value

            # Create user
            success = await supabase.create_user(str(self.member.id), self.member.name)
            if success:
                # Add user to server
                await supabase.add_user_to_server(str(self.member.id), str(interaction.guild_id))
                
                # Update user with form data
                await supabase.update_user(str(self.member.id), user_data)
                
                # Create embed for confirmation
                embed = discord.Embed(
                    title="✅ User Created Successfully",
                    color=discord.Color.green()
                )
                embed.add_field(name="User", value=self.member.mention, inline=True)
                embed.add_field(name="Initial Money", value=f"${money:,}", inline=True)
                embed.add_field(name="Initial Bank", value=f"${bank:,}", inline=True)
                if self.psn.value:
                    embed.add_field(name="PSN ID", value=self.psn.value, inline=True)
                if self.notes.value:
                    embed.add_field(name="Notes", value=self.notes.value, inline=False)
                
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("❌ Failed to create user. Please try again.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

class Moderator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_command = {}  # For rate limiting

    def is_admin():
        """Check if user has administrator permissions."""
        async def predicate(ctx):
            return ctx.author.guild_permissions.administrator
        return commands.check(predicate)

    def is_mod():
        """Check if user has moderator permissions."""
        async def predicate(ctx):
            return ctx.author.guild_permissions.manage_guild
        return commands.check(predicate)

    def rate_limit(self, ctx, seconds: int = 5):
        """Rate limit command usage."""
        current_time = datetime.now().timestamp()
        last_used = self._last_command.get(ctx.author.id, 0)
        
        if current_time - last_used < seconds:
            return False
        
        self._last_command[ctx.author.id] = current_time
        return True

    async def log_mod_action(self, ctx, action: str, target: Union[discord.Member, str], reason: Optional[str] = None):
        """Log moderator actions to database."""
        try:
            await supabase.table('mod_logs').insert({
                'server_id': str(ctx.guild.id),
                'moderator_id': str(ctx.author.id),
                'action': action,
                'target_id': str(target.id) if isinstance(target, discord.Member) else target,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log moderator action: {str(e)}")

    @commands.group(invoke_without_command=True)
    @is_mod()
    async def mod(self, ctx):
        """Moderator commands for server management"""
        try:
            if not ctx.author.guild_permissions.manage_guild:
                await ctx.send("❌ You need the 'Manage Server' permission to use moderator commands.")
                return
            
            # Create help embed
            embed = discord.Embed(
                title="Moderator Commands",
                description="Available moderator commands:",
                color=discord.Color.blue()
            )
            
            # Add command fields
            embed.add_field(
                name="!mod settings",
                value="View current server settings",
                inline=False
            )
            embed.add_field(
                name="!mod userinfo <user>",
                value="Get detailed information about a user",
                inline=False
            )
            embed.add_field(
                name="!mod serverstats",
                value="View server statistics",
                inline=False
            )
            embed.add_field(
                name="!mod ban <user> [reason]",
                value="Ban a user from using the bot",
                inline=False
            )
            embed.add_field(
                name="!mod unban <user>",
                value="Unban a user from using the bot",
                inline=False
            )
            embed.add_field(
                name="!mod banned",
                value="List all banned users",
                inline=False
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in mod command: {str(e)}")
            await ctx.send(f"An error occurred while processing the command: {str(e)}")

    @mod.command(name="settings")
    @is_mod()
    async def view_settings(self, ctx):
        """View current server settings."""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ You need the 'Manage Server' permission to view server settings.")
            return
        try:
            if not self.rate_limit(ctx):
                await ctx.send("Please wait a few seconds before using this command again.")
                return

            settings = supabase.get_server_settings(str(ctx.guild.id))
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
            logger.error(f"Error in view_settings: {str(e)}")
            await ctx.send(f"An error occurred while fetching server settings: {str(e)}")

    @mod.command(name="setprefix")
    @is_admin()  # Only admins can change prefix
    async def set_prefix(self, ctx, new_prefix: str):
        """Set the server's command prefix."""
        try:
            if not self.rate_limit(ctx, 10):  # 10 second cooldown for prefix changes
                await ctx.send("Please wait 10 seconds before changing the prefix again.")
                return

            if len(new_prefix) > MAX_PREFIX_LENGTH:
                await ctx.send(f"Prefix must be {MAX_PREFIX_LENGTH} characters or less!")
                return

            # Validate prefix characters
            if not all(c.isalnum() or c in '!@#$%^&*()_+-=[]{}|;:,.<>?/~`' for c in new_prefix):
                await ctx.send("Prefix contains invalid characters!")
                return

            success = await supabase.update_server_settings(
                str(ctx.guild.id),
                {"prefix": new_prefix}
            )

            if success:
                await self.log_mod_action(ctx, "set_prefix", new_prefix)
                await ctx.send(f"Command prefix updated to: `{new_prefix}`")
            else:
                await ctx.send("Failed to update prefix. Please try again.")
        except Exception as e:
            logger.error(f"Error in set_prefix: {str(e)}")
            await ctx.send("An error occurred while updating the prefix.")

    @mod.command(name="setdaily")
    @is_admin()  # Only admins can change daily amount
    async def set_daily(self, ctx, amount: int):
        """Set the daily reward amount."""
        try:
            if not self.rate_limit(ctx, 10):
                await ctx.send("Please wait 10 seconds before changing the daily amount again.")
                return

            if amount < 0 or amount > MAX_DAILY_AMOUNT:
                await ctx.send(f"Amount must be between 0 and ${MAX_DAILY_AMOUNT:,}!")
                return

            success = await supabase.update_server_settings(
                str(ctx.guild.id),
                {"daily_amount": amount}
            )

            if success:
                await self.log_mod_action(ctx, "set_daily", str(amount))
                await ctx.send(f"Daily reward amount updated to: ${amount:,}")
            else:
                await ctx.send("Failed to update daily amount. Please try again.")
        except Exception as e:
            logger.error(f"Error in set_daily: {str(e)}")
            await ctx.send("An error occurred while updating the daily amount.")

    @mod.command(name="setcooldown")
    @is_admin()  # Only admins can change cooldowns
    async def set_cooldown(self, ctx, type: str, hours: int):
        """Set cooldown for turf capture or heists."""
        try:
            if not self.rate_limit(ctx, 10):
                await ctx.send("Please wait 10 seconds before changing cooldowns again.")
                return

            if hours < MIN_COOLDOWN or hours > MAX_COOLDOWN:
                await ctx.send(f"Cooldown must be between {MIN_COOLDOWN} and {MAX_COOLDOWN} hours!")
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
                await self.log_mod_action(ctx, "set_cooldown", f"{type}:{hours}")
                await ctx.send(f"{type.title()} cooldown updated to {hours} hours.")
            else:
                await ctx.send("Failed to update cooldown. Please try again.")
        except Exception as e:
            logger.error(f"Error in set_cooldown: {str(e)}")
            await ctx.send("An error occurred while updating the cooldown.")

    @mod.command(name="userinfo")
    @is_mod()
    async def user_info(self, ctx, member: discord.Member):
        """Get detailed information about a user"""
        try:
            # Get user data from database
            user_data = supabase.table('users').select('*').eq('id', str(member.id)).execute()
            family_data = None
            regime_data = None
            hit_stats = None
            
            if user_data.data:
                user = user_data.data[0]
                # Get family info if user is in a family
                if user.get('family_id'):
                    family = supabase.table('families').select('*').eq('id', user['family_id']).execute()
                    if family.data:
                        family_data = family.data[0]
                        # Get regime info
                        regime = supabase.table('family_members').select('regime_id').eq('user_id', str(member.id)).execute()
                        if regime.data and regime.data[0].get('regime_id'):
                            regime_info = supabase.table('regimes').select('*').eq('id', regime.data[0]['regime_id']).execute()
                            if regime_info.data:
                                regime_data = regime_info.data[0]
                
                # Get hit statistics
                hit_stats = supabase.table('hit_stats').select('*').eq('user_id', str(member.id)).execute()
                if hit_stats.data:
                    hit_stats = hit_stats.data[0]

            # Create embed
            embed = discord.Embed(
                title=f"User Information: {member.display_name}",
                color=member.color
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Basic Discord info
            embed.add_field(
                name="Discord Info",
                value=f"ID: {member.id}\n"
                      f"Joined: <t:{int(member.joined_at.timestamp())}:R>\n"
                      f"Account Created: <t:{int(member.created_at.timestamp())}:R>",
                inline=False
            )

            # Family info
            if family_data:
                embed.add_field(
                    name="Family Info",
                    value=f"Family: {family_data['name']}\n"
                          f"Rank: {user.get('family_rank_id', 'None')}\n"
                          f"Member Since: <t:{int(datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')).timestamp())}:R>",
                    inline=False
                )

            # Regime info
            if regime_data:
                embed.add_field(
                    name="Regime Info",
                    value=f"Regime: {regime_data['name']}\n"
                          f"Leader: {ctx.guild.get_member(int(regime_data['leader_id'])).mention if ctx.guild.get_member(int(regime_data['leader_id'])) else 'Unknown'}",
                    inline=False
                )

            # Hit statistics
            if hit_stats:
                success_rate = (hit_stats['successful_hits'] / hit_stats['total_hits'] * 100) if hit_stats['total_hits'] > 0 else 0
                embed.add_field(
                    name="Hit Statistics",
                    value=f"Total Hits: {hit_stats['total_hits']}\n"
                          f"Successful: {hit_stats['successful_hits']}\n"
                          f"Failed: {hit_stats['failed_hits']}\n"
                          f"Success Rate: {success_rate:.1f}%\n"
                          f"Total Payout: ${hit_stats['total_payout']:,}",
                    inline=False
                )

            # Economy info
            if user_data.data:
                user = user_data.data[0]
                embed.add_field(
                    name="Economy",
                    value=f"Cash: ${user.get('money', 0):,}\n"
                          f"Bank: ${user.get('bank', 0):,}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error getting user info: {str(e)}")

    @mod.command(name="serverstats")
    @is_mod()
    async def server_stats(self, ctx):
        """Get detailed statistics about the server"""
        try:
            # Get server data
            server_data = supabase.table('servers').select('*').eq('id', str(ctx.guild.id)).execute()
            if not server_data.data:
                return await ctx.send("❌ Server not found in database.")

            # Get family data
            families = supabase.table('families').select('*').eq('main_server_id', str(ctx.guild.id)).execute()
            
            # Get user statistics
            users = supabase.table('users').select('*').execute()
            family_members = supabase.table('family_members').select('*').execute()
            
            # Get hit statistics
            hit_stats = supabase.table('hit_stats').select('*').execute()
            
            # Calculate statistics
            total_users = len(users.data) if users.data else 0
            total_families = len(families.data) if families.data else 0
            total_family_members = len(family_members.data) if family_members.data else 0
            total_hits = sum(stat['total_hits'] for stat in hit_stats.data) if hit_stats.data else 0
            total_successful_hits = sum(stat['successful_hits'] for stat in hit_stats.data) if hit_stats.data else 0
            total_payout = sum(stat['total_payout'] for stat in hit_stats.data) if hit_stats.data else 0

            # Create embed
            embed = discord.Embed(
                title=f"Server Statistics: {ctx.guild.name}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

            # Server Info
            embed.add_field(
                name="Server Info",
                value=f"Members: {ctx.guild.member_count}\n"
                      f"Created: <t:{int(ctx.guild.created_at.timestamp())}:R>",
                inline=False
            )

            # Family Statistics
            embed.add_field(
                name="Family Statistics",
                value=f"Total Families: {total_families}\n"
                      f"Total Family Members: {total_family_members}\n"
                      f"Average Members per Family: {total_family_members/total_families:.1f}" if total_families > 0 else "No families",
                inline=False
            )

            # Hit Statistics
            success_rate = (total_successful_hits / total_hits * 100) if total_hits > 0 else 0
            embed.add_field(
                name="Hit Statistics",
                value=f"Total Hits: {total_hits}\n"
                      f"Successful Hits: {total_successful_hits}\n"
                      f"Success Rate: {success_rate:.1f}%\n"
                      f"Total Payout: ${total_payout:,}",
                inline=False
            )

            # Top Families
            if families.data:
                top_families = sorted(families.data, key=lambda x: x.get('reputation', 0), reverse=True)[:5]
                family_list = "\n".join([f"{i+1}. {f['name']} - Rep: {f.get('reputation', 0)}" for i, f in enumerate(top_families)])
                embed.add_field(
                    name="Top 5 Families by Reputation",
                    value=family_list,
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error getting server stats: {str(e)}")

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

    @mod.command(name="cleanup")
    @is_mod()
    async def cleanup_database(self, ctx):
        """Clean up database entries for users who have left the server"""
        try:
            # Get all users in database
            users = supabase.table('users').select('*').execute()
            if not users.data:
                return await ctx.send("No users found in database.")

            # Get all server members
            server_members = set(str(member.id) for member in ctx.guild.members)

            # Find users who have left
            left_users = [user for user in users.data if user['id'] not in server_members]

            if not left_users:
                return await ctx.send("No cleanup needed - all users are still in the server.")

            # Confirm cleanup
            confirm_msg = await ctx.send(
                f"Found {len(left_users)} users who have left the server.\n"
                "This will remove their data from the database.\n"
                "React with ✅ to confirm or ❌ to cancel."
            )
            await confirm_msg.add_reaction("✅")
            await confirm_msg.add_reaction("❌")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except TimeoutError:
                return await ctx.send("Cleanup cancelled - no response received.")

            if str(reaction.emoji) == "❌":
                return await ctx.send("Cleanup cancelled.")

            # Perform cleanup
            cleaned = 0
            for user in left_users:
                try:
                    # Remove user data
                    supabase.table('users').delete().eq('id', user['id']).execute()
                    supabase.table('family_members').delete().eq('user_id', user['id']).execute()
                    supabase.table('hit_stats').delete().eq('user_id', user['id']).execute()
                    cleaned += 1
                except Exception as e:
                    print(f"Error cleaning up user {user['id']}: {str(e)}")

            await ctx.send(f"✅ Cleanup complete. Removed data for {cleaned} users.")
        except Exception as e:
            await ctx.send(f"❌ Error during cleanup: {str(e)}")

    @mod.command(name="backup")
    @is_mod()
    async def backup_database(self, ctx):
        """Create a backup of important server data"""
        try:
            # Get all important data
            families = supabase.table('families').select('*').execute()
            users = supabase.table('users').select('*').execute()
            family_members = supabase.table('family_members').select('*').execute()
            hit_stats = supabase.table('hit_stats').select('*').execute()
            regimes = supabase.table('regimes').select('*').execute()

            # Create backup file
            backup_data = {
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'server_id': str(ctx.guild.id),
                'server_name': ctx.guild.name,
                'families': families.data if families.data else [],
                'users': users.data if users.data else [],
                'family_members': family_members.data if family_members.data else [],
                'hit_stats': hit_stats.data if hit_stats.data else [],
                'regimes': regimes.data if regimes.data else []
            }

            # Save to file
            filename = f"backup_{ctx.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                import json
                json.dump(backup_data, f, indent=2)

            # Send file
            await ctx.send("✅ Backup created successfully!", file=discord.File(filename))
        except Exception as e:
            await ctx.send(f"❌ Error creating backup: {str(e)}")

    @mod.command(name="audit")
    @is_mod()
    async def audit_log(self, ctx, days: int = 7):
        """View recent server activity audit log"""
        try:
            if not self.rate_limit(ctx, 10):
                await ctx.send("Please wait 10 seconds before checking the audit log again.")
                return

            if days < 1 or days > MAX_AUDIT_DAYS:
                await ctx.send(f"Days must be between 1 and {MAX_AUDIT_DAYS}!")
                return

            # Get recent transactions
            transactions = supabase.table('transactions').select('*').gte('timestamp', (datetime.now(pytz.UTC) - timedelta(days=days)).isoformat()).execute()
            
            # Get recent hit contracts
            hits = supabase.table('hit_contracts').select('*').gte('created_at', (datetime.now(pytz.UTC) - timedelta(days=days)).isoformat()).execute()
            
            # Get recent family changes
            family_changes = supabase.table('family_members').select('*').gte('created_at', (datetime.now(pytz.UTC) - timedelta(days=days)).isoformat()).execute()

            embed = discord.Embed(
                title=f"Server Audit Log - Last {days} Days",
                color=discord.Color.blue()
            )

            # Transaction summary
            if transactions.data:
                total_transactions = len(transactions.data)
                total_amount = sum(t['amount'] for t in transactions.data)
                embed.add_field(
                    name="Transaction Summary",
                    value=f"Total Transactions: {total_transactions}\n"
                          f"Total Amount: ${total_amount:,}",
                    inline=False
                )

            # Hit contract summary
            if hits.data:
                total_hits = len(hits.data)
                successful_hits = len([h for h in hits.data if h['status'] == 'completed'])
                embed.add_field(
                    name="Hit Contract Summary",
                    value=f"Total Contracts: {total_hits}\n"
                          f"Successful Hits: {successful_hits}\n"
                          f"Success Rate: {(successful_hits/total_hits*100):.1f}%",
                    inline=False
                )

            # Family changes summary
            if family_changes.data:
                new_members = len(family_changes.data)
                embed.add_field(
                    name="Family Changes",
                    value=f"New Family Members: {new_members}",
                    inline=False
                )

            # Recent activity
            recent_activity = []
            for t in transactions.data[:5]:
                recent_activity.append(f"Transaction: ${t['amount']:,} - {t['type']}")
            for h in hits.data[:5]:
                recent_activity.append(f"Hit Contract: {h['status']} - ${h['reward']:,}")
            
            if recent_activity:
                embed.add_field(
                    name="Recent Activity",
                    value="\n".join(recent_activity),
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in audit_log: {str(e)}")
            await ctx.send("An error occurred while fetching the audit log.")

    @mod.command(name="ban")
    @is_mod()
    async def ban_user(self, ctx, member: discord.Member, *, reason: Optional[str] = None):
        """Ban a user from using the bot."""
        try:
            if not self.rate_limit(ctx, 5):
                await ctx.send("Please wait 5 seconds before banning another user.")
                return

            # Check if user is trying to ban themselves
            if member.id == ctx.author.id:
                await ctx.send("You cannot ban yourself!")
                return

            # Check if user is trying to ban a bot
            if member.bot:
                await ctx.send("You cannot ban bots!")
                return

            # Check if user is trying to ban someone with higher permissions
            if member.top_role >= ctx.author.top_role:
                await ctx.send("You cannot ban someone with higher or equal permissions!")
                return

            # Validate reason length
            if reason and len(reason) > MAX_BAN_REASON_LENGTH:
                await ctx.send(f"Ban reason must be {MAX_BAN_REASON_LENGTH} characters or less!")
                return

            # Check if user is already banned
            existing_ban = supabase.get_banned_user(str(member.id), str(ctx.guild.id))
            if existing_ban:
                await ctx.send("This user is already banned!")
                return

            # Ban the user
            success = await supabase.ban_user(
                user_id=str(member.id),
                server_id=str(ctx.guild.id),
                reason=reason
            )

            if success:
                await self.log_mod_action(ctx, "ban", member, reason)
                await ctx.send(f"Successfully banned {member.mention} from using the bot.")
            else:
                await ctx.send("Failed to ban user. Please try again.")
        except Exception as e:
            logger.error(f"Error in ban_user: {str(e)}")
            await ctx.send("An error occurred while banning the user.")

    @mod.command(name="unban")
    @is_mod()
    async def unban_user(self, ctx, member: discord.Member):
        """Unban a user from using the bot."""
        try:
            if not self.rate_limit(ctx, 5):
                await ctx.send("Please wait 5 seconds before unbanning another user.")
                return

            # Check if user is banned
            existing_ban = supabase.get_banned_user(str(member.id), str(ctx.guild.id))
            if not existing_ban:
                await ctx.send("This user is not banned!")
                return

            # Unban the user
            success = await supabase.unban_user(str(member.id), str(ctx.guild.id))

            if success:
                await self.log_mod_action(ctx, "unban", member)
                await ctx.send(f"Successfully unbanned {member.mention} from using the bot.")
            else:
                await ctx.send("Failed to unban user. Please try again.")
        except Exception as e:
            logger.error(f"Error in unban_user: {str(e)}")
            await ctx.send("An error occurred while unbanning the user.")

    @mod.command(name="banned")
    @is_mod()
    async def list_banned(self, ctx):
        """List all banned users in this server."""
        try:
            banned_users = supabase.get_banned_users(str(ctx.guild.id))
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
            # Define GTA V turfs with their locations
            turfs = [
                # Los Santos City Center
                {
                    "name": "Vinewood Hills",
                    "description": "Luxury residential area with high-end properties and celebrity homes",
                    "gta_coordinates": "Vinewood Hills"
                },
                {
                    "name": "Downtown Los Santos",
                    "description": "Business district with corporate offices and financial institutions",
                    "gta_coordinates": "Downtown LS"
                },
                {
                    "name": "Vinewood Boulevard",
                    "description": "Entertainment district with clubs, theaters, and tourist attractions",
                    "gta_coordinates": "Vinewood Blvd"
                },
                {
                    "name": "Rockford Hills",
                    "description": "Upscale shopping district with luxury boutiques",
                    "gta_coordinates": "Rockford Hills"
                },
                
                # Beach and Port Areas
                {
                    "name": "Vespucci Beach",
                    "description": "Popular beach area with tourist attractions and nightlife",
                    "gta_coordinates": "Vespucci Beach"
                },
                {
                    "name": "Del Perro Beach",
                    "description": "Coastal area with beachfront properties and pier",
                    "gta_coordinates": "Del Perro Beach"
                },
                {
                    "name": "Terminal",
                    "description": "Port area with shipping facilities and warehouses",
                    "gta_coordinates": "Terminal"
                },
                
                # South Los Santos
                {
                    "name": "Strawberry",
                    "description": "Working-class neighborhood with local businesses",
                    "gta_coordinates": "Strawberry"
                },
                {
                    "name": "Grove Street",
                    "description": "Historic gang territory with street influence",
                    "gta_coordinates": "Grove Street"
                },
                {
                    "name": "Davis",
                    "description": "Urban neighborhood with street markets",
                    "gta_coordinates": "Davis"
                },
                
                # East Los Santos
                {
                    "name": "La Mesa",
                    "description": "Industrial area with warehouses and factories",
                    "gta_coordinates": "La Mesa"
                },
                {
                    "name": "El Burro Heights",
                    "description": "Residential area with local businesses",
                    "gta_coordinates": "El Burro Heights"
                },
                
                # North Los Santos
                {
                    "name": "Mirror Park",
                    "description": "Hipster neighborhood with art galleries and cafes",
                    "gta_coordinates": "Mirror Park"
                },
                {
                    "name": "Burton",
                    "description": "Residential area with shopping centers",
                    "gta_coordinates": "Burton"
                },
                
                # Blaine County (Rural Areas)
                {
                    "name": "Sandy Shores",
                    "description": "Desert town with local businesses and airfield",
                    "gta_coordinates": "Sandy Shores"
                },
                {
                    "name": "Paleto Bay",
                    "description": "Coastal town with fishing industry and small businesses",
                    "gta_coordinates": "Paleto Bay"
                },
                {
                    "name": "Grapeseed",
                    "description": "Agricultural area with farms and rural businesses",
                    "gta_coordinates": "Grapeseed"
                },
                
                # Special Areas
                {
                    "name": "Fort Zancudo",
                    "description": "Military base with restricted access",
                    "gta_coordinates": "Fort Zancudo"
                },
                {
                    "name": "Los Santos International Airport",
                    "description": "Major transportation hub with cargo facilities",
                    "gta_coordinates": "LSIA"
                },
                {
                    "name": "Maze Bank Tower",
                    "description": "Financial district with corporate headquarters",
                    "gta_coordinates": "Maze Bank"
                },
                
                # Arena and Entertainment (Special Areas)
                {
                    "name": "Arena Complex",
                    "description": "Massive entertainment complex hosting deathmatches and vehicle battles",
                    "gta_coordinates": "Arena War"
                },
                {
                    "name": "Diamond Casino",
                    "description": "Luxury casino and resort with high-stakes gambling",
                    "gta_coordinates": "Diamond Casino"
                },
                {
                    "name": "Maze Bank Arena",
                    "description": "Sports and entertainment venue for major events",
                    "gta_coordinates": "Maze Bank Arena"
                },
                {
                    "name": "Galileo Observatory",
                    "description": "Historic landmark with tourist attractions",
                    "gta_coordinates": "Galileo"
                },
                
                # Industrial and Manufacturing (Special Areas)
                {
                    "name": "Humane Labs",
                    "description": "Research facility with valuable technology",
                    "gta_coordinates": "Humane Labs"
                },
                {
                    "name": "Bolingbroke Penitentiary",
                    "description": "Maximum security prison with restricted access",
                    "gta_coordinates": "Bolingbroke"
                },
                {
                    "name": "Palmer-Taylor Power Station",
                    "description": "Major power generation facility",
                    "gta_coordinates": "Power Station"
                },
                
                # Additional Areas (Rural)
                {
                    "name": "Mount Chiliad",
                    "description": "Mountain area with tourist attractions and hiking trails",
                    "gta_coordinates": "Mount Chiliad"
                },
                {
                    "name": "Alamo Sea",
                    "description": "Large lake area with recreational activities",
                    "gta_coordinates": "Alamo Sea"
                },
                {
                    "name": "Great Chaparral",
                    "description": "Rural area with ranches and farms",
                    "gta_coordinates": "Great Chaparral"
                }
            ]

            # Create turfs in database
            async with self.bot.pool.acquire() as conn:
                for turf in turfs:
                    await conn.execute(
                        """
                        INSERT INTO turfs (name, description, gta_coordinates)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (name) DO NOTHING
                        """,
                        turf['name'], turf['description'], turf['gta_coordinates']
                    )

            await ctx.send(f"Successfully created {len(turfs)} turfs!")
        except Exception as e:
            await ctx.send(f"Error creating turfs: {str(e)}")

    @mod.command(name="setpsn")
    @is_mod()
    async def set_psn(self, ctx, member: discord.Member, psn: str):
        """Set a user's PlayStation Network ID."""
        try:
            # Check if PSN is already taken
            existing_user = supabase.table('users').select('id').eq('psn', psn).execute()
            if existing_user.data:
                await ctx.send("❌ This PSN is already registered to another user!")
                return

            # Get or create user
            user = await supabase.get_user(str(member.id))
            if not user:
                # Create new user
                success = await supabase.create_user(str(member.id), member.name)
                if not success:
                    await ctx.send("❌ Failed to create user!")
                    return

            # Update PSN
            result = supabase.table('users').update({'psn': psn}).eq('id', str(member.id)).execute()
            if result.data:
                await ctx.send(f"✅ Set {member.mention}'s PSN to: `{psn}`")
            else:
                await ctx.send("❌ Failed to update PSN. Please try again.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @mod.command(name="createuser")
    @is_mod()
    async def create_user(self, ctx, member: discord.Member):
        """Manually create a user in the database using a form."""
        try:
            # Create and show the modal
            modal = CreateUserModal(member)
            await ctx.send("Please fill out the form to create the user:")
            await ctx.send_modal(modal)
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    """Add the Moderator cog to the bot."""
    try:
        await bot.add_cog(Moderator(bot))
        logger.info("Moderator cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Moderator cog: {e}") 