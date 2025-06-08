import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from db.supabase_client import supabase
import logging
import uuid
from typing import Optional

logger = logging.getLogger('mafia-bot')

class Family(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def family(self, ctx):
        """Family management commands."""
        await ctx.send_help(ctx.command)

    @family.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_family(self, ctx, name: str):
        """Create a new family (Admin only)."""
        try:
            # Check if user already has a family
            user = await supabase.get_user(str(ctx.author.id))
            if user and user.get("family_id"):
                await ctx.send("You are already in a family!")
                return

            # Create the family
            family_id = await supabase.create_family(
                name=name,
                leader_id=str(ctx.author.id),
                main_server_id=str(ctx.guild.id)
            )

            if family_id:
                # Update user's family association
                await supabase.update_user_family(str(ctx.author.id), family_id)
                await ctx.send(f"Family '{name}' has been created! {ctx.author.mention} is the leader.")
            else:
                await ctx.send("Failed to create family. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="invite")
    async def invite_member(self, ctx, member: discord.Member):
        """Invite a member to your family."""
        try:
            # Check if inviter is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to invite members!")
                return

            # Check if inviter is the family leader
            family = await supabase.get_family(user["family_id"])
            if not family or family["leader_id"] != str(ctx.author.id):
                await ctx.send("Only the family leader can invite members!")
                return

            # Check if target is already in a family
            target_user = await supabase.get_user(str(member.id))
            if target_user and target_user.get("family_id"):
                await ctx.send(f"{member.mention} is already in a family!")
                return

            # Create invite
            invite_id = await supabase.create_family_invite(
                family_id=user["family_id"],
                inviter_id=str(ctx.author.id),
                target_id=str(member.id),
                server_id=str(ctx.guild.id)
            )

            if invite_id:
                await ctx.send(f"{member.mention} has been invited to join the family!")
            else:
                await ctx.send("Failed to create invite. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="accept")
    async def accept_invite(self, ctx, invite_id: str):
        """Accept a family invite."""
        try:
            # Check if user is already in a family
            user = await supabase.get_user(str(ctx.author.id))
            if user and user.get("family_id"):
                await ctx.send("You are already in a family!")
                return

            # Accept invite
            success = await supabase.accept_family_invite(
                invite_id=invite_id,
                user_id=str(ctx.author.id)
            )

            if success:
                await ctx.send(f"Welcome to the family, {ctx.author.mention}!")
            else:
                await ctx.send("Invalid or expired invite!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="leave")
    async def leave_family(self, ctx):
        """Leave your current family."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You are not in a family!")
                return

            # Check if user is the leader
            family = await supabase.get_family(user["family_id"])
            if family and family["leader_id"] == str(ctx.author.id):
                await ctx.send("Family leaders cannot leave their family! Transfer leadership first.")
                return

            # Leave family
            success = await supabase.update_user_family(str(ctx.author.id), None)
            if success:
                await ctx.send(f"{ctx.author.mention} has left the family.")
            else:
                await ctx.send("Failed to leave family. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="transfer")
    async def transfer_leadership(self, ctx, new_leader: discord.Member):
        """Transfer family leadership to another member."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to transfer leadership!")
                return

            # Check if user is the leader
            family = await supabase.get_family(user["family_id"])
            if not family or family["leader_id"] != str(ctx.author.id):
                await ctx.send("Only the family leader can transfer leadership!")
                return

            # Check if new leader is in the same family
            new_leader_user = await supabase.get_user(str(new_leader.id))
            if not new_leader_user or new_leader_user.get("family_id") != user["family_id"]:
                await ctx.send(f"{new_leader.mention} must be a member of your family!")
                return

            # Transfer leadership
            success = await supabase.update_family_leader(user["family_id"], str(new_leader.id))
            if success:
                await ctx.send(f"Leadership has been transferred to {new_leader.mention}!")
            else:
                await ctx.send("Failed to transfer leadership. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="info")
    async def family_info(self, ctx, family_name: Optional[str] = None):
        """Display information about a family."""
        try:
            if family_name:
                # Get family by name
                family = await supabase.get_family_by_name(family_name)
            else:
                # Get user's family
                user = await supabase.get_user(str(ctx.author.id))
                if not user or not user.get("family_id"):
                    await ctx.send("You are not in a family! Specify a family name to view its info.")
                    return
                family = await supabase.get_family(user["family_id"])

            if not family:
                await ctx.send("Family not found!")
                return

            # Get family members
            members = await supabase.get_family_members(family["id"])
            
            # Create embed
            embed = discord.Embed(
                title=f"Family: {family['name']}",
                color=discord.Color.blue()
            )
            
            # Add leader info
            leader = self.bot.get_user(int(family["leader_id"]))
            leader_name = leader.name if leader else "Unknown"
            embed.add_field(name="Leader", value=leader_name, inline=True)
            
            # Add member count
            embed.add_field(name="Members", value=str(len(members)), inline=True)
            
            # Add family money
            embed.add_field(name="Family Money", value=f"${family['family_money']:,}", inline=True)
            
            # Add reputation
            embed.add_field(name="Reputation", value=str(family["reputation"]), inline=True)
            
            # Add member list
            member_list = []
            for member in members:
                user = self.bot.get_user(int(member["user_id"]))
                name = user.name if user else "Unknown"
                member_list.append(name)
            
            embed.add_field(name="Members", value="\n".join(member_list) if member_list else "No members", inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @family.command(name="servers")
    async def list_family_servers(self, ctx):
        """List all servers associated with your family."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to use this command!")
                return

            # Get family servers
            servers = await supabase.get_family_servers(user["family_id"])
            
            if not servers:
                await ctx.send("Your family has no associated servers!")
                return

            # Create embed
            embed = discord.Embed(
                title="Family Servers",
                color=discord.Color.blue()
            )
            
            for server in servers:
                server_name = server["name"]
                is_main = " (Main Server)" if server["id"] == server["main_server_id"] else ""
                embed.add_field(
                    name=f"{server_name}{is_main}",
                    value=f"Server ID: {server['id']}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Family(bot)) 