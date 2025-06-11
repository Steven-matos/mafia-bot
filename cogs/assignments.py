import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import pytz
from typing import Optional
from utils.checks import is_family_don, is_regime_leader, is_family_member
from db.supabase_client import supabase
import logging

logger = logging.getLogger('mafia-bot')

class Assignments(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @is_family_member()
    async def regime(self, ctx):
        """Manage family regimes and assignments"""
        await ctx.send_help(ctx.command)

    @regime.command(name="setdefault")
    @is_family_don()
    async def set_default_regime(self, ctx, regime_name: str):
        """Set the default regime for new recruits"""
        try:
            # Get regime
            regime = supabase.table('regimes').select('*').eq('family_id', ctx.family_id).eq('name', regime_name).execute()
            if not regime.data:
                return await ctx.send("❌ Regime not found.")

            # Update family's default regime
            result = supabase.table('families').update({
                'default_regime_id': regime.data[0]['id']
            }).eq('id', ctx.family_id).execute()
            
            if result.data:
                await ctx.send(f"✅ Set **{regime_name}** as the default regime for new recruits.")
            else:
                await ctx.send("❌ Failed to set default regime.")
        except Exception as e:
            await ctx.send(f"❌ Error setting default regime: {str(e)}")

    @regime.command(name="create")
    @is_family_don()
    async def create_regime(self, ctx, name: str, leader: discord.Member, *, description: Optional[str] = None):
        """Create a new regime in your family"""
        try:
            # Check if leader is in the family
            leader_data = supabase.table('family_members').select('*').eq('user_id', str(leader.id)).eq('family_id', ctx.family_id).execute()
            if not leader_data.data:
                return await ctx.send("The leader must be a member of your family.")

            # Create regime
            regime_data = {
                'family_id': ctx.family_id,
                'name': name,
                'description': description,
                'leader_id': str(leader.id)
            }
            result = supabase.table('regimes').insert(regime_data).execute()
            
            if result.data:
                await ctx.send(f"✅ Created regime **{name}** with {leader.mention} as leader.")
            else:
                await ctx.send("❌ Failed to create regime.")
        except Exception as e:
            await ctx.send(f"❌ Error creating regime: {str(e)}")

    @regime.command(name="list")
    @is_family_member()
    async def list_regimes(self, ctx):
        """List all regimes in your family"""
        try:
            regimes = supabase.table('regimes').select('*').eq('family_id', ctx.family_id).execute()
            
            if not regimes.data:
                return await ctx.send("No regimes found in your family.")

            embed = discord.Embed(title="Family Regimes", color=discord.Color.blue())
            for regime in regimes.data:
                leader = ctx.guild.get_member(int(regime['leader_id']))
                leader_name = leader.name if leader else "Unknown"
                embed.add_field(
                    name=regime['name'],
                    value=f"Leader: {leader_name}\nDescription: {regime['description'] or 'No description'}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error listing regimes: {str(e)}")

    @regime.command(name="assign")
    @is_regime_leader()
    async def assign_member(self, ctx, member: discord.Member, regime_name: str):
        """Assign a family member to a regime"""
        try:
            # Get regime
            regime = supabase.table('regimes').select('*').eq('family_id', ctx.family_id).eq('name', regime_name).execute()
            if not regime.data:
                return await ctx.send("❌ Regime not found.")

            # Check if member is in family
            member_data = supabase.table('family_members').select('*').eq('user_id', str(member.id)).eq('family_id', ctx.family_id).execute()
            if not member_data.data:
                return await ctx.send("❌ Member is not in your family.")

            # Update member's regime
            result = supabase.table('family_members').update({'regime_id': regime.data[0]['id']}).eq('user_id', str(member.id)).execute()
            
            if result.data:
                await ctx.send(f"✅ Assigned {member.mention} to regime **{regime_name}**.")
            else:
                await ctx.send("❌ Failed to assign member to regime.")
        except Exception as e:
            await ctx.send(f"❌ Error assigning member: {str(e)}")

    @commands.group(invoke_without_command=True)
    @is_family_member()
    async def assignment(self, ctx):
        """Manage family assignments"""
        await ctx.send_help(ctx.command)

    @assignment.command(name="create")
    @is_regime_leader()
    async def create_assignment(self, ctx, regime_name: str, member: discord.Member, title: str, reward: int, deadline_hours: int, *, description: str):
        """Create a new assignment for a regime member"""
        try:
            # Get regime
            regime = supabase.table('regimes').select('*').eq('family_id', ctx.family_id).eq('name', regime_name).execute()
            if not regime.data:
                return await ctx.send("❌ Regime not found.")

            # Check if member is in the regime
            member_data = supabase.table('family_members').select('*').eq('user_id', str(member.id)).eq('regime_id', regime.data[0]['id']).execute()
            if not member_data.data:
                return await ctx.send("❌ Member is not in this regime.")

            # Create assignment
            deadline = datetime.now(pytz.UTC) + timedelta(hours=deadline_hours)
            assignment_data = {
                'family_id': ctx.family_id,
                'regime_id': regime.data[0]['id'],
                'title': title,
                'description': description,
                'reward_amount': reward,
                'deadline': deadline.isoformat(),
                'created_by': str(ctx.author.id),
                'assigned_to': str(member.id)
            }
            result = supabase.table('assignments').insert(assignment_data).execute()
            
            if result.data:
                embed = discord.Embed(
                    title="New Assignment Created",
                    description=f"**{title}**\n\n{description}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Reward", value=f"${reward:,}")
                embed.add_field(name="Deadline", value=f"<t:{int(deadline.timestamp())}:R>")
                embed.add_field(name="Assigned To", value=member.mention)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to create assignment.")
        except Exception as e:
            await ctx.send(f"❌ Error creating assignment: {str(e)}")

    @assignment.command(name="list")
    @is_family_member()
    async def list_assignments(self, ctx, status: Optional[str] = "pending"):
        """List assignments for your regime"""
        try:
            # Get member's regime
            member_data = supabase.table('family_members').select('regime_id').eq('user_id', str(ctx.author.id)).execute()
            if not member_data.data or not member_data.data[0]['regime_id']:
                return await ctx.send("❌ You are not assigned to any regime.")

            # Get assignments
            assignments = supabase.table('assignments').select('*').eq('regime_id', member_data.data[0]['regime_id']).eq('status', status).execute()
            
            if not assignments.data:
                return await ctx.send(f"No {status} assignments found.")

            embed = discord.Embed(title=f"{status.title()} Assignments", color=discord.Color.blue())
            for assignment in assignments.data:
                creator = ctx.guild.get_member(int(assignment['created_by']))
                creator_name = creator.name if creator else "Unknown"
                
                deadline = datetime.fromisoformat(assignment['deadline'].replace('Z', '+00:00'))
                embed.add_field(
                    name=assignment['title'],
                    value=f"Description: {assignment['description']}\nReward: ${assignment['reward_amount']:,}\nDeadline: <t:{int(deadline.timestamp())}:R>\nCreated by: {creator_name}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error listing assignments: {str(e)}")

    @assignment.command(name="complete")
    @is_family_member()
    async def complete_assignment(self, ctx, assignment_id: int):
        """Mark an assignment as completed"""
        try:
            # Get assignment
            assignment = supabase.table('assignments').select('*').eq('id', assignment_id).execute()
            if not assignment.data:
                return await ctx.send("❌ Assignment not found.")

            # Check if assignment is assigned to the user
            if str(assignment.data[0]['assigned_to']) != str(ctx.author.id):
                return await ctx.send("❌ This assignment is not assigned to you.")

            # Check if assignment is already completed
            if assignment.data[0]['status'] in ['completed', 'failed', 'expired']:
                return await ctx.send("❌ This assignment is already completed.")

            # Update assignment status
            result = supabase.table('assignments').update({
                'status': 'completed',
                'completed_at': datetime.now(pytz.UTC).isoformat()
            }).eq('id', assignment_id).execute()
            
            if result.data:
                # Add reward to user's balance
                supabase.table('users').update({
                    'balance': supabase.raw(f"balance + {assignment.data[0]['reward_amount']}")
                }).eq('user_id', str(ctx.author.id)).execute()
                
                await ctx.send(f"✅ Assignment completed! You received ${assignment.data[0]['reward_amount']:,}.")
            else:
                await ctx.send("❌ Failed to complete assignment.")
        except Exception as e:
            await ctx.send(f"❌ Error completing assignment: {str(e)}")

    @regime.command(name="distribution")
    @is_family_don()
    async def manage_distribution(self, ctx, regime_name: str, action: str, target_count: Optional[int] = None):
        """Manage regime distribution settings
        Actions: add, remove, setcount
        """
        try:
            # Get regime
            regime = supabase.table('regimes').select('*').eq('family_id', ctx.family_id).eq('name', regime_name).execute()
            if not regime.data:
                return await ctx.send("❌ Regime not found.")

            regime_id = regime.data[0]['id']

            if action.lower() == "add":
                # Add regime to distribution
                result = supabase.table('regime_distribution').insert({
                    'family_id': ctx.family_id,
                    'regime_id': regime_id,
                    'is_active': True
                }).execute()
                
                if result.data:
                    await ctx.send(f"✅ Added **{regime_name}** to automatic regime distribution.")
                else:
                    await ctx.send("❌ Failed to add regime to distribution.")

            elif action.lower() == "remove":
                # Remove regime from distribution
                result = supabase.table('regime_distribution').delete().eq('family_id', ctx.family_id).eq('regime_id', regime_id).execute()
                
                if result.data:
                    await ctx.send(f"✅ Removed **{regime_name}** from automatic regime distribution.")
                else:
                    await ctx.send("❌ Failed to remove regime from distribution.")

            elif action.lower() == "setcount":
                if target_count is None:
                    return await ctx.send("❌ Please specify a target member count.")
                
                # Update target member count
                result = supabase.table('regime_distribution').update({
                    'target_member_count': target_count
                }).eq('family_id', ctx.family_id).eq('regime_id', regime_id).execute()
                
                if result.data:
                    await ctx.send(f"✅ Set target member count for **{regime_name}** to {target_count}.")
                else:
                    await ctx.send("❌ Failed to update target member count.")

            else:
                await ctx.send("❌ Invalid action. Use: add, remove, or setcount")

        except Exception as e:
            await ctx.send(f"❌ Error managing regime distribution: {str(e)}")

    @regime.command(name="listdistribution")
    @is_family_member()
    async def list_distribution(self, ctx):
        """List all regimes in the distribution system"""
        try:
            # Get all regimes in distribution
            distribution = supabase.table('regime_distribution').select('*, regimes(name)').eq('family_id', ctx.family_id).execute()
            
            if not distribution.data:
                return await ctx.send("No regimes are set up for automatic distribution.")

            embed = discord.Embed(
                title="📊 Regime Distribution Settings",
                description="Regimes configured for automatic member distribution",
                color=discord.Color.blue()
            )

            for dist in distribution.data:
                regime = dist['regimes']
                embed.add_field(
                    name=regime['name'],
                    value=f"Status: {'Active' if dist['is_active'] else 'Inactive'}\n"
                          f"Target Members: {dist['target_member_count']}",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error listing regime distribution: {str(e)}")

    async def get_optimal_regime(self, family_id: str) -> Optional[int]:
        """Get the optimal regime to assign a new member to based on current distribution"""
        try:
            # Get all active regimes in distribution
            distribution = supabase.table('regime_distribution').select('*, regimes(name)').eq('family_id', family_id).eq('is_active', True).execute()
            
            if not distribution.data:
                return None

            # Get current member counts for each regime
            member_counts = {}
            for dist in distribution.data:
                regime_id = dist['regime_id']
                count = supabase.table('family_members').select('*').eq('regime_id', regime_id).execute()
                member_counts[regime_id] = len(count.data)

            # Find regime with lowest member count relative to target
            optimal_regime = None
            lowest_ratio = float('inf')

            for dist in distribution.data:
                regime_id = dist['regime_id']
                current_count = member_counts.get(regime_id, 0)
                target_count = dist['target_member_count'] or 1  # Default to 1 if not set
                
                ratio = current_count / target_count
                if ratio < lowest_ratio:
                    lowest_ratio = ratio
                    optimal_regime = regime_id

            return optimal_regime

        except Exception as e:
            print(f"Error getting optimal regime: {str(e)}")
            return None

async def setup(bot):
    await bot.add_cog(Assignments(bot)) 