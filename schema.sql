-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add PSN field to users table
ALTER TABLE users ADD COLUMN psn TEXT;
ALTER TABLE users ADD CONSTRAINT users_psn_unique UNIQUE (psn);
CREATE INDEX idx_users_psn ON users(psn);

-- Modify turfs table for variable income
ALTER TABLE turfs ADD COLUMN base_income INTEGER NOT NULL DEFAULT 1000;
ALTER TABLE turfs ADD COLUMN income_multiplier DECIMAL(5,2) NOT NULL DEFAULT 1.00;
ALTER TABLE turfs DROP COLUMN income;
ALTER TABLE turfs ADD CONSTRAINT positive_base_income CHECK (base_income >= 0);
ALTER TABLE turfs ADD CONSTRAINT positive_income_multiplier CHECK (income_multiplier > 0);

-- Servers table (must be first since it's referenced by many other tables)
CREATE TABLE servers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    is_family_server BOOLEAN DEFAULT FALSE,
    family_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Users table (must be early since it's referenced by many other tables)
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    psn TEXT UNIQUE,
    family_id UUID,
    family_rank_id UUID,
    money INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    last_daily TIMESTAMP WITH TIME ZONE,
    last_work TIMESTAMP WITH TIME ZONE,
    last_rob TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
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

-- Now we can add the foreign key constraints to servers and users
ALTER TABLE servers
ADD CONSTRAINT fk_servers_family
FOREIGN KEY (family_id) REFERENCES families(id);

ALTER TABLE users
ADD CONSTRAINT fk_users_family
FOREIGN KEY (family_id) REFERENCES families(id);

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

-- Now we can add the family_rank_id foreign key to users
ALTER TABLE users
ADD CONSTRAINT fk_users_family_rank
FOREIGN KEY (family_rank_id) REFERENCES family_ranks(id);

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

-- User servers table (for tracking which servers a user is in)
CREATE TABLE user_servers (
    user_id TEXT REFERENCES users(id),
    server_id TEXT REFERENCES servers(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    is_moderator BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, server_id)
);

-- Family members table
CREATE TABLE family_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    rank_id UUID REFERENCES family_ranks(id),
    regime_id UUID,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(family_id, user_id)
);

-- Turfs table
CREATE TABLE turfs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    base_income INTEGER NOT NULL DEFAULT 1000,
    income_multiplier DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    family_id UUID REFERENCES families(id),
    captured_at TIMESTAMP WITH TIME ZONE,
    last_income_collected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT REFERENCES users(id),
    type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    target_user_id TEXT REFERENCES users(id),
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

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_by TEXT NOT NULL,
    meeting_time TIMESTAMP WITH TIME ZONE NOT NULL,
    channel_id TEXT NOT NULL,
    message_id TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    duration_minutes INTEGER,
    reminder_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- Meeting RSVPs table
CREATE TABLE IF NOT EXISTS meeting_rsvps (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    family_id UUID NOT NULL,
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

-- Regimes table
CREATE TABLE IF NOT EXISTS regimes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    leader_id TEXT REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, name)
);

-- Now we can add the regime_id foreign key to family_members
ALTER TABLE family_members
ADD CONSTRAINT fk_family_members_regime
FOREIGN KEY (regime_id) REFERENCES regimes(id) ON DELETE SET NULL;

-- Assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    regime_id UUID REFERENCES regimes(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    reward_amount INTEGER NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by TEXT REFERENCES users(id),
    assigned_to TEXT REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'expired'))
);

-- Regime distribution settings table
CREATE TABLE IF NOT EXISTS regime_distribution (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID REFERENCES families(id) ON DELETE CASCADE,
    regime_id UUID REFERENCES regimes(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT true,
    target_member_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_id, regime_id)
);

-- Add security constraints
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

-- Add indexes for better performance
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
CREATE INDEX idx_meetings_scheduled_by ON meetings(created_by);
CREATE INDEX idx_meetings_meeting_time ON meetings(meeting_time);
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_reminder_sent ON meetings(reminder_sent);
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
CREATE INDEX idx_mod_logs_server ON mod_logs(server_id);
CREATE INDEX idx_mod_logs_moderator ON mod_logs(moderator_id);
CREATE INDEX idx_mod_logs_timestamp ON mod_logs(timestamp);
CREATE INDEX idx_security_settings_server ON security_settings(server_id);
CREATE INDEX idx_family_members_family ON family_members(family_id);
CREATE INDEX idx_family_members_user ON family_members(user_id);
CREATE INDEX idx_family_members_rank ON family_members(rank_id);
CREATE INDEX idx_family_members_regime ON family_members(regime_id);
CREATE INDEX idx_regimes_family ON regimes(family_id);
CREATE INDEX idx_regimes_leader ON regimes(leader_id);
CREATE INDEX idx_assignments_family ON assignments(family_id);
CREATE INDEX idx_assignments_regime ON assignments(regime_id);
CREATE INDEX idx_assignments_created_by ON assignments(created_by);
CREATE INDEX idx_assignments_assigned_to ON assignments(assigned_to);
CREATE INDEX idx_assignments_status ON assignments(status);
CREATE INDEX idx_regime_distribution_family ON regime_distribution(family_id);
CREATE INDEX idx_regime_distribution_regime ON regime_distribution(regime_id);

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

CREATE TRIGGER update_families_updated_at
    BEFORE UPDATE ON families
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_family_ranks_updated_at
    BEFORE UPDATE ON family_ranks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mentorships_updated_at
    BEFORE UPDATE ON mentorships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hit_stats_updated_at
    BEFORE UPDATE ON hit_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hit_verifications_updated_at
    BEFORE UPDATE ON hit_verifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regime_distribution_updated_at
    BEFORE UPDATE ON regime_distribution
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 