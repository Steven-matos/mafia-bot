import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import asyncio
import logging
from collections import defaultdict

# Load environment variables
load_dotenv()

logger = logging.getLogger('mafia-bot')

class RateLimiter:
    def __init__(self, max_calls: int, time_window: int):
        """
        Initialize rate limiter.
        :param max_calls: Maximum number of calls allowed in the time window
        :param time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
        self.lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        """
        Try to acquire a rate limit token.
        :param key: Rate limit key (e.g., user_id, server_id)
        :return: True if token acquired, False if rate limited
        """
        async with self.lock:
            now = datetime.now(timezone.utc)
            # Remove old calls outside the time window
            self.calls[key] = [call_time for call_time in self.calls[key]
                             if (now - call_time).total_seconds() < self.time_window]
            
            if len(self.calls[key]) >= self.max_calls:
                return False
            
            self.calls[key].append(now)
            return True

    async def wait_for_token(self, key: str, timeout: int = 30) -> bool:
        """
        Wait for a rate limit token to become available.
        :param key: Rate limit key
        :param timeout: Maximum time to wait in seconds
        :return: True if token acquired, False if timed out
        """
        start_time = datetime.now(timezone.utc)
        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            if await self.acquire(key):
                return True
            await asyncio.sleep(0.1)
        return False

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        if not self.url or not self.key:
            raise ValueError("Missing Supabase credentials in .env file")
        self.client: Client = create_client(self.url, self.key)
        
        # Initialize rate limiters
        # 100 calls per minute for general operations
        self.general_limiter = RateLimiter(max_calls=100, time_window=60)
        # 20 calls per minute for write operations
        self.write_limiter = RateLimiter(max_calls=20, time_window=60)
        # 5 calls per minute for high-impact operations
        self.high_impact_limiter = RateLimiter(max_calls=5, time_window=60)

    async def _execute_with_rate_limit(self, operation: str, key: str, func, *args, **kwargs):
        """
        Execute a function with rate limiting.
        :param operation: Operation type ('read', 'write', 'high_impact')
        :param key: Rate limit key
        :param func: Function to execute
        :param args: Function arguments
        :param kwargs: Function keyword arguments
        :return: Function result
        """
        # Select appropriate rate limiter
        limiter = {
            'read': self.general_limiter,
            'write': self.write_limiter,
            'high_impact': self.high_impact_limiter
        }.get(operation, self.general_limiter)

        # Wait for rate limit token
        if not await limiter.wait_for_token(key):
            logger.warning(f"Rate limit exceeded for {operation} operation with key {key}")
            raise Exception("Rate limit exceeded. Please try again later.")

        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing {operation} operation: {str(e)}")
            raise

    # Server-related methods
    async def register_server(self, server_id: str, name: str, is_family_server: bool = False, family_id: Optional[str] = None) -> bool:
        """Register a new server in the database."""
        async def _register():
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
                    "turf_capture_cooldown": 24
                }
                self.client.table("server_settings").insert(settings_data).execute()
                return True
            except Exception as e:
                logger.error(f"Error registering server: {e}")
                return False

        return await self._execute_with_rate_limit('write', server_id, _register)

    def get_server_settings(self, server_id: str) -> Optional[Dict]:
        """Get server settings from the database."""
        try:
            response = self.client.table("server_settings") \
                .select("*") \
                .eq("server_id", server_id) \
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting server settings: {str(e)}")
            return None

    async def update_server_settings(self, server_id: str, settings: Dict) -> bool:
        """Update server settings."""
        async def _update_settings():
            try:
                self.client.table("server_settings").update(settings).eq("server_id", server_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error updating server settings: {e}")
                return False

        return await self._execute_with_rate_limit('write', server_id, _update_settings)

    async def add_user_to_server(self, user_id: str, server_id: str) -> bool:
        """Add a user to a server."""
        async def _add_user():
            try:
                data = {
                    "user_id": user_id,
                    "server_id": server_id
                }
                self.client.table("user_servers").insert(data).execute()
                return True
            except Exception as e:
                logger.error(f"Error adding user to server: {e}")
                return False

        return await self._execute_with_rate_limit('write', f"{user_id}:{server_id}", _add_user)

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
        async def _get_user():
            try:
                response = self.client.table("users").select("*").eq("id", user_id).execute()
                return response.data[0] if response.data else None
            except Exception as e:
                logger.error(f"Error getting user: {e}")
                return None

        return await self._execute_with_rate_limit('read', user_id, _get_user)

    async def create_user(self, user_id: str, username: str) -> bool:
        """Create a new user in the database."""
        async def _create_user():
            try:
                data = {
                    "id": user_id,
                    "username": username,
                    "psn": None,  # PSN will be set later
                    "money": 0,
                    "bank": 0,
                    "reputation": 0,
                    "inventory": {},
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                self.client.table("users").insert(data).execute()
                return True
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                return False

        return await self._execute_with_rate_limit('write', user_id, _create_user)

    async def update_user_money(self, user_id: str, amount: int, is_bank: bool = False) -> bool:
        """Update user's money or bank balance."""
        async def _update_money():
            try:
                field = "bank" if is_bank else "money"
                self.client.table("users").update({field: amount}).eq("id", user_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error updating user money: {e}")
                return False

        return await self._execute_with_rate_limit('write', user_id, _update_money)

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
        async def _record_transaction():
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
                logger.error(f"Error recording transaction: {e}")
                return False

        return await self._execute_with_rate_limit('write', f"{user_id}:{server_id}", _record_transaction)

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
        async def _reset_user():
            try:
                await self.client.table("users").update({
                    "money": 0,
                    "bank": 0,
                    "family_id": None,
                    "last_daily": None,
                    "last_heist": None
                }).eq("id", user_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error resetting user: {str(e)}")
                return False

        return await self._execute_with_rate_limit('high_impact', user_id, _reset_user)

    async def reset_family(self, family_id: str) -> bool:
        """Reset a family's progress."""
        async def _reset_family():
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
                logger.error(f"Error resetting family: {str(e)}")
                return False

        return await self._execute_with_rate_limit('high_impact', family_id, _reset_family)

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

    def get_banned_users(self, server_id: str) -> List[Dict]:
        """Get all banned users for a server."""
        try:
            response = self.client.table("banned_users") \
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

    async def create_hit_contract(self, target_id: str, target_psn: str, requester_id: str, family_id: str, reward: int, description: str, server_id: str) -> Optional[str]:
        """Create a new hit contract."""
        try:
            data = {
                "target_id": target_id,
                "target_psn": target_psn,
                "requester_id": requester_id,
                "family_id": family_id,
                "reward": reward,
                "description": description,
                "server_id": server_id,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            response = self.client.table("hit_contracts").insert(data).execute()
            return response.data[0]["id"] if response.data else None
        except Exception as e:
            print(f"Error creating hit contract: {e}")
            return None

    async def get_hit_contract(self, contract_id: str) -> Optional[Dict]:
        """Get hit contract details."""
        try:
            response = self.client.table("hit_contracts").select("*").eq("id", contract_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting hit contract: {e}")
            return None

    async def get_pending_hit_contracts(self, family_id: str) -> List[Dict]:
        """Get all pending hit contracts for a family."""
        try:
            response = self.client.table("hit_contracts").select("*").eq("family_id", family_id).eq("status", "pending").execute()
            return response.data
        except Exception as e:
            print(f"Error getting pending hit contracts: {e}")
            return []

    async def update_hit_contract_status(self, contract_id: str, status: str, approved_by: Optional[str] = None) -> bool:
        """Update hit contract status."""
        try:
            data = {
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat() if status in ["completed", "failed"] else None
            }
            if approved_by:
                data["approved_by"] = approved_by
            self.client.table("hit_contracts").update(data).eq("id", contract_id).execute()
            return True
        except Exception as e:
            print(f"Error updating hit contract status: {e}")
            return False

    async def get_user_hit_contracts(self, user_id: str) -> List[Dict]:
        """Get all hit contracts involving a user (as target or requester)."""
        try:
            response = self.client.table("hit_contracts").select("*").or_(f"target_id.eq.{user_id},requester_id.eq.{user_id}").execute()
            return response.data
        except Exception as e:
            print(f"Error getting user hit contracts: {e}")
            return []

    async def create_family_relationship(self, family_id: str, target_family_id: str, relationship_type: str, created_by: str, notes: str, server_id: str) -> Optional[str]:
        """Create a new family relationship (alliance or KOS)."""
        try:
            data = {
                "family_id": family_id,
                "target_family_id": target_family_id,
                "relationship_type": relationship_type,
                "created_by": created_by,
                "notes": notes,
                "server_id": server_id,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            response = self.client.table("family_relationships").insert(data).execute()
            return response.data[0]["id"] if response.data else None
        except Exception as e:
            print(f"Error creating family relationship: {e}")
            return None

    async def get_family_relationships(self, family_id: str, relationship_type: Optional[str] = None) -> List[Dict]:
        """Get all relationships for a family."""
        try:
            query = self.client.table("family_relationships").select("*").eq("family_id", family_id)
            if relationship_type:
                query = query.eq("relationship_type", relationship_type)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error getting family relationships: {e}")
            return []

    async def delete_family_relationship(self, relationship_id: str) -> bool:
        """Delete a family relationship."""
        try:
            self.client.table("family_relationships").delete().eq("id", relationship_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting family relationship: {e}")
            return False

    async def get_family_relationship(self, family_id: str, target_family_id: str) -> Optional[Dict]:
        """Get relationship between two families."""
        try:
            response = self.client.table("family_relationships").select("*").eq("family_id", family_id).eq("target_family_id", target_family_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting family relationship: {e}")
            return None

    async def create_family_rank(self, family_id: str, name: str, display_name: str, emoji: str, rank_order: int) -> Optional[str]:
        """Create a new family rank."""
        try:
            data = {
                "family_id": family_id,
                "name": name,
                "display_name": display_name,
                "emoji": emoji,
                "rank_order": rank_order
            }
            result = await self.client.table("family_ranks").insert(data).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            print(f"Error creating family rank: {str(e)}")
            return None

    async def get_family_ranks(self, family_id: str) -> List[Dict]:
        """Get all ranks for a family, ordered by rank_order."""
        try:
            result = await self.client.table("family_ranks")\
                .select("*")\
                .eq("family_id", family_id)\
                .order("rank_order")\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting family ranks: {str(e)}")
            return []

    async def update_family_rank(self, rank_id: str, **kwargs) -> bool:
        """Update a family rank."""
        try:
            result = await self.client.table("family_ranks")\
                .update(kwargs)\
                .eq("id", rank_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error updating family rank: {str(e)}")
            return False

    async def delete_family_rank(self, rank_id: str) -> bool:
        """Delete a family rank."""
        try:
            result = await self.client.table("family_ranks")\
                .delete()\
                .eq("id", rank_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error deleting family rank: {str(e)}")
            return False

    async def get_user_rank(self, user_id: str) -> Optional[Dict]:
        """Get a user's family rank."""
        try:
            result = await self.client.table("users")\
                .select("family_rank_id")\
                .eq("id", user_id)\
                .execute()
            
            if not result.data or not result.data[0].get("family_rank_id"):
                return None

            rank_result = await self.client.table("family_ranks")\
                .select("*")\
                .eq("id", result.data[0]["family_rank_id"])\
                .execute()
            
            return rank_result.data[0] if rank_result.data else None
        except Exception as e:
            print(f"Error getting user rank: {str(e)}")
            return None

    async def set_user_rank(self, user_id: str, rank_id: str) -> bool:
        """Set a user's family rank."""
        try:
            result = await self.client.table("users")\
                .update({"family_rank_id": rank_id})\
                .eq("id", user_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error setting user rank: {str(e)}")
            return False

    async def set_bot_channel(self, server_id: str, channel_id: str, channel_type: str, announcement_type: str = 'all', interval_minutes: int = 60) -> bool:
        """Set a bot channel for a specific type and announcement type."""
        try:
            data = {
                "server_id": server_id,
                "channel_id": channel_id,
                "channel_type": channel_type,
                "announcement_type": announcement_type,
                "interval_minutes": interval_minutes,
                "is_enabled": True,
                "last_announcement": None
            }
            result = await self.client.table("bot_channels")\
                .upsert(data, on_conflict="server_id,channel_id,announcement_type")\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error setting bot channel: {str(e)}")
            return False

    async def get_bot_channel(self, server_id: str, channel_type: str, announcement_type: str = 'all') -> Optional[Dict]:
        """Get a bot channel ID and settings for a specific type and announcement type."""
        try:
            result = await self.client.table("bot_channels")\
                .select("*")\
                .eq("server_id", server_id)\
                .eq("channel_type", channel_type)\
                .eq("announcement_type", announcement_type)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting bot channel: {str(e)}")
            return None

    async def get_all_bot_channels(self, server_id: str) -> List[Dict]:
        """Get all bot channels and their settings for a server."""
        try:
            result = await self.client.table("bot_channels")\
                .select("*")\
                .eq("server_id", server_id)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting all bot channels: {str(e)}")
            return []

    async def update_bot_channel_settings(self, server_id: str, channel_id: str, announcement_type: str, **kwargs) -> bool:
        """Update settings for a specific bot channel announcement type."""
        try:
            result = await self.client.table("bot_channels")\
                .update(kwargs)\
                .eq("server_id", server_id)\
                .eq("channel_id", channel_id)\
                .eq("announcement_type", announcement_type)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error updating bot channel settings: {str(e)}")
            return False

    async def delete_bot_channel(self, server_id: str, channel_id: str, announcement_type: str) -> bool:
        """Delete a specific bot channel announcement type."""
        try:
            result = await self.client.table("bot_channels")\
                .delete()\
                .eq("server_id", server_id)\
                .eq("channel_id", channel_id)\
                .eq("announcement_type", announcement_type)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error deleting bot channel: {str(e)}")
            return False

    async def get_announcement_channels(self, server_id: str, announcement_type: str) -> List[Dict]:
        """Get all channels that should receive a specific type of announcement."""
        try:
            result = await self.client.table("bot_channels")\
                .select("*")\
                .eq("server_id", server_id)\
                .or_(f"announcement_type.eq.{announcement_type},announcement_type.eq.all")\
                .eq("is_enabled", True)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting announcement channels: {str(e)}")
            return []

    async def create_mentorship(self, mentor_id: str, mentee_id: str, family_id: str, notes: str = None) -> Optional[str]:
        """Create a new mentorship relationship."""
        try:
            data = {
                "mentor_id": mentor_id,
                "mentee_id": mentee_id,
                "family_id": family_id,
                "status": "active",
                "notes": notes
            }
            result = await self.client.table("mentorships").insert(data).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            print(f"Error creating mentorship: {str(e)}")
            return None

    async def get_mentorship(self, mentorship_id: str) -> Optional[Dict]:
        """Get a mentorship relationship by ID."""
        try:
            result = await self.client.table("mentorships")\
                .select("*")\
                .eq("id", mentorship_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting mentorship: {str(e)}")
            return None

    async def get_user_mentorships(self, user_id: str, role: str = "mentor") -> List[Dict]:
        """Get all mentorships for a user, either as mentor or mentee."""
        try:
            field = f"{role}_id"
            result = await self.client.table("mentorships")\
                .select("*")\
                .eq(field, user_id)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting user mentorships: {str(e)}")
            return []

    async def get_family_mentorships(self, family_id: str, status: str = "active") -> List[Dict]:
        """Get all mentorships for a family."""
        try:
            result = await self.client.table("mentorships")\
                .select("*")\
                .eq("family_id", family_id)\
                .eq("status", status)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting family mentorships: {str(e)}")
            return []

    async def update_mentorship(self, mentorship_id: str, **kwargs) -> bool:
        """Update a mentorship relationship."""
        try:
            result = await self.client.table("mentorships")\
                .update(kwargs)\
                .eq("id", mentorship_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error updating mentorship: {str(e)}")
            return False

    async def end_mentorship(self, mentorship_id: str, status: str = "completed", notes: str = None) -> bool:
        """End a mentorship relationship."""
        try:
            data = {
                "status": status,
                "end_date": datetime.now(timezone.utc).isoformat(),
                "notes": notes
            }
            result = await self.client.table("mentorships")\
                .update(data)\
                .eq("id", mentorship_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error ending mentorship: {str(e)}")
            return False

    async def update_hit_stats(self, user_id: str, server_id: str, family_id: str, success: bool, payout: int = 0) -> bool:
        """Update hit statistics for a user."""
        try:
            # First try to get existing stats
            result = await self.client.table("hit_stats")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("server_id", server_id)\
                .eq("family_id", family_id)\
                .execute()

            if result.data:
                # Update existing stats
                stats = result.data[0]
                update_data = {
                    "successful_hits": stats["successful_hits"] + (1 if success else 0),
                    "failed_hits": stats["failed_hits"] + (0 if success else 1),
                    "total_hits": stats["total_hits"] + 1,
                    "total_payout": stats["total_payout"] + (payout if success else 0)
                }
                result = await self.client.table("hit_stats")\
                    .update(update_data)\
                    .eq("id", stats["id"])\
                    .execute()
            else:
                # Create new stats
                data = {
                    "user_id": user_id,
                    "server_id": server_id,
                    "family_id": family_id,
                    "successful_hits": 1 if success else 0,
                    "failed_hits": 0 if success else 1,
                    "total_hits": 1,
                    "total_payout": payout if success else 0
                }
                result = await self.client.table("hit_stats")\
                    .insert(data)\
                    .execute()

            return bool(result.data)
        except Exception as e:
            print(f"Error updating hit stats: {str(e)}")
            return False

    async def get_hit_stats(self, user_id: str, server_id: str, family_id: str) -> Optional[Dict]:
        """Get hit statistics for a user."""
        try:
            result = await self.client.table("hit_stats")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("server_id", server_id)\
                .eq("family_id", family_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting hit stats: {str(e)}")
            return None

    async def get_family_hit_leaderboard(self, server_id: str, family_id: str, limit: int = 10) -> List[Dict]:
        """Get hit statistics leaderboard for a family."""
        try:
            result = await self.client.table("hit_stats")\
                .select("*")\
                .eq("server_id", server_id)\
                .eq("family_id", family_id)\
                .order("successful_hits", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting family hit leaderboard: {str(e)}")
            return []

    async def get_server_hit_leaderboard(self, server_id: str, limit: int = 10) -> List[Dict]:
        """Get hit statistics leaderboard for a server."""
        try:
            result = await self.client.table("hit_stats")\
                .select("*")\
                .eq("server_id", server_id)\
                .order("successful_hits", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting server hit leaderboard: {str(e)}")
            return []

    async def update_hit_contract_proof(self, contract_id: str, proof_url: str) -> bool:
        """Update a hit contract with proof of completion."""
        try:
            result = await self.client.table("hit_contracts")\
                .update({"proof_url": proof_url, "status": "completed"})\
                .eq("id", contract_id)\
                .execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error updating hit contract proof: {str(e)}")
            return False

    async def verify_hit_contract(self, contract_id: str, verifier_id: str, server_id: str, status: str, reason: str = None) -> bool:
        """Verify a hit contract completion."""
        try:
            # Create verification record
            verification_data = {
                "contract_id": contract_id,
                "verifier_id": verifier_id,
                "server_id": server_id,
                "status": status,
                "reason": reason
            }
            result = await self.client.table("hit_verifications")\
                .insert(verification_data)\
                .execute()

            if not result.data:
                return False

            # Update contract status
            contract_status = "verified" if status == "approved" else "failed"
            result = await self.client.table("hit_contracts")\
                .update({"status": contract_status})\
                .eq("id", contract_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            print(f"Error verifying hit contract: {str(e)}")
            return False

    async def get_hit_verification(self, contract_id: str) -> Optional[Dict]:
        """Get verification details for a hit contract."""
        try:
            result = await self.client.table("hit_verifications")\
                .select("*")\
                .eq("contract_id", contract_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting hit verification: {str(e)}")
            return None

    async def get_upcoming_meetings(self, server_id: str, limit: int = 10) -> List[Dict]:
        """
        Get upcoming meetings for a server.
        :param server_id: The server ID
        :param limit: Maximum number of meetings to return
        :return: List of upcoming meetings
        """
        try:
            now = datetime.now(timezone.utc)
            response = self.client.table("meetings") \
                .select("*") \
                .eq("server_id", server_id) \
                .gte("meeting_time", now.isoformat()) \
                .order("meeting_time") \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting upcoming meetings: {str(e)}")
            return []

# Singleton instance
_supabase_client = None

def get_supabase_client() -> SupabaseClient:
    """
    Get or create a singleton instance of SupabaseClient.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client

# Create global instance for backward compatibility
supabase = get_supabase_client() 