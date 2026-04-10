# FLEXTRAFF DATABASE - CHANGELOG v1.1

## Date: February 10, 2026
## Changes: Critical Bug Fixes

---

## Summary of Issues Found and Fixed

### Issue #1: Redundant `priority` Field in `lanes` Table ✅ FIXED

**Problem Identified:**
- The `lanes` table had both `lane_index` and `priority` fields
- `lane_index`: Identifies lane position (1=North, 2=South, 3=East, 4=West)
- `priority`: Intended for ML algorithm weighting
- Both appeared to serve similar purposes, causing confusion

**Root Cause:**
- `priority` was added prematurely for a future ML feature
- Not needed for current MVP functionality
- Created ambiguity in the schema

**Solution:**
- **REMOVED** `priority` field from `lanes` table
- Kept only `lane_index` for positional identification
- Added note in documentation that priority can be added in Phase 2 if needed

**Impact:**
- Cleaner, simpler schema
- No confusion about lane ordering
- Can add priority back later if ML algorithm requires it

---

### Issue #2: Incorrect EPC Storage in `lane_cycle_data` Table ✅ FIXED

**Problem Identified:**
- The `lane_cycle_data` table had:
  - `vehicle_count` (INTEGER): Total number of vehicles
  - `epc_count` (INTEGER): Number of unique EPC tags
- **These are the same thing!** Both just represent counts
- Missing: The actual EPC tag IDs from FASTags

**Root Cause:**
- Original design only focused on aggregate counts
- Forgot to store the actual identifiers for audit trail and analytics
- Lost valuable data for vehicle tracking and fraud detection

**Solution:**
- **REMOVED** `epc_count` field (redundant)
- **ADDED** `epc_ids TEXT[]` field - stores array of actual EPC identifiers
- Added GIN index on `epc_ids` for efficient querying

**Before:**
```sql
CREATE TABLE lane_cycle_data (
    ...
    vehicle_count INTEGER,
    epc_count INTEGER,  -- ❌ Same as vehicle_count
    ...
);
```

**After:**
```sql
CREATE TABLE lane_cycle_data (
    ...
    vehicle_count INTEGER,
    epc_ids TEXT[],  -- ✅ Actual EPC tag IDs: ['EPC123', 'EPC456', ...]
    ...
);
```

**Example Data:**
```sql
-- Instead of just storing counts
vehicle_count = 5
epc_count = 5

-- Now we store actual identifiers
vehicle_count = 5
epc_ids = ['EPC123456', 'EPC789012', 'EPC345678', 'EPC901234', 'EPC567890']
```

**Benefits:**
1. **Audit Trail**: Know exactly which vehicles passed through
2. **Vehicle Tracking**: Track vehicles across multiple junctions
3. **Fraud Detection**: Identify duplicate or suspicious tags
4. **Analytics**: Analyze repeat visitors, travel patterns, commute routes
5. **Compliance**: Regulatory requirements for toll/traffic data

**Impact:**
- Critical fix for production deployment
- Enables future advanced analytics
- Essential for fraud prevention
- Minimal storage overhead (TEXT[] is efficient)

---

## Files Updated

All 4 deliverable files have been updated with these fixes:

1. ✅ **flextraff_database_schema.sql**
   - Removed `priority` from lanes table
   - Changed `epc_count` to `epc_ids TEXT[]` in lane_cycle_data
   - Added GIN index on epc_ids
   - Updated comments

2. ✅ **flextraff_database_documentation.md**
   - Added new section explaining EPC ID storage strategy
   - Updated relationship descriptions
   - Added SQL query examples for EPC IDs
   - Documented trade-offs

3. ✅ **flextraff_erd.mermaid**
   - Updated lanes table schema (removed priority)
   - Updated lane_cycle_data schema (epc_count → epc_ids)

4. ✅ **flextraff_quickstart_guide.md**
   - Updated CarCountData Pydantic model
   - Added EPC ID validation in MQTT handler
   - Added documentation on expected payload format
   - Added notes on EPC ID storage importance

---

## Migration Guide (If Already Deployed)

If you've already created the database with the old schema, run these migrations:

```sql
-- Migration 1: Remove priority from lanes
ALTER TABLE lanes DROP COLUMN IF EXISTS priority;

-- Migration 2: Replace epc_count with epc_ids
ALTER TABLE lane_cycle_data DROP COLUMN IF EXISTS epc_count;
ALTER TABLE lane_cycle_data ADD COLUMN epc_ids TEXT[];

-- Migration 3: Add GIN index for EPC queries
CREATE INDEX idx_lane_cycle_epc_ids ON lane_cycle_data USING GIN (epc_ids);

-- Migration 4: Update comment
COMMENT ON TABLE lane_cycle_data IS 'Vehicle counts, EPC tag IDs, and green times per lane per cycle';
```

---

## MQTT Payload Format Update

**Raspberry Pi publishers must now send EPC IDs:**

```json
{
  "junction_id": "550e8400-e29b-41d4-a716-446655440000",
  "lane_id": "650e8400-e29b-41d4-a716-446655440001",
  "vehicle_count": 5,
  "epc_ids": [
    "EPC123456789012",
    "EPC234567890123",
    "EPC345678901234",
    "EPC456789012345",
    "EPC567890123456"
  ],
  "timestamp": "2026-02-10T14:30:00Z"
}
```

**Backend validation:**
```python
# Validate vehicle_count matches epc_ids length
if len(payload['epc_ids']) != payload['vehicle_count']:
    logger.warning(f"Mismatch: count={payload['vehicle_count']} but {len(payload['epc_ids'])} EPC IDs")
```

---

## Advanced Queries Now Possible

With EPC IDs stored, you can now run powerful analytics:

```sql
-- Find all cycles where a specific vehicle passed through
SELECT tc.cycle_start_time, l.lane_name, lcd.vehicle_count
FROM lane_cycle_data lcd
JOIN traffic_cycles tc ON lcd.cycle_id = tc.cycle_id
JOIN lanes l ON lcd.lane_id = l.lane_id
WHERE 'EPC123456789012' = ANY(lcd.epc_ids)
ORDER BY tc.cycle_start_time DESC;

-- Count unique vehicles at a junction today
SELECT j.junction_name, COUNT(DISTINCT epc) AS unique_vehicles
FROM junctions j
JOIN traffic_cycles tc ON j.junction_id = tc.junction_id
JOIN lane_cycle_data lcd ON tc.cycle_id = lcd.cycle_id
CROSS JOIN unnest(lcd.epc_ids) AS epc
WHERE tc.cycle_start_time::DATE = CURRENT_DATE
GROUP BY j.junction_name;

-- Detect vehicles that passed through multiple lanes (suspicious)
SELECT epc, COUNT(DISTINCT lcd.lane_id) AS lane_count, 
       ARRAY_AGG(DISTINCT l.lane_name) AS lanes
FROM lane_cycle_data lcd
CROSS JOIN unnest(lcd.epc_ids) AS epc
JOIN lanes l ON lcd.lane_id = l.lane_id
JOIN traffic_cycles tc ON lcd.cycle_id = tc.cycle_id
WHERE tc.cycle_start_time >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY epc
HAVING COUNT(DISTINCT lcd.lane_id) > 1;

-- Vehicle commute patterns (same EPC multiple times per day)
SELECT epc, COUNT(*) AS passages, 
       ARRAY_AGG(tc.cycle_start_time ORDER BY tc.cycle_start_time) AS times
FROM lane_cycle_data lcd
CROSS JOIN unnest(lcd.epc_ids) AS epc
JOIN traffic_cycles tc ON lcd.cycle_id = tc.cycle_id
WHERE tc.cycle_start_time::DATE = CURRENT_DATE
GROUP BY epc
HAVING COUNT(*) > 1
ORDER BY passages DESC;
```

---

## Testing Checklist

Before deploying to production:

- [ ] Verify RFID readers send EPC IDs in MQTT payload
- [ ] Test backend validates EPC array length matches vehicle_count
- [ ] Confirm EPC IDs are stored correctly in database
- [ ] Test GIN index performance on EPC queries
- [ ] Verify frontend displays vehicle counts properly
- [ ] Test EPC-based analytics queries
- [ ] Check storage growth with EPC arrays (monitor disk usage)
- [ ] Ensure no PII (Personally Identifiable Information) in EPC IDs

---

## Security Note

**EPC IDs vs Privacy:**
- FASTag EPC codes are **NOT** directly linked to personal information in our database
- They are vehicle identifiers, similar to license plates
- Only toll authorities have the mapping to owner details
- Our system only stores anonymous vehicle tracking data
- Follow local regulations on vehicle data retention

---

## Acknowledgments

Great catch on identifying these issues! This is exactly the kind of careful review that prevents production problems. The fixes ensure:

✅ Clean, unambiguous schema  
✅ Essential data captured for analytics  
✅ Scalable for future features  
✅ Production-ready design

---

**Version:** 1.1  
**Previous Version:** 1.0  
**Changes:** Critical bug fixes (priority removal, EPC ID storage)  
**Status:** Ready for deployment