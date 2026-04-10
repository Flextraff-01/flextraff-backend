import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


class DatabaseService:
    """
    Supabase Database Service for FlexTraff ATCS Backend
    Handles all database operations including system logging
    """

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase = None

        self.logger = logging.getLogger("DatabaseService")
        self.logger.setLevel(logging.INFO)

        if not self.supabase_url or not self.supabase_service_key:
            self.logger.warning(
                "Supabase credentials not configured - using mock mode for testing"
            )
            return

        self.supabase: Client = create_client(
            self.supabase_url, self.supabase_service_key
        )

        self.logger.info("✅ DatabaseService initialized")

    # ------------------------------------------------------------------
    # 🔥 SYSTEM LOGGING (SAFE + ASYNC FIXED)
    # ------------------------------------------------------------------

    async def log_system_event(
        self,
        message: str,
        log_level: str = "INFO",
        component: str = "backend",
        junction_id: Optional[int] = None,
    ) -> None:
        """
        Insert system log into system_logs table
        NEVER raises exception (logging must be safe)
        """
        try:
            log_data = {
                "log_level": log_level,
                "component": component,
                "message": message,
                "junction_id": junction_id,
            }

            await asyncio.to_thread(
                lambda: self.supabase.table("system_logs")
                .insert(log_data)
                .execute()
            )

        except Exception as e:
            # Logging should never crash the system
            self.logger.error(f"❌ Failed to insert system log: {e}")

    async def log_system_error(
        self,
        error_message: str,
        error_type: str = "SYSTEM_ERROR",
        component: str = "backend",
        junction_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log system errors or crashes with additional metadata
        NEVER raises exception (logging must be safe)
        """
        try:
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "log_level": "ERROR",
                "component": component,
                "message": f"{error_type}: {error_message}",
                "junction_id": junction_id,
                "metadata": metadata or {},
            }

            self.supabase.table("system_logs").insert(log_data).execute()

        except Exception as e:
            # Logging should never crash the system
            self.logger.error(f"❌ Failed to insert error log: {e}")

    # ------------------------------------------------------------------
    # � RFID SCANNER LOGS (NEW)
    # ------------------------------------------------------------------

    async def log_rfid_scanner_data(
        self,
        junction_id: int,
        cycle_id: int,
        lane_car_count: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Log RFID scanner data (car counts and cycle ID) for user visibility
        
        Args:
            junction_id: ID of the junction
            cycle_id: ID of the traffic cycle
            lane_car_count: Dict with keys 'north', 'south', 'east', 'west' containing car counts
        
        Returns:
            The inserted record data
        """
        try:
            log_data = {
                "junction_id": junction_id,
                "cycle_id": cycle_id,
                "lane_car_count": lane_car_count,
                "log_timestamp": datetime.utcnow().isoformat(),
            }

            result = (
                self.supabase.table("rfid_scanners")
                .insert(log_data)
                .execute()
            )

            if not result.data:
                raise Exception("No data returned from insert")

            await self.log_system_event(
                message=f"RFID scanner log created | cycle_id={cycle_id} | counts={lane_car_count}",
                component="rfid_scanner",
                junction_id=junction_id,
            )

            return result.data[0]

        except Exception as e:
            await self.log_system_error(
                error_message=str(e),
                error_type="RFID_LOGGING_ERROR",
                component="rfid_scanner",
                junction_id=junction_id,
                metadata={"cycle_id": cycle_id, "lane_car_count": lane_car_count},
            )
            raise

    # ------------------------------------------------------------------
    # �🚗 VEHICLE DETECTIONS
    # ------------------------------------------------------------------

    async def log_vehicle_detection(
        self,
        junction_id: int,
        lane_number: int,
        fastag_id: str,
        vehicle_type: str = "car",
    ) -> Dict[str, Any]:
        try:
            detection_data = {
                "junction_id": junction_id,
                "lane_number": lane_number,
                "fastag_id": fastag_id,
                "vehicle_type": vehicle_type,
                "processing_status": "processed",
            }

            result = await asyncio.to_thread(
                lambda: self.supabase.table("vehicle_detections")
                .insert(detection_data)
                .execute()
            )

            if not result.data:
                raise Exception("No data returned from insert")

            await self.log_system_event(
                message=f"Vehicle detected | FASTag={fastag_id} | lane={lane_number}",
                component="vehicle_detection",
                junction_id=junction_id,
            )

            return result.data[0]

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="vehicle_detection",
                junction_id=junction_id,
            )
            raise

    # ------------------------------------------------------------------
    # 🚦 TRAFFIC CYCLES
    # ------------------------------------------------------------------

    async def log_traffic_cycle(
        self,
        junction_id: int,
        lane_counts: List[int],
        green_times: List[int],
        cycle_time: int,
        calculation_time_ms: int,
    ) -> Dict[str, Any]:
        try:
            cycle_data = {
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
                "calculation_time_ms": calculation_time_ms,
            }

            result = await asyncio.to_thread(
                lambda: self.supabase.table("traffic_cycles")
                .insert(cycle_data)
                .execute()
            )

            if not result.data:
                raise Exception("No data returned from insert")

            await self.log_system_event(
                message=(
                    f"Traffic cycle calculated | "
                    f"cycle={cycle_time}s | vehicles={sum(lane_counts)}"
                ),
                component="traffic_calculator",
                junction_id=junction_id,
            )

            return result.data[0]

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="traffic_calculator",
                junction_id=junction_id,
            )
            raise

    # ------------------------------------------------------------------
    # 📊 QUERIES
    # ------------------------------------------------------------------

    async def get_current_lane_counts(
        self, junction_id: int, time_window_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        try:
            time_threshold = (
                datetime.utcnow() - timedelta(minutes=time_window_minutes)
            ).isoformat()

            result = await asyncio.to_thread(
                lambda: self.supabase.table("vehicle_detections")
                .select("lane_number")
                .eq("junction_id", junction_id)
                .gte("detection_timestamp", time_threshold)
                .execute()
            )

            lane_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            lane_names = {1: "North", 2: "South", 3: "East", 4: "West"}

            for row in result.data:
                ln = row["lane_number"]
                if ln in lane_counts:
                    lane_counts[ln] += 1

            return [
                {
                    "lane": lane_names[i],
                    "lane_number": i,
                    "count": lane_counts[i],
                }
                for i in range(1, 5)
            ]

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="lane_count_query",
                junction_id=junction_id,
            )
            return []

    async def get_vehicles_count_by_date(
        self, junction_id: int, target_date: date
    ) -> int:
        try:
            start = target_date.isoformat()
            end = (target_date + timedelta(days=1)).isoformat()

            result = await asyncio.to_thread(
                lambda: self.supabase.table("vehicle_detections")
                .select("id", count="exact")
                .eq("junction_id", junction_id)
                .gte("detection_timestamp", start)
                .lt("detection_timestamp", end)
                .execute()
            )

            return result.count or 0

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="vehicle_count_query",
                junction_id=junction_id,
            )
            return 0

    async def get_current_traffic_cycle(
        self, junction_id: int
    ) -> Optional[Dict[str, Any]]:
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase.table("traffic_cycles")
                .select("*")
                .eq("junction_id", junction_id)
                .order("cycle_start_time", desc=True)
                .limit(1)
                .execute()
            )

            return result.data[0] if result.data else None

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="traffic_cycle_query",
                junction_id=junction_id,
            )
            return None

    async def get_all_junctions(self) -> List[Dict[str, Any]]:
        try:
            result = await asyncio.to_thread(
                lambda: self.supabase.table("traffic_junctions")
                .select("*")
                .eq("status", "active")
                .order("junction_name")
                .execute()
            )

            return result.data or []

        except Exception as e:
            await self.log_system_event(
                message=str(e),
                log_level="ERROR",
                component="junction_query",
            )
            return []

    # ------------------------------------------------------------------
    # ❤️ HEALTH
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        try:
            await asyncio.to_thread(
                lambda: self.supabase.table("traffic_junctions")
                .select("id")
                .limit(1)
                .execute()
            )

            return {
                "database_connected": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
