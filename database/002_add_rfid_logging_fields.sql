-- Migration: Add logging fields to rfid_scanners table
-- Date: 2026-01-18
-- Purpose: Store lane car counts and cycle IDs for RFID scanner logs
-- These fields allow tracking traffic cycle data at the scanner level for monitoring

-- Add lane_car_count column to store car counts in JSON format
-- Format: {"north": 5, "south": 3, "east": 8, "west": 4}
ALTER TABLE rfid_scanners 
ADD COLUMN IF NOT EXISTS lane_car_count jsonb DEFAULT '{}'::jsonb;

-- Add cycle_id column to link scanner logs with traffic cycles
ALTER TABLE rfid_scanners 
ADD COLUMN IF NOT EXISTS cycle_id bigint REFERENCES traffic_cycles(id) ON DELETE SET NULL;

-- Add log_timestamp to track when scanner recorded this cycle data
ALTER TABLE rfid_scanners 
ADD COLUMN IF NOT EXISTS log_timestamp timestamp with time zone DEFAULT now();

-- Create index for faster lookups by cycle_id
CREATE INDEX IF NOT EXISTS idx_rfid_scanners_cycle_id ON rfid_scanners(cycle_id);

-- Create index for faster lookups by timestamp
CREATE INDEX IF NOT EXISTS idx_rfid_scanners_log_timestamp ON rfid_scanners(log_timestamp);
