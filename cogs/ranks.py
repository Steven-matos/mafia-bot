import discord
from discord.ext import commands
from db.supabase_client import supabase
import logging
from typing import Optional

logger = logging.getLogger('mafia-bot')

class Ranks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_family_leader():
        """Check if user is a family leader."""
        async def predicate(ctx):
            family = await supabase.get_user_family(str(ctx.author.id))
            return family and family["leader_id"] == str(ctx.author.id)
        return commands.check(predicate)

    @commands.group(invoke_without_command=True)
    async def rank(self, ctx):
        """Family rank management commands."""
        await ctx.send_help(ctx.command)

    @rank.command(name="create")
    @is_family_leader()
    async def create_rank(self, ctx, name: str, display_name: str, emoji: str, order: int):
        """Create a new family rank."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to create ranks!")
                return

            # Create rank
            rank_id = await supabase.create_family_rank(
                family_id=user["family_id"],
                name=name,
                display_name=display_name,
                emoji=emoji,
                rank_order=order
            )

            if rank_id:
                embed = discord.Embed(
                    title="👑 Rank Created",
                    description=f"New rank created for your family: {emoji} {display_name}",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Internal Name", value=name, inline=True)
                embed.add_field(name="Order", value=str(order), inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to create rank. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rank.command(name="list")
    async def list_ranks(self, ctx, family_name: Optional[str] = None):
        """List all ranks for a family."""
        try:
            if family_name:
                # Get family by name
                family = await supabase.get_family_by_name(family_name)
            else:
                # Get user's family
                user = await supabase.get_user(str(ctx.author.id))
                if not user or not user.get("family_id"):
                    await ctx.send("You must be in a family to view ranks!")
                    return
                family = await supabase.get_family(user["family_id"])

            if not family:
                await ctx.send("Family not found!")
                return

            # Get ranks
            ranks = await supabase.get_family_ranks(family["id"])
            if not ranks:
                await ctx.send(f"{family['name']} has no ranks defined.")
                return

            # Create embed
            embed = discord.Embed(
                title=f"👑 {family['name']} Ranks",
                description="Family hierarchy from highest to lowest rank",
                color=discord.Color.gold()
            )

            for rank in ranks:
                embed.add_field(
                    name=f"{rank['emoji']} {rank['display_name']}",
                    value=f"**Internal Name:** {rank['name']}\n"
                          f"**Order:** {rank['rank_order']}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rank.command(name="set")
    @is_family_leader()
    async def set_rank(self, ctx, member: discord.Member, rank_name: str):
        """Set a member's family rank."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to set ranks!")
                return

            # Get target user
            target = await supabase.get_user(str(member.id))
            if not target or target.get("family_id") != user["family_id"]:
                await ctx.send("Target user must be in your family!")
                return

            # Get ranks
            ranks = await supabase.get_family_ranks(user["family_id"])
            target_rank = next((r for r in ranks if r["name"].lower() == rank_name.lower()), None)
            
            if not target_rank:
                await ctx.send(f"Rank '{rank_name}' not found in your family!")
                return

            # Set rank
            success = await supabase.set_user_rank(str(member.id), target_rank["id"])
            if success:
                embed = discord.Embed(
                    title="👑 Rank Updated",
                    description=f"{member.mention}'s rank has been updated.",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="New Rank",
                    value=f"{target_rank['emoji']} {target_rank['display_name']}",
                    inline=False
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to update rank. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rank.command(name="delete")
    @is_family_leader()
    async def delete_rank(self, ctx, rank_name: str):
        """Delete a family rank."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to delete ranks!")
                return

            # Get ranks
            ranks = await supabase.get_family_ranks(user["family_id"])
            target_rank = next((r for r in ranks if r["name"].lower() == rank_name.lower()), None)
            
            if not target_rank:
                await ctx.send(f"Rank '{rank_name}' not found in your family!")
                return

            # Delete rank
            success = await supabase.delete_family_rank(target_rank["id"])
            if success:
                embed = discord.Embed(
                    title="🗑️ Rank Deleted",
                    description=f"The rank {target_rank['emoji']} {target_rank['display_name']} has been deleted.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to delete rank. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @rank.command(name="update")
    @is_family_leader()
    async def update_rank(self, ctx, rank_name: str, field: str, *, value: str):
        """Update a family rank's properties."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to update ranks!")
                return

            # Get ranks
            ranks = await supabase.get_family_ranks(user["family_id"])
            target_rank = next((r for r in ranks if r["name"].lower() == rank_name.lower()), None)
            
            if not target_rank:
                await ctx.send(f"Rank '{rank_name}' not found in your family!")
                return

            # Validate field
            valid_fields = ["display_name", "emoji", "rank_order"]
            if field not in valid_fields:
                await ctx.send(f"Invalid field. Must be one of: {', '.join(valid_fields)}")
                return

            # Convert rank_order to int if needed
            if field == "rank_order":
                try:
                    value = int(value)
                except ValueError:
                    await ctx.send("Rank order must be a number!")
                    return

            # Update rank
            success = await supabase.update_family_rank(target_rank["id"], **{field: value})
            if success:
                embed = discord.Embed(
                    title="📝 Rank Updated",
                    description=f"The rank {target_rank['emoji']} {target_rank['display_name']} has been updated.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Updated Field", value=field, inline=True)
                embed.add_field(name="New Value", value=str(value), inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to update rank. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Ranks(bot)) 