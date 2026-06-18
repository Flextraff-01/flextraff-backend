"""
Admin Management API Endpoints
Handles junction management and user-junction access allocation
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.access_control import require_admin
from app.models.user_models import (
    AdminBulkAccessGrant,
    AdminBulkAccessRevoke,
    ChangePasswordRequest,
    JunctionAccessCreate,
    JunctionAccessResponse,
    UserCreate,
    UserDetailedResponse,
    UserJunctionsResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user_management_service import UserManagementService


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def get_user_service():
    return UserManagementService()


# ============================================================================
# JUNCTION MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/junctions", status_code=status.HTTP_201_CREATED)
async def create_junction(
    junction_data: dict,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Create a new junction (admin only)
    
    Required fields:
    - junction_name: str
    - latitude: float
    - longitude: float
    - city: str
    """

    try:
        # Validate required fields
        required_fields = ["junction_name", "latitude", "longitude", "city"]
        if not all(field in junction_data for field in required_fields):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(required_fields)}",
            )

        junction = await user_service.create_junction(
            junction_name=junction_data.get("junction_name"),
            latitude=junction_data.get("latitude"),
            longitude=junction_data.get("longitude"),
            city=junction_data.get("city"),
            description=junction_data.get("description"),
        )

        if not junction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create junction",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="CREATE_JUNCTION",
            resource=f"junction_{junction['id']}",
            details={
                "junction_name": junction_data.get("junction_name"),
                "city": junction_data.get("city"),
            },
        )

        return {
            "status": "success",
            "junction": junction,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating junction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create junction",
        )


@router.get("/junctions")
async def list_junctions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    List all junctions with pagination (admin only)
    """

    try:
        junctions, total = await user_service.list_junctions(
            limit=limit, offset=offset
        )

        return {
            "junctions": junctions,
            "total": total,
            "page": offset // limit + 1,
            "page_size": limit,
        }

    except Exception as e:
        logger.error(f"Error listing junctions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list junctions",
        )


@router.get("/junctions/{junction_id}")
async def get_junction(
    junction_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Get junction details by ID (admin only)
    """

    try:
        junction = await user_service.get_junction_by_id(junction_id)

        if not junction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Junction not found",
            )

        return junction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching junction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch junction",
        )


@router.put("/junctions/{junction_id}")
async def update_junction(
    junction_id: int,
    junction_update: dict,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Update junction details (admin only)
    """

    try:
        junction = await user_service.update_junction(
            junction_id=junction_id,
            junction_name=junction_update.get("junction_name"),
            latitude=junction_update.get("latitude"),
            longitude=junction_update.get("longitude"),
            city=junction_update.get("city"),
            description=junction_update.get("description"),
            is_active=junction_update.get("is_active"),
        )

        if not junction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Junction not found",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="UPDATE_JUNCTION",
            resource=f"junction_{junction_id}",
            details=junction_update,
        )

        return {
            "status": "success",
            "junction": junction,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating junction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update junction",
        )


@router.delete("/junctions/{junction_id}")
async def delete_junction(
    junction_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Delete a junction (admin only)
    """

    try:
        success = await user_service.delete_junction(junction_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Junction not found",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="DELETE_JUNCTION",
            resource=f"junction_{junction_id}",
        )

        return {
            "status": "success",
            "message": f"Junction {junction_id} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting junction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete junction",
        )


# ============================================================================
# USER-JUNCTION ALLOCATION ENDPOINTS
# ============================================================================

@router.post("/users/{user_id}/junctions/bulk")
async def grant_bulk_junction_access(
    user_id: int,
    access_data: AdminBulkAccessGrant,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Grant user access to multiple junctions (admin only)
    """

    try:
        # Verify user_id matches
        if access_data.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID mismatch",
            )

        results = await user_service.grant_bulk_junction_access(
            user_id=user_id,
            junction_ids=access_data.junction_ids,
            access_level=access_data.access_level,
            granted_by=admin["id"],
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to grant junction access",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="GRANT_BULK_JUNCTION_ACCESS",
            resource=f"user_{user_id}",
            details={
                "junction_ids": access_data.junction_ids,
                "access_level": access_data.access_level,
                "count": len(access_data.junction_ids),
            },
        )

        return {
            "status": "success",
            "message": f"Access granted to {len(access_data.junction_ids)} junctions",
            "granted_junctions": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting bulk junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant junction access",
        )

@router.post("/users/{user_id}/junctions")
async def grant_junction_access(
    user_id: int,
    access_data: JunctionAccessCreate,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Grant user access to a single junction (admin only)
    """

    try:
        access = await user_service.grant_junction_access(
            user_id=user_id,
            junction_id=access_data.junction_id,
            access_level=access_data.access_level,
            granted_by_user_id=admin["id"],
        )

        if not access:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to grant junction access",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="GRANT_JUNCTION_ACCESS",
            resource=f"user_{user_id}",
            details={
                "junction_id": access_data.junction_id,
                "access_level": access_data.access_level,
            },
        )

        return {
            "status": "success",
            "message": f"Access granted to junction {access_data.junction_id}",
            "access": access,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant junction access",
        )


@router.delete("/users/{user_id}/junctions/{junction_id}")
async def revoke_junction_access(
    user_id: int,
    junction_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Revoke user access to a single junction (admin only)
    """

    try:
        success = await user_service.revoke_junction_access(user_id, junction_id, revoked_by_user_id=admin["id"],)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User-junction access not found",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="REVOKE_JUNCTION_ACCESS",
            resource=f"user_{user_id}",
            details={"junction_id": junction_id},
        )

        return {
            "status": "success",
            "message": f"Access revoked from junction {junction_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke junction access",
        )


@router.post("/users/{user_id}/junctions/revoke-bulk")
async def revoke_bulk_junction_access(
    user_id: int,
    access_data: AdminBulkAccessRevoke,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Revoke user access to multiple junctions (admin only)
    """

    try:
        # Verify user_id matches
        if access_data.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID mismatch",
            )

        results = await user_service.revoke_bulk_junction_access(
            user_id=user_id,
            junction_ids=access_data.junction_ids,
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke junction access",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="REVOKE_BULK_JUNCTION_ACCESS",
            resource=f"user_{user_id}",
            details={
                "junction_ids": access_data.junction_ids,
                "count": len(access_data.junction_ids),
            },
        )

        return {
            "status": "success",
            "message": f"Access revoked from {len(access_data.junction_ids)} junctions",
            "revoked_junctions": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking bulk junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke junction access",
        )


@router.get("/users/{user_id}/junctions", response_model=UserJunctionsResponse)
async def get_user_junction_access(
    user_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Get all junctions accessible by a user (admin only)
    """

    try:
        junctions = await user_service.get_user_junctions_with_access_levels(user_id)

        if junctions is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return junctions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user junction access",
        )



# ============================================================================
# ADMIN: USER MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Create a new user (admin only)
    """

    try:
        user = await user_service.create_user(
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            role=user_data.role,
            email=user_data.email,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="CREATE_USER",
            resource=f"user_{user['id']}",
            details={"username": user_data.username, "role": user_data.role},
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get("/", response_model=UserListResponse)
async def list_users(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:

    try:
        users, total = await user_service.list_users(limit=limit, offset=offset)

        return {
            "users": users,
            "total": total,
            "page": offset // limit + 1,
            "page_size": limit,
        }

    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get("/{user_id}", response_model=UserDetailedResponse)
async def get_user(
    user_id: int,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        junctions = user_service.get_user_junctions(user_id)
        user["junctions"] = [{"junction_id": j} for j in junctions]

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:

    try:
        user = await user_service.update_user(
            user_id=user_id,
            full_name=user_update.full_name,
            email=user_update.email,
            is_active=user_update.is_active,
            role=user_update.role,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="UPDATE_USER",
            resource=f"user_{user_id}",
            details=user_update.dict(exclude_none=True),
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.post("/{user_id}/change-password")
async def change_password(
    user_id: int,
    password_data: ChangePasswordRequest,
    admin: dict = Depends(require_admin),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:

    try:
        success = await user_service.change_password(
            user_id,
            password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        await user_service.log_audit(
            user_id=admin["id"],
            action="CHANGE_PASSWORD",
            resource=f"user_{user_id}",
        )

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )