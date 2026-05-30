-- Sample Data for FlexTraff ATCS Backend
-- Run this AFTER running supabase_setup.sql

-- Insert Sample Traffic Junctions
INSERT INTO traffic_junctions (junction_name, location, latitude, longitude) VALUES
('Main Street & Oak Ave', 'Downtown Mumbai', 19.0760, 72.8777),
('Highway 101 & Pine St', 'Suburb Delhi', 28.7041, 77.1025),
('Central Square Junction', 'Bangalore Tech Park', 12.9716, 77.5946);

-- Insert Sample RFID Scanners
INSERT INTO rfid_scanners (junction_id, lane_number, scanner_mac_address, scanner_position) VALUES
(1, 1, '00:11:22:33:44:55', 'North Lane Entry'),
(1, 2, '00:11:22:33:44:56', 'South Lane Entry'),
(1, 3, '00:11:22:33:44:57', 'East Lane Entry'),
(1, 4, '00:11:22:33:44:58', 'West Lane Entry'),
(2, 1, '00:11:22:33:44:59', 'North Lane Entry'),
(2, 2, '00:11:22:33:44:60', 'South Lane Entry'),
(2, 3, '00:11:22:33:44:61', 'East Lane Entry'),
(2, 4, '00:11:22:33:44:62', 'West Lane Entry'),
(3, 1, '00:11:22:33:44:63', 'North Lane Entry'),
(3, 2, '00:11:22:33:44:64', 'South Lane Entry'),
(3, 3, '00:11:22:33:44:65', 'East Lane Entry'),
(3, 4, '00:11:22:33:44:66', 'West Lane Entry');

-- Insert Demo Scenarios
INSERT INTO demo_scenarios (scenario_name, description, lane_counts, expected_cycle_time) VALUES
('Rush Hour Peak', 'Heavy traffic simulation with high vehicle counts', ARRAY[45, 38, 52, 41], 150),
('Normal Traffic', 'Standard traffic flow during regular hours', ARRAY[25, 22, 28, 24], 120),
('Light Traffic', 'Off-peak hours with minimal vehicles', ARRAY[8, 12, 6, 10], 120),
('Uneven Distribution', 'One busy lane scenario - highway merge', ARRAY[60, 15, 18, 12], 140),
('Emergency Scenario', 'Emergency vehicle priority testing', ARRAY[30, 35, 40, 25], 130);

-- Insert Sample Vehicle Detections (last 10 minutes)
INSERT INTO vehicle_detections (junction_id, scanner_id, lane_number, fastag_id, vehicle_type, detection_timestamp) VALUES
(1, 1, 1, 'FT001234567890', 'car', NOW() - INTERVAL '9 minutes'),
(1, 2, 2, 'FT001234567891', 'car', NOW() - INTERVAL '8 minutes'),
(1, 3, 3, 'FT001234567892', 'truck', NOW() - INTERVAL '7 minutes'),
(1, 4, 4, 'FT001234567893', 'car', NOW() - INTERVAL '6 minutes'),
(1, 1, 1, 'FT001234567894', 'car', NOW() - INTERVAL '5 minutes'),
(1, 2, 2, 'FT001234567895', 'bike', NOW() - INTERVAL '4 minutes'),
(1, 3, 3, 'FT001234567896', 'car', NOW() - INTERVAL '3 minutes'),
(1, 4, 4, 'FT001234567897', 'car', NOW() - INTERVAL '2 minutes'),
(1, 1, 1, 'FT001234567898', 'car', NOW() - INTERVAL '1 minute'),
(1, 2, 2, 'FT001234567899', 'car', NOW());

-- Insert Sample Traffic Cycle
INSERT INTO traffic_cycles (
    junction_id, 
    total_cycle_time, 
    lane_1_green_time, 
    lane_2_green_time, 
    lane_3_green_time, 
    lane_4_green_time,
    lane_1_vehicle_count,
    lane_2_vehicle_count,
    lane_3_vehicle_count,
    lane_4_vehicle_count,
    total_vehicles_detected,
    calculation_time_ms
) VALUES
(1, 130, 35, 30, 40, 25, 3, 3, 2, 2, 10, 45);

-- Success message
SELECT 
    'Sample data inserted successfully!' as message,
    (SELECT COUNT(*) FROM traffic_junctions) as junctions_count,
    (SELECT COUNT(*) FROM rfid_scanners) as scanners_count,
    (SELECT COUNT(*) FROM demo_scenarios) as scenarios_count,
    (SELECT COUNT(*) FROM vehicle_detections) as detections_count,
    (SELECT COUNT(*) FROM traffic_cycles) as cycles_count;