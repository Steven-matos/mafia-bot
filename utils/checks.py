from discord.ext import commands
from db.supabase_client import supabase

def is_regime_leader():
    async def predicate(ctx):
        # Check if user is in a family
        member_data = supabase.table('family_members').select('*').eq('user_id', str(ctx.author.id)).execute()
        if not member_data.data:
            raise commands.CheckFailure("You must be in a family to use this command.")
        
        # Get user's family
        family = member_data.data[0]
        ctx.family_id = family['family_id']
        
        # Check if user is a regime leader
        regime = supabase.table('regimes').select('*').eq('leader_id', str(ctx.author.id)).eq('family_id', ctx.family_id).execute()
        if not regime.data:
            raise commands.CheckFailure("You must be a regime leader to use this command.")
        
        return True
    return commands.check(predicate)

def is_family_member():
    async def predicate(ctx):
        # Check if user is in a family
        member_data = supabase.table('family_members').select('*').eq('user_id', str(ctx.author.id)).execute()
        if not member_data.data:
            raise commands.CheckFailure("You must be in a family to use this command.")
        
        # Get user's family
        family = member_data.data[0]
        ctx.family_id = family['family_id']
        return True
    return commands.check(predicate)

def is_family_don():
    async def predicate(ctx):
        # Check if user is in a family
        member_data = supabase.table('family_members').select('*').eq('user_id', str(ctx.author.id)).execute()
        if not member_data.data:
            raise commands.CheckFailure("You must be in a family to use this command.")
        
        # Get user's family
        family = member_data.data[0]
        ctx.family_id = family['family_id']
        
        # Check if user is the don (leader) of their family
        family_data = supabase.table('families').select('*').eq('id', ctx.family_id).execute()
        if not family_data.data or family_data.data[0]['leader_id'] != str(ctx.author.id):
            raise commands.CheckFailure("You must be the don of your family to use this command.")
        
        return True
    return commands.check(predicate)

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

def is_admin_or_mod():
    """Check if user is an admin or moderator."""
    async def predicate(ctx):
        user_servers = await supabase.get_user_servers(str(ctx.author.id))
        server = next((s for s in user_servers if s["server_id"] == str(ctx.guild.id)), None)
        return server and server["role"] in ["admin", "moderator"]
    return commands.check(predicate) 