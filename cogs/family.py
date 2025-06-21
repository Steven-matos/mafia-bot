import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from db.supabase_client import supabase
import logging
import uuid
from typing import Optional, List

logger = logging.getLogger('mafia-bot')

class CreateFamilyModal(discord.ui.Modal, title='Create New Family'):
    def __init__(self):
        super().__init__()
        self.name = discord.ui.TextInput(
            label='Family Name',
            placeholder='Enter family name',
            required=True,
            min_length=3,
            max_length=32
        )
        self.description = discord.ui.TextInput(
            label='Description',
            placeholder='Enter family description (optional)',
            required=False,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.name)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Check if user already has a family
            user = await supabase.get_user(str(interaction.user.id))
            if user and user.get("family_id"):
                await interaction.response.send_message("You are already in a family!", ephemeral=True)
                return

            # Create the family
            family_id = await supabase.create_family(
                name=self.name.value,
                leader_id=str(interaction.user.id),
                main_server_id=str(interaction.guild.id),
                description=self.description.value
            )

            if family_id:
                # Update user's family association
                await supabase.update_user_family(str(interaction.user.id), family_id)
                embed = discord.Embed(
                    title="👨‍👩‍👧‍👦 Family Created",
                    description=f"Family '{self.name.value}' has been created!\n{interaction.user.mention} is the leader.",
                    color=discord.Color.green()
                )
                if self.description.value:
                    embed.add_field(name="Description", value=self.description.value, inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("Failed to create family. Please try again.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in create family modal: {str(e)}")
            await interaction.response.send_message("An error occurred while creating the family.", ephemeral=True)

class FamilyInviteView(discord.ui.View):
    def __init__(self, invite_id: str, family_name: str, inviter: discord.Member):
        super().__init__(timeout=300)  # 5 minute timeout
        self.invite_id = invite_id
        self.family_name = family_name
        self.inviter = inviter

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check if user is already in a family
            user = await supabase.get_user(str(interaction.user.id))
            if user and user.get("family_id"):
                await interaction.response.send_message("You are already in a family!", ephemeral=True)
                return

            # Accept invite
            success = await supabase.accept_family_invite(
                invite_id=self.invite_id,
                user_id=str(interaction.user.id)
            )

            if success:
                embed = discord.Embed(
                    title="👨‍👩‍👧‍👦 Welcome to the Family",
                    description=f"Welcome to {self.family_name}, {interaction.user.mention}!",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                # Disable buttons
                for child in self.children:
                    child.disabled = True
                await interaction.message.edit(view=self)
            else:
                await interaction.response.send_message("Invalid or expired invite!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in accept invite: {str(e)}")
            await interaction.response.send_message("An error occurred while accepting the invite.", ephemeral=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Delete invite
            await supabase.delete_family_invite(self.invite_id)
            embed = discord.Embed(
                title="Invite Declined",
                description=f"{interaction.user.mention} has declined the invite to {self.family_name}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            # Disable buttons
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        except Exception as e:
            logger.error(f"Error in decline invite: {str(e)}")
            await interaction.response.send_message("An error occurred while declining the invite.", ephemeral=True)

class Family(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="family", invoke_without_command=True)
    async def family(self, ctx):
        """Family management commands."""
        await ctx.send_help(ctx.command)

    @family.command(name="create")
    @app_commands.describe()
    @commands.has_permissions(administrator=True)
    async def create_family(self, ctx):
        """Create a new family (Admin only)."""
        try:
            # Check if user already has a family
            user = await supabase.get_user(str(ctx.author.id))
            if user and user.get("family_id"):
                await ctx.send("You are already in a family!")
                return

            # Show create family modal
            modal = CreateFamilyModal()
            await ctx.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in create_family: {str(e)}")
            await ctx.send("An error occurred while creating the family.")

    @family.command(name="invite")
    @app_commands.describe(member="The member to invite to your family")
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
            invite_id = str(uuid.uuid4())
            success = await supabase.create_family_invite(
                family_id=user["family_id"],
                inviter_id=str(ctx.author.id),
                target_id=str(member.id),
                server_id=str(ctx.guild.id)
            )

            if success:
                embed = discord.Embed(
                    title="👨‍👩‍👧‍👦 Family Invite",
                    description=f"{member.mention}, you have been invited to join {family['name']}!",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Invited by", value=ctx.author.mention, inline=True)
                if family.get("description"):
                    embed.add_field(name="Family Description", value=family["description"], inline=False)
                
                view = FamilyInviteView(invite_id, family["name"], ctx.author)
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.send("Failed to create invite. Please try again.")
        except Exception as e:
            logger.error(f"Error in invite_member: {str(e)}")
            await ctx.send("An error occurred while inviting the member.")

    @family.command(name="leave")
    @app_commands.describe()
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

            # Create confirmation view
            class ConfirmView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
                        return
                    
                    success = await supabase.update_user_family(str(ctx.author.id), None)
                    if success:
                        embed = discord.Embed(
                            title="👋 Left Family",
                            description=f"{ctx.author.mention} has left {family['name']}.",
                            color=discord.Color.blue()
                        )
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message("Failed to leave family. Please try again.", ephemeral=True)
                    
                    # Disable buttons
                    for child in self.children:
                        child.disabled = True
                    await interaction.message.edit(view=self)

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("Cancelled leaving the family.")
                    # Disable buttons
                    for child in self.children:
                        child.disabled = True
                    await interaction.message.edit(view=self)

            embed = discord.Embed(
                title="⚠️ Confirm Leave",
                description=f"Are you sure you want to leave {family['name']}?",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, view=ConfirmView())
        except Exception as e:
            logger.error(f"Error in leave_family: {str(e)}")
            await ctx.send("An error occurred while leaving the family.")

    @family.command(name="transfer")
    @app_commands.describe(member="The member to transfer leadership to")
    async def transfer_leadership(self, ctx, member: discord.Member):
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
            new_leader_user = await supabase.get_user(str(member.id))
            if not new_leader_user or new_leader_user.get("family_id") != user["family_id"]:
                await ctx.send(f"{member.mention} must be a member of your family!")
                return

            # Create confirmation view
            class ConfirmView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
                        return
                    
                    success = await supabase.update_family_leader(user["family_id"], str(member.id))
                    if success:
                        embed = discord.Embed(
                            title="👑 Leadership Transferred",
                            description=f"Leadership of {family['name']} has been transferred to {member.mention}!",
                            color=discord.Color.green()
                        )
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message("Failed to transfer leadership. Please try again.", ephemeral=True)
                    
                    # Disable buttons
                    for child in self.children:
                        child.disabled = True
                    await interaction.message.edit(view=self)

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
                        return
                    
                    await interaction.response.send_message("Cancelled leadership transfer.")
                    # Disable buttons
                    for child in self.children:
                        child.disabled = True
                    await interaction.message.edit(view=self)

            embed = discord.Embed(
                title="⚠️ Confirm Leadership Transfer",
                description=f"Are you sure you want to transfer leadership of {family['name']} to {member.mention}?",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, view=ConfirmView())
        except Exception as e:
            logger.error(f"Error in transfer_leadership: {str(e)}")
            await ctx.send("An error occurred while transferring leadership.")

    @family.command(name="info")
    @app_commands.describe(family_name="The name of the family to view info for")
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
                title=f"👨‍👩‍👧‍👦 Family: {family['name']}",
                color=discord.Color.blue()
            )
            
            # Add leader info
            leader = self.bot.get_user(int(family["leader_id"]))
            leader_name = leader.name if leader else "Unknown"
            embed.add_field(name="👑 Leader", value=leader_name, inline=True)
            
            # Add member count
            embed.add_field(name="👥 Members", value=str(len(members)), inline=True)
            
            # Add family money
            embed.add_field(name="💰 Family Money", value=f"${family['family_money']:,}", inline=True)
            
            # Add reputation
            embed.add_field(name="⭐ Reputation", value=str(family["reputation"]), inline=True)
            
            if family.get("description"):
                embed.add_field(name="📝 Description", value=family["description"], inline=False)
            
            # Add member list
            member_list = []
            for member in members:
                user = self.bot.get_user(int(member["user_id"]))
                name = user.name if user else "Unknown"
                rank = member.get("rank", "Member")
                member_list.append(f"{name} ({rank})")
            
            embed.add_field(name="👥 Members", value="\n".join(member_list) if member_list else "No members", inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in family_info: {str(e)}")
            await ctx.send("An error occurred while fetching family information.")

    @family.command(name="servers")
    @app_commands.describe()
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
                title="🌐 Family Servers",
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
            logger.error(f"Error in list_family_servers: {str(e)}")
            await ctx.send("An error occurred while fetching family servers.")

async def setup(bot):
    await bot.add_cog(Family(bot)) 