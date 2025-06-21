import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
from db.supabase_client import supabase
import logging
from typing import Optional
import random
from discord.ext.commands import cooldown, BucketType

logger = logging.getLogger('mafia-bot')

# Constants for security limits
MAX_TRANSFER_AMOUNT = 1000000  # $1M max transfer
MAX_DAILY_AMOUNT = 10000  # $10K max daily
ROB_COOLDOWN = 3600  # 1 hour cooldown
TRANSFER_COOLDOWN = 300  # 5 minutes cooldown
DAILY_COOLDOWN = 86400  # 24 hours cooldown

class TransferModal(discord.ui.Modal, title='Transfer Money'):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member
        self.amount = discord.ui.TextInput(
            label='Amount',
            placeholder='Enter amount to transfer',
            required=True,
            min_length=1,
            max_length=10
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount <= 0:
                await interaction.response.send_message("Amount must be positive!", ephemeral=True)
                return
            if amount > MAX_TRANSFER_AMOUNT:
                await interaction.response.send_message(f"Amount cannot exceed ${MAX_TRANSFER_AMOUNT:,}!", ephemeral=True)
                return

            # Get sender's data
            sender = await supabase.get_user(str(interaction.user.id))
            if not sender:
                await interaction.response.send_message("You haven't started your criminal career yet!", ephemeral=True)
                return

            if sender['money'] < amount:
                await interaction.response.send_message("You don't have enough money!", ephemeral=True)
                return

            # Get receiver's data
            receiver = await supabase.get_user(str(self.member.id))
            if not receiver:
                await supabase.create_user(str(self.member.id), self.member.name)
                receiver = await supabase.get_user(str(self.member.id))

            # Transfer money
            new_sender_money = sender['money'] - amount
            new_receiver_money = receiver['money'] + amount

            await supabase.update_user_money(str(interaction.user.id), new_sender_money)
            await supabase.update_user_money(str(self.member.id), new_receiver_money)

            # Record transaction
            await supabase.record_transaction(
                user_id=str(interaction.user.id),
                amount=-amount,
                type="transfer",
                target_user_id=str(self.member.id),
                notes=f"Transfer to {self.member.name}",
                server_id=str(interaction.guild.id)
            )

            await supabase.record_transaction(
                user_id=str(self.member.id),
                amount=amount,
                type="transfer",
                target_user_id=str(interaction.user.id),
                notes=f"Transfer from {interaction.user.name}",
                server_id=str(interaction.guild.id)
            )

            embed = discord.Embed(
                title="💸 Money Transferred",
                description=f"Successfully transferred ${amount:,} to {self.member.mention}!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in transfer modal: {str(e)}")
            await interaction.response.send_message("An error occurred while transferring money.", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_amount = 1000  # Amount of money given daily
        self.daily_cooldown = 24  # Hours between daily collects

    def validate_amount(self, amount: int) -> bool:
        """Validate transaction amount."""
        return 0 < amount <= MAX_TRANSFER_AMOUNT

    @commands.hybrid_group(name="economy", invoke_without_command=True)
    async def economy(self, ctx):
        """Economy management commands."""
        await ctx.send_help(ctx.command)

    @economy.command(name="balance")
    @app_commands.describe(member="The member to check balance for")
    async def check_balance(self, ctx, member: Optional[discord.Member] = None):
        """Check your or another user's balance."""
        try:
            target = member or ctx.author
            user = await supabase.get_user(str(target.id))
            
            if not user:
                await ctx.send(f"{target.mention} hasn't started their criminal career yet!")
                return

            embed = discord.Embed(
                title=f"💰 {target.name}'s Balance",
                color=discord.Color.gold()
            )
            embed.add_field(name="Cash", value=f"${user['money']:,}", inline=True)
            embed.add_field(name="Bank", value=f"${user['bank']:,}", inline=True)
            embed.add_field(name="Total", value=f"${user['money'] + user['bank']:,}", inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in check_balance: {str(e)}")
            await ctx.send("An error occurred while checking the balance.")

    @economy.command(name="daily")
    @app_commands.describe()
    @commands.cooldown(1, DAILY_COOLDOWN, BucketType.user)
    async def daily_reward(self, ctx):
        """Claim your daily reward."""
        try:
            # Get server settings
            settings = supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found! Please contact an administrator.")
                return

            # Get user
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await supabase.create_user(str(ctx.author.id), ctx.author.name)
                user = await supabase.get_user(str(ctx.author.id))

            # Check if user has claimed daily reward
            last_daily = user.get('last_daily')
            if last_daily:
                time_left = datetime.now(timezone.utc) - last_daily
                if time_left.total_seconds() < DAILY_COOLDOWN:
                    remaining = DAILY_COOLDOWN - time_left.total_seconds()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    await ctx.send(f"You can claim your daily reward in {hours}h {minutes}m!")
                    return

            # Validate daily amount
            daily_amount = min(settings['daily_amount'], MAX_DAILY_AMOUNT)

            # Give daily reward
            new_money = user['money'] + daily_amount
            await supabase.update_user_money(str(ctx.author.id), new_money)
            await supabase.update_user_last_daily(str(ctx.author.id))

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=daily_amount,
                type="daily",
                notes="Daily reward",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="💰 Daily Reward Claimed",
                description=f"You received ${daily_amount:,}!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in daily_reward: {str(e)}")
            await ctx.send("An error occurred while claiming your daily reward.")

    @economy.command(name="transfer")
    @app_commands.describe(member="The member to transfer money to", amount="Amount to transfer")
    @commands.cooldown(1, TRANSFER_COOLDOWN, BucketType.user)
    async def transfer_money(self, ctx, member: discord.Member, amount: int):
        """Transfer money to another user."""
        try:
            # Input validation
            if not self.validate_amount(amount):
                await ctx.send(f"Invalid amount! Must be between 1 and ${MAX_TRANSFER_AMOUNT:,}")
                return

            if member.bot:
                await ctx.send("You cannot transfer money to bots!")
                return

            if member.id == ctx.author.id:
                await ctx.send("You cannot transfer money to yourself!")
                return

            # Get sender's data
            sender = await supabase.get_user(str(ctx.author.id))
            if not sender:
                await ctx.send("You haven't started your criminal career yet!")
                return

            if sender['money'] < amount:
                await ctx.send("You don't have enough money!")
                return

            # Get receiver's data
            receiver = await supabase.get_user(str(member.id))
            if not receiver:
                await supabase.create_user(str(member.id), member.name)
                receiver = await supabase.get_user(str(member.id))

            # Transfer money
            new_sender_money = sender['money'] - amount
            new_receiver_money = receiver['money'] + amount

            await supabase.update_user_money(str(ctx.author.id), new_sender_money)
            await supabase.update_user_money(str(member.id), new_receiver_money)

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=-amount,
                type="transfer",
                target_user_id=str(member.id),
                notes=f"Transfer to {member.name}",
                server_id=str(ctx.guild.id)
            )

            await supabase.record_transaction(
                user_id=str(member.id),
                amount=amount,
                type="transfer",
                target_user_id=str(ctx.author.id),
                notes=f"Transfer from {ctx.author.name}",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="💸 Money Transferred",
                description=f"Successfully transferred ${amount:,} to {member.mention}!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in transfer_money: {str(e)}")
            await ctx.send("An error occurred while transferring money.")

    @economy.command(name="deposit")
    @app_commands.describe(amount="Amount to deposit")
    async def deposit_money(self, ctx, amount: int):
        """Deposit money into your bank account."""
        try:
            if amount <= 0:
                await ctx.send("Amount must be positive!")
                return

            # Get user data
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await ctx.send("You haven't started your criminal career yet!")
                return

            if user['money'] < amount:
                await ctx.send("You don't have enough money!")
                return

            # Update balances
            new_money = user['money'] - amount
            new_bank = user['bank'] + amount

            await supabase.update_user_money(str(ctx.author.id), new_money)
            await supabase.update_user_bank(str(ctx.author.id), new_bank)

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=-amount,
                type="deposit",
                notes="Bank deposit",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="🏦 Money Deposited",
                description=f"Successfully deposited ${amount:,} into your bank account!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in deposit_money: {str(e)}")
            await ctx.send("An error occurred while depositing money.")

    @economy.command(name="withdraw")
    @app_commands.describe(amount="Amount to withdraw")
    async def withdraw_money(self, ctx, amount: int):
        """Withdraw money from your bank account."""
        try:
            if amount <= 0:
                await ctx.send("Amount must be positive!")
                return

            # Get user data
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await ctx.send("You haven't started your criminal career yet!")
                return

            if user['bank'] < amount:
                await ctx.send("You don't have enough money in your bank account!")
                return

            # Update balances
            new_money = user['money'] + amount
            new_bank = user['bank'] - amount

            await supabase.update_user_money(str(ctx.author.id), new_money)
            await supabase.update_user_bank(str(ctx.author.id), new_bank)

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=amount,
                type="withdraw",
                notes="Bank withdrawal",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="🏦 Money Withdrawn",
                description=f"Successfully withdrew ${amount:,} from your bank account!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in withdraw_money: {str(e)}")
            await ctx.send("An error occurred while withdrawing money.")

    @economy.command(name="rob")
    @app_commands.describe(member="The member to rob")
    @commands.cooldown(1, ROB_COOLDOWN, BucketType.user)
    async def rob_user(self, ctx, member: discord.Member):
        """Attempt to rob another user."""
        try:
            if member.bot:
                await ctx.send("You cannot rob bots!")
                return

            if member.id == ctx.author.id:
                await ctx.send("You cannot rob yourself!")
                return

            # Get user data
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await ctx.send("You haven't started your criminal career yet!")
                return

            target = await supabase.get_user(str(member.id))
            if not target:
                await ctx.send(f"{member.mention} hasn't started their criminal career yet!")
                return

            if target['money'] < 100:
                await ctx.send(f"{member.mention} doesn't have enough money to rob!")
                return

            # 30% chance of success
            if random.random() < 0.3:
                # Calculate amount to steal (10-30% of target's money)
                steal_percent = random.uniform(0.1, 0.3)
                amount = int(target['money'] * steal_percent)

                # Update balances
                new_target_money = target['money'] - amount
                new_user_money = user['money'] + amount

                await supabase.update_user_money(str(member.id), new_target_money)
                await supabase.update_user_money(str(ctx.author.id), new_user_money)

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=amount,
                    type="rob",
                    target_user_id=str(member.id),
                    notes=f"Successful robbery from {member.name}",
                    server_id=str(ctx.guild.id)
                )

                await supabase.record_transaction(
                    user_id=str(member.id),
                    amount=-amount,
                    type="rob",
                    target_user_id=str(ctx.author.id),
                    notes=f"Robbed by {ctx.author.name}",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="🦹 Successful Robbery",
                    description=f"You successfully robbed ${amount:,} from {member.mention}!",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                # Failed robbery
                embed = discord.Embed(
                    title="🚔 Failed Robbery",
                    description=f"Your attempt to rob {member.mention} failed!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in rob_user: {str(e)}")
            await ctx.send("An error occurred while attempting to rob the user.")

    @economy.command(name="leaderboard")
    @app_commands.describe()
    async def show_leaderboard(self, ctx):
        """View the server's wealth leaderboard."""
        try:
            # Get top 10 users by total wealth
            users = await supabase.get_wealth_leaderboard(str(ctx.guild.id), limit=10)
            
            if not users:
                await ctx.send("No users found!")
                return

            embed = discord.Embed(
                title="💰 Wealth Leaderboard",
                color=discord.Color.gold()
            )

            for i, user in enumerate(users, 1):
                member = ctx.guild.get_member(int(user['user_id']))
                if member:
                    total = user['money'] + user['bank']
                    embed.add_field(
                        name=f"{i}. {member.name}",
                        value=f"Total: ${total:,}\nCash: ${user['money']:,}\nBank: ${user['bank']:,}",
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in show_leaderboard: {str(e)}")
            await ctx.send("An error occurred while fetching the leaderboard.")

    @daily_reward.error
    @transfer_money.error
    @rob_user.error
    async def command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandOnCooldown):
            hours = int(error.retry_after // 3600)
            minutes = int((error.retry_after % 3600) // 60)
            await ctx.send(f"You can use this command again in {hours}h {minutes}m!")
        else:
            logger.error(f"Command error: {str(error)}")
            await ctx.send("An error occurred while processing the command.")

async def setup(bot):
    await bot.add_cog(Economy(bot)) 