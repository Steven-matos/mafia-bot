import discord
from discord.ext import commands
from db.supabase_client import supabase
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger('mafia-bot')

class Mentorship(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_family_leader():
        """Check if user is a family leader."""
        async def predicate(ctx):
            family = await supabase.get_user_family(str(ctx.author.id))
            return family and family["leader_id"] == str(ctx.author.id)
        return commands.check(predicate)

    def is_eligible_mentor():
        """Check if user is eligible to be a mentor (Made Men or Capo)."""
        async def predicate(ctx):
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                return False
            
            rank = await supabase.get_user_rank(str(ctx.author.id))
            if not rank:
                return False
            
            # Get all ranks for the family
            ranks = await supabase.get_family_ranks(user["family_id"])
            if not ranks:
                return False
            
            # Find Made Men and Capo ranks
            mademen_rank = next((r for r in ranks if r["name"].lower() == "mademen"), None)
            capo_rank = next((r for r in ranks if r["name"].lower() == "capo"), None)
            
            if not mademen_rank or not capo_rank:
                return False
            
            # Check if user's rank is Made Men or Capo
            return rank["rank_order"] in [mademen_rank["rank_order"], capo_rank["rank_order"]]
        return commands.check(predicate)

    @commands.group(invoke_without_command=True)
    async def mentor(self, ctx):
        """Mentorship management commands."""
        await ctx.send_help(ctx.command)

    @mentor.command(name="assign")
    @is_family_leader()
    async def assign_mentor(self, ctx, mentor: discord.Member, mentee: discord.Member, *, notes: str = None):
        """Assign a mentor to a mentee."""
        try:
            # Get family
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You must be in a family to assign mentors!")
                return

            # Check if mentor is eligible
            mentor_rank = await supabase.get_user_rank(str(mentor.id))
            if not mentor_rank:
                await ctx.send(f"{mentor.mention} must have a rank to be a mentor!")
                return

            # Get all ranks for the family
            ranks = await supabase.get_family_ranks(family["id"])
            if not ranks:
                await ctx.send("No ranks defined for this family!")
                return

            # Find Made Men and Capo ranks
            mademen_rank = next((r for r in ranks if r["name"].lower() == "mademen"), None)
            capo_rank = next((r for r in ranks if r["name"].lower() == "capo"), None)
            
            if not mademen_rank or not capo_rank:
                await ctx.send("Made Men or Capo ranks not found in this family!")
                return

            # Check if mentor's rank is Made Men or Capo
            if mentor_rank["rank_order"] not in [mademen_rank["rank_order"], capo_rank["rank_order"]]:
                await ctx.send(f"{mentor.mention} must be a Made Man or Capo to be a mentor!")
                return

            # Check if mentee is a recruit
            mentee_rank = await supabase.get_user_rank(str(mentee.id))
            if not mentee_rank:
                await ctx.send(f"{mentee.mention} must have a rank to be a mentee!")
                return

            # Find Recruit rank
            recruit_rank = next((r for r in ranks if r["name"].lower() == "recruits"), None)
            if not recruit_rank:
                await ctx.send("Recruit rank not found in this family!")
                return

            # Check if mentee is a recruit
            if mentee_rank["rank_order"] != recruit_rank["rank_order"]:
                await ctx.send(f"{mentee.mention} must be a Recruit to be a mentee!")
                return

            # Create mentorship
            mentorship_id = await supabase.create_mentorship(
                mentor_id=str(mentor.id),
                mentee_id=str(mentee.id),
                family_id=family["id"],
                notes=notes
            )

            if mentorship_id:
                embed = discord.Embed(
                    title="👨‍🏫 Mentorship Assigned",
                    description=f"{mentor.mention} has been assigned as {mentee.mention}'s mentor.",
                    color=discord.Color.blue()
                )
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to assign mentor. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mentor.command(name="list")
    async def list_mentorships(self, ctx, family_name: Optional[str] = None):
        """List all active mentorships for a family."""
        try:
            if family_name:
                # Get family by name
                family = await supabase.get_family_by_name(family_name)
            else:
                # Get user's family
                user = await supabase.get_user(str(ctx.author.id))
                if not user or not user.get("family_id"):
                    await ctx.send("You must be in a family to view mentorships!")
                    return
                family = await supabase.get_family(user["family_id"])

            if not family:
                await ctx.send("Family not found!")
                return

            # Get mentorships
            mentorships = await supabase.get_family_mentorships(family["id"])
            if not mentorships:
                await ctx.send(f"{family['name']} has no active mentorships.")
                return

            # Create embed
            embed = discord.Embed(
                title=f"👨‍🏫 {family['name']} Mentorships",
                description="Active mentor-mentee relationships",
                color=discord.Color.blue()
            )

            for mentorship in mentorships:
                mentor = ctx.guild.get_member(int(mentorship["mentor_id"]))
                mentee = ctx.guild.get_member(int(mentorship["mentee_id"]))
                if mentor and mentee:
                    embed.add_field(
                        name=f"{mentor.display_name} → {mentee.display_name}",
                        value=f"**Started:** <t:{int(datetime.fromisoformat(mentorship['start_date']).timestamp())}:R>\n"
                              f"**Notes:** {mentorship['notes'] or 'None'}",
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mentor.command(name="end")
    @is_family_leader()
    async def end_mentorship(self, ctx, mentee: discord.Member, *, reason: str = None):
        """End a mentorship relationship."""
        try:
            # Get family
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You must be in a family to end mentorships!")
                return

            # Get mentorships
            mentorships = await supabase.get_family_mentorships(family["id"])
            target_mentorship = next((m for m in mentorships if m["mentee_id"] == str(mentee.id)), None)
            
            if not target_mentorship:
                await ctx.send(f"No active mentorship found for {mentee.mention}!")
                return

            # End mentorship
            success = await supabase.end_mentorship(
                mentorship_id=target_mentorship["id"],
                status="completed",
                notes=reason
            )

            if success:
                mentor = ctx.guild.get_member(int(target_mentorship["mentor_id"]))
                embed = discord.Embed(
                    title="✅ Mentorship Completed",
                    description=f"The mentorship between {mentor.mention} and {mentee.mention} has been completed.",
                    color=discord.Color.green()
                )
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to end mentorship. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @mentor.command(name="my")
    async def my_mentorships(self, ctx):
        """View your current mentorship relationships."""
        try:
            # Get user's mentorships as both mentor and mentee
            mentor_mentorships = await supabase.get_user_mentorships(str(ctx.author.id), "mentor")
            mentee_mentorships = await supabase.get_user_mentorships(str(ctx.author.id), "mentee")

            if not mentor_mentorships and not mentee_mentorships:
                await ctx.send("You have no active mentorship relationships.")
                return

            # Create embed
            embed = discord.Embed(
                title="👨‍🏫 Your Mentorships",
                description="Your current mentorship relationships",
                color=discord.Color.blue()
            )

            # Add mentor relationships
            if mentor_mentorships:
                mentor_field = ""
                for mentorship in mentor_mentorships:
                    mentee = ctx.guild.get_member(int(mentorship["mentee_id"]))
                    if mentee:
                        mentor_field += f"**Mentee:** {mentee.mention}\n"
                        mentor_field += f"**Started:** <t:{int(datetime.fromisoformat(mentorship['start_date']).timestamp())}:R>\n"
                        if mentorship["notes"]:
                            mentor_field += f"**Notes:** {mentorship['notes']}\n"
                        mentor_field += "\n"
                if mentor_field:
                    embed.add_field(name="As Mentor", value=mentor_field, inline=False)

            # Add mentee relationships
            if mentee_mentorships:
                mentee_field = ""
                for mentorship in mentee_mentorships:
                    mentor = ctx.guild.get_member(int(mentorship["mentor_id"]))
                    if mentor:
                        mentee_field += f"**Mentor:** {mentor.mention}\n"
                        mentee_field += f"**Started:** <t:{int(datetime.fromisoformat(mentorship['start_date']).timestamp())}:R>\n"
                        if mentorship["notes"]:
                            mentee_field += f"**Notes:** {mentorship['notes']}\n"
                        mentee_field += "\n"
                if mentee_field:
                    embed.add_field(name="As Mentee", value=mentee_field, inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Mentorship(bot)) 