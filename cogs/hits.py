import discord
from discord.ext import commands
from db.supabase_client import supabase
from datetime import datetime, timezone
import logging
from typing import Optional

logger = logging.getLogger('mafia-bot')

class Hits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_family_leader():
        """Check if user is a family leader."""
        async def predicate(ctx):
            family = await supabase.get_user_family(str(ctx.author.id))
            return family and family["leader_id"] == str(ctx.author.id)
        return commands.check(predicate)

    def is_eligible_for_hits():
        """Check if user is eligible to request hits (Made Men or higher)."""
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
            
            # Find Made Men rank
            mademen_rank = next((r for r in ranks if r["name"].lower() == "mademen"), None)
            if not mademen_rank:
                return False
            
            # Check if user's rank is Made Men or higher (lower rank_order means higher rank)
            return rank["rank_order"] <= mademen_rank["rank_order"]
        return commands.check(predicate)

    @commands.group(name='hit', invoke_without_command=True)
    async def hit(self, ctx):
        """Hit contract management commands."""
        await ctx.send_help(ctx.command)

    @hit.command(name='stats')
    async def hit_stats(self, ctx, member: Optional[discord.Member] = None):
        """View hit statistics for yourself or another member."""
        target = member or ctx.author
        
        # Get user's family
        user_family = await supabase.get_user_family(str(target.id))
        if not user_family:
            await ctx.send(f"{target.mention} is not in a family.")
            return

        # Get hit stats
        stats = await supabase.get_hit_stats(str(target.id), str(ctx.guild.id), user_family['family_id'])
        if not stats:
            await ctx.send(f"{target.mention} has no hit statistics yet.")
            return

        embed = discord.Embed(
            title=f"Hit Statistics for {target.display_name}",
            color=discord.Color.blue()
        )
        
        success_rate = (stats['successful_hits'] / stats['total_hits'] * 100) if stats['total_hits'] > 0 else 0
        
        embed.add_field(name="Total Hits", value=str(stats['total_hits']), inline=True)
        embed.add_field(name="Successful", value=str(stats['successful_hits']), inline=True)
        embed.add_field(name="Failed", value=str(stats['failed_hits']), inline=True)
        embed.add_field(name="Success Rate", value=f"{success_rate:.1f}%", inline=True)
        embed.add_field(name="Total Payout", value=f"${stats['total_payout']:,}", inline=True)
        
        await ctx.send(embed=embed)

    @hit.command(name='leaderboard')
    async def hit_leaderboard(self, ctx, scope: str = 'family'):
        """View hit statistics leaderboard.
        
        Parameters:
        -----------
        scope: The scope of the leaderboard (family or server)
        """
        if scope.lower() not in ['family', 'server']:
            await ctx.send("Invalid scope. Use 'family' or 'server'.")
            return

        # Get user's family for family scope
        if scope.lower() == 'family':
            user_family = await supabase.get_user_family(str(ctx.author.id))
            if not user_family:
                await ctx.send("You must be in a family to view family leaderboard.")
                return
            stats = await supabase.get_family_hit_leaderboard(str(ctx.guild.id), user_family['family_id'])
            title = f"Hit Leaderboard - {user_family['family_name']}"
        else:
            stats = await supabase.get_server_hit_leaderboard(str(ctx.guild.id))
            title = "Server Hit Leaderboard"

        if not stats:
            await ctx.send("No hit statistics available.")
            return

        embed = discord.Embed(
            title=title,
            color=discord.Color.gold()
        )

        for i, stat in enumerate(stats, 1):
            user = ctx.guild.get_member(int(stat['user_id']))
            if user:
                success_rate = (stat['successful_hits'] / stat['total_hits'] * 100) if stat['total_hits'] > 0 else 0
                value = (
                    f"Total Hits: {stat['total_hits']}\n"
                    f"Successful: {stat['successful_hits']}\n"
                    f"Success Rate: {success_rate:.1f}%\n"
                    f"Total Payout: ${stat['total_payout']:,}"
                )
                embed.add_field(
                    name=f"{i}. {user.display_name}",
                    value=value,
                    inline=False
                )

        await ctx.send(embed=embed)

    async def update_hit_stats(self, user_id: str, server_id: str, family_id: str, success: bool, payout: int = 0):
        """Update hit statistics for a user."""
        await supabase.update_hit_stats(user_id, server_id, family_id, success, payout)

    @hit.command(name='request')
    @is_eligible_for_hits()
    async def request_hit(self, ctx, target: discord.Member, target_psn: str, reward: int, *, description: str):
        """Request a hit contract on a target."""
        try:
            # Check if user is in a family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to request a hit!")
                return

            # Check if target is in the same family
            target_user = await supabase.get_user(str(target.id))
            if target_user and target_user.get("family_id") == user["family_id"]:
                await ctx.send("You cannot request a hit on a member of your own family!")
                return

            # Check if user has enough money
            if user["money"] < reward:
                await ctx.send("You don't have enough money to pay for this hit!")
                return

            # Create hit contract
            contract_id = await supabase.create_hit_contract(
                target_id=str(target.id),
                target_psn=target_psn,
                requester_id=str(ctx.author.id),
                family_id=user["family_id"],
                reward=reward,
                description=description,
                server_id=str(ctx.guild.id)
            )

            if contract_id:
                # Deduct money from requester
                await supabase.update_user_money(str(ctx.author.id), -reward)
                
                embed = discord.Embed(
                    title="🎯 Hit Contract Requested",
                    description=f"A new hit contract has been requested.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Target", value=target.mention, inline=True)
                embed.add_field(name="Target PSN", value=target_psn, inline=True)
                embed.add_field(name="Reward", value=f"${reward:,}", inline=True)
                embed.add_field(name="Description", value=description, inline=False)
                embed.add_field(name="Status", value="Pending Don's approval", inline=True)
                
                await ctx.send(embed=embed)

                # After successful hit request, update stats
                await self.update_hit_stats(
                    str(ctx.author.id),
                    str(ctx.guild.id),
                    user["family_id"],
                    False  # Initially false, will be updated when hit is completed
                )
            else:
                await ctx.send("Failed to create hit contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name="list")
    @is_family_leader()
    async def list_hits(self, ctx):
        """List all pending hit contracts for your family."""
        try:
            # Get user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id"):
                await ctx.send("You must be in a family to view hit contracts!")
                return

            # Get pending hits
            hits = await supabase.get_pending_hit_contracts(user["family_id"])
            if not hits:
                await ctx.send("No pending hit contracts found.")
                return

            embed = discord.Embed(
                title="🎯 Pending Hit Contracts",
                description="Hit contracts awaiting your approval",
                color=discord.Color.red()
            )

            for hit in hits:
                target = ctx.guild.get_member(int(hit["target_id"]))
                requester = ctx.guild.get_member(int(hit["requester_id"]))
                
                if target and requester:
                    embed.add_field(
                        name=f"Contract #{hit['id'][:8]}",
                        value=f"**Target:** {target.mention}\n"
                              f"**Target PSN:** {hit['target_psn']}\n"
                              f"**Requester:** {requester.mention}\n"
                              f"**Reward:** ${hit['reward']:,}\n"
                              f"**Description:** {hit['description']}\n"
                              f"**Requested:** <t:{int(datetime.fromisoformat(hit['created_at']).timestamp())}:R>",
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name="approve")
    @is_family_leader()
    async def approve_hit(self, ctx, contract_id: str):
        """Approve a hit contract."""
        try:
            # Get hit contract
            contract = await supabase.get_hit_contract(contract_id)
            if not contract:
                await ctx.send("Hit contract not found!")
                return

            # Check if contract belongs to user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id") or user["family_id"] != contract["family_id"]:
                await ctx.send("You can only approve hit contracts for your own family!")
                return

            # Update contract status
            success = await supabase.update_hit_contract_status(
                contract_id=contract_id,
                status="approved",
                approved_by=str(ctx.author.id)
            )

            if success:
                target = ctx.guild.get_member(int(contract["target_id"]))
                requester = ctx.guild.get_member(int(contract["requester_id"]))
                
                embed = discord.Embed(
                    title="✅ Hit Contract Approved",
                    description=f"The hit contract has been approved by {ctx.author.mention}.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Target", value=target.mention, inline=True)
                embed.add_field(name="Target PSN", value=contract["target_psn"], inline=True)
                embed.add_field(name="Requester", value=requester.mention, inline=True)
                embed.add_field(name="Reward", value=f"${contract['reward']:,}", inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to approve hit contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name="reject")
    @is_family_leader()
    async def reject_hit(self, ctx, contract_id: str, *, reason: str):
        """Reject a hit contract."""
        try:
            # Get hit contract
            contract = await supabase.get_hit_contract(contract_id)
            if not contract:
                await ctx.send("Hit contract not found!")
                return

            # Check if contract belongs to user's family
            user = await supabase.get_user(str(ctx.author.id))
            if not user or not user.get("family_id") or user["family_id"] != contract["family_id"]:
                await ctx.send("You can only reject hit contracts for your own family!")
                return

            # Update contract status
            success = await supabase.update_hit_contract_status(
                contract_id=contract_id,
                status="rejected"
            )

            if success:
                # Refund the requester
                await supabase.update_user_money(contract["requester_id"], contract["reward"])
                
                target = ctx.guild.get_member(int(contract["target_id"]))
                requester = ctx.guild.get_member(int(contract["requester_id"]))
                
                embed = discord.Embed(
                    title="❌ Hit Contract Rejected",
                    description=f"The hit contract has been rejected by {ctx.author.mention}.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Target", value=target.mention, inline=True)
                embed.add_field(name="Target PSN", value=contract["target_psn"], inline=True)
                embed.add_field(name="Requester", value=requester.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to reject hit contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name='complete')
    @is_eligible_for_hits()
    async def complete_hit(self, ctx, contract_id: str, proof_url: str):
        """Complete a hit contract with proof.
        
        Parameters:
        -----------
        contract_id: The ID of the hit contract
        proof_url: URL to the proof (image/video) of the hit completion
        """
        try:
            # Get contract details
            contract = await supabase.get_hit_contract(contract_id)
            if not contract:
                await ctx.send("Invalid contract ID.")
                return

            if contract['status'] != 'approved':
                await ctx.send("This contract is not approved for completion.")
                return

            if contract['requester_id'] != str(ctx.author.id):
                await ctx.send("You can only complete your own hit contracts.")
                return

            # Update contract with proof
            success = await supabase.update_hit_contract_proof(contract_id, proof_url)
            if success:
                embed = discord.Embed(
                    title="Hit Contract Completed",
                    description="The hit has been completed and is awaiting verification.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Contract ID", value=contract_id, inline=True)
                embed.add_field(name="Target", value=f"<@{contract['target_id']}>", inline=True)
                embed.add_field(name="Proof", value=proof_url, inline=False)
                
                # Notify family leadership
                family = await supabase.get_family(contract['family_id'])
                if family:
                    leadership_roles = ['Don', 'Godfather', 'Underboss']
                    for role in leadership_roles:
                        role_member = await supabase.get_family_member_by_rank(contract['family_id'], role)
                        if role_member:
                            member = ctx.guild.get_member(int(role_member['user_id']))
                            if member:
                                await member.send(embed=embed)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to complete hit contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name='verify')
    @commands.has_permissions(manage_guild=True)
    async def verify_hit(self, ctx, contract_id: str, status: str, *, reason: str = None):
        """Verify a completed hit contract.
        
        Parameters:
        -----------
        contract_id: The ID of the hit contract
        status: Whether to approve or reject the hit (approved/rejected)
        reason: Reason for the decision (optional)
        """
        try:
            if status.lower() not in ['approved', 'rejected']:
                await ctx.send("Invalid status. Use 'approved' or 'rejected'.")
                return

            # Get contract details
            contract = await supabase.get_hit_contract(contract_id)
            if not contract:
                await ctx.send("Invalid contract ID.")
                return

            if contract['status'] != 'completed':
                await ctx.send("This contract is not ready for verification.")
                return

            # Check if user is family leadership
            user_family = await supabase.get_user_family(str(ctx.author.id), str(ctx.guild.id))
            if not user_family or user_family['family_id'] != contract['family_id']:
                await ctx.send("You can only verify hits for your own family.")
                return

            user_rank = await supabase.get_user_rank(str(ctx.author.id), str(ctx.guild.id))
            if not user_rank or user_rank['rank_name'] not in ['Don', 'Godfather', 'Underboss']:
                await ctx.send("Only family leadership (Don, Godfather, Underboss) can verify hits.")
                return

            # Verify the hit
            success = await supabase.verify_hit_contract(
                contract_id,
                str(ctx.author.id),
                str(ctx.guild.id),
                status.lower(),
                reason
            )

            if success:
                embed = discord.Embed(
                    title=f"Hit Contract {status.title()}",
                    description=reason if reason else f"The hit has been {status.lower()}.",
                    color=discord.Color.green() if status.lower() == 'approved' else discord.Color.red()
                )
                embed.add_field(name="Contract ID", value=contract_id, inline=True)
                embed.add_field(name="Target", value=f"<@{contract['target_id']}>", inline=True)
                embed.add_field(name="Requester", value=f"<@{contract['requester_id']}>", inline=True)
                embed.add_field(name="Verifier", value=ctx.author.mention, inline=True)
                embed.add_field(name="Proof", value=contract['proof_url'], inline=False)

                # Update stats if approved
                if status.lower() == 'approved':
                    await self.update_hit_stats(
                        contract['requester_id'],
                        str(ctx.guild.id),
                        contract['family_id'],
                        True,
                        contract['reward']
                    )

                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to verify hit contract. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name='proof')
    async def view_proof(self, ctx, contract_id: str):
        """View the proof for a completed hit contract."""
        try:
            contract = await supabase.get_hit_contract(contract_id)
            if not contract:
                await ctx.send("Invalid contract ID.")
                return

            if not contract['proof_url']:
                await ctx.send("No proof has been submitted for this contract.")
                return

            # Check if user is in the same family
            user_family = await supabase.get_user_family(str(ctx.author.id), str(ctx.guild.id))
            if not user_family or user_family['family_id'] != contract['family_id']:
                await ctx.send("You can only view proof for hits in your family.")
                return

            embed = discord.Embed(
                title="Hit Contract Proof",
                color=discord.Color.blue()
            )
            embed.add_field(name="Contract ID", value=contract_id, inline=True)
            embed.add_field(name="Target", value=f"<@{contract['target_id']}>", inline=True)
            embed.add_field(name="Requester", value=f"<@{contract['requester_id']}>", inline=True)
            embed.add_field(name="Status", value=contract['status'].title(), inline=True)
            embed.add_field(name="Proof", value=contract['proof_url'], inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @hit.command(name="status")
    async def hit_status(self, ctx):
        """View your hit contract status."""
        try:
            # Get user's hit contracts
            hits = await supabase.get_user_hit_contracts(str(ctx.author.id))
            if not hits:
                await ctx.send("You have no hit contracts.")
                return

            embed = discord.Embed(
                title="🎯 Your Hit Contracts",
                description="Hit contracts involving you",
                color=discord.Color.blue()
            )

            for hit in hits:
                target = ctx.guild.get_member(int(hit["target_id"]))
                requester = ctx.guild.get_member(int(hit["requester_id"]))
                
                if target and requester:
                    status_emoji = {
                        "pending": "⏳",
                        "approved": "✅",
                        "rejected": "❌",
                        "completed": "🎯",
                        "failed": "💀"
                    }.get(hit["status"], "❓")
                    
                    embed.add_field(
                        name=f"{status_emoji} Contract #{hit['id'][:8]}",
                        value=f"**Target:** {target.mention}\n"
                              f"**Target PSN:** {hit['target_psn']}\n"
                              f"**Requester:** {requester.mention}\n"
                              f"**Reward:** ${hit['reward']:,}\n"
                              f"**Status:** {hit['status'].title()}\n"
                              f"**Created:** <t:{int(datetime.fromisoformat(hit['created_at']).timestamp())}:R>",
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Hits(bot)) 