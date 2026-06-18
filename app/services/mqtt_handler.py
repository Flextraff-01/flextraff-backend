"""
MQTT Handler - FlexTraff Adaptive Traffic Control System

Architecture:
- Each lane's RFID Pi publishes to: flextraff/junction_{id}/lane_{name}/car_count
- Backend subscribes to wildcard:   flextraff/+/+/car_count
- Backend publishes per lane to:    flextraff/junction_{id}/lane_{name}/green_time

Background tasks:
- Watchdog  : runs every 30s, marks lanes static if no data for 60s
- Conductor : runs every 30s, calculates and publishes green times per junction
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi_mqtt import FastMQTT, MQTTConfig

from app.services.database_service import DatabaseService
from app.services.traffic_calculator import TrafficCalculator

logger = logging.getLogger(__name__)
db_service = DatabaseService()

# ── MQTT Configuration ────────────────────────────────────────────────────────
mqtt_config = MQTTConfig(
    host="broker.hivemq.com",
    port=1883,
    keepalive=60,
    version=4,
)
mqtt = FastMQTT(config=mqtt_config)

# ── Constants ─────────────────────────────────────────────────────────────────
LANE_NAMES = ["north", "south", "east", "west"]
STATIC_GREEN = 45  # fixed green time (seconds) for a broken lane
TIMEOUT_SECS = 60  # mark lane static if no message for 60s (2 missed reports)
CONDUCTOR_INTERVAL = 30  # conductor runs every 30s (matches Pi publish interval)

# ── In-memory state ───────────────────────────────────────────────────────────
# { junction_id: { lane_name: { count, last_seen, mode } } }
# mode: "dynamic" = working, "static" = broken/no data
junction_state: Dict[int, Dict[str, Dict[str, Any]]] = {}


def _init_junction(junction_id: int):
    """Initialize in-memory state for a junction if not present"""
    if junction_id not in junction_state:
        junction_state[junction_id] = {
            lane: {
                "count": 0,
                "last_seen": 0.0,  # 0.0 = never received
                "mode": "static",
            }
            for lane in LANE_NAMES
        }


# ── MQTT Lifecycle ────────────────────────────────────────────────────────────


@mqtt.on_connect()
def connect(client, flags, rc, properties):
    print("=" * 60)
    print("✅ MQTT CONNECTED to broker.hivemq.com")
    print("=" * 60)
    # Subscribe to per-lane car count topics using wildcards
    # + matches one level: junction_1, lane_north, etc.
    client.subscribe("flextraff/+/+/car_count", qos=1)
    print("📡 Subscribed to: flextraff/+/+/car_count")
    print("🎧 Listening for per-lane car counts from Raspberry Pi...\n")


@mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    print("⚠️ MQTT Disconnected from broker")


@mqtt.on_subscribe()
def subscribe(client, mid, qos, properties):
    print(f"✅ Subscription confirmed (mid={mid}, qos={qos})")


@mqtt.on_message()
async def message_handler(client, topic, payload, qos, properties):
    """
    Handles incoming per-lane car count messages.

    Topic format : flextraff/junction_{id}/lane_{name}/car_count
    Payload      : { "count": 12, "timestamp": 1234567890 }
    """
    print(f"\n📩 MQTT MESSAGE on topic: {topic}")
    try:
        # ── Parse topic ──────────────────────────────────────────────
        # e.g. ["flextraff", "junction_1", "lane_north", "car_count"]
        parts = topic.split("/")
        if len(parts) != 4:
            logger.warning(f"Unexpected topic format: {topic}")
            return

        junction_part = parts[1]  # "junction_1"
        lane_part = parts[2]  # "lane_north"

        junction_id = int(junction_part.split("_")[1])
        lane_name = lane_part.split("_")[1]  # "north"

        if lane_name not in LANE_NAMES:
            logger.warning(f"Unknown lane name in topic: {lane_name}")
            return

        # ── Parse payload ─────────────────────────────────────────────
        data = json.loads(payload.decode())
        count = max(0, int(data.get("count", 0)))

        # ── Update in-memory state ────────────────────────────────────
        _init_junction(junction_id)
        prev_mode = junction_state[junction_id][lane_name]["mode"]
        junction_state[junction_id][lane_name] = {
            "count": count,
            "last_seen": time.time(),
            "mode": "dynamic",
        }

        # Log recovery if lane was previously static
        if prev_mode == "static":
            print(f"✅ Lane {lane_name} junction {junction_id} RECOVERED → dynamic")
            await db_service.log_system_event(
                message=f"Lane {lane_name} recovered → DYNAMIC",
                component="mqtt_handler",
                junction_id=junction_id,
            )

        print(f"📥 junction={junction_id} lane={lane_name} count={count} mode=dynamic")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error on topic {topic}: {e}")
    except Exception as e:
        logger.error(f"Message handler error: {str(e)}")
        await db_service.log_system_error(
            error_message=str(e),
            error_type="MQTT_MESSAGE_ERROR",
            component="mqtt_handler",
        )


# ── Background Tasks ──────────────────────────────────────────────────────────


async def watchdog():
    """
    Runs every 30s.
    Checks last_seen timestamp for each lane.
    If no message received for TIMEOUT_SECS (60s) → mark lane STATIC.
    If message resumed after being static → already recovered in message_handler.
    """
    print("🐕 Watchdog started")
    while True:
        await asyncio.sleep(30)
        now = time.time()

        for junction_id, lanes in junction_state.items():
            for lane_name, state in lanes.items():
                if state["last_seen"] == 0.0:
                    continue  # never received data for this lane yet

                elapsed = now - state["last_seen"]

                if elapsed > TIMEOUT_SECS and state["mode"] == "dynamic":
                    state["mode"] = "static"
                    print(
                        f"⚠️  junction={junction_id} lane={lane_name} → STATIC "
                        f"(no data for {elapsed:.0f}s)"
                    )
                    await db_service.log_system_event(
                        message=f"Lane {lane_name} marked STATIC — no data for {elapsed:.0f}s",
                        log_level="WARNING",
                        component="watchdog",
                        junction_id=junction_id,
                    )


async def conductor():
    """
    Runs every 30s.
    For each active junction:
      1. Check if manual mode is ON → publish fixed manual times
      2. Otherwise → calculate dynamic green times, override static lanes with 45s
      3. Publish per-lane green_time topics
      4. Log cycle to traffic_cycles table
    """
    print("🎼 Conductor started")
    while True:
        await asyncio.sleep(CONDUCTOR_INTERVAL)
        try:
            junctions = await db_service.get_all_junctions()
            for junction in junctions:
                await _process_junction(junction)
        except Exception as e:
            logger.error(f"Conductor error: {str(e)}")
            await db_service.log_system_error(
                error_message=str(e),
                error_type="CONDUCTOR_ERROR",
                component="conductor",
            )


async def _process_junction(junction: Dict[str, Any]):
    """Process one junction — decide manual vs auto, publish green times"""
    junction_id = junction["id"]
    try:
        sb = db_service.supabase

        # Check if manual mode is active for this junction
        manual = (
            sb.table("manual_signal_configs")
            .select("*")
            .eq("junction_id", junction_id)
            .eq("is_manual_mode", True)
            .limit(1)
            .execute()
        )

        if manual.data:
            await _publish_manual(junction_id, manual.data[0])
        else:
            await _publish_auto(junction)

    except Exception as e:
        logger.error(f"Error processing junction {junction_id}: {str(e)}")
        await db_service.log_system_error(
            error_message=str(e),
            error_type="JUNCTION_PROCESS_ERROR",
            component="conductor",
            junction_id=junction_id,
        )


async def _publish_manual(junction_id: int, config: Dict[str, Any]):
    """
    Manual override mode:
    Publish fixed green times from manual_signal_configs to each lane.
    No traffic calculation done.
    """
    green_times = [
        config["lane_1_green_time"],
        config["lane_2_green_time"],
        config["lane_3_green_time"],
        config["lane_4_green_time"],
    ]
    yellow_time = config.get("yellow_time", 5)

    for i, lane in enumerate(LANE_NAMES):
        topic = f"flextraff/junction_{junction_id}/lane_{lane}/green_time"
        payload = json.dumps(
            {
                "green_time": green_times[i],
                "yellow_time": yellow_time,
                "mode": "manual",
            }
        )
        mqtt.client.publish(topic, payload, qos=1, retain=False)
        print(f"📡 [MANUAL] junction={junction_id} lane={lane} green={green_times[i]}s")

    # Log to traffic_cycles with status="manual"
    try:
        cycle_time = sum(green_times) + 4 * yellow_time
        db_service.supabase.table("traffic_cycles").insert(
            {
                "junction_id": junction_id,
                "total_cycle_time": cycle_time,
                "lane_1_green_time": green_times[0],
                "lane_2_green_time": green_times[1],
                "lane_3_green_time": green_times[2],
                "lane_4_green_time": green_times[3],
                "lane_1_vehicle_count": 0,
                "lane_2_vehicle_count": 0,
                "lane_3_vehicle_count": 0,
                "lane_4_vehicle_count": 0,
                "total_vehicles_detected": 0,
                "algorithm_version": "manual",
                "calculation_time_ms": 0,
                "status": "manual",
            }
        ).execute()
    except Exception as e:
        logger.error(f"Failed to log manual cycle: {str(e)}")


async def _publish_auto(junction: Dict[str, Any]):
    """
    Automatic mode:
    - Dynamic lanes → use real car count, run TrafficCalculator
    - Static lanes  → override with STATIC_GREEN (45s)
    - Publish per lane, log to traffic_cycles
    """
    junction_id = junction["id"]
    min_time = junction.get("min_time", 15)
    max_time = junction.get("max_time", 90)
    base_cycle_time = junction.get("base_cycle_time", 120)
    yellow_time = junction.get("yellow_light_duration", 5)

    _init_junction(junction_id)
    state = junction_state[junction_id]

    # Build lane counts — 0 for static lanes (calculator will assign min_time)
    lane_counts = [
        state[lane]["count"] if state[lane]["mode"] == "dynamic" else 0
        for lane in LANE_NAMES
    ]

    # Calculate green times
    calc_start = datetime.now()
    try:
        calculator = TrafficCalculator(
            min_time=min_time,
            max_time=max_time,
            base_cycle_time=base_cycle_time,
            db_service=db_service,
        )
        green_times, cycle_time = await calculator.calculate_green_times(
            lane_counts, junction_id=junction_id
        )
    except Exception as e:
        logger.error(f"Calculation failed for junction {junction_id}: {str(e)}")
        await db_service.log_system_error(
            error_message=str(e),
            error_type="CALCULATION_ERROR",
            component="conductor",
            junction_id=junction_id,
        )
        return

    calc_ms = int((datetime.now() - calc_start).total_seconds() * 1000)

    # Override static lanes with fixed STATIC_GREEN time
    for i, lane in enumerate(LANE_NAMES):
        if state[lane]["mode"] == "static":
            green_times[i] = STATIC_GREEN

    # Publish per lane
    for i, lane in enumerate(LANE_NAMES):
        topic = f"flextraff/junction_{junction_id}/lane_{lane}/green_time"
        payload = json.dumps(
            {
                "green_time": green_times[i],
                "yellow_time": yellow_time,
                "mode": state[lane]["mode"],
            }
        )
        mqtt.client.publish(topic, payload, qos=1, retain=False)
        print(
            f"📡 [{state[lane]['mode'].upper():7}] "
            f"junction={junction_id} lane={lane} green={green_times[i]}s"
        )

    # Log to traffic_cycles
    try:
        db_service.supabase.table("traffic_cycles").insert(
            {
                "junction_id": junction_id,
                "total_cycle_time": cycle_time,
                "lane_1_green_time": green_times[0],
                "lane_2_green_time": green_times[1],
                "lane_3_green_time": green_times[2],
                "lane_4_green_time": green_times[3],
                "lane_1_vehicle_count": lane_counts[0],
                "lane_2_vehicle_count": lane_counts[1],
                "lane_3_vehicle_count": lane_counts[2],
                "lane_4_vehicle_count": lane_counts[3],
                "total_vehicles_detected": sum(lane_counts),
                "algorithm_version": "v1.0",
                "calculation_time_ms": calc_ms,
                "status": "active",
                "min_lane_time": min_time,
                "max_lane_time": max_time,
            }
        ).execute()
    except Exception as e:
        logger.error(f"Failed to log auto cycle: {str(e)}")

    await db_service.log_system_event(
        message=(
            f"Cycle complete | "
            f"green={green_times} | "
            f"counts={lane_counts} | "
            f"static_lanes={[l for l in LANE_NAMES if state[l]['mode'] == 'static']}"
        ),
        component="conductor",
        junction_id=junction_id,
    )


# ── Export ────────────────────────────────────────────────────────────────────
__all__ = ["mqtt", "watchdog", "conductor"]
