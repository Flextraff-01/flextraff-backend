"""
Controls API Endpoints
Handles manual override and automatic mode configuration for junctions
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.middleware.access_control import get_current_user, require_admin
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="/api/v1/controls", tags=["controls"])
logger = logging.getLogger(__name__)


def get_user_service():
    return UserManagementService()


# ── Pydantic models ───────────────────────────────────────────────────────────


class ManualConfig(BaseModel):
    lane_1_green_time: int
    lane_2_green_time: int
    lane_3_green_time: int
    lane_4_green_time: int
    yellow_time: int = 5


class AutoConfig(BaseModel):
    min_lane_time: int = 15
    max_lane_time: int = 90


# ============================================================================
# GET current config for a junction
# ============================================================================


@router.get("/{junction_id}")
async def get_junction_config(
    junction_id: int,
    user: dict = Depends(get_current_user),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Get current manual and auto config for a junction"""
    try:
        sb = user_service._get_supabase()

        # Get manual config
        manual = (
            sb.table("manual_signal_configs")
            .select("*")
            .eq("junction_id", junction_id)
            .limit(1)
            .execute()
        )

        # ✅ Get auto config from traffic_junctions
        auto = (
            sb.table("traffic_junctions")
            .select("id, min_time, max_time, base_cycle_time, yellow_light_duration")
            .eq("id", junction_id)
            .limit(1)
            .execute()
        )

        return {
            "junction_id": junction_id,
            "manual_config": manual.data[0] if manual.data else None,
            "auto_config": auto.data[0] if auto.data else None,
        }

    except Exception as e:
        logger.error(f"Error fetching junction config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch junction config",
        )


# ============================================================================
# MANUAL OVERRIDE
# ============================================================================


@router.post("/{junction_id}/manual")
async def set_manual_config(
    junction_id: int,
    config: ManualConfig,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Set manual signal config for a junction (admin only)"""
    try:
        sb = user_service._get_supabase()

        payload = {
            "junction_id": junction_id,
            "is_manual_mode": True,
            "lane_1_green_time": config.lane_1_green_time,
            "lane_2_green_time": config.lane_2_green_time,
            "lane_3_green_time": config.lane_3_green_time,
            "lane_4_green_time": config.lane_4_green_time,
            "yellow_time": config.yellow_time,
            "updated_by": admin["id"],
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Check if config already exists for this junction
        existing = (
            sb.table("manual_signal_configs")
            .select("id")
            .eq("junction_id", junction_id)
            .limit(1)
            .execute()
        )

        if existing.data:
            sb.table("manual_signal_configs").update(payload).eq(
                "junction_id", junction_id
            ).execute()
        else:
            sb.table("manual_signal_configs").insert(payload).execute()

        await user_service.log_audit(
            user_id=admin["id"],
            junction_id=junction_id,
            action="SET_MANUAL_OVERRIDE",
            resource=f"junction_{junction_id}",
            details={
                "lane_1": config.lane_1_green_time,
                "lane_2": config.lane_2_green_time,
                "lane_3": config.lane_3_green_time,
                "lane_4": config.lane_4_green_time,
                "yellow": config.yellow_time,
            },
        )

        return {
            "status": "success",
            "message": f"Manual override set for junction {junction_id}",
            "config": payload,
        }

    except Exception as e:
        logger.error(f"Error setting manual config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set manual config",
        )


# ============================================================================
# AUTOMATIC MODE
# ============================================================================


@router.post("/{junction_id}/auto")
async def set_auto_config(
    junction_id: int,
    config: AutoConfig,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Set automatic mode config for a junction (admin only)"""
    try:
        if config.min_lane_time >= config.max_lane_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_lane_time must be less than max_lane_time",
            )

        sb = user_service._get_supabase()

        result = (
            sb.table("traffic_junctions")
            .update(
                {
                    "min_time": config.min_lane_time,
                    "max_time": config.max_lane_time,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", junction_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Junction not found",
            )

        # Disable manual mode if it was active
        existing_manual = (
            sb.table("manual_signal_configs")
            .select("id")
            .eq("junction_id", junction_id)
            .limit(1)
            .execute()
        )

        if existing_manual.data:
            sb.table("manual_signal_configs").update(
                {
                    "is_manual_mode": False,
                    "updated_by": admin["id"],
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("junction_id", junction_id).execute()

        await user_service.log_audit(
            user_id=admin["id"],
            junction_id=junction_id,
            action="SET_AUTO_MODE",
            resource=f"junction_{junction_id}",
            details={
                "min_lane_time": config.min_lane_time,
                "max_lane_time": config.max_lane_time,
            },
        )

        return {
            "status": "success",
            "message": f"Automatic mode set for junction {junction_id}",
            "config": {
                "min_lane_time": config.min_lane_time,
                "max_lane_time": config.max_lane_time,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting auto config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set auto config",
        )


# ============================================================================
# DISABLE MANUAL OVERRIDE (switch back to auto)
# ============================================================================


@router.post("/{junction_id}/disable-manual")
async def disable_manual(
    junction_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Disable manual override and return to automatic mode"""
    try:
        sb = user_service._get_supabase()

        sb.table("manual_signal_configs").update(
            {
                "is_manual_mode": False,
                "updated_by": admin["id"],
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("junction_id", junction_id).execute()

        return {
            "status": "success",
            "message": f"Manual override disabled for junction {junction_id}",
        }

    except Exception as e:
        logger.error(f"Error disabling manual override: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable manual override",
        )
