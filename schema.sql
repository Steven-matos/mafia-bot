-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create mod_logs table for audit logging
CREATE TABLE mod_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id TEXT REFERENCES servers(id),
    moderator_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create security_settings table
CREATE TABLE security_settings (
    server_id TEXT PRIMARY KEY REFERENCES servers(id),
    max_transfer_amount INTEGER DEFAULT 1000000,
    max_daily_amount INTEGER DEFAULT 10000,
    min_cooldown INTEGER DEFAULT 1,
    max_cooldown INTEGER DEFAULT 168,
    max_ban_reason_length INTEGER DEFAULT 1000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Servers table
CREATE TABLE servers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_family_server BOOLEAN DEFAULT FALSE,
    family_id UUID REFERENCES families(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Bot channels table
CREATE TABLE bot_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id TEXT REFERENCES servers(id),
    channel_id TEXT NOT NULL,
    channel_type TEXT NOT NULL CHECK (channel_type IN ('announcements', 'hits', 'ranks', 'turfs', 'family')),
    announcement_type TEXT NOT NULL CHECK (announcement_type IN ('all', 'hits', 'ranks', 'turfs', 'family', 'meetings', 'events', 'wars', 'income')),
    interval_minutes INTEGER DEFAULT 60,
    is_enabled BOOLEAN DEFAULT true,
    last_announcement TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, channel_id, announcement_type)
);

-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    family_id UUID REFERENCES families(id),
    family_rank_id UUID REFERENCES family_ranks(id),
    money INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    last_daily TIMESTAMP WITH TIME ZONE,
    last_work TIMESTAMP WITH TIME ZONE,
    last_rob TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- User servers table (for tracking which servers a user is in)
CREATE TABLE user_servers (
    user_id TEXT REFERENCES users(id),
    server_id TEXT REFERENCES servers(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (user_id, server_id)
);

-- Families table
CREATE TABLE families (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    leader_id TEXT REFERENCES users(id),
    family_money INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    description TEXT,
    main_server_id TEXT REFERENCES servers(id)
);

-- Turfs table
CREATE TABLE turfs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    income INTEGER NOT NULL,
    family_id UUID REFERENCES families(id),
    captured_at TIMESTAMP WITH TIME ZONE,
    last_income_collected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Shop items table
CREATE TABLE shop_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    is_consumable BOOLEAN DEFAULT FALSE
);

-- Transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES users(id),
    type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    target_user_id TEXT REFERENCES users(id),
    item_id TEXT REFERENCES shop_items(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(),
    notes TEXT,
    server_id TEXT REFERENCES servers(id)
);

-- Family invites table
CREATE TABLE family_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id),
    user_id TEXT REFERENCES users(id),
    invited_by TEXT REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    server_id TEXT REFERENCES servers(id),
    UNIQUE(family_id, user_id)
);

-- Server settings table
CREATE TABLE server_settings (
    server_id TEXT PRIMARY KEY REFERENCES servers(id),
    prefix TEXT DEFAULT '!',
    daily_amount INTEGER DEFAULT 1000,
    turf_capture_cooldown INTEGER DEFAULT 24,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create banned_users table
CREATE TABLE banned_users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    reason TEXT,
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, server_id)
);

-- Create recruitment_steps table
CREATE TABLE recruitment_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    required_role_id TEXT,
    verification_channel_id TEXT,
    verification_message TEXT,
    requires_image BOOLEAN DEFAULT FALSE,
    image_requirements TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create recruitment_progress table
CREATE TABLE recruitment_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    current_step INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, family_id)
);

-- Create recruitment_verifications table
CREATE TABLE recruitment_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    progress_id UUID REFERENCES recruitment_progress(id) ON DELETE CASCADE,
    step_id UUID REFERENCES recruitment_steps(id) ON DELETE CASCADE,
    verified_by TEXT NOT NULL,
    notes TEXT,
    verified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create recruitment_image_submissions table
CREATE TABLE recruitment_image_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    progress_id UUID REFERENCES recruitment_progress(id) ON DELETE CASCADE,
    step_id UUID REFERENCES recruitment_steps(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by TEXT,
    review_status TEXT DEFAULT 'pending',
    review_notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE
);

-- Insert some default shop items
INSERT INTO shop_items (id, name, description, price, item_type, is_consumable) VALUES
    ('lockpick', 'Lockpick', 'Used to break into vehicles and buildings', 500, 'tool', TRUE),
    ('fake_id', 'Fake ID', 'Helps avoid identification', 1000, 'tool', FALSE),
    ('pistol', 'Pistol', 'Basic firearm for protection', 2000, 'weapon', FALSE),
    ('shotgun', 'Shotgun', 'Powerful close-range weapon', 5000, 'weapon', FALSE),
    ('armor', 'Body Armor', 'Provides protection from damage', 3000, 'equipment', FALSE),
    ('phone', 'Burner Phone', 'Untraceable communication device', 800, 'tool', FALSE),
    ('c4', 'C4 Explosive', 'Used for heists and sabotage', 10000, 'tool', TRUE),
    ('medkit', 'Medkit', 'Restores health after injuries', 1500, 'consumable', TRUE);

-- Create meetings table
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_by TEXT NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    meeting_time TIMESTAMP WITH TIME ZONE NOT NULL,
    channel_id TEXT,
    message_id TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create meeting_rsvps table
CREATE TABLE meeting_rsvps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    responded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(meeting_id, user_id)
);

-- Hit contracts table
CREATE TABLE hit_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id TEXT REFERENCES users(id),
    target_psn TEXT NOT NULL,
    requester_id TEXT REFERENCES users(id),
    family_id UUID REFERENCES families(id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'completed', 'verified', 'failed')),
    reward INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE,
    approved_by TEXT REFERENCES users(id),
    server_id TEXT REFERENCES servers(id),
    proof_url TEXT,
    FOREIGN KEY (target_id, server_id) REFERENCES user_servers(user_id, server_id) ON DELETE CASCADE
);

-- Family relationships table
CREATE TABLE family_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id),
    target_family_id UUID REFERENCES families(id),
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('alliance', 'kos')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by TEXT REFERENCES users(id),
    notes TEXT,
    server_id TEXT REFERENCES servers(id),
    UNIQUE(family_id, target_family_id)
);

-- Create family_ranks table
CREATE TABLE family_ranks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id),
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    emoji TEXT NOT NULL,
    rank_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(family_id, name)
);

-- Create mentorship table
CREATE TABLE IF NOT EXISTS mentorships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mentor_id TEXT REFERENCES users(id),
    mentee_id TEXT REFERENCES users(id),
    family_id UUID REFERENCES families(id),
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'terminated')),
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(mentee_id, family_id)
);

-- Create hit statistics table
CREATE TABLE IF NOT EXISTS hit_stats (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    family_id TEXT NOT NULL,
    successful_hits INTEGER DEFAULT 0,
    failed_hits INTEGER DEFAULT 0,
    total_hits INTEGER DEFAULT 0,
    total_payout BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, server_id, family_id),
    FOREIGN KEY (user_id, server_id) REFERENCES user_servers(user_id, server_id) ON DELETE CASCADE,
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
);

-- Add trigger to update updated_at
CREATE TRIGGER update_hit_stats_updated_at
    BEFORE UPDATE ON hit_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create hit verifications table
CREATE TABLE IF NOT EXISTS hit_verifications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    contract_id UUID NOT NULL,
    verifier_id TEXT NOT NULL,
    server_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('approved', 'rejected')),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contract_id) REFERENCES hit_contracts(id) ON DELETE CASCADE,
    FOREIGN KEY (verifier_id, server_id) REFERENCES user_servers(user_id, server_id) ON DELETE CASCADE
);

-- Add trigger to update updated_at
CREATE TRIGGER update_hit_verifications_updated_at
    BEFORE UPDATE ON hit_verifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for better performance
CREATE INDEX idx_users_family_id ON users(family_id);
CREATE INDEX idx_users_family_rank_id ON users(family_rank_id);
CREATE INDEX idx_turfs_family_id ON turfs(family_id);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX idx_family_invites_user_id ON family_invites(user_id);
CREATE INDEX idx_user_servers_user_id ON user_servers(user_id);
CREATE INDEX idx_user_servers_server_id ON user_servers(server_id);
CREATE INDEX idx_banned_users_user_id ON banned_users(user_id);
CREATE INDEX idx_banned_users_server_id ON banned_users(server_id);
CREATE INDEX idx_recruitment_steps_family ON recruitment_steps(family_id);
CREATE INDEX idx_recruitment_progress_user ON recruitment_progress(user_id);
CREATE INDEX idx_recruitment_progress_family ON recruitment_progress(family_id);
CREATE INDEX idx_recruitment_verifications_progress ON recruitment_verifications(progress_id);
CREATE INDEX idx_recruitment_verifications_step ON recruitment_verifications(step_id);
CREATE INDEX idx_recruitment_image_submissions_progress ON recruitment_image_submissions(progress_id);
CREATE INDEX idx_recruitment_image_submissions_step ON recruitment_image_submissions(step_id);
CREATE INDEX idx_meetings_server ON meetings(server_id);
CREATE INDEX idx_meetings_scheduled_by ON meetings(scheduled_by);
CREATE INDEX idx_meetings_meeting_time ON meetings(meeting_time);
CREATE INDEX idx_meeting_rsvps_meeting ON meeting_rsvps(meeting_id);
CREATE INDEX idx_meeting_rsvps_user ON meeting_rsvps(user_id);
CREATE INDEX idx_meeting_rsvps_status ON meeting_rsvps(status);
CREATE INDEX idx_hit_contracts_target ON hit_contracts(target_id);
CREATE INDEX idx_hit_contracts_requester ON hit_contracts(requester_id);
CREATE INDEX idx_hit_contracts_family ON hit_contracts(family_id);
CREATE INDEX idx_hit_contracts_status ON hit_contracts(status);
CREATE INDEX idx_hit_contracts_server ON hit_contracts(server_id);
CREATE INDEX idx_family_relationships_family ON family_relationships(family_id);
CREATE INDEX idx_family_relationships_target ON family_relationships(target_family_id);
CREATE INDEX idx_family_relationships_type ON family_relationships(relationship_type);
CREATE INDEX idx_family_relationships_server ON family_relationships(server_id);
CREATE INDEX idx_family_ranks_family_id ON family_ranks(family_id);
CREATE INDEX idx_family_ranks_rank_order ON family_ranks(rank_order);
CREATE INDEX idx_bot_channels_server_id ON bot_channels(server_id);
CREATE INDEX idx_bot_channels_channel_type ON bot_channels(channel_type);
CREATE INDEX idx_mentorships_mentor_id ON mentorships(mentor_id);
CREATE INDEX idx_mentorships_mentee_id ON mentorships(mentee_id);
CREATE INDEX idx_mentorships_family_id ON mentorships(family_id);
CREATE INDEX idx_mentorships_status ON mentorships(status);

-- Row Level Security (RLS) Policies

-- Servers table policies
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Servers are viewable by everyone"
    ON servers FOR SELECT
    USING (true);

-- Users table policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users are viewable by everyone"
    ON users FOR SELECT
    USING (true);

CREATE POLICY "Users can update their own data"
    ON users FOR UPDATE
    USING (auth.uid() = id);

-- User servers table policies
ALTER TABLE user_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their server memberships"
    ON user_servers FOR SELECT
    USING (user_id = current_user);

-- Families table policies
ALTER TABLE families ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Families are viewable by everyone"
    ON families FOR SELECT
    USING (true);

CREATE POLICY "Family leaders can update their family"
    ON families FOR UPDATE
    USING (auth.uid() = leader_id);

-- Turfs table policies
ALTER TABLE turfs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Turfs are viewable by everyone"
    ON turfs FOR SELECT
    USING (true);

CREATE POLICY "Family leaders can update their turfs"
    ON turfs FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM families
        WHERE families.id = turfs.family_id
        AND families.leader_id = auth.uid()
    ));

-- Shop items table policies
ALTER TABLE shop_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view shop items"
    ON shop_items FOR SELECT
    USING (true);

-- Transactions table policies
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own transactions"
    ON transactions FOR SELECT
    USING (user_id = current_user OR target_user_id = current_user);

-- Family invites table policies
ALTER TABLE family_invites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own invites"
    ON family_invites FOR SELECT
    USING (user_id = current_user);

CREATE POLICY "Family leaders can create invites"
    ON family_invites FOR INSERT
    WITH CHECK (
        invited_by IN (
            SELECT leader_id FROM families WHERE id = family_id
        )
    );

CREATE POLICY "Users can delete their own invites"
    ON family_invites FOR DELETE
    USING (user_id = current_user);

-- Server settings table policies
ALTER TABLE server_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view server settings"
    ON server_settings FOR SELECT
    USING (true);

-- Banned_users table policies
ALTER TABLE banned_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own bans"
    ON banned_users FOR SELECT
    USING (auth.uid()::text = user_id);

CREATE POLICY "Server admins can view their server's bans"
    ON banned_users FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM servers
            WHERE servers.id = banned_users.server_id
            AND servers.admin_id = auth.uid()::text
        )
    );

CREATE POLICY "Server admins can manage their server's bans"
    ON banned_users FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM servers
            WHERE servers.id = banned_users.server_id
            AND servers.admin_id = auth.uid()::text
        )
    );

-- Recruitment steps policies
ALTER TABLE recruitment_steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their family's recruitment steps"
    ON recruitment_steps FOR SELECT
    USING (
        family_id IN (
            SELECT family_id FROM user_servers
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family leaders can manage their family's recruitment steps"
    ON recruitment_steps FOR ALL
    USING (
        family_id IN (
            SELECT f.id FROM families f
            WHERE f.leader_id = auth.uid()
        )
    );

-- Recruitment progress policies
ALTER TABLE recruitment_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own recruitment progress"
    ON recruitment_progress FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Family leaders can view their family's recruitment progress"
    ON recruitment_progress FOR SELECT
    USING (
        family_id IN (
            SELECT f.id FROM families f
            WHERE f.leader_id = auth.uid()
        )
    );

CREATE POLICY "Users can create their own recruitment progress"
    ON recruitment_progress FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Family leaders can update recruitment progress"
    ON recruitment_progress FOR UPDATE
    USING (
        family_id IN (
            SELECT f.id FROM families f
            WHERE f.leader_id = auth.uid()
        )
    );

-- Recruitment verifications policies
ALTER TABLE recruitment_verifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own verifications"
    ON recruitment_verifications FOR SELECT
    USING (
        progress_id IN (
            SELECT id FROM recruitment_progress
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family leaders can manage verifications"
    ON recruitment_verifications FOR ALL
    USING (
        step_id IN (
            SELECT rs.id FROM recruitment_steps rs
            JOIN families f ON f.id = rs.family_id
            WHERE f.leader_id = auth.uid()
        )
    );

-- Recruitment image submissions policies
ALTER TABLE recruitment_image_submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own image submissions"
    ON recruitment_image_submissions FOR SELECT
    USING (
        progress_id IN (
            SELECT id FROM recruitment_progress
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can submit images for their recruitment"
    ON recruitment_image_submissions FOR INSERT
    WITH CHECK (
        progress_id IN (
            SELECT id FROM recruitment_progress
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family leaders can review image submissions"
    ON recruitment_image_submissions FOR UPDATE
    USING (
        step_id IN (
            SELECT rs.id FROM recruitment_steps rs
            JOIN families f ON f.id = rs.family_id
            WHERE f.leader_id = auth.uid()
        )
    );

-- Meetings table policies
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view meetings in their servers"
    ON meetings FOR SELECT
    USING (
        server_id IN (
            SELECT server_id FROM user_servers
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can manage meetings"
    ON meetings FOR ALL
    USING (
        scheduled_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM user_servers
            WHERE user_id = auth.uid()
            AND server_id = meetings.server_id
            AND role IN ('admin', 'moderator')
        )
    );

-- Meeting_rsvps table policies
ALTER TABLE meeting_rsvps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own RSVPs"
    ON meeting_rsvps FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can manage their own RSVPs"
    ON meeting_rsvps FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own RSVPs"
    ON meeting_rsvps FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY "Admins can view all RSVPs"
    ON meeting_rsvps FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM meetings m
            JOIN user_servers us ON us.server_id = m.server_id
            WHERE m.id = meeting_rsvps.meeting_id
            AND us.user_id = auth.uid()
            AND us.role IN ('admin', 'moderator')
        )
    );

-- Family relationships policies
ALTER TABLE family_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Family relationships are viewable by everyone"
    ON family_relationships FOR SELECT
    USING (true);

CREATE POLICY "Family leaders can manage relationships"
    ON family_relationships FOR ALL
    USING (EXISTS (
        SELECT 1 FROM families
        WHERE families.id = family_relationships.family_id
        AND families.leader_id = auth.uid()
    ));

CREATE POLICY "Users can create their own family relationships"
    ON family_relationships FOR INSERT
    WITH CHECK (
        family_id IN (
            SELECT family_id FROM user_servers
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Family leaders can delete their family relationships"
    ON family_relationships FOR DELETE
    USING (
        family_id IN (
            SELECT f.id FROM families f
            WHERE f.leader_id = auth.uid()
        )
    );

-- Family ranks policies
ALTER TABLE family_ranks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Family ranks are viewable by everyone"
    ON family_ranks FOR SELECT
    USING (true);

CREATE POLICY "Family leaders can manage ranks"
    ON family_ranks FOR ALL
    USING (EXISTS (
        SELECT 1 FROM families
        WHERE families.id = family_ranks.family_id
        AND families.leader_id = auth.uid()
    ));

-- Bot channels policies
ALTER TABLE bot_channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Bot channels are viewable by everyone"
    ON bot_channels FOR SELECT
    USING (true);

CREATE POLICY "Server moderators can manage bot channels"
    ON bot_channels FOR ALL
    USING (EXISTS (
        SELECT 1 FROM user_servers
        WHERE user_servers.server_id = bot_channels.server_id
        AND user_servers.user_id = auth.uid()
        AND user_servers.is_moderator = true
    ));

-- Mentorship policies
ALTER TABLE mentorships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Mentorships are viewable by family members"
    ON mentorships FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM users
        WHERE users.id = auth.uid()
        AND users.family_id = mentorships.family_id
    ));

CREATE POLICY "Family leaders can manage mentorships"
    ON mentorships FOR ALL
    USING (EXISTS (
        SELECT 1 FROM families
        WHERE families.id = mentorships.family_id
        AND families.leader_id = auth.uid()
    ));

CREATE POLICY "Mentors can update their own mentorships"
    ON mentorships FOR UPDATE
    USING (mentor_id = auth.uid());

-- Update users table
ALTER TABLE users 
DROP COLUMN IF EXISTS last_heist;

-- Update server_settings table
ALTER TABLE server_settings 
DROP COLUMN IF EXISTS heist_cooldown;

-- Update items table to remove heist-specific items
DELETE FROM items WHERE name = 'c4';

-- Add GTA V roleplay specific items
INSERT INTO items (name, description, price, type, is_tradeable) VALUES
('pistol', 'Standard issue pistol', 5000, 'weapon', TRUE),
('smg', 'Submachine gun', 10000, 'weapon', TRUE),
('shotgun', 'Pump-action shotgun', 15000, 'weapon', TRUE),
('rifle', 'Assault rifle', 20000, 'weapon', TRUE),
('armor', 'Basic body armor', 5000, 'armor', TRUE),
('heavy_armor', 'Heavy body armor', 10000, 'armor', TRUE),
('phone', 'Mobile phone for communications', 1000, 'tool', TRUE),
('lockpick', 'Tool for breaking into vehicles', 2000, 'tool', TRUE),
('first_aid', 'Basic medical supplies', 1000, 'medical', TRUE),
('bandage', 'For treating wounds', 500, 'medical', TRUE);

-- Regimes table
CREATE TABLE IF NOT EXISTS regimes (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    leader_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, name)
);

-- Assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    regime_id INTEGER REFERENCES regimes(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    reward_amount INTEGER NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by BIGINT NOT NULL,
    assigned_to BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'expired'))
);

-- Add regime_id to family_members table
ALTER TABLE family_members ADD COLUMN IF NOT EXISTS regime_id INTEGER REFERENCES regimes(id) ON DELETE SET NULL;

-- Remove RP-specific tables if they exist
DROP TABLE IF EXISTS rp_events;
DROP TABLE IF EXISTS rp_contracts;
DROP TABLE IF EXISTS rp_proof;

-- Remove RP-specific columns if they exist
ALTER TABLE users DROP COLUMN IF EXISTS rp_level;
ALTER TABLE users DROP COLUMN IF EXISTS rp_xp;
ALTER TABLE users DROP COLUMN IF EXISTS last_rp_action;

-- Regime distribution settings table
CREATE TABLE IF NOT EXISTS regime_distribution (
    id SERIAL PRIMARY KEY,
    family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
    regime_id INTEGER REFERENCES regimes(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    target_member_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, regime_id)
);

-- Add security constraints to existing tables
ALTER TABLE users
ADD CONSTRAINT positive_money CHECK (money >= 0),
ADD CONSTRAINT positive_bank CHECK (bank >= 0);

ALTER TABLE families
ADD CONSTRAINT positive_family_money CHECK (family_money >= 0),
ADD CONSTRAINT positive_reputation CHECK (reputation >= 0);

ALTER TABLE transactions
ADD CONSTRAINT positive_amount CHECK (amount > 0);

ALTER TABLE hit_contracts
ADD CONSTRAINT positive_reward CHECK (reward > 0);

-- Add indexes for security-related queries
CREATE INDEX idx_mod_logs_server ON mod_logs(server_id);
CREATE INDEX idx_mod_logs_moderator ON mod_logs(moderator_id);
CREATE INDEX idx_mod_logs_timestamp ON mod_logs(timestamp);
CREATE INDEX idx_security_settings_server ON security_settings(server_id);

-- Add trigger for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to tables that need timestamp updates
CREATE TRIGGER update_servers_updated_at
    BEFORE UPDATE ON servers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_security_settings_updated_at
    BEFORE UPDATE ON security_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 