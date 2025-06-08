import discord
from discord.ext import commands
from db.supabase_client import supabase
from datetime import datetime, timezone
import logging
from typing import Optional

logger = logging.getLogger('mafia-bot')

class Relationships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_family_leader():
        """Check if user is a family leader."""
        async def predicate(ctx):
            family = await supabase.get_user_family(str(ctx.author.id))
            return family and family["leader_id"] == str(ctx.author.id)
        return commands.check(predicate)

    @commands.group(invoke_without_command=True)
    async def relationship(self, ctx):
        """Family relationship management commands."""
        await ctx.send_help(ctx.command)

    @relationship.command(name="alliance")
    @is_family_leader()
    async def create_alliance(self, ctx, target_family: str, *, notes: str):
        """Create an alliance with another family."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to create alliances!")
                return

            # Get target family
            target_family_data = await supabase.get_family_by_name(target_family)
            if not target_family_data:
                await ctx.send("Target family not found!")
                return

            # Check if trying to ally with own family
            if target_family_data["id"] == user["family_id"]:
                await ctx.send("You cannot create an alliance with your own family!")
                return

            # Check if relationship already exists
            existing = await supabase.get_family_relationship(user["family_id"], target_family_data["id"])
            if existing:
                await ctx.send(f"Relationship with {target_family} already exists!")
                return

            # Create alliance
            relationship_id = await supabase.create_family_relationship(
                family_id=user["family_id"],
                target_family_id=target_family_data["id"],
                relationship_type="alliance",
                created_by=str(ctx.author.id),
                notes=notes,
                server_id=str(ctx.guild.id)
            )

            if relationship_id:
                embed = discord.Embed(
                    title="🤝 Alliance Created",
                    description=f"An alliance has been formed between your family and {target_family}.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Notes", value=notes, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to create alliance. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @relationship.command(name="kos")
    @is_family_leader()
    async def create_kos(self, ctx, target_family: str, *, reason: str):
        """Declare another family as KOS (Kill On Sight)."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to declare KOS!")
                return

            # Get target family
            target_family_data = await supabase.get_family_by_name(target_family)
            if not target_family_data:
                await ctx.send("Target family not found!")
                return

            # Check if trying to KOS own family
            if target_family_data["id"] == user["family_id"]:
                await ctx.send("You cannot declare your own family as KOS!")
                return

            # Check if relationship already exists
            existing = await supabase.get_family_relationship(user["family_id"], target_family_data["id"])
            if existing:
                await ctx.send(f"Relationship with {target_family} already exists!")
                return

            # Create KOS relationship
            relationship_id = await supabase.create_family_relationship(
                family_id=user["family_id"],
                target_family_id=target_family_data["id"],
                relationship_type="kos",
                created_by=str(ctx.author.id),
                notes=reason,
                server_id=str(ctx.guild.id)
            )

            if relationship_id:
                embed = discord.Embed(
                    title="⚔️ KOS Declared",
                    description=f"Your family has declared {target_family} as KOS.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to declare KOS. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @relationship.command(name="remove")
    @is_family_leader()
    async def remove_relationship(self, ctx, target_family: str):
        """Remove a relationship with another family."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to remove relationships!")
                return

            # Get target family
            target_family_data = await supabase.get_family_by_name(target_family)
            if not target_family_data:
                await ctx.send("Target family not found!")
                return

            # Get relationship
            relationship = await supabase.get_family_relationship(user["family_id"], target_family_data["id"])
            if not relationship:
                await ctx.send(f"No relationship exists with {target_family}!")
                return

            # Delete relationship
            success = await supabase.delete_family_relationship(relationship["id"])
            if success:
                embed = discord.Embed(
                    title="🔄 Relationship Removed",
                    description=f"Your family's relationship with {target_family} has been removed.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to remove relationship. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @relationship.command(name="list")
    async def list_relationships(self, ctx, family_name: Optional[str] = None):
        """List all relationships for a family."""
        try:
            if family_name:
                # Get family by name
                family = await supabase.get_family_by_name(family_name)
            else:
                # Get user's family
                user = await supabase.get_user(str(ctx.author.id))
                if not user or not user.get("family_id"):
                    await ctx.send("You must be in a family to view relationships!")
                    return
                family = await supabase.get_family(user["family_id"])

            if not family:
                await ctx.send("Family not found!")
                return

            # Get relationships
            relationships = await supabase.get_family_relationships(family["id"])
            if not relationships:
                await ctx.send(f"{family['name']} has no relationships with other families.")
                return

            # Create embeds for alliances and KOS
            alliance_embed = discord.Embed(
                title="🤝 Alliances",
                description=f"Alliances for {family['name']}",
                color=discord.Color.blue()
            )

            kos_embed = discord.Embed(
                title="⚔️ KOS List",
                description=f"KOS declarations for {family['name']}",
                color=discord.Color.red()
            )

            for rel in relationships:
                target_family = await supabase.get_family(rel["target_family_id"])
                if target_family:
                    if rel["relationship_type"] == "alliance":
                        alliance_embed.add_field(
                            name=target_family["name"],
                            value=f"**Notes:** {rel['notes']}\n"
                                  f"**Created:** <t:{int(datetime.fromisoformat(rel['created_at']).timestamp())}:R>",
                            inline=False
                        )
                    else:  # kos
                        kos_embed.add_field(
                            name=target_family["name"],
                            value=f"**Reason:** {rel['notes']}\n"
                                  f"**Declared:** <t:{int(datetime.fromisoformat(rel['created_at']).timestamp())}:R>",
                            inline=False
                        )

            # Send embeds
            if alliance_embed.fields:
                await ctx.send(embed=alliance_embed)
            if kos_embed.fields:
                await ctx.send(embed=kos_embed)
            if not alliance_embed.fields and not kos_embed.fields:
                await ctx.send(f"{family['name']} has no relationships with other families.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Relationships(bot)) 