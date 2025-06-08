-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Servers table
CREATE TABLE servers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_family_server BOOLEAN DEFAULT FALSE,
    family_id UUID REFERENCES families(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    money INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    last_daily_collect TIMESTAMP WITH TIME ZONE,
    family_id UUID REFERENCES families(id),
    family_rank TEXT,
    reputation INTEGER DEFAULT 0,
    inventory JSONB DEFAULT '{}',
    jail_release_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
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
    name TEXT UNIQUE NOT NULL,
    leader_id TEXT REFERENCES users(id),
    family_money INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    description TEXT,
    main_server_id TEXT REFERENCES servers(id)
);

-- Turfs table
CREATE TABLE turfs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    owner_family_id UUID REFERENCES families(id),
    last_captured_at TIMESTAMP WITH TIME ZONE,
    money_payout_per_day INTEGER DEFAULT 100,
    description TEXT,
    gta_coordinates TEXT,
    server_id TEXT REFERENCES servers(id)
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
    heist_cooldown INTEGER DEFAULT 12,
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

-- Create indexes for better performance
CREATE INDEX idx_users_family_id ON users(family_id);
CREATE INDEX idx_turfs_owner_family_id ON turfs(owner_family_id);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX idx_family_invites_user_id ON family_invites(user_id);
CREATE INDEX idx_user_servers_user_id ON user_servers(user_id);
CREATE INDEX idx_user_servers_server_id ON user_servers(server_id);
CREATE INDEX idx_turfs_server_id ON turfs(server_id);
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

-- Row Level Security (RLS) Policies

-- Servers table policies
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view servers"
    ON servers FOR SELECT
    USING (true);

-- Users table policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own data"
    ON users FOR SELECT
    USING (id = current_user);

CREATE POLICY "Users can update their own data"
    ON users FOR UPDATE
    USING (id = current_user);

-- User servers table policies
ALTER TABLE user_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their server memberships"
    ON user_servers FOR SELECT
    USING (user_id = current_user);

-- Families table policies
ALTER TABLE families ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view families"
    ON families FOR SELECT
    USING (true);

CREATE POLICY "Family leaders can update their family"
    ON families FOR UPDATE
    USING (leader_id = current_user);

-- Turfs table policies
ALTER TABLE turfs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view turfs"
    ON turfs FOR SELECT
    USING (true);

CREATE POLICY "Family members can update owned turfs"
    ON turfs FOR UPDATE
    USING (
        owner_family_id IN (
            SELECT family_id FROM users WHERE id = current_user
        )
    );

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