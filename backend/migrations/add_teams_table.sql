-- Migration: Add Teams table and update existing tables for multi-team support
-- Run this migration to enable multi-team functionality

-- 1. Create the teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id VARCHAR NOT NULL UNIQUE,
    team_name VARCHAR,
    domain VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique constraint and index
CREATE UNIQUE INDEX IF NOT EXISTS uq_teams_team_id ON teams(team_id);
CREATE INDEX IF NOT EXISTS idx_teams_team_id ON teams(team_id);

-- 2. Migrate existing data to teams table
-- Insert existing team IDs from slack_installations
INSERT INTO teams (team_id, team_name, is_active, created_at, updated_at)
SELECT DISTINCT 
    team_id,
    team_name,
    true,
    created_at,
    updated_at
FROM slack_installations
WHERE team_id NOT IN (SELECT team_id FROM teams)
ON CONFLICT (team_id) DO NOTHING;

-- Insert any team IDs from zoho_installations that don't exist
INSERT INTO teams (team_id, is_active, created_at, updated_at)
SELECT DISTINCT 
    team_id,
    true,
    created_at,
    updated_at
FROM zoho_installations
WHERE team_id NOT IN (SELECT team_id FROM teams)
ON CONFLICT (team_id) DO NOTHING;

-- Insert any team IDs from gmail_installations that don't exist
INSERT INTO teams (team_id, is_active, created_at, updated_at)
SELECT DISTINCT 
    team_id,
    true,
    created_at,
    updated_at
FROM gmail_installations
WHERE team_id NOT IN (SELECT team_id FROM teams)
ON CONFLICT (team_id) DO NOTHING;

-- 3. Update existing tables to add foreign key constraints
-- Note: We'll add the constraints after ensuring data integrity

-- First, ensure all team_ids in child tables exist in teams table
-- This handles any orphaned records
INSERT INTO teams (team_id, is_active, created_at, updated_at)
SELECT DISTINCT 
    team_id,
    true,
    NOW(),
    NOW()
FROM (
    SELECT team_id FROM slack_installations WHERE team_id IS NOT NULL
    UNION
    SELECT team_id FROM zoho_installations WHERE team_id IS NOT NULL
    UNION
    SELECT team_id FROM gmail_installations WHERE team_id IS NOT NULL
    UNION
    SELECT team_id FROM event_logs WHERE team_id IS NOT NULL
) AS all_team_ids
WHERE team_id NOT IN (SELECT team_id FROM teams)
ON CONFLICT (team_id) DO NOTHING;

-- 4. Add foreign key constraints (if they don't exist)
-- Note: PostgreSQL will skip if constraint already exists

-- Slack installations
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_slack_installations_team_id'
    ) THEN
        ALTER TABLE slack_installations 
        ADD CONSTRAINT fk_slack_installations_team_id 
        FOREIGN KEY (team_id) REFERENCES teams(team_id);
    END IF;
END $$;

-- Zoho installations
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_zoho_installations_team_id'
    ) THEN
        ALTER TABLE zoho_installations 
        ADD CONSTRAINT fk_zoho_installations_team_id 
        FOREIGN KEY (team_id) REFERENCES teams(team_id);
    END IF;
END $$;

-- Gmail installations
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_gmail_installations_team_id'
    ) THEN
        ALTER TABLE gmail_installations 
        ADD CONSTRAINT fk_gmail_installations_team_id 
        FOREIGN KEY (team_id) REFERENCES teams(team_id);
    END IF;
END $$;

-- Event logs
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_event_logs_team_id'
    ) THEN
        ALTER TABLE event_logs 
        ADD CONSTRAINT fk_event_logs_team_id 
        FOREIGN KEY (team_id) REFERENCES teams(team_id);
    END IF;
END $$;

-- 5. Add team_id column to leads table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'leads' AND column_name = 'team_id'
    ) THEN
        ALTER TABLE leads ADD COLUMN team_id VARCHAR;
        
        -- Set a default team_id for existing leads (use the first team if any)
        UPDATE leads 
        SET team_id = (SELECT team_id FROM teams LIMIT 1)
        WHERE team_id IS NULL;
        
        -- Make team_id NOT NULL after setting default values
        ALTER TABLE leads ALTER COLUMN team_id SET NOT NULL;
        
        -- Add foreign key constraint
        ALTER TABLE leads 
        ADD CONSTRAINT fk_leads_team_id 
        FOREIGN KEY (team_id) REFERENCES teams(team_id);
        
        -- Add index
        CREATE INDEX idx_leads_team_id ON leads(team_id);
    END IF;
END $$;

-- 6. Remove team_name column from slack_installations (now in teams table)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'slack_installations' AND column_name = 'team_name'
    ) THEN
        ALTER TABLE slack_installations DROP COLUMN team_name;
    END IF;
END $$;

-- 7. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_slack_installations_team_id ON slack_installations(team_id);
CREATE INDEX IF NOT EXISTS idx_zoho_installations_team_id ON zoho_installations(team_id);
CREATE INDEX IF NOT EXISTS idx_gmail_installations_team_id ON gmail_installations(team_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_team_id ON event_logs(team_id);

-- 8. Update the updated_at trigger for teams table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_teams_updated_at ON teams;
CREATE TRIGGER update_teams_updated_at
    BEFORE UPDATE ON teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migration completed successfully
-- You can now use multi-team functionality 