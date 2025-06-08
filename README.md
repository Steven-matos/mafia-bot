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

### Economy Commands

- `!balance` - Check your current balance
- `!collect` - Collect your daily money (24h cooldown)
- `!transfer @user amount` - Transfer money to another user
- `!deposit amount` - Deposit money into your bank account
- `!withdraw amount` - Withdraw money from your bank account

### Family Commands

- `!createfamily name` - Create a new crime family
- `!familyinfo [name]` - View family information
- `!invite @user` - Invite a user to your family
- `!joinfamily name` - Join a family you've been invited to
- `!leavefamily` - Leave your current family
- `!promote @user rank` - Promote a family member
- `!demote @user rank` - Demote a family member
- `!kick @user` - Kick a member from your family

### Turf Commands

- `!turf list` - List all available turfs
- `!turf info <name>` - View detailed information about a specific turf
- `!turf capture <name>` - Attempt to capture a turf for your family
- `!turf income` - Collect income from your family's turfs

### Moderator Commands

- `!mod settings` - View current server settings
- `!mod setcooldown <type> <hours>` - Set cooldown for turf capture or heists
  - Types: turf, heist
- `!mod createturfs` - Create all GTA V turfs for the server
  - Creates turfs in regions:
    - Los Santos City Center
    - Beach and Port Areas
    - South Los Santos
    - East Los Santos
    - North Los Santos
    - Blaine County
    - Special Areas
    - Arena and Entertainment
    - Industrial and Manufacturing
    - Additional Areas

### Roleplay Commands

- `!shop` - View available items in the shop
- `!buy item_id [quantity]` - Buy items from the shop
- `!inventory` - View your inventory
- `!heist type` - Start a heist with your family
  - Available types: bank, jewelry, drug_run
- `!status` - Check your current status

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