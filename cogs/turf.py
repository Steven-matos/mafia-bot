import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
from db.supabase_client import supabase
import logging
import random
from typing import Optional

logger = logging.getLogger('mafia-bot')

class Turf(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.capture_cooldown = 24  # Hours between capture attempts
        self.capture_chance = 0.6   # 60% chance of successful capture

    @commands.group(invoke_without_command=True)
    async def turf(self, ctx):
        """Turf management commands."""
        await ctx.send_help(ctx.command)

    @turf.command(name="list")
    async def list_turfs(self, ctx):
        """List all turfs in the server."""
        try:
            # Get server settings
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found!")
                return

            # Get all turfs
            turfs = await supabase.get_server_turfs(str(ctx.guild.id))
            if not turfs:
                await ctx.send("No turfs found in this server!")
                return

            embed = discord.Embed(
                title="🏢 Turfs",
                color=discord.Color.blue()
            )

            for turf in turfs:
                owner = "Unclaimed" if not turf["owner_family_id"] else "Unknown"
                if turf["owner_family_id"]:
                    family = await supabase.get_family(turf["owner_family_id"])
                    if family:
                        owner = family["name"]

                last_captured = "Never"
                if turf["last_captured_at"]:
                    last_captured = datetime.fromisoformat(turf["last_captured_at"].replace('Z', '+00:00'))
                    last_captured = last_captured.strftime("%Y-%m-%d %H:%M")

                embed.add_field(
                    name=turf["name"],
                    value=f"Owner: {owner}\nLast Captured: {last_captured}\nIncome: ${turf['income']:,}/hour",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @turf.command(name="info")
    async def turf_info(self, ctx, turf_name: str):
        """Get information about a specific turf."""
        try:
            # Get turf
            turf = await supabase.get_turf_by_name(turf_name, str(ctx.guild.id))
            if not turf:
                await ctx.send("Turf not found!")
                return

            embed = discord.Embed(
                title=f"🏢 {turf['name']}",
                color=discord.Color.blue()
            )

            # Add owner info
            owner = "Unclaimed" if not turf["owner_family_id"] else "Unknown"
            if turf["owner_family_id"]:
                family = await supabase.get_family(turf["owner_family_id"])
                if family:
                    owner = family["name"]

            embed.add_field(name="Owner", value=owner, inline=True)

            # Add income info
            embed.add_field(name="Income", value=f"${turf['income']:,}/hour", inline=True)

            # Add last captured info
            last_captured = "Never"
            if turf["last_captured_at"]:
                last_captured = datetime.fromisoformat(turf["last_captured_at"].replace('Z', '+00:00'))
                last_captured = last_captured.strftime("%Y-%m-%d %H:%M")

            embed.add_field(name="Last Captured", value=last_captured, inline=True)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @turf.command(name="capture")
    async def capture_turf(self, ctx, turf_name: str):
        """Attempt to capture a turf for your family."""
        try:
            # Get server settings
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found!")
                return

            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to capture turfs!")
                return

            # Get turf
            turf = await supabase.get_turf_by_name(turf_name, str(ctx.guild.id))
            if not turf:
                await ctx.send("Turf not found!")
                return

            # Check cooldown
            if turf["last_captured_at"]:
                last_captured = datetime.fromisoformat(turf["last_captured_at"].replace('Z', '+00:00'))
                time_diff = datetime.now(timezone.utc) - last_captured
                
                if time_diff < timedelta(hours=settings["turf_capture_cooldown"]):
                    remaining = timedelta(hours=settings["turf_capture_cooldown"]) - time_diff
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    await ctx.send(f"This turf can be captured again in {hours}h {minutes}m")
                    return

            # Capture turf
            success = await supabase.update_turf_owner(turf["id"], user["family_id"])
            if success:
                family = await supabase.get_family(user["family_id"])
                embed = discord.Embed(
                    title="🏢 Turf Captured",
                    description=f"{family['name']} has captured {turf['name']}!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Income", value=f"${turf['income']:,}/hour")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to capture turf. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @turf.command(name="income")
    async def collect_income(self, ctx):
        """Collect income from your family's turfs."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to collect turf income!")
                return

            # Get family
            family = await supabase.get_family(user["family_id"])
            if not family:
                await ctx.send("Family not found!")
                return

            # Get family's turfs
            turfs = await supabase.get_family_turfs(family["id"])
            if not turfs:
                await ctx.send("Your family doesn't own any turfs!")
                return

            # Calculate total income
            total_income = sum(turf["income"] for turf in turfs)

            # Update family money
            new_family_money = family["family_money"] + total_income
            await supabase.update_family_money(family["id"], new_family_money)

            # Record transaction
            await supabase.record_transaction(
                user_id=str(ctx.author.id),
                amount=total_income,
                type="turf_income",
                notes=f"Income from {len(turfs)} turfs",
                server_id=str(ctx.guild.id)
            )

            embed = discord.Embed(
                title="💰 Turf Income Collected",
                description=f"Your family collected ${total_income:,} from {len(turfs)} turfs!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Family Balance", value=f"${new_family_money:,}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Turf(bot)) 