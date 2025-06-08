import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
from db.supabase_client import supabase
import logging
import random
import json
from typing import Optional

logger = logging.getLogger('mafia-bot')

class RPEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.heist_cooldown = 12  # Hours between heists
        self.heist_types = {
            'bank': {
                'min_players': 2,
                'max_players': 4,
                'success_chance': 0.4,
                'reward_range': (50000, 100000),
                'jail_time': 24,  # Hours
                'reputation_change': 10
            },
            'jewelry': {
                'min_players': 1,
                'max_players': 3,
                'success_chance': 0.6,
                'reward_range': (20000, 50000),
                'jail_time': 12,
                'reputation_change': 5
            },
            'drug_run': {
                'min_players': 1,
                'max_players': 2,
                'success_chance': 0.7,
                'reward_range': (10000, 30000),
                'jail_time': 8,
                'reputation_change': 3
            }
        }

    @commands.group(invoke_without_command=True)
    async def rp(self, ctx):
        """Roleplay event commands."""
        await ctx.send_help(ctx.command)

    @rp.command(name="heist")
    async def start_heist(self, ctx):
        """Start a heist event."""
        try:
            # Get server settings
            settings = await supabase.get_server_settings(str(ctx.guild.id))
            if not settings:
                await ctx.send("Server settings not found!")
                return

            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to start a heist!")
                return

            # Check cooldown
            last_heist = user.get("last_heist")
            if last_heist:
                last_heist = datetime.fromisoformat(last_heist.replace('Z', '+00:00'))
                time_diff = datetime.now(timezone.utc) - last_heist
                
                if time_diff < timedelta(hours=settings["heist_cooldown"]):
                    remaining = timedelta(hours=settings["heist_cooldown"]) - time_diff
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    await ctx.send(f"You can start another heist in {hours}h {minutes}m")
                    return

            # Get family
            family = await supabase.get_family(user["family_id"])
            if not family:
                await ctx.send("Family not found!")
                return

            # Calculate heist success chance and reward
            success_chance = 0.4  # 40% base chance
            min_reward = 5000
            max_reward = 20000

            # Add family reputation bonus
            rep_bonus = min(family["reputation"] * 0.01, 0.2)  # Up to 20% bonus
            success_chance += rep_bonus

            # Attempt heist
            if random.random() < success_chance:
                # Success
                reward = random.randint(min_reward, max_reward)
                new_family_money = family["family_money"] + reward
                await supabase.update_family_money(family["id"], new_family_money)
                await supabase.update_user_last_heist(str(ctx.author.id))

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=reward,
                    type="heist",
                    notes="Successful heist",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="🦹 Heist Successful",
                    description=f"Your family successfully pulled off a heist!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reward", value=f"${reward:,}")
                embed.add_field(name="New Family Balance", value=f"${new_family_money:,}")
            else:
                # Failure
                fine = random.randint(1000, 5000)
                new_family_money = max(0, family["family_money"] - fine)
                await supabase.update_family_money(family["id"], new_family_money)
                await supabase.update_user_last_heist(str(ctx.author.id))

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=-fine,
                    type="heist",
                    notes="Failed heist",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="👮 Heist Failed",
                    description="The heist went wrong and your family had to pay a fine!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Fine", value=f"${fine:,}")
                embed.add_field(name="New Family Balance", value=f"${new_family_money:,}")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rp.command(name="contract")
    async def create_contract(self, ctx, target: discord.Member, amount: int):
        """Create a contract on another player."""
        try:
            if amount <= 0:
                await ctx.send("Contract amount must be positive!")
                return

            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to create contracts!")
                return

            # Check if target is in a family
            target_user = await supabase.get_user(str(target.id))
            if not target_user or not target_user.get("family_id"):
                await ctx.send("Target must be in a family!")
                return

            # Check if target is in the same family
            if target_user["family_id"] == user["family_id"]:
                await ctx.send("You cannot create a contract on a family member!")
                return

            # Get family
            family = await supabase.get_family(user["family_id"])
            if not family:
                await ctx.send("Family not found!")
                return

            # Check if family has enough money
            if family["family_money"] < amount:
                await ctx.send("Your family doesn't have enough money for this contract!")
                return

            # Create contract
            contract_id = await supabase.create_contract(
                creator_id=str(ctx.author.id),
                target_id=str(target.id),
                amount=amount,
                server_id=str(ctx.guild.id)
            )

            if contract_id:
                # Deduct money from family
                new_family_money = family["family_money"] - amount
                await supabase.update_family_money(family["id"], new_family_money)

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=-amount,
                    type="contract",
                    target_user_id=str(target.id),
                    notes="Contract creation",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="📜 Contract Created",
                    description=f"A contract has been placed on {target.mention}!",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Bounty", value=f"${amount:,}")
                embed.add_field(name="New Family Balance", value=f"${new_family_money:,}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to create contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rp.command(name="contracts")
    async def list_contracts(self, ctx):
        """List all active contracts."""
        try:
            # Get all contracts
            contracts = await supabase.get_active_contracts(str(ctx.guild.id))
            if not contracts:
                await ctx.send("No active contracts!")
                return

            embed = discord.Embed(
                title="📜 Active Contracts",
                color=discord.Color.orange()
            )

            for contract in contracts:
                creator = ctx.guild.get_member(int(contract["creator_id"]))
                target = ctx.guild.get_member(int(contract["target_id"]))
                
                creator_name = creator.name if creator else "Unknown"
                target_name = target.name if target else "Unknown"

                embed.add_field(
                    name=f"Contract #{contract['id']}",
                    value=f"Target: {target_name}\nBounty: ${contract['amount']:,}\nCreated by: {creator_name}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rp.command(name="claim")
    async def claim_contract(self, ctx, contract_id: str):
        """Claim a contract bounty."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to claim contracts!")
                return

            # Get contract
            contract = await supabase.get_contract(contract_id)
            if not contract:
                await ctx.send("Contract not found!")
                return

            if contract["status"] != "active":
                await ctx.send("This contract has already been claimed!")
                return

            # Check if user is the target
            if contract["target_id"] == str(ctx.author.id):
                await ctx.send("You cannot claim a contract on yourself!")
                return

            # Get family
            family = await supabase.get_family(user["family_id"])
            if not family:
                await ctx.send("Family not found!")
                return

            # Update contract status
            success = await supabase.update_contract_status(
                contract_id,
                "completed",
                str(ctx.author.id)
            )

            if success:
                # Add money to family
                new_family_money = family["family_money"] + contract["amount"]
                await supabase.update_family_money(family["id"], new_family_money)

                # Record transaction
                await supabase.record_transaction(
                    user_id=str(ctx.author.id),
                    amount=contract["amount"],
                    type="contract_claim",
                    target_user_id=contract["target_id"],
                    notes="Contract bounty claimed",
                    server_id=str(ctx.guild.id)
                )

                embed = discord.Embed(
                    title="💰 Contract Claimed",
                    description=f"Your family has claimed the contract bounty!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Bounty", value=f"${contract['amount']:,}")
                embed.add_field(name="New Family Balance", value=f"${new_family_money:,}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to claim contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="shop")
    async def shop(self, ctx):
        """View the shop items."""
        items = await supabase.get_shop_items()
        
        if not items:
            await ctx.send("No items available in the shop!")
            return

        embed = discord.Embed(
            title="🛍️ Shop",
            description="Available items for purchase",
            color=discord.Color.blue()
        )

        # Group items by type
        items_by_type = {}
        for item in items:
            item_type = item['item_type']
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        for item_type, type_items in items_by_type.items():
            value = ""
            for item in type_items:
                value += f"**{item['name']}** - ${item['price']:,}\n"
                value += f"_{item['description']}_\n"
                if item['is_consumable']:
                    value += "🔸 Consumable\n"
                value += "\n"
            
            embed.add_field(
                name=f"📦 {item_type.title()}",
                value=value,
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy_item(self, ctx, item_id: str, quantity: int = 1):
        """Buy an item from the shop."""
        if quantity <= 0:
            await ctx.send("Quantity must be positive!")
            return

        user = await supabase.get_user(str(ctx.author.id))
        if not user:
            await supabase.create_user(str(ctx.author.id), ctx.author.name)
            user = await supabase.get_user(str(ctx.author.id))

        item = await supabase.get_shop_item(item_id)
        if not item:
            await ctx.send("Item not found!")
            return

        total_cost = item['price'] * quantity
        if user['money'] < total_cost:
            await ctx.send("You don't have enough money!")
            return

        # Update user's money and inventory
        new_money = user['money'] - total_cost
        inventory = user.get('inventory', {})
        inventory[item_id] = inventory.get(item_id, 0) + quantity

        await supabase.update_user_money(str(ctx.author.id), new_money)
        await supabase.update_user_inventory(str(ctx.author.id), inventory)

        # Record transaction
        await supabase.record_transaction(
            user_id=str(ctx.author.id),
            amount=-total_cost,
            type="buy_item",
            item_id=item_id,
            notes=f"Bought {quantity}x {item['name']}"
        )

        embed = discord.Embed(
            title="🛍️ Purchase Successful",
            description=f"Successfully bought {quantity}x {item['name']}",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Cost", value=f"${total_cost:,}")
        embed.add_field(name="New Balance", value=f"${new_money:,}")
        
        await ctx.send(embed=embed)

    @commands.command(name="inventory")
    async def inventory(self, ctx):
        """View your inventory."""
        user = await supabase.get_user(str(ctx.author.id))
        if not user:
            await supabase.create_user(str(ctx.author.id), ctx.author.name)
            user = await supabase.get_user(str(ctx.author.id))

        inventory = user.get('inventory', {})
        if not inventory:
            await ctx.send("Your inventory is empty!")
            return

        embed = discord.Embed(
            title="🎒 Inventory",
            color=discord.Color.blue()
        )

        for item_id, quantity in inventory.items():
            item = await supabase.get_shop_item(item_id)
            if item:
                value = f"Quantity: {quantity}\n"
                value += f"_{item['description']}_\n"
                if item['is_consumable']:
                    value += "🔸 Consumable"
                
                embed.add_field(
                    name=item['name'],
                    value=value,
                    inline=True
                )

        await ctx.send(embed=embed)

    @commands.command(name="status")
    async def status(self, ctx):
        """Check your current status."""
        user = await supabase.get_user(str(ctx.author.id))
        if not user:
            await supabase.create_user(str(ctx.author.id), ctx.author.name)
            user = await supabase.get_user(str(ctx.author.id))

        embed = discord.Embed(
            title="👤 Status",
            color=discord.Color.blue()
        )

        # Add basic info
        embed.add_field(name="Money", value=f"${user['money']:,}", inline=True)
        embed.add_field(name="Bank", value=f"${user['bank']:,}", inline=True)
        embed.add_field(name="Reputation", value=str(user['reputation']), inline=True)

        # Add family info if in a family
        if user.get('family_id'):
            family = await supabase.get_family(user['family_id'])
            if family:
                embed.add_field(name="Family", value=family['name'], inline=True)
                embed.add_field(name="Rank", value=user.get('family_rank', 'Member'), inline=True)

        # Add jail status if in jail
        if user.get('jail_release_time'):
            release_time = datetime.fromisoformat(user['jail_release_time'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) < release_time:
                remaining = release_time - datetime.now(timezone.utc)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                embed.add_field(
                    name="Jail Status",
                    value=f"In jail for {hours}h {minutes}m",
                    inline=False
                )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RPEvents(bot)) 