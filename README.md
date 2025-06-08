# GTA V Crime Family Discord Bot

A Discord bot for GTA V crime family roleplay servers, featuring a persistent economy, turf control, family management, and other roleplay features.

## Features

- 💰 Economy system with cash and bank accounts
- 👨‍👩‍👧‍👦 Family management with ranks and permissions
- 🗺️ Turf control system with daily payouts
- 🎮 Roleplay events including heists and shop
- 📊 Reputation system
- 🏦 Transaction logging
- 🎒 Inventory system

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gta-rp-mafia-bot.git
cd gta-rp-mafia-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following variables:
```env
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Set up the Supabase database using the provided SQL schema in `schema.sql`.

5. Run the bot:
```bash
python main.py
```

## Commands

All commands use the prefix `!` by default. You can check your server's prefix using `!prefix`.

### Economy Commands

- `!balance` - Check your current balance
- `!collect` - Collect your daily money (24h cooldown)
- `!transfer @user amount` - Transfer money to another user
- `!deposit amount` - Deposit money into your bank account
- `!withdraw amount` - Withdraw money from your bank account

### Family Commands

- `!family create name` - Create a new crime family
- `!family info [name]` - View family information
- `!family accept invite_id` - Accept a family invite
- `!family leave` - Leave your current family
- `!family transfer @user` - Transfer family leadership to another member

### Turf Commands

- `!turf list` - List all available turfs
- `!turf info <name>` - View detailed information about a specific turf
- `!turf capture <name>` - Attempt to capture a turf for your family
- `!turf income` - Collect income from your family's turfs

### Moderator Commands

- `!mod settings` - View current server settings
- `!mod setprefix prefix` - Set the server's command prefix
- `!mod setdaily amount` - Set the daily reward amount
- `!mod setcooldown <type> <hours>` - Set cooldown for turf capture or heists
  - Types: turf, heist
- `!mod createturfs` - Create all GTA V turfs for the server
- `!mod ban @user [reason]` - Ban a user from using the bot in this server
- `!mod unban @user` - Unban a user from using the bot in this server
- `!mod banned` - List all banned users
- `!mod userinfo @user` - Get detailed information about a user
  - Shows Discord info, family info, regime info, hit statistics, and economy info
- `!mod serverstats` - View detailed server statistics
  - Shows member counts, family statistics, hit statistics, and top families
- `!mod resetuser @user` - Reset a user's data (removes from family, resets balance)
- `!mod resetfamily family_name` - Reset a family's data (removes all members, resets balance)
- `!mod cleanup` - Clean up database entries for users who have left the server
  - Removes data for users no longer in the server
  - Requires confirmation before proceeding
- `!mod backup` - Create a backup of important server data
  - Exports families, users, family members, hit stats, and regimes to a JSON file
- `!mod audit [days]` - View recent server activity audit log
  - Shows transaction summaries, hit contract statistics, and family changes
  - Default time period is 7 days

### Hit System Commands

- `!hit request <target> <target_psn> <reward> <description>` - Request a hit contract (Made Men and higher only)
- `!hit list` - List all active hit contracts
- `!hit complete <contract_id> <proof_url>` - Complete a hit contract with proof
  - `proof_url`: URL to image/video proof of the hit
  - Proof will be reviewed by family leadership
- `!hit verify <contract_id> <status> [reason]` - Verify a completed hit (Don/Godfather/Underboss only)
  - `status`: approved or rejected
  - `reason`: Optional reason for the decision
- `!hit proof <contract_id>` - View the proof for a completed hit
- `!hit stats [member]` - View hit statistics for yourself or another member
  - Shows total hits, successful hits, failed hits, success rate, and total payout
- `!hit leaderboard [scope]` - View hit statistics leaderboard
  - `scope`: family (default) or server
  - Shows top hit contractors ranked by successful hits

### Family Relationship Commands

- `!relationship alliance family_name notes` - Create an alliance with another family (Don only)
  - Requires being a family leader
  - Cannot ally with own family
  - Includes notes about the alliance
- `!relationship kos family_name reason` - Declare another family as KOS (Don only)
  - Requires being a family leader
  - Cannot declare own family as KOS
  - Includes reason for KOS declaration
- `!relationship remove family_name` - Remove a relationship with another family (Don only)
- `!relationship list [family_name]` - List all relationships for a family
  - Shows both alliances and KOS declarations
  - Can view any family's relationships
  - Includes timestamps and notes/reasons

### Family Rank Commands

- `!rank create name display_name emoji order` - Create a new family rank (Don only)
  - Requires being a family leader
  - Example: `!rank create godfather "God Father" 👑 1`
- `!rank list [family_name]` - List all ranks for a family
  - Shows ranks in order from highest to lowest
  - Can view any family's ranks
- `!rank set @member rank_name` - Set a member's family rank (Don only)
  - Requires being a family leader
  - Member must be in your family
- `!rank delete rank_name` - Delete a family rank (Don only)
  - Requires being a family leader
  - Cannot delete ranks that are in use
- `!rank update rank_name field value` - Update a rank's properties (Don only)
  - Requires being a family leader
  - Fields: display_name, emoji, rank_order

### Bot Channel Commands

- `!channel set <channel> <type> [announcement_type] [interval_minutes]` - Set a channel for bot announcements
  - `type`: The type of channel (announcements, logs, etc.)
  - `announcement_type`: Type of announcements to send (default: all)
    - `all`: All announcements
    - `family`: Family-related announcements
    - `turf`: Turf-related announcements
    - `economy`: Economy-related announcements
    - `hits`: Hit-related announcements
    - `mentorship`: Mentorship-related announcements
  - `interval_minutes`: How often to send announcements (default: 60)
- `!channel list` - List all configured bot channels and their settings
- `!channel update <channel> <announcement_type> [interval_minutes] [enabled]` - Update settings for a specific channel and announcement type
- `!channel remove <channel> <announcement_type>` - Remove a specific announcement type from a channel
- `!channel types` - List all available announcement types

### Mentorship Commands

- `!mentor assign @mentor @mentee [notes]` - Assign a mentor to a mentee (Don only)
  - Mentor must be a Made Man or Capo
  - Mentee must be a Recruit
  - Optional notes for the mentorship
- `!mentor list [family_name]` - List all active mentorships for a family
- `!mentor end @mentee [reason]` - End a mentorship relationship (Don only)
- `!mentor my` - View your current mentorship relationships

### Recruitment Commands

- `!recruitment addstep step_number title [requires_image] description` - Add a new step to the recruitment process (Don only)
- `!recruitment remove step_number` - Remove a recruitment step (Don only)

### Help Commands

- `!help` - Show the main help menu
- `!help <command>` - Show detailed help for a specific command
- `!prefix` - Show the bot's command prefix

### Regime Commands
- `!regime create <name> <leader> [description]` - Create a new regime (Don only)
- `!regime list` - List all regimes in your family
- `!regime assign <member> <regime_name>` - Assign a member to a regime (Regime Leader only)
- `!regime distribution <regime_name> add` - Add a regime to automatic distribution (Don only)
- `!regime distribution <regime_name> remove` - Remove a regime from automatic distribution (Don only)
- `!regime distribution <regime_name> setcount <number>` - Set target member count for a regime (Don only)
- `!regime listdistribution` - View current regime distribution settings

The regime distribution system automatically assigns new recruits to regimes based on target member counts:
- Each regime can have a target member count
- New recruits are assigned to the regime with the lowest ratio of current members to target members
- This ensures an even distribution of members across all active regimes
- Family leaders can adjust target counts at any time to change the distribution

### Assignment Commands
- `!assignment create <regime_name> <member> <title> <reward> <deadline_hours> <description>` - Create a new assignment (Regime Leader only)
- `!assignment list [status]` - List assignments for your regime (default: pending)
- `!assignment complete <assignment_id>` - Mark an assignment as completed

Assignment Statuses:
- pending: New assignments waiting to be started
- in_progress: Assignments currently being worked on
- completed: Successfully completed assignments
- failed: Failed assignments
- expired: Assignments that passed their deadline

## Heist Types

1. Bank Heist
   - Requires 2-4 players
   - 40% success chance
   - Reward: $50,000 - $100,000
   - 24h jail time if failed
   - +10 reputation if successful

2. Jewelry Store
   - Requires 1-3 players
   - 60% success chance
   - Reward: $20,000 - $50,000
   - 12h jail time if failed
   - +5 reputation if successful

3. Drug Run
   - Requires 1-2 players
   - 70% success chance
   - Reward: $10,000 - $30,000
   - 8h jail time if failed
   - +3 reputation if successful

## Turf System

The turf system is based on GTA V's locations and territories. Each turf provides hourly income to the controlling family. Turfs are organized into regions:

### Los Santos City Center
- Vinewood Hills ($5,000/hour)
- Downtown Los Santos ($4,500/hour)
- Vinewood Boulevard ($4,000/hour)
- Rockford Hills ($4,200/hour)

### Beach and Port Areas
- Vespucci Beach ($3,500/hour)
- Del Perro Beach ($3,200/hour)
- Terminal ($3,800/hour)

### South Los Santos
- Strawberry ($3,000/hour)
- Grove Street ($2,800/hour)
- Davis ($2,500/hour)

### East Los Santos
- La Mesa ($3,200/hour)
- El Burro Heights ($2,200/hour)

### North Los Santos
- Mirror Park ($2,800/hour)
- Burton ($2,600/hour)

### Blaine County
- Sandy Shores ($2,000/hour)
- Paleto Bay ($2,200/hour)
- Grapeseed ($1,800/hour)

### Special Areas
- Fort Zancudo ($4,800/hour)
- Los Santos International Airport ($4,600/hour)
- Maze Bank Tower ($5,200/hour)

### Arena and Entertainment
- Arena Complex ($5,500/hour)
- Diamond Casino ($6,000/hour)
- Maze Bank Arena ($4,800/hour)
- Galileo Observatory ($2,800/hour)

### Industrial and Manufacturing
- Humane Labs ($4,500/hour)
- Bolingbroke Penitentiary ($4,200/hour)
- Palmer-Taylor Power Station ($3,800/hour)

### Additional Areas
- Mount Chiliad ($2,200/hour)
- Alamo Sea ($2,000/hour)
- Great Chaparral ($1,800/hour)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 