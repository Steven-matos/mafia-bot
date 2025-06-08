import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("Missing Supabase credentials in .env file")
        self.client: Client = create_client(self.url, self.key)

    # Server-related methods
    async def register_server(self, server_id: str, name: str, is_family_server: bool = False, family_id: Optional[str] = None) -> bool:
        """Register a new server in the database."""
        try:
            data = {
                "id": server_id,
                "name": name,
                "is_family_server": is_family_server,
                "family_id": family_id
            }
            self.client.table("servers").insert(data).execute()
            
            # Create default server settings
            settings_data = {
                "server_id": server_id,
                "prefix": "!",
                "daily_amount": 1000,
                "turf_capture_cooldown": 24,
                "heist_cooldown": 12
            }
            self.client.table("server_settings").insert(settings_data).execute()
            return True
        except Exception as e:
            print(f"Error registering server: {e}")
            return False

    async def get_server_settings(self, server_id: str) -> Optional[Dict]:
        """Get server settings."""
        try:
            response = self.client.table("server_settings").select("*").eq("server_id", server_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting server settings: {e}")
            return None

    async def update_server_settings(self, server_id: str, settings: Dict) -> bool:
        """Update server settings."""
        try:
            self.client.table("server_settings").update(settings).eq("server_id", server_id).execute()
            return True
        except Exception as e:
            print(f"Error updating server settings: {e}")
            return False

    async def add_user_to_server(self, user_id: str, server_id: str) -> bool:
        """Add a user to a server."""
        try:
            data = {
                "user_id": user_id,
                "server_id": server_id
            }
            self.client.table("user_servers").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error adding user to server: {e}")
            return False

    async def get_user_servers(self, user_id: str) -> List[Dict]:
        """Get all servers a user is in."""
        try:
            response = self.client.table("user_servers").select("server_id").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting user servers: {e}")
            return []

    async def get_family_servers(self, family_id: str) -> List[Dict]:
        """Get all servers associated with a family."""
        try:
            response = self.client.table("servers").select("*").eq("family_id", family_id).execute()
            return response.data
        except Exception as e:
            print(f"Error getting family servers: {e}")
            return []

    # Existing methods with server context
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user data from the database."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    async def create_user(self, user_id: str, username: str) -> bool:
        """Create a new user in the database."""
        try:
            data = {
                "id": user_id,
                "username": username,
                "money": 0,
                "bank": 0,
                "reputation": 0,
                "inventory": {},
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.client.table("users").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    async def update_user_money(self, user_id: str, amount: int, is_bank: bool = False) -> bool:
        """Update user's money or bank balance."""
        try:
            field = "bank" if is_bank else "money"
            self.client.table("users").update({field: amount}).eq("id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating user money: {e}")
            return False

    async def get_family(self, family_id: str) -> Optional[Dict]:
        """Get family data from the database."""
        try:
            response = self.client.table("families").select("*").eq("id", family_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting family: {e}")
            return None

    async def create_family(self, name: str, leader_id: str, main_server_id: str) -> Optional[str]:
        """Create a new family in the database."""
        try:
            data = {
                "name": name,
                "leader_id": leader_id,
                "family_money": 0,
                "reputation": 0,
                "main_server_id": main_server_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            response = self.client.table("families").insert(data).execute()
            return response.data[0]["id"] if response.data else None
        except Exception as e:
            print(f"Error creating family: {e}")
            return None

    async def get_turf(self, turf_id: str) -> Optional[Dict]:
        """Get turf data from the database."""
        try:
            response = self.client.table("turfs").select("*").eq("id", turf_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting turf: {e}")
            return None

    async def update_turf_owner(self, turf_id: str, family_id: str) -> bool:
        """Update turf ownership."""
        try:
            data = {
                "owner_family_id": family_id,
                "last_captured_at": datetime.now(timezone.utc).isoformat()
            }
            self.client.table("turfs").update(data).eq("id", turf_id).execute()
            return True
        except Exception as e:
            print(f"Error updating turf owner: {e}")
            return False

    async def record_transaction(self, user_id: str, amount: int, type: str, 
                               target_user_id: Optional[str] = None,
                               item_id: Optional[str] = None,
                               notes: Optional[str] = None,
                               server_id: Optional[str] = None) -> bool:
        """Record a transaction in the database."""
        try:
            data = {
                "user_id": user_id,
                "type": type,
                "amount": amount,
                "target_user_id": target_user_id,
                "item_id": item_id,
                "notes": notes,
                "server_id": server_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.client.table("transactions").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error recording transaction: {e}")
            return False

    async def get_shop_items(self) -> List[Dict]:
        """Get all shop items from the database."""
        try:
            response = self.client.table("shop_items").select("*").execute()
            return response.data
        except Exception as e:
            print(f"Error getting shop items: {e}")
            return []

    async def reset_user(self, user_id: str) -> bool:
        """Reset a user's progress."""
        try:
            # Reset user's money and bank
            await self.client.table("users").update({
                "money": 0,
                "bank": 0,
                "family_id": None,
                "last_daily": None,
                "last_heist": None
            }).eq("id", user_id).execute()
            return True
        except Exception as e:
            print(f"Error resetting user: {str(e)}")
            return False

    async def reset_family(self, family_id: str) -> bool:
        """Reset a family's progress."""
        try:
            # Reset family's money and reputation
            await self.client.table("families").update({
                "family_money": 0,
                "reputation": 0
            }).eq("id", family_id).execute()

            # Reset all family members
            await self.client.table("users").update({
                "money": 0,
                "bank": 0,
                "family_id": None,
                "last_daily": None,
                "last_heist": None
            }).eq("family_id", family_id).execute()

            # Reset all family turfs
            await self.client.table("turfs").update({
                "owner_id": None,
                "last_captured": None
            }).eq("owner_id", family_id).execute()

            return True
        except Exception as e:
            print(f"Error resetting family: {str(e)}")
            return False

    async def get_server_transactions(self, server_id: str, days: int) -> List[Dict]:
        """Get all transactions for a server in the last X days."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            response = await self.client.table("transactions") \
                .select("*") \
                .eq("server_id", server_id) \
                .gte("created_at", cutoff_date.isoformat()) \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting server transactions: {str(e)}")
            return []

    async def ban_user(self, user_id: str, server_id: str, reason: Optional[str] = None) -> bool:
        """Ban a user from using the bot in a server."""
        try:
            await self.client.table("banned_users").insert({
                "user_id": user_id,
                "server_id": server_id,
                "reason": reason,
                "banned_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Error banning user: {str(e)}")
            return False

    async def unban_user(self, user_id: str, server_id: str) -> bool:
        """Unban a user from using the bot in a server."""
        try:
            await self.client.table("banned_users") \
                .delete() \
                .eq("user_id", user_id) \
                .eq("server_id", server_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error unbanning user: {str(e)}")
            return False

    async def get_banned_users(self, server_id: str) -> List[Dict]:
        """Get all banned users for a server."""
        try:
            response = await self.client.table("banned_users") \
                .select("*") \
                .eq("server_id", server_id) \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting banned users: {str(e)}")
            return []

    async def create_recruitment_step(self, family_id: str, step_number: int, title: str, description: str, requires_image: bool = False, image_requirements: str = None) -> dict:
        """Create a new recruitment step."""
        try:
            data = {
                "family_id": family_id,
                "step_number": step_number,
                "title": title,
                "description": description,
                "requires_image": requires_image,
                "image_requirements": image_requirements
            }
            response = await self.client.table("recruitment_steps").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating recruitment step: {str(e)}")
            return None

    async def get_recruitment_steps(self, family_id: str) -> List[Dict]:
        """Get all recruitment steps for a family."""
        try:
            response = await self.client.table("recruitment_steps") \
                .select("*") \
                .eq("family_id", family_id) \
                .order("step_number") \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting recruitment steps: {str(e)}")
            return []

    async def update_recruitment_step(self, step_id: str, updates: Dict) -> bool:
        """Update a recruitment step."""
        try:
            await self.client.table("recruitment_steps") \
                .update(updates) \
                .eq("id", step_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error updating recruitment step: {str(e)}")
            return False

    async def delete_recruitment_step(self, step_id: str) -> bool:
        """Delete a recruitment step."""
        try:
            await self.client.table("recruitment_steps") \
                .delete() \
                .eq("id", step_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error deleting recruitment step: {str(e)}")
            return False

    async def start_recruitment(self, user_id: str, family_id: str) -> Optional[Dict]:
        """Start the recruitment process for a user."""
        try:
            response = await self.client.table("recruitment_progress").insert({
                "user_id": user_id,
                "family_id": family_id,
                "current_step": 1,
                "status": "in_progress"
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error starting recruitment: {str(e)}")
            return None

    async def get_recruitment_progress(self, user_id: str, family_id: str) -> Optional[Dict]:
        """Get a user's recruitment progress."""
        try:
            response = await self.client.table("recruitment_progress") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("family_id", family_id) \
                .single() \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting recruitment progress: {str(e)}")
            return None

    async def update_recruitment_progress(self, progress_id: str, updates: Dict) -> bool:
        """Update a user's recruitment progress."""
        try:
            await self.client.table("recruitment_progress") \
                .update(updates) \
                .eq("id", progress_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error updating recruitment progress: {str(e)}")
            return False

    async def verify_recruitment_step(self, progress_id: str, step_id: str,
                                   verified_by: str, notes: Optional[str] = None) -> bool:
        """Verify a user's completion of a recruitment step."""
        try:
            await self.client.table("recruitment_verifications").insert({
                "progress_id": progress_id,
                "step_id": step_id,
                "verified_by": verified_by,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "notes": notes,
                "status": "completed"
            }).execute()
            return True
        except Exception as e:
            print(f"Error verifying recruitment step: {str(e)}")
            return False

    async def get_recruitment_verifications(self, progress_id: str) -> List[Dict]:
        """Get all verifications for a user's recruitment progress."""
        try:
            response = await self.client.table("recruitment_verifications") \
                .select("*") \
                .eq("progress_id", progress_id) \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting recruitment verifications: {str(e)}")
            return []

    async def submit_recruitment_image(self, progress_id: str, step_id: str, image_url: str, submitted_by: str) -> dict:
        """Submit an image for a recruitment step."""
        try:
            data = {
                "progress_id": progress_id,
                "step_id": step_id,
                "image_url": image_url,
                "submitted_by": submitted_by,
                "review_status": "pending"
            }
            response = await self.client.table("recruitment_image_submissions").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error submitting recruitment image: {str(e)}")
            return None

    async def get_recruitment_image_submissions(self, progress_id: str) -> list:
        """Get all image submissions for a recruitment progress."""
        try:
            response = await self.client.table("recruitment_image_submissions")\
                .select("*")\
                .eq("progress_id", progress_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting recruitment image submissions: {str(e)}")
            return []

    async def review_recruitment_image(self, submission_id: str, reviewed_by: str, review_status: str, review_notes: str = None) -> dict:
        """Review an image submission."""
        try:
            data = {
                "reviewed_by": reviewed_by,
                "review_status": review_status,
                "review_notes": review_notes,
                "reviewed_at": datetime.now(timezone.utc).isoformat()
            }
            response = await self.client.table("recruitment_image_submissions")\
                .update(data)\
                .eq("id", submission_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error reviewing recruitment image: {str(e)}")
            return None

    async def get_pending_image_submissions(self, family_id: str) -> list:
        """Get all pending image submissions for a family."""
        try:
            response = await self.client.table("recruitment_image_submissions")\
                .select("*, recruitment_steps!inner(*), recruitment_progress!inner(*)")\
                .eq("recruitment_steps.family_id", family_id)\
                .eq("review_status", "pending")\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting pending image submissions: {str(e)}")
            return []

    async def create_meeting(self, server_id: str, title: str, description: str, scheduled_by: str, meeting_time: datetime, channel_id: str = None) -> dict:
        """Create a new meeting."""
        try:
            data = {
                "server_id": server_id,
                "title": title,
                "description": description,
                "scheduled_by": scheduled_by,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
                "meeting_time": meeting_time.isoformat(),
                "channel_id": channel_id,
                "status": "scheduled"
            }
            response = await self.client.table("meetings").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating meeting: {str(e)}")
            return None

    async def get_meeting(self, meeting_id: str) -> dict:
        """Get a meeting by ID."""
        try:
            response = await self.client.table("meetings")\
                .select("*")\
                .eq("id", meeting_id)\
                .single()\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting meeting: {str(e)}")
            return None

    async def get_server_meetings(self, server_id: str, status: str = None) -> list:
        """Get all meetings for a server."""
        try:
            query = self.client.table("meetings")\
                .select("*")\
                .eq("server_id", server_id)
            
            if status:
                query = query.eq("status", status)
            
            response = await query.order("meeting_time", desc=True).execute()
            return response.data
        except Exception as e:
            print(f"Error getting server meetings: {str(e)}")
            return []

    async def update_meeting(self, meeting_id: str, data: dict) -> dict:
        """Update a meeting."""
        try:
            response = await self.client.table("meetings")\
                .update(data)\
                .eq("id", meeting_id)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating meeting: {str(e)}")
            return None

    async def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting."""
        try:
            response = await self.client.table("meetings")\
                .delete()\
                .eq("id", meeting_id)\
                .execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error deleting meeting: {str(e)}")
            return False

    async def create_rsvp(self, meeting_id: str, user_id: str, status: str, notes: str = None) -> dict:
        """Create or update an RSVP for a meeting."""
        try:
            data = {
                "meeting_id": meeting_id,
                "user_id": user_id,
                "status": status,
                "notes": notes,
                "responded_at": datetime.now(timezone.utc).isoformat()
            }
            response = await self.client.table("meeting_rsvps")\
                .upsert(data)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating RSVP: {str(e)}")
            return None

    async def get_meeting_rsvps(self, meeting_id: str) -> list:
        """Get all RSVPs for a meeting."""
        try:
            response = await self.client.table("meeting_rsvps")\
                .select("*")\
                .eq("meeting_id", meeting_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting meeting RSVPs: {str(e)}")
            return []

    async def get_user_rsvps(self, user_id: str) -> list:
        """Get all RSVPs for a user."""
        try:
            response = await self.client.table("meeting_rsvps")\
                .select("*, meetings!inner(*)")\
                .eq("user_id", user_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting user RSVPs: {str(e)}")
            return []

    async def create_server_turfs(self, server_id: str, turfs: List[Dict]) -> bool:
        """Create multiple turfs for a server."""
        try:
            # Add server_id to each turf
            for turf in turfs:
                turf["server_id"] = server_id
                turf["created_at"] = datetime.now(timezone.utc).isoformat()
            
            response = await self.client.table("turfs").insert(turfs).execute()
            return True
        except Exception as e:
            print(f"Error creating server turfs: {str(e)}")
            return False

# Create a singleton instance
supabase = SupabaseClient() 