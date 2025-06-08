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