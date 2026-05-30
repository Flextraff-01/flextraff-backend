-- FlexTraff ATCS Database Schema (Core Traffic Management)
-- Run this in Supabase SQL Editor
-- No Authentication - Focus on Traffic Management Only

-- Traffic Junctions Management
CREATE TABLE traffic_junctions (
    id bigint primary key generated always as identity,
    junction_name text NOT NULL UNIQUE,
    location text,
    latitude numeric(10,8),
    longitude numeric(11,8),
    status text DEFAULT 'active',
    algorithm_config jsonb DEFAULT '{"min_time": 15, "max_time": 90, "base_cycle_time": 120}',
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- RFID Scanners Configuration
CREATE TABLE rfid_scanners (
    id bigint primary key generated always as identity,
    junction_id bigint references traffic_junctions(id) on delete cascade,
    lane_number integer NOT NULL CHECK (lane_number BETWEEN 1 AND 4),
    scanner_mac_address text UNIQUE,
    scanner_position text,
    status text DEFAULT 'active',
    last_heartbeat timestamp with time zone,
    created_at timestamp with time zone DEFAULT now()
);

-- Vehicle Detection Events
CREATE TABLE vehicle_detections (
    id bigint primary key generated always as identity,
    junction_id bigint references traffic_junctions(id),
    scanner_id bigint references rfid_scanners(id),
    lane_number integer NOT NULL,
    fastag_id text NOT NULL,
    detection_timestamp timestamp with time zone DEFAULT now(),
    vehicle_type text DEFAULT 'car',
    processing_status text DEFAULT 'pending',
    created_at timestamp with time zone DEFAULT now()
);

-- Calculated Traffic Cycles
CREATE TABLE traffic_cycles (
    id bigint primary key generated always as identity,
    junction_id bigint references traffic_junctions(id),
    cycle_start_time timestamp with time zone DEFAULT now(),
    total_cycle_time integer NOT NULL,
    lane_1_green_time integer NOT NULL,
    lane_2_green_time integer NOT NULL,
    lane_3_green_time integer NOT NULL,
    lane_4_green_time integer NOT NULL,
    lane_1_vehicle_count integer DEFAULT 0,
    lane_2_vehicle_count integer DEFAULT 0,
    lane_3_vehicle_count integer DEFAULT 0,
    lane_4_vehicle_count integer DEFAULT 0,
    total_vehicles_detected integer NOT NULL,
    algorithm_version text DEFAULT 'v1.0',
    calculation_time_ms integer,
    status text DEFAULT 'active'
);

-- System Performance Logs
CREATE TABLE system_logs (
    id bigint primary key generated always as identity,
    junction_id bigint references traffic_junctions(id),
    log_level text NOT NULL,
    component text NOT NULL,
    message text NOT NULL,
    metadata jsonb,
    timestamp timestamp with time zone DEFAULT now()
);

-- Demo Scenarios
CREATE TABLE demo_scenarios (
    id bigint primary key generated always as identity,
    scenario_name text NOT NULL,
    description text,
    lane_counts integer[] NOT NULL CHECK (array_length(lane_counts, 1) = 4),
    expected_cycle_time integer,
    expected_green_times integer[] CHECK (array_length(expected_green_times, 1) = 4),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_vehicle_detections_junction_time ON vehicle_detections(junction_id, detection_timestamp);
CREATE INDEX idx_vehicle_detections_lane_time ON vehicle_detections(lane_number, detection_timestamp);
CREATE INDEX idx_traffic_cycles_junction_time ON traffic_cycles(junction_id, cycle_start_time);
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_rfid_scanners_junction ON rfid_scanners(junction_id);