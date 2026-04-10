# FLEXTRAFF DATABASE DESIGN DOCUMENTATION

## Overview
This document explains the design decisions, relationships, and best practices for the Flextraff traffic management system database.

---

## Table of Contents
1. [Schema Overview](#schema-overview)
2. [Table Relationships](#table-relationships)
3. [Key Design Decisions](#key-design-decisions)
4. [Indexing Strategy](#indexing-strategy)
5. [Data Flow](#data-flow)
6. [Security Considerations](#security-considerations)
7. [Performance Optimizations](#performance-optimizations)
8. [API Integration Points](#api-integration-points)
9. [Analytics & Reporting](#analytics--reporting)
10. [Maintenance & Operations](#maintenance--operations)

---

## Schema Overview

### Core Tables (11 tables)

1. **users** - User authentication and authorization
2. **junctions** - Traffic intersections/signals
3. **user_junction_access** - User-junction permissions (many-to-many)
4. **lanes** - Individual lanes at each junction (4 per junction)
5. **edge_devices** - Raspberry Pi IoT devices (8 per junction)
6. **traffic_cycles** - Historical record of each signal cycle
7. **lane_cycle_data** - Car counts and green times per lane per cycle
8. **manual_override_history** - Manual mode override logs
9. **system_logs** - Application logs and errors
10. **mqtt_messages** - Raw MQTT message debugging (optional)
11. **junction_daily_stats** - Pre-computed analytics

### Views (3 views)
- **v_junction_health** - Real-time junction and device status
- **v_user_permissions** - User access summary
- **v_recent_cycles** - Recent traffic cycles with aggregated lane data

---

## Table Relationships

### Entity Relationship Diagram (ERD)

```
users (1) ----< user_junction_access >---- (M) junctions
                                                   |
                                                   | (1)
                                                   |
                                                   V
                                                lanes (M)
                                                   |
                                                   | (1)
                                                   |
                                                   V
                                            edge_devices (M)
                                                   
junctions (1) ----< traffic_cycles (M)
                         |
                         | (1)
                         |
                         V
                  lane_cycle_data (M) >---- lanes

junctions (1) ----< manual_override_history (M) >---- users

system_logs >---- (optional FK to junctions, devices, users)
mqtt_messages >---- (optional FK to edge_devices)
```

### Key Relationships

1. **Users ↔ Junctions (Many-to-Many)**
   - Junction table: `user_junction_access`
   - Admin users can access all junctions
   - Regular users only access assigned junctions

2. **Junctions → Lanes (One-to-Many)**
   - Each junction has exactly 4 lanes (N, S, E, W)
   - Enforced via UNIQUE constraint on (junction_id, lane_index)

3. **Lanes → Edge Devices (One-to-Many)**
   - Each lane has exactly 2 devices (RFID counter + light controller)
   - Enforced via UNIQUE constraint on (lane_id, device_type)
   - `lane_index` identifies the lane position (1=North, 2=South, 3=East, 4=West)
   - Note: A `priority` field for ML weighting can be added in Phase 2 if needed

4. **Traffic Cycles → Lane Cycle Data (One-to-Many)**
   - Each cycle has 4 lane records (one per lane)
   - Stores vehicle counts and green times

---

## Key Design Decisions

### 1. UUID Primary Keys
**Decision:** Use UUIDs instead of auto-incrementing integers

**Rationale:**
- Better for distributed systems (no ID collision)
- Harder to guess/enumerate records (security)
- Easier to merge data from multiple sources
- Future-proof for microservices architecture

**Trade-off:** Slightly larger storage (16 bytes vs 4-8 bytes)

### 2. Normalized Schema (3NF)
**Decision:** Follow Third Normal Form

**Benefits:**
- Eliminates data redundancy
- Ensures data integrity
- Easier to maintain and extend
- Better for transactional consistency

**Example:** Lane data separated from junction data, not duplicated

### 3. JSONB for Flexible Metadata
**Decision:** Use JSONB for `system_logs.metadata` and `mqtt_messages.payload`

**Rationale:**
- Flexibility for varying log structures
- Efficient querying with GIN indexes
- No schema changes needed for new log types
- PostgreSQL JSONB is performant

### 4. Timestamp with Time Zone
**Decision:** All timestamps use `TIMESTAMP WITH TIME ZONE`

**Rationale:**
- Handles multi-timezone deployments
- Accurate for international expansion
- No ambiguity in time representation
- Best practice for PostgreSQL

### 5. Soft Deletes vs Hard Deletes
**Decision:** Use CASCADE deletes for most relationships, but preserve history

**Rationale:**
- Historical data (cycles, logs) never deleted
- Users/junctions can be deleted (SET NULL on logs)
- Simplifies data integrity
- Separate archival process for old data

### 7. EPC Tag ID Storage
**Decision:** Store array of EPC IDs in `lane_cycle_data.epc_ids` as TEXT[]

**Rationale:**
- Preserves actual FASTag EPC identifiers for audit trail
- Enables vehicle tracking across multiple junctions (future phase)
- Allows duplicate detection and fraud prevention
- Can analyze repeat visitors and traffic patterns
- PostgreSQL TEXT[] type is efficient with GIN indexing

**Usage:**
```sql
-- Store EPC IDs
INSERT INTO lane_cycle_data (cycle_id, lane_id, vehicle_count, epc_ids, ...)
VALUES ('...', '...', 5, ARRAY['EPC123456', 'EPC789012', 'EPC345678', 'EPC901234', 'EPC567890'], ...);

-- Query vehicles that passed through
SELECT * FROM lane_cycle_data 
WHERE 'EPC123456' = ANY(epc_ids);

-- Count unique vehicles across multiple cycles
SELECT COUNT(DISTINCT unnest(epc_ids)) 
FROM lane_cycle_data 
WHERE cycle_id IN (...);
```

**Trade-off:** Slightly larger storage, but essential for analytics and fraud detection

### 8. Separate Manual Override Tracking
**Decision:** Create dedicated `manual_override_history` table

**Rationale:**
- Analytics on manual intervention patterns
- Compliance and audit trail
- Helps ML model learn when manual intervention occurs
- Tracks duration of overrides

---

## Indexing Strategy

### Primary Indexes (Automatic)
All primary keys have automatic B-tree indexes.

### Foreign Key Indexes
All foreign key columns are indexed for JOIN performance:
- `user_junction_access(user_id, junction_id)`
- `lanes(junction_id)`
- `edge_devices(lane_id)`
- `traffic_cycles(junction_id)`
- `lane_cycle_data(cycle_id, lane_id)`

### Query-Optimized Indexes

1. **Time-based queries** (DESC for recent-first):
   ```sql
   idx_cycles_start_time ON traffic_cycles(cycle_start_time DESC)
   idx_logs_logged_at ON system_logs(logged_at DESC)
   ```

2. **Composite indexes** for common filter combinations:
   ```sql
   idx_cycles_junction_time ON traffic_cycles(junction_id, cycle_start_time DESC)
   ```

3. **Partial indexes** for active records only:
   ```sql
   idx_users_active ON users(is_active) WHERE is_active = TRUE
   idx_lanes_active ON lanes(is_active) WHERE is_active = TRUE
   ```

4. **GIN indexes** for JSONB columns:
   ```sql
   idx_logs_metadata ON system_logs USING GIN (metadata)
   idx_mqtt_payload ON mqtt_messages USING GIN (payload)
   ```

### Index Maintenance
- Run `VACUUM ANALYZE` weekly on high-traffic tables
- Monitor index bloat with `pg_stat_user_indexes`
- Consider `REINDEX` for heavily updated tables

---

## Data Flow

### 1. Real-time Traffic Cycle Flow

```
┌─────────────────┐
│ RFID Reader (Pi)│
│ Counts vehicles │
└────────┬────────┘
         │ Publishes to MQTT
         │ topic: car-counts
         ▼
┌─────────────────┐
│ FastAPI Backend │
│ Subscribes MQTT │
└────────┬────────┘
         │ 1. Reads car counts
         │ 2. Runs algorithm
         │ 3. Calculates green times
         ├─────────────────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌──────────────────┐
│ INSERT INTO     │      │ Publishes to MQTT│
│ traffic_cycles  │      │ topic: green-time│
│ lane_cycle_data │      └────────┬─────────┘
└─────────────────┘               │
                                  ▼
                         ┌─────────────────┐
                         │ Light Control Pi│
                         │ Changes lights  │
                         └─────────────────┘
```

### 2. Manual Override Flow

```
┌─────────────────┐
│ User (Frontend) │
│ Sets manual times│
└────────┬────────┘
         │ WebSocket/HTTP
         ▼
┌─────────────────┐
│ FastAPI Backend │
└────────┬────────┘
         │ 1. Validate user access
         │ 2. UPDATE junctions SET current_mode = 'manual_override'
         │ 3. INSERT INTO manual_override_history
         │ 4. Publish to MQTT green-time topic
         ▼
┌─────────────────┐
│ Traffic lights  │
│ use manual times│
└─────────────────┘
```

### 3. System Logging Flow

```
┌──────────────────────────┐
│ Any system component     │
│ (Backend, Pi, Frontend)  │
└───────────┬──────────────┘
            │ WebSocket/HTTP
            ▼
┌─────────────────────────┐
│ FastAPI Backend         │
│ /api/logs endpoint      │
└───────────┬─────────────┘
            │ INSERT INTO system_logs
            ▼
┌─────────────────────────┐
│ PostgreSQL Database     │
│ + Real-time to Frontend │
│   via WebSocket         │
└─────────────────────────┘
```

---

## Security Considerations

### 1. Password Storage
- **NEVER** store plain text passwords
- Use bcrypt or Argon2 for hashing
- Set cost factor appropriately (bcrypt rounds: 12-14)

```python
# Example with bcrypt
import bcrypt

hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
```

### 2. Row-Level Security (RLS)
Enable PostgreSQL RLS for multi-tenant isolation:

```sql
ALTER TABLE junctions ENABLE ROW LEVEL SECURITY;

-- Users can only see their assigned junctions
CREATE POLICY user_junction_access_policy ON junctions
    FOR SELECT
    USING (
        junction_id IN (
            SELECT junction_id 
            FROM user_junction_access 
            WHERE user_id = current_setting('app.user_id')::UUID
        )
        OR 
        current_setting('app.is_admin')::BOOLEAN = TRUE
    );
```

### 3. API Authentication
- Use JWT tokens for API authentication
- Store tokens in `httpOnly` cookies (not localStorage)
- Implement token refresh mechanism
- Set short expiry times (15-30 minutes)

### 4. Input Validation
- Validate all user inputs at API layer
- Use parameterized queries (prevent SQL injection)
- Sanitize all text inputs
- Rate limit API endpoints

### 5. HTTPS/TLS
- Enforce HTTPS for all API communication
- Use TLS 1.2+ for database connections
- Encrypt MQTT messages (MQTT over TLS)

---

## Performance Optimizations

### 1. Connection Pooling
Configure PostgreSQL connection pooling:

```python
# FastAPI with asyncpg
from databases import Database

DATABASE_URL = "postgresql://user:pass@host:5432/flextraff"
database = Database(
    DATABASE_URL,
    min_size=5,      # Minimum connections
    max_size=20,     # Maximum connections
)
```

### 2. Query Optimization

**Bad Query (N+1 problem):**
```python
# Don't do this - makes N queries
junctions = await db.fetch("SELECT * FROM junctions")
for junction in junctions:
    lanes = await db.fetch("SELECT * FROM lanes WHERE junction_id = $1", junction['id'])
```

**Good Query (Single JOIN):**
```python
# Do this - single query
query = """
    SELECT j.*, l.* 
    FROM junctions j
    LEFT JOIN lanes l ON j.junction_id = l.junction_id
"""
results = await db.fetch(query)
```

### 3. Caching Strategy
Cache frequently accessed, rarely changed data:

```python
# Redis cache example
import redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Cache junction list for 5 minutes
junctions = r.get('junctions:all')
if not junctions:
    junctions = await db.fetch("SELECT * FROM junctions")
    r.setex('junctions:all', 300, json.dumps(junctions))
```

### 4. Batch Inserts
For high-volume data (car counts, logs):

```python
# Instead of inserting one-by-one
records = [
    {'cycle_id': cycle_id, 'lane_id': lane1_id, 'vehicle_count': 15, ...},
    {'cycle_id': cycle_id, 'lane_id': lane2_id, 'vehicle_count': 20, ...},
]

# Use executemany
await db.execute_many(
    "INSERT INTO lane_cycle_data (...) VALUES (...)",
    records
)
```

### 5. Partitioning (for scale)
If traffic_cycles grows > 10M rows, partition by time:

```sql
-- Create partitioned table
CREATE TABLE traffic_cycles (
    ...
) PARTITION BY RANGE (cycle_start_time);

-- Create monthly partitions
CREATE TABLE traffic_cycles_2026_02 PARTITION OF traffic_cycles
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE traffic_cycles_2026_03 PARTITION OF traffic_cycles
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
```

### 6. Materialized Views
For expensive analytics queries:

```sql
CREATE MATERIALIZED VIEW mv_junction_stats AS
SELECT 
    junction_id,
    DATE(cycle_start_time) AS date,
    COUNT(*) AS total_cycles,
    AVG(total_cycle_time) AS avg_cycle_time,
    SUM(lcd.vehicle_count) AS total_vehicles
FROM traffic_cycles tc
JOIN lane_cycle_data lcd ON tc.cycle_id = lcd.cycle_id
GROUP BY junction_id, DATE(cycle_start_time);

-- Refresh daily via cron
REFRESH MATERIALIZED VIEW mv_junction_stats;
```

---

## API Integration Points

### 1. User Management

```python
# POST /api/users/register
{
    "username": "user1",
    "email": "user1@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
}

# POST /api/users/login
{
    "username": "user1",
    "password": "secure_password"
}
# Returns: JWT token

# GET /api/users/me
# Headers: Authorization: Bearer <token>
# Returns: User profile + assigned junctions
```

### 2. Junction Management

```python
# GET /api/junctions
# Returns: List of junctions user can access

# GET /api/junctions/{junction_id}
# Returns: Junction details + lanes + devices

# PUT /api/junctions/{junction_id}/mode
{
    "mode": "manual_override",  # or "automatic"
    "settings": {
        "total_cycle_time": 180,
        "north_lane_time": 40,
        "south_lane_time": 50,
        "east_lane_time": 60,
        "west_lane_time": 30  # Auto-calculated
    }
}
```

### 3. Real-time Data

```python
# WebSocket: ws://api.flextraff.com/ws/junction/{junction_id}
# Streams:
{
    "type": "car_count",
    "junction_id": "uuid",
    "lane_id": "uuid",
    "count": 15,
    "timestamp": "2026-02-10T14:30:00Z"
}

{
    "type": "green_time",
    "junction_id": "uuid",
    "green_times": [40, 50, 60, 30],  # N, S, E, W
    "timestamp": "2026-02-10T14:30:00Z"
}

{
    "type": "log",
    "level": "ERROR",
    "message": "Device offline",
    "device_id": "uuid"
}
```

### 4. Analytics

```python
# GET /api/analytics/junction/{junction_id}/daily
# Query params: start_date, end_date
# Returns: Daily aggregated statistics

# GET /api/analytics/junction/{junction_id}/peak-hours
# Returns: Traffic patterns by hour of day

# GET /api/analytics/junction/{junction_id}/export
# Returns: CSV download of historical data
```

---

## Analytics & Reporting

### Key Metrics to Track

1. **Traffic Flow Metrics**
   - Average vehicles per cycle
   - Peak traffic hours
   - Lane-wise distribution
   - Cycle time utilization

2. **System Performance**
   - Device uptime percentage
   - MQTT message latency
   - Algorithm execution time
   - Manual override frequency

3. **Efficiency Metrics**
   - Average wait time reduction
   - Throughput improvement
   - Congestion incidents
   - Emergency override events

### Sample Analytics Queries

```sql
-- Peak traffic hours
SELECT 
    EXTRACT(HOUR FROM cycle_start_time) AS hour,
    AVG(lcd.vehicle_count) AS avg_vehicles,
    COUNT(*) AS cycle_count
FROM traffic_cycles tc
JOIN lane_cycle_data lcd ON tc.cycle_id = lcd.cycle_id
WHERE tc.junction_id = $1
  AND tc.cycle_start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY hour
ORDER BY avg_vehicles DESC;

-- Manual override patterns
SELECT 
    u.username,
    DATE(override_start) AS date,
    COUNT(*) AS override_count,
    AVG(duration_minutes) AS avg_duration
FROM manual_override_history moh
JOIN users u ON moh.user_id = u.user_id
WHERE moh.junction_id = $1
GROUP BY u.username, DATE(override_start)
ORDER BY date DESC;

-- Device health report
SELECT 
    j.junction_name,
    l.lane_name,
    ed.device_type,
    ed.status,
    ed.last_heartbeat,
    CASE 
        WHEN ed.last_heartbeat > NOW() - INTERVAL '5 minutes' THEN 'Healthy'
        WHEN ed.last_heartbeat > NOW() - INTERVAL '15 minutes' THEN 'Warning'
        ELSE 'Critical'
    END AS health_status
FROM edge_devices ed
JOIN lanes l ON ed.lane_id = l.lane_id
JOIN junctions j ON l.junction_id = j.junction_id
ORDER BY j.junction_name, l.lane_index, ed.device_type;
```

---

## Maintenance & Operations

### Daily Tasks
- Monitor system_logs for errors
- Check device heartbeats
- Verify MQTT connectivity
- Review manual override frequency

### Weekly Tasks
- Run VACUUM ANALYZE on high-traffic tables
- Review slow query logs
- Check disk space utilization
- Audit user access patterns

### Monthly Tasks
- Archive old logs (>90 days)
- Review and optimize indexes
- Update junction_daily_stats
- Generate monthly reports

### Backup Strategy
1. **Full backup** - Daily at 2 AM
2. **Incremental backup** - Every 4 hours
3. **WAL archiving** - Continuous
4. **Off-site replication** - Real-time to secondary region
5. **Retention** - Keep 30 days of daily backups

### Monitoring Alerts
- Device offline > 5 minutes
- Database connection pool exhaustion
- High error log rate (>10/minute)
- MQTT broker disconnection
- Disk space > 80%

### Database Maintenance Scripts

```sql
-- Weekly cleanup (run via cron)
DO $$
BEGIN
    -- Archive old system logs
    UPDATE system_logs 
    SET is_archived = TRUE 
    WHERE logged_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
      AND is_archived = FALSE;
    
    -- Delete old MQTT messages
    DELETE FROM mqtt_messages 
    WHERE received_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Refresh materialized views
    REFRESH MATERIALIZED VIEW mv_junction_stats;
    
    -- Update daily stats
    INSERT INTO junction_daily_stats (junction_id, stat_date, ...)
    SELECT ...
    FROM traffic_cycles
    WHERE cycle_start_time::DATE = CURRENT_DATE - INTERVAL '1 day'
    ON CONFLICT (junction_id, stat_date) DO UPDATE ...;
END $$;
```

---

## Migration & Deployment

### Initial Setup
```bash
# 1. Create database
createdb flextraff

# 2. Run schema
psql -U postgres -d flextraff -f flextraff_database_schema.sql

# 3. Create admin user
psql -U postgres -d flextraff -c "INSERT INTO users ..."

# 4. Verify tables
psql -U postgres -d flextraff -c "\dt"
```

### Schema Versioning
Use migration tools like Alembic (Python) or Flyway:

```python
# alembic/versions/001_initial_schema.py
def upgrade():
    op.create_table('users', ...)
    op.create_table('junctions', ...)
    # ...

def downgrade():
    op.drop_table('junctions')
    op.drop_table('users')
```

---

## Future Enhancements

### Phase 2 Features
1. **Vehicle Classification**
   - Add `vehicle_type` to lane_cycle_data (car, truck, bike, etc.)
   - Weight different vehicle types in algorithm

2. **Weather Integration**
   - Add `weather_conditions` table
   - Factor weather into green time calculations

3. **ML Model Integration**
   - Store model predictions in dedicated table
   - A/B test ML vs rule-based algorithm
   - Track model performance metrics

4. **Emergency Vehicle Priority**
   - Add `emergency_vehicle_detected` flag
   - Override normal cycle for emergency routes

5. **Multi-Junction Coordination**
   - Sync green times across multiple junctions
   - "Green wave" for arterial roads

### Scalability Roadmap
- **10 junctions**: Current schema handles easily
- **100 junctions**: Add read replicas, Redis caching
- **1000 junctions**: Partition tables, microservices architecture
- **10000+ junctions**: Multi-region deployment, event sourcing

---

## Conclusion

This database schema is designed for:
- ✅ Production-grade reliability
- ✅ Scalability to 100s of junctions
- ✅ Real-time data processing
- ✅ Rich analytics capabilities
- ✅ Security and compliance
- ✅ Easy maintenance and operations

**Next Steps:**
1. Review and approve schema
2. Set up database on Supabase
3. Implement API endpoints
4. Build frontend dashboards
5. Deploy to staging environment
6. Load test with simulated data
7. Deploy to production

---

**Document Version:** 1.0  
**Last Updated:** February 10, 2026  
**Author:** Flextraff Team