"""
User Management API Endpoints
Handles authentication, user management, and junction access control
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.middleware.access_control import get_current_user, require_admin
from app.models.user_models import (
    AdminBulkAccessGrant,
    AdminBulkAccessRevoke,
    ChangePasswordRequest,
    JunctionAccessCreate,
    LoginRequest,
    TokenRefreshRequest,
    UserCreate,
    UserDetailedResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user_management_service import UserManagementService


router = APIRouter(prefix="/api/v1/users", tags=["users"])
logger = logging.getLogger(__name__)

def get_user_service():
    return UserManagementService()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@router.post("/login")
async def login(
    request: Request,
    credentials: LoginRequest,
    user_service: UserManagementService = Depends(get_user_service)
):
    """
    Login with username and password
    """

    try:
        user = await user_service.authenticate_user(
            credentials.username,
            credentials.password
        )

        if not user:
            logger.warning(f"Failed login attempt for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # ==================================================
        # 2FA NOT ENABLED → FORCE SETUP
        # ==================================================
        if not user.get("is_2fa_enabled"):

            # Create temporary session token
            temp_session = await user_service.create_session(
                user,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            return {
                "requires_2fa_setup": True,
                "is_2fa_enabled": False,
                "username": user["username"],
                "temp_token": temp_session["access_token"],
                "message": "2FA setup required"
            }

        # ==================================================
        # 2FA ENABLED → VERIFY OTP
        # ==================================================
        return {
            "requires_2fa": True,
            "is_2fa_enabled": True,
            "username": user["username"],
            "message": "OTP verification required"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/refresh-token")
async def refresh_token(
    data: TokenRefreshRequest,
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Refresh access token using refresh token
    """

    try:
        result = await user_service.refresh_access_token(data.refresh_token)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout")
async def logout(
    request: Request,
    user: dict = Depends(get_current_user),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """
    Logout user and invalidate session
    """

    try:
        session_token = request.headers.get("X-Session-Token")

        if session_token:
            await user_service.logout(session_token, user["id"])

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================


@router.get("/me", response_model=UserDetailedResponse)
async def get_current_user_profile(
    user: dict = Depends(get_current_user),
    user_service: UserManagementService = Depends(get_user_service),
) -> dict:
    """Get current user's profile with junction access info"""

    try:
        user_data = await user_service.get_user_by_id(user["id"])

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        junctions = user_service.get_user_junctions(user["id"])
        user_data["junctions"] = [{"junction_id": j} for j in junctions]

        return user_data

    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile",
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
