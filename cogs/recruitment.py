import discord
from discord.ext import commands
from db.supabase_client import supabase
from typing import Optional
from datetime import datetime, timezone

class Recruitment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_family_leader():
        """Check if user is a family leader."""
        async def predicate(ctx):
            family = await supabase.get_user_family(str(ctx.author.id))
            return family and family["leader_id"] == str(ctx.author.id)
        return commands.check(predicate)

    @commands.group(invoke_without_command=True)
    @is_family_leader()
    async def recruitment(self, ctx):
        """Manage family recruitment process."""
        await ctx.send_help(ctx.command)

    @recruitment.command(name="addstep")
    @is_family_leader()
    async def add_step(self, ctx, step_number: int, title: str, requires_image: bool = False, *, description: str):
        """Add a new step to the recruitment process."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            # Extract image requirements if this step requires an image
            image_requirements = None
            if requires_image:
                # Look for image requirements in the description
                if "Image Requirements:" in description:
                    desc_parts = description.split("Image Requirements:", 1)
                    description = desc_parts[0].strip()
                    image_requirements = desc_parts[1].strip()

            step = await supabase.create_recruitment_step(
                family["id"],
                step_number,
                title,
                description,
                requires_image,
                image_requirements
            )

            if step:
                embed = discord.Embed(
                    title="✅ Step Added",
                    description=f"Added step {step_number} to the recruitment process.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Title", value=title)
                embed.add_field(name="Description", value=description)
                if requires_image:
                    embed.add_field(name="Image Required", value="Yes", inline=True)
                    if image_requirements:
                        embed.add_field(name="Image Requirements", value=image_requirements, inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to add step. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="setverification")
    @is_family_leader()
    async def set_verification(self, ctx, step_number: int, channel: discord.TextChannel, *, message: str):
        """Set verification requirements for a step."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            success = await supabase.update_recruitment_step(step["id"], {
                "verification_channel_id": str(channel.id),
                "verification_message": message
            })

            if success:
                embed = discord.Embed(
                    title="✅ Verification Set",
                    description=f"Updated verification for step {step_number}.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Channel", value=channel.mention)
                embed.add_field(name="Message", value=message)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to update verification. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="setrole")
    @is_family_leader()
    async def set_role(self, ctx, step_number: int, role: discord.Role):
        """Set a required role for a step."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            success = await supabase.update_recruitment_step(step["id"], {
                "required_role_id": str(role.id)
            })

            if success:
                embed = discord.Embed(
                    title="✅ Role Requirement Set",
                    description=f"Updated role requirement for step {step_number}.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Role", value=role.mention)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to update role requirement. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="list")
    @is_family_leader()
    async def list_steps(self, ctx):
        """List all recruitment steps."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            steps = await supabase.get_recruitment_steps(family["id"])
            if not steps:
                await ctx.send("No recruitment steps found.")
                return

            embed = discord.Embed(
                title="📋 Recruitment Steps",
                description=f"Recruitment process for {family['name']}",
                color=discord.Color.blue()
            )

            for step in sorted(steps, key=lambda x: x["step_number"]):
                step_info = f"**{step['title']}**\n{step['description']}\n"
                if step["required_role_id"]:
                    role = ctx.guild.get_role(int(step["required_role_id"]))
                    if role:
                        step_info += f"Required Role: {role.mention}\n"
                if step["verification_channel_id"]:
                    channel = ctx.guild.get_channel(int(step["verification_channel_id"]))
                    if channel:
                        step_info += f"Verification Channel: {channel.mention}\n"
                embed.add_field(
                    name=f"Step {step['step_number']}",
                    value=step_info,
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="remove")
    @is_family_leader()
    async def remove_step(self, ctx, step_number: int):
        """Remove a recruitment step."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            success = await supabase.delete_recruitment_step(step["id"])
            if success:
                await ctx.send(f"Step {step_number} has been removed.")
            else:
                await ctx.send("Failed to remove step. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="start")
    async def start_recruitment(self, ctx, member: discord.Member):
        """Start the recruitment process for a user."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not in a family!")
                return

            # Check if user is already in recruitment
            progress = await supabase.get_recruitment_progress(str(member.id), family["id"])
            if progress:
                await ctx.send(f"{member.mention} is already in the recruitment process!")
                return

            # Start recruitment
            progress = await supabase.start_recruitment(str(member.id), family["id"])
            if progress:
                steps = await supabase.get_recruitment_steps(family["id"])
                if not steps:
                    await ctx.send("No recruitment steps found. Please add steps first.")
                    return

                current_step = next((s for s in steps if s["step_number"] == 1), None)
                if not current_step:
                    await ctx.send("Error: First step not found!")
                    return

                embed = discord.Embed(
                    title="🎉 Recruitment Started",
                    description=f"{member.mention} has started the recruitment process for {family['name']}!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Current Step",
                    value=f"**{current_step['title']}**\n{current_step['description']}",
                    inline=False
                )

                if current_step["required_role_id"]:
                    role = ctx.guild.get_role(int(current_step["required_role_id"]))
                    if role:
                        embed.add_field(name="Required Role", value=role.mention)

                if current_step["verification_channel_id"]:
                    channel = ctx.guild.get_channel(int(current_step["verification_channel_id"]))
                    if channel:
                        embed.add_field(name="Verification Channel", value=channel.mention)
                        if current_step["verification_message"]:
                            await channel.send(
                                f"{member.mention} {current_step['verification_message']}"
                            )

                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to start recruitment. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="verify")
    @is_family_leader()
    async def verify_step(self, ctx, member: discord.Member, step_number: int, *, notes: Optional[str] = None):
        """Verify a user's completion of a recruitment step."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            # Get user's progress
            progress = await supabase.get_recruitment_progress(str(member.id), family["id"])
            if not progress:
                await ctx.send(f"{member.mention} is not in the recruitment process!")
                return

            # Get step
            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            # Verify step
            success = await supabase.verify_recruitment_step(
                progress["id"],
                step["id"],
                str(ctx.author.id),
                notes
            )

            if success:
                # Check if this was the last step
                if step_number == len(steps):
                    # Complete recruitment
                    await supabase.update_recruitment_progress(progress["id"], {
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    })

                    # Get optimal regime for distribution
                    assignments_cog = ctx.bot.get_cog('Assignments')
                    if assignments_cog:
                        optimal_regime_id = await assignments_cog.get_optimal_regime(family["id"])
                        
                        if optimal_regime_id:
                            # Assign to optimal regime
                            await supabase.table('family_members').update({
                                'regime_id': optimal_regime_id
                            }).eq('user_id', str(member.id)).execute()
                            
                            regime = supabase.table('regimes').select('name').eq('id', optimal_regime_id).execute()
                            regime_name = regime.data[0]['name'] if regime.data else "Unknown"
                            await ctx.send(f"🎉 {member.mention} has completed the recruitment process and been assigned to the **{regime_name}** regime!")
                        else:
                            await ctx.send(f"🎉 {member.mention} has completed the recruitment process!")
                    else:
                        await ctx.send(f"🎉 {member.mention} has completed the recruitment process!")
                else:
                    # Move to next step
                    next_step = next((s for s in steps if s["step_number"] == step_number + 1), None)
                    if next_step:
                        await supabase.update_recruitment_progress(progress["id"], {
                            "current_step": next_step["step_number"]
                        })
                        embed = discord.Embed(
                            title="✅ Step Verified",
                            description=f"{member.mention} has completed step {step_number}!",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="Next Step",
                            value=f"**{next_step['title']}**\n{next_step['description']}",
                            inline=False
                        )
                        await ctx.send(embed=embed)

                        # Send verification message for next step
                        if next_step["verification_channel_id"] and next_step["verification_message"]:
                            channel = ctx.guild.get_channel(int(next_step["verification_channel_id"]))
                            if channel:
                                await channel.send(
                                    f"{member.mention} {next_step['verification_message']}"
                                )
                    else:
                        await ctx.send("Error: Next step not found!")
            else:
                await ctx.send("Failed to verify step. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="progress")
    async def view_progress(self, ctx, member: Optional[discord.Member] = None):
        """View recruitment progress for a user."""
        try:
            target = member or ctx.author
            family = await supabase.get_user_family(str(target.id))
            if not family:
                await ctx.send(f"{target.mention} is not in a family!")
                return

            progress = await supabase.get_recruitment_progress(str(target.id), family["id"])
            if not progress:
                await ctx.send(f"{target.mention} is not in the recruitment process!")
                return

            steps = await supabase.get_recruitment_steps(family["id"])
            verifications = await supabase.get_recruitment_verifications(progress["id"])

            embed = discord.Embed(
                title="📊 Recruitment Progress",
                description=f"Progress for {target.mention} in {family['name']}",
                color=discord.Color.blue()
            )

            for step in sorted(steps, key=lambda x: x["step_number"]):
                verification = next((v for v in verifications if v["step_id"] == step["id"]), None)
                status = "✅ Completed" if verification else "⏳ Pending"
                if step["step_number"] == progress["current_step"]:
                    status = "🔄 Current Step"

                step_info = f"**{step['title']}**\n{step['description']}\nStatus: {status}"
                if verification and verification["notes"]:
                    step_info += f"\nNotes: {verification['notes']}"
                if verification and verification["verified_by"]:
                    verifier = ctx.guild.get_member(int(verification["verified_by"]))
                    if verifier:
                        step_info += f"\nVerified by: {verifier.mention}"

                embed.add_field(
                    name=f"Step {step['step_number']}",
                    value=step_info,
                    inline=False
                )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="submit")
    async def submit_image(self, ctx, step_number: int):
        """Submit an image for a recruitment step."""
        try:
            # Check if user is in a family
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not in a family!")
                return

            # Get user's progress
            progress = await supabase.get_recruitment_progress(str(ctx.author.id), family["id"])
            if not progress:
                await ctx.send("You are not in the recruitment process!")
                return

            # Get step
            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            # Check if step requires an image
            if not step["requires_image"]:
                await ctx.send("This step does not require an image submission!")
                return

            # Check if user has already submitted an image for this step
            submissions = await supabase.get_recruitment_image_submissions(progress["id"])
            existing_submission = next((s for s in submissions if s["step_id"] == step["id"]), None)
            if existing_submission:
                await ctx.send("You have already submitted an image for this step!")
                return

            # Wait for image
            await ctx.send(
                f"Please submit an image for step {step_number}.\n"
                f"**Requirements:** {step['image_requirements']}\n"
                "You have 5 minutes to submit an image."
            )

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and len(m.attachments) > 0

            try:
                message = await self.bot.wait_for('message', check=check, timeout=300)
                image_url = message.attachments[0].url

                # Submit image
                submission = await supabase.submit_recruitment_image(
                    progress["id"],
                    step["id"],
                    image_url,
                    str(ctx.author.id)
                )

                if submission:
                    embed = discord.Embed(
                        title="✅ Image Submitted",
                        description=f"Your image has been submitted for step {step_number}.",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=image_url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Failed to submit image. Please try again.")
            except TimeoutError:
                await ctx.send("No image was submitted within the time limit.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="review")
    @is_family_leader()
    async def review_image(self, ctx, member: discord.Member, step_number: int, status: str, *, notes: Optional[str] = None):
        """Review an image submission for a recruitment step."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            # Get user's progress
            progress = await supabase.get_recruitment_progress(str(member.id), family["id"])
            if not progress:
                await ctx.send(f"{member.mention} is not in the recruitment process!")
                return

            # Get step
            steps = await supabase.get_recruitment_steps(family["id"])
            step = next((s for s in steps if s["step_number"] == step_number), None)
            if not step:
                await ctx.send(f"Step {step_number} not found!")
                return

            # Get submission
            submissions = await supabase.get_recruitment_image_submissions(progress["id"])
            submission = next((s for s in submissions if s["step_id"] == step["id"]), None)
            if not submission:
                await ctx.send(f"No image submission found for step {step_number}!")
                return

            if submission["review_status"] != "pending":
                await ctx.send("This submission has already been reviewed!")
                return

            # Validate status
            valid_statuses = ["approved", "rejected", "needs_revision"]
            if status.lower() not in valid_statuses:
                await ctx.send(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
                return

            # Review submission
            result = await supabase.review_recruitment_image(
                submission["id"],
                str(ctx.author.id),
                status.lower(),
                notes
            )

            if result:
                embed = discord.Embed(
                    title="✅ Review Submitted",
                    description=f"Image submission for step {step_number} has been reviewed.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Status", value=status.capitalize())
                if notes:
                    embed.add_field(name="Notes", value=notes, inline=False)
                await ctx.send(embed=embed)

                # If approved, verify the step
                if status.lower() == "approved":
                    await self.verify_step(ctx, member, step_number, notes=notes)
            else:
                await ctx.send("Failed to submit review. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @recruitment.command(name="pending")
    @is_family_leader()
    async def list_pending(self, ctx):
        """List all pending image submissions."""
        try:
            family = await supabase.get_user_family(str(ctx.author.id))
            if not family:
                await ctx.send("You are not a family leader!")
                return

            submissions = await supabase.get_pending_image_submissions(family["id"])
            if not submissions:
                await ctx.send("No pending image submissions found.")
                return

            embed = discord.Embed(
                title="📝 Pending Submissions",
                description="Image submissions awaiting review",
                color=discord.Color.blue()
            )

            for submission in submissions:
                step = submission["recruitment_steps"]
                progress = submission["recruitment_progress"]
                user = ctx.guild.get_member(int(progress["user_id"]))
                
                if user:
                    embed.add_field(
                        name=f"Step {step['step_number']} - {user.display_name}",
                        value=f"**Title:** {step['title']}\n"
                              f"**Requirements:** {step['image_requirements']}\n"
                              f"**Submitted:** <t:{int(datetime.fromisoformat(submission['submitted_at']).timestamp())}:R>",
                        inline=False
                    )

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Recruitment(bot)) 