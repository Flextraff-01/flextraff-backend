-- FlexTraff User Management Schema
-- Migration: Add user authentication and access control
-- This migration adds user tables for role-based access to traffic junctions

-- Users Table
-- Stores user credentials and profile information
CREATE TABLE IF NOT EXISTS users (
    id bigint primary key generated always as identity,
    username text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    full_name text NOT NULL,
    email text UNIQUE,
    role text NOT NULL CHECK (role IN ('ADMIN', 'OPERATOR', 'OBSERVER')),
    is_active boolean DEFAULT true,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- User Junction Access Table
-- Maps users to traffic junctions they can manage/view
-- One user can manage multiple junctions
-- One junction can be managed by multiple users
CREATE TABLE IF NOT EXISTS user_junctions (
    id bigint primary key generated always as identity,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    junction_id bigint NOT NULL REFERENCES traffic_junctions(id) ON DELETE CASCADE,
    access_level text NOT NULL CHECK (access_level IN ('OPERATOR', 'OBSERVER')),
    granted_at timestamp with time zone DEFAULT now(),
    granted_by bigint REFERENCES users(id),
    UNIQUE(user_id, junction_id)
);

-- User Sessions Table
-- Tracks active sessions for token management
CREATE TABLE IF NOT EXISTS user_sessions (
    id bigint primary key generated always as identity,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token text NOT NULL UNIQUE,
    refresh_token text NOT NULL UNIQUE,
    ip_address text,
    user_agent text,
    expires_at timestamp with time zone NOT NULL,
    last_used timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);

-- Audit Log Table
-- Tracks all user actions on junctions for compliance and debugging
CREATE TABLE IF NOT EXISTS user_audit_logs (
    id bigint primary key generated always as identity,
    user_id bigint REFERENCES users(id) ON DELETE SET NULL,
    junction_id bigint REFERENCES traffic_junctions(id) ON DELETE SET NULL,
    action text NOT NULL,
    resource text NOT NULL,
    details jsonb,
    ip_address text,
    timestamp timestamp with time zone DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_user_junctions_user_id ON user_junctions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_junctions_junction_id ON user_junctions(junction_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh_token ON user_sessions(refresh_token);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON user_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_junction_id ON user_audit_logs(junction_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON user_audit_logs(timestamp);

-- Create RLS policies for users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_junctions table
ALTER TABLE user_junctions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_sessions table
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for audit logs
ALTER TABLE user_audit_logs ENABLE ROW LEVEL SECURITY;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
