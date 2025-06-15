-- Add session_id column to teams table for session-based isolation
-- This allows multiple users to use the app without seeing each other's data

ALTER TABLE teams ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_teams_session_id ON teams(session_id);

-- Update existing teams to have a default session_id (for backward compatibility)
-- This ensures existing data remains accessible
UPDATE teams SET session_id = 'legacy_session' WHERE session_id IS NULL; 