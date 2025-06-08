import discord
from discord.ext import commands, tasks
from db.supabase_client import supabase
from typing import Optional
from datetime import datetime, timezone, timedelta
import re

def is_admin_or_mod():
    """Check if user is an admin or moderator."""
    async def predicate(ctx):
        user_servers = await supabase.get_user_servers(str(ctx.author.id))
        server = next((s for s in user_servers if s["server_id"] == str(ctx.guild.id)), None)
        return server and server["role"] in ["admin", "moderator"]
    return commands.check(predicate)

class Meetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_upcoming_meetings.start()

    def cog_unload(self):
        self.check_upcoming_meetings.cancel()

    @tasks.loop(minutes=5)
    async def check_upcoming_meetings(self):
        """Check for upcoming meetings and send reminders."""
        try:
            # Get meetings happening in the next hour
            upcoming = await supabase.get_upcoming_meetings(timedelta(hours=1))
            
            for meeting in upcoming:
                # Skip if already reminded
                if meeting.get("reminder_sent"):
                    continue

                # Get the channel
                channel = self.bot.get_channel(int(meeting["channel_id"]))
                if not channel:
                    continue

                # Get RSVPs
                rsvps = await supabase.get_meeting_rsvps(meeting["id"])
                attending = sum(1 for r in rsvps if r["status"] == "attending")
                
                # Create reminder embed
                embed = discord.Embed(
                    title="⏰ Meeting Reminder",
                    description=f"**{meeting['title']}** is starting soon!",
                    color=discord.Color.blue()
                )
                
                meeting_time = datetime.fromisoformat(meeting["meeting_time"])
                embed.add_field(
                    name="Time",
                    value=f"<t:{int(meeting_time.timestamp())}:F> (<t:{int(meeting_time.timestamp())}:R>)",
                    inline=False
                )
                
                if meeting.get("duration_minutes"):
                    embed.add_field(
                        name="Duration",
                        value=f"{meeting['duration_minutes']} minutes",
                        inline=True
                    )
                
                # Send reminder
                await channel.send(embed=embed)
                
                # Mark reminder as sent
                await supabase.update_meeting(meeting["id"], {"reminder_sent": True})
        except Exception as e:
            print(f"Error in check_upcoming_meetings: {str(e)}")

    @commands.group(invoke_without_command=True)
    async def meeting(self, ctx):
        """Manage meetings and RSVPs."""
        await ctx.send_help(ctx.command)

    @meeting.command(name="schedule")
    @is_admin_or_mod()
    async def schedule_meeting(self, ctx, channel: discord.TextChannel, time: str, *, title: str):
        """Schedule a new meeting.
        
        Parameters:
        -----------
        channel: The channel to post the meeting in
        time: Meeting time (YYYY-MM-DD HH:MM)
        title: Meeting title
        """
        try:
            # Parse the time string
            try:
                meeting_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
                meeting_time = meeting_time.replace(tzinfo=timezone.utc)
            except ValueError:
                await ctx.send("Invalid time format. Please use YYYY-MM-DD HH:MM")
                return

            # Create the meeting
            meeting = await supabase.create_meeting(
                str(ctx.guild.id),
                title,
                f"Scheduled by {ctx.author.mention}",
                str(ctx.author.id),
                meeting_time,
                str(channel.id)
            )

            if meeting:
                # Create the RSVP message
                embed = discord.Embed(
                    title=f"📅 Meeting: {title}",
                    description=f"Scheduled by {ctx.author.mention}",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Time",
                    value=f"<t:{int(meeting_time.timestamp())}:F> (<t:{int(meeting_time.timestamp())}:R>)",
                    inline=False
                )
                embed.add_field(
                    name="RSVP Status",
                    value="Click the buttons below to RSVP",
                    inline=False
                )

                # Send the message with buttons
                message = await channel.send(embed=embed, view=RSVPView(meeting["id"]))
                
                # Update the meeting with the message ID
                await supabase.update_meeting(meeting["id"], {
                    "message_id": str(message.id)
                })

                await ctx.send(f"Meeting scheduled successfully! Check {channel.mention}")
            else:
                await ctx.send("Failed to schedule meeting. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @meeting.command(name="reschedule")
    @is_admin_or_mod()
    async def reschedule_meeting(self, ctx, meeting_id: str, new_time: str):
        """Reschedule a meeting to a new time.
        
        Parameters:
        -----------
        meeting_id: The ID of the meeting to reschedule
        new_time: New meeting time (YYYY-MM-DD HH:MM)
        """
        try:
            meeting = await supabase.get_meeting(meeting_id)
            if not meeting:
                await ctx.send("Meeting not found.")
                return

            if meeting["status"] != "scheduled":
                await ctx.send("Can only reschedule scheduled meetings.")
                return

            # Parse the new time
            try:
                new_meeting_time = datetime.strptime(new_time, "%Y-%m-%d %H:%M")
                new_meeting_time = new_meeting_time.replace(tzinfo=timezone.utc)
            except ValueError:
                await ctx.send("Invalid time format. Please use YYYY-MM-DD HH:MM")
                return

            # Update meeting time
            success = await supabase.update_meeting(meeting_id, {
                "meeting_time": new_meeting_time.isoformat(),
                "reminder_sent": False  # Reset reminder flag
            })

            if success:
                # Update the message if it exists
                if meeting["channel_id"] and meeting["message_id"]:
                    try:
                        channel = ctx.guild.get_channel(int(meeting["channel_id"]))
                        if channel:
                            message = await channel.fetch_message(int(meeting["message_id"]))
                            if message:
                                embed = message.embeds[0]
                                embed.set_field_at(
                                    0,
                                    name="Time",
                                    value=f"<t:{int(new_meeting_time.timestamp())}:F> (<t:{int(new_meeting_time.timestamp())}:R>)",
                                    inline=False
                                )
                                await message.edit(embed=embed)
                    except:
                        pass

                await ctx.send("Meeting rescheduled successfully.")
            else:
                await ctx.send("Failed to reschedule meeting. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @meeting.command(name="list")
    async def list_meetings(self, ctx):
        """List all scheduled meetings."""
        try:
            meetings = await supabase.get_server_meetings(str(ctx.guild.id), "scheduled")
            if not meetings:
                await ctx.send("No scheduled meetings found.")
                return

            embed = discord.Embed(
                title="📅 Scheduled Meetings",
                color=discord.Color.blue()
            )

            for meeting in meetings:
                meeting_time = datetime.fromisoformat(meeting["meeting_time"])
                rsvps = await supabase.get_meeting_rsvps(meeting["id"])
                
                attending = sum(1 for r in rsvps if r["status"] == "attending")
                not_attending = sum(1 for r in rsvps if r["status"] == "not_attending")
                pending = sum(1 for r in rsvps if r["status"] == "pending")

                value = f"**Time:** <t:{int(meeting_time.timestamp())}:F>\n"
                value += f"**RSVPs:** ✅ {attending} | ❌ {not_attending} | ⏳ {pending}"
                
                if meeting.get("duration_minutes"):
                    value += f"\n**Duration:** {meeting['duration_minutes']} minutes"

                embed.add_field(
                    name=meeting["title"],
                    value=value,
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @meeting.command(name="rsvps")
    @is_admin_or_mod()
    async def view_rsvps(self, ctx, meeting_id: str):
        """View RSVPs for a specific meeting."""
        try:
            meeting = await supabase.get_meeting(meeting_id)
            if not meeting:
                await ctx.send("Meeting not found.")
                return

            rsvps = await supabase.get_meeting_rsvps(meeting_id)
            if not rsvps:
                await ctx.send("No RSVPs found for this meeting.")
                return

            embed = discord.Embed(
                title=f"📊 RSVPs for {meeting['title']}",
                color=discord.Color.blue()
            )

            # Group RSVPs by status
            attending = []
            not_attending = []
            pending = []

            for rsvp in rsvps:
                user = ctx.guild.get_member(int(rsvp["user_id"]))
                if user:
                    if rsvp["status"] == "attending":
                        attending.append(user.mention)
                    elif rsvp["status"] == "not_attending":
                        not_attending.append(user.mention)
                    else:
                        pending.append(user.mention)

            if attending:
                embed.add_field(
                    name="✅ Attending",
                    value="\n".join(attending) or "None",
                    inline=False
                )
            if not_attending:
                embed.add_field(
                    name="❌ Not Attending",
                    value="\n".join(not_attending) or "None",
                    inline=False
                )
            if pending:
                embed.add_field(
                    name="⏳ Pending",
                    value="\n".join(pending) or "None",
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @meeting.command(name="cancel")
    @is_admin_or_mod()
    async def cancel_meeting(self, ctx, meeting_id: str):
        """Cancel a scheduled meeting."""
        try:
            meeting = await supabase.get_meeting(meeting_id)
            if not meeting:
                await ctx.send("Meeting not found.")
                return

            if meeting["status"] != "scheduled":
                await ctx.send("This meeting is not scheduled.")
                return

            # Update meeting status
            success = await supabase.update_meeting(meeting_id, {
                "status": "cancelled"
            })

            if success:
                # Update the RSVP message if it exists
                if meeting["channel_id"] and meeting["message_id"]:
                    try:
                        channel = ctx.guild.get_channel(int(meeting["channel_id"]))
                        if channel:
                            message = await channel.fetch_message(int(meeting["message_id"]))
                            if message:
                                embed = message.embeds[0]
                                embed.color = discord.Color.red()
                                embed.add_field(
                                    name="Status",
                                    value="❌ Cancelled",
                                    inline=False
                                )
                                await message.edit(embed=embed, view=None)
                    except:
                        pass

                await ctx.send("Meeting cancelled successfully.")
            else:
                await ctx.send("Failed to cancel meeting. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

class RSVPView(discord.ui.View):
    def __init__(self, meeting_id: str):
        super().__init__(timeout=None)
        self.meeting_id = meeting_id

    @discord.ui.button(label="Attending", style=discord.ButtonStyle.green, custom_id="rsvp_attending")
    async def attending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rsvp(interaction, "attending")

    @discord.ui.button(label="Not Attending", style=discord.ButtonStyle.red, custom_id="rsvp_not_attending")
    async def not_attending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rsvp(interaction, "not_attending")

    async def handle_rsvp(self, interaction: discord.Interaction, status: str):
        try:
            # Get meeting details
            meeting = await supabase.get_meeting(self.meeting_id)
            if not meeting:
                await interaction.response.send_message("Meeting not found.", ephemeral=True)
                return

            # Check if meeting is still scheduled
            if meeting["status"] != "scheduled":
                await interaction.response.send_message("This meeting is no longer scheduled.", ephemeral=True)
                return

            # Create/update RSVP
            rsvp = await supabase.create_rsvp(
                self.meeting_id,
                str(interaction.user.id),
                status
            )

            if rsvp:
                # Update the message
                rsvps = await supabase.get_meeting_rsvps(self.meeting_id)
                attending = sum(1 for r in rsvps if r["status"] == "attending")
                not_attending = sum(1 for r in rsvps if r["status"] == "not_attending")
                pending = sum(1 for r in rsvps if r["status"] == "pending")

                embed = interaction.message.embeds[0]
                embed.set_field_at(
                    1,
                    name="RSVP Status",
                    value=f"✅ Attending: {attending}\n❌ Not Attending: {not_attending}\n⏳ Pending: {pending}",
                    inline=False
                )
                await interaction.message.edit(embed=embed)

                await interaction.response.send_message(
                    f"You have marked yourself as {'attending' if status == 'attending' else 'not attending'}.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Failed to update RSVP. Please try again.",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Meetings(bot)) 