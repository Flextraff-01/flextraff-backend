"""
FlexTraff MQTT Simulator
Simulates 4 RFID-sender Pis and 4 signal-receiver Pis for one junction.

Usage:
    python simulator.py [--junction_id 1] [--fail_lane north]

Options:
    --junction_id : Junction ID to simulate (default: 1)
    --fail_lane   : Lane to simulate failure (default: none)
                    After 60s, this lane stops publishing — should go STATIC

Requirements:
    pip install paho-mqtt
"""

import argparse
import json
import random
import signal
import sys
import threading
import time
import uuid

import paho.mqtt.client as mqtt

# ── Config ────────────────────────────────────────────────────────────────────
BROKER = "broker.hivemq.com"
PORT = 1883
LANE_NAMES = ["north", "south", "east", "west"]
PUBLISH_INTERVAL = 30  # seconds — matches backend CONDUCTOR_INTERVAL

# ── Parse args ────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="FlexTraff MQTT Simulator")
parser.add_argument(
    "--junction_id", type=int, default=1, help="Junction ID to simulate"
)
parser.add_argument(
    "--fail_lane", type=str, default=None, help="Lane to fail after 60s"
)
args = parser.parse_args()

JUNCTION_ID = args.junction_id
FAIL_LANE = args.fail_lane
START_TIME = time.time()

print("=" * 60)
print(f"🚦 FlexTraff MQTT Simulator")
print(f"   Junction ID : {JUNCTION_ID}")
print(f"   Fail Lane   : {FAIL_LANE or 'None (all lanes healthy)'}")
print(f"   Broker      : {BROKER}:{PORT}")
print(f"   Publish every {PUBLISH_INTERVAL}s per lane")
print("=" * 60)

running = True


def shutdown_handler(sig, frame):
    global running
    print("\n🛑 Shutting down simulator...")
    running = False
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)


# ============================================================================
# RFID SENDER Pi (× 4) — one per lane
# Publishes car count every 30s
# ============================================================================


def rfid_sender(lane_name: str):
    """Simulates one RFID-sender Pi for a specific lane"""
    client_id = f"rfid_{lane_name}_{uuid.uuid4().hex[:6]}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    topic = f"flextraff/junction_{JUNCTION_ID}/lane_{lane_name}/car_count"

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"[RFID-{lane_name:5}] ✅ Connected to broker")
        else:
            print(f"[RFID-{lane_name:5}] ❌ Connection failed (rc={rc})")

    def on_disconnect(c, userdata, rc):
        print(f"[RFID-{lane_name:5}] ⚠️  Disconnected (rc={rc})")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(BROKER, PORT, keepalive=120)
    client.loop_start()

    # Wait for connection
    time.sleep(2)

    while running:
        elapsed = time.time() - START_TIME

        # Simulate lane failure after 60s for the specified fail lane
        if FAIL_LANE == lane_name and elapsed > 60:
            print(
                f"[RFID-{lane_name:5}] 💀 SIMULATING FAILURE "
                f"— stopped publishing (elapsed={elapsed:.0f}s)"
            )
            # Stop publishing — backend watchdog should detect this within 60s
            time.sleep(PUBLISH_INTERVAL)
            continue

        # Simulate realistic car counts (random 0-80 per lane)
        count = random.randint(0, 80)

        payload = json.dumps(
            {
                "count": count,
                "timestamp": int(time.time()),
            }
        )

        result = client.publish(topic, payload, qos=1, retain=False)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[RFID-{lane_name:5}] 📤 Published count={count:3} → {topic}")
        else:
            print(f"[RFID-{lane_name:5}] ❌ Publish failed (rc={result.rc})")

        time.sleep(PUBLISH_INTERVAL)

    client.loop_stop()
    client.disconnect()


# ============================================================================
# SIGNAL RECEIVER Pi (× 4) — one per lane
# Subscribes and prints received green times
# ============================================================================


def signal_receiver(lane_name: str):
    """Simulates one signal-controller Pi for a specific lane"""
    client_id = f"sig_{lane_name}_{uuid.uuid4().hex[:6]}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    topic = f"flextraff/junction_{JUNCTION_ID}/lane_{lane_name}/green_time"

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            c.subscribe(topic, qos=1)
            print(f"[SIG -{lane_name:5}] ✅ Connected & subscribed → {topic}")
        else:
            print(f"[SIG -{lane_name:5}] ❌ Connection failed (rc={rc})")

    def on_message(c, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            green_time = data.get("green_time", "?")
            yellow_time = data.get("yellow_time", "?")
            mode = data.get("mode", "?")

            indicator = (
                "🟢" if mode == "dynamic" else "🟡" if mode == "manual" else "🔴"
            )
            print(
                f"[SIG -{lane_name:5}] {indicator} RECEIVED "
                f"green={green_time}s yellow={yellow_time}s mode={mode}"
            )
        except Exception as e:
            print(f"[SIG -{lane_name:5}] ❌ Message error: {e}")

    def on_disconnect(c, userdata, rc):
        print(f"[SIG -{lane_name:5}] ⚠️  Disconnected (rc={rc})")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(BROKER, PORT, keepalive=120)
    client.loop_forever()


# ============================================================================
# START ALL THREADS
# ============================================================================

threads = []

# Start 4 signal receivers first (they need to be ready before messages arrive)
for lane in LANE_NAMES:
    t = threading.Thread(target=signal_receiver, args=(lane,), daemon=True)
    t.start()
    threads.append(t)
    time.sleep(0.5)

print("\n⏳ Signal receivers started. Starting RFID senders in 3s...\n")
time.sleep(3)

# Start 4 RFID senders
for lane in LANE_NAMES:
    t = threading.Thread(target=rfid_sender, args=(lane,), daemon=True)
    t.start()
    threads.append(t)
    time.sleep(0.3)

print("\n🚀 All 8 simulated Pis running.")
if FAIL_LANE:
    print(f"⏳ Lane '{FAIL_LANE}' will stop publishing after 60s.")
    print(f"   Backend should mark it STATIC within 60s of last message.\n")

# Keep main thread alive
while running:
    time.sleep(1)
