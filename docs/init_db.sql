-- Database Schema for Viral Rapper Pipeline
-- Version: 1.0
-- Created: 2026-02-26
-- Updated: 2026-02-26 (PostgreSQL support for Render.com)
-- Purpose: Store user-specific settings for Telegram bot customization

-- ============================================
-- IMPORTANT: This schema supports both PostgreSQL (production on Render.com)
-- and SQLite (local development). Use appropriate data types for your database.
-- ============================================

-- ============================================
-- Table: user_settings
-- Purpose: Store per-user customization settings (API keys, prompts, preferences)
-- ============================================
CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY,  -- Use BIGINT for PostgreSQL, INTEGER for SQLite
    
    -- API Keys (encrypted with cryptography.fernet)
    gemini_api_key TEXT,  -- NULL = use default from .env
    elevenlabs_api_key TEXT,  -- NULL = use default from .env
    grok_video_api_key TEXT,  -- NULL = use default from .env
    
    -- Gemini Image Generation Settings
    gemini_system_prompt TEXT DEFAULT 'Generate a high-quality, realistic image of a Russian rapper as [role] in [theme] style. Professional photography, cinematic lighting, detailed background.',
    
    -- ElevenLabs Voice Settings
    elevenlabs_voice_id TEXT DEFAULT '21m00Tcm4TlvDq8ikWAM',  -- Default Russian male voice
    
    -- Video Quality Settings
    video_quality TEXT DEFAULT 'high' CHECK(video_quality IN ('high', 'medium')),  -- high=5000k, medium=3000k bitrate
    intro_duration INTEGER DEFAULT 4 CHECK(intro_duration BETWEEN 3 AND 5),  -- seconds
    clip_duration INTEGER DEFAULT 4 CHECK(clip_duration BETWEEN 3 AND 5),  -- seconds per rapper
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- ============================================
-- Table: generation_history (Optional - Phase 5)
-- Purpose: Track video generation history for analytics
-- ============================================
CREATE TABLE IF NOT EXISTS generation_history (
    id SERIAL PRIMARY KEY,  -- Use SERIAL for PostgreSQL, INTEGER AUTOINCREMENT for SQLite
    user_id BIGINT NOT NULL,
    theme TEXT NOT NULL,
    rappers TEXT NOT NULL,  -- JSON array of rapper names
    video_path TEXT,
    duration INTEGER,  -- seconds
    cost REAL,  -- estimated cost in USD
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
);

CREATE INDEX IF NOT EXISTS idx_generation_history_user_id ON generation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_generation_history_status ON generation_history(status);
CREATE INDEX IF NOT EXISTS idx_generation_history_created_at ON generation_history(created_at);

-- ============================================
-- Trigger: Update updated_at timestamp (PostgreSQL)
-- Note: SQLite uses different syntax, adjust if using SQLite
-- ============================================
-- PostgreSQL version:
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_settings_timestamp
BEFORE UPDATE ON user_settings
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- SQLite version (comment out if using PostgreSQL):
-- CREATE TRIGGER IF NOT EXISTS update_user_settings_timestamp 
-- AFTER UPDATE ON user_settings
-- FOR EACH ROW
-- BEGIN
--     UPDATE user_settings SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
-- END;

-- ============================================
-- Sample Data (for testing)
-- ============================================
-- INSERT INTO user_settings (user_id, gemini_system_prompt, elevenlabs_voice_id, video_quality)
-- VALUES (123456789, 'Custom prompt here', '21m00Tcm4TlvDq8ikWAM', 'high');

-- ============================================
-- Migration Notes for Render.com:
-- 1. Connect to PostgreSQL: psql $DATABASE_URL
-- 2. Run this schema: \i docs/init_db.sql
-- 3. Verify tables: \dt
-- 4. Check indexes: \di
-- ============================================

