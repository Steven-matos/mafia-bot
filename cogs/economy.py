import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
from db.supabase_client import supabase
import logging
from typing import Optional
import random

logger = logging.getLogger('mafia-bot')

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_amount = 1000  # Amount of money given daily
        self.daily_cooldown = 24  # Hours between daily collects

    @commands.group(invoke_without_command=True)
    async def economy(self, ctx):
        """Economy management commands."""
        await ctx.send_help(ctx.command)

    @economy.command(name="balance")
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
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="daily")
    async def daily_reward(self, ctx):
        """Claim your daily reward."""
        try:
            # Get server settings
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found!")
                return

            # Get user
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await supabase.create_user(str(ctx.author.id), ctx.author.name)
                user = await supabase.get_user(str(ctx.author.id))

            # Check if user has claimed daily reward
            last_daily = user.get('last_daily')
            if last_daily:
                await ctx.send("You've already claimed your daily reward! Come back tomorrow.")
                return

            # Give daily reward
            new_money = user['money'] + settings['daily_amount']
            await supabase.update_user_money(str(ctx.author.id), new_money)
            await supabase.update_user_last_daily(str(ctx.author.id))

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=settings['daily_amount'],
                type="daily",
                notes="Daily reward",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="💰 Daily Reward Claimed",
                description=f"You received ${settings['daily_amount']:,}!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="transfer")
    async def transfer_money(self, ctx, member: discord.Member, amount: int):
        """Transfer money to another user."""
        try:
            if amount <= 0:
                await ctx.send("Amount must be positive!")
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
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="deposit")
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
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="withdraw")
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
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="rob")
    async def rob_user(self, ctx, member: discord.Member):
        """Attempt to rob another user."""
        try:
            # Get user data
            user = await supabase.get_user(str(ctx.author.id))
            if not user:
                await ctx.send("You haven't started your criminal career yet!")
                return

            target = await supabase.get_user(str(member.id))
            if not target:
                await ctx.send("Target hasn't started their criminal career yet!")
                return

            if target['money'] < 100:
                await ctx.send("Target doesn't have enough money to rob!")
                return

            # 50% chance of success
            if random.random() < 0.5:
                # Success
                amount = min(target['money'], random.randint(100, 1000))
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
                    notes="Successful robbery",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="🦹 Robbery Successful",
                    description=f"You successfully robbed ${amount:,} from {member.mention}!",
                    color=discord.Color.green()
                )
            else:
                # Failure
                fine = random.randint(100, 500)
                new_user_money = max(0, user['money'] - fine)

                await supabase.update_user_money(str(ctx.author.id), new_user_money)

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=-fine,
                    type="rob",
                    target_user_id=str(member.id),
                    notes="Failed robbery",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="👮 Robbery Failed",
                    description=f"You were caught and fined ${fine:,}!",
                    color=discord.Color.red()
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @economy.command(name="leaderboard")
    async def show_leaderboard(self, ctx):
        """Show the server's wealth leaderboard."""
        try:
            # Get all users in the server
            users = await supabase.get_server_users(str(ctx.guild.id))
            if not users:
                await ctx.send("No users found in this server!")
                return

            # Sort users by total wealth
            sorted_users = sorted(
                users,
                key=lambda x: x['money'] + x['bank'],
                reverse=True
            )[:10]  # Top 10

            embed = discord.Embed(
                title="🏆 Wealth Leaderboard",
                color=discord.Color.gold()
            )

            for i, user in enumerate(sorted_users, 1):
                total = user['money'] + user['bank']
                member = ctx.guild.get_member(int(user['id']))
                name = member.name if member else "Unknown"
                embed.add_field(
                    name=f"{i}. {name}",
                    value=f"${total:,}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Economy(bot)) 