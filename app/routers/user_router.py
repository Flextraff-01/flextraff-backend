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
    AuditLogResponse,
    ChangePasswordRequest,
    JunctionAccessCreate,
    JunctionAccessResponse,
    LoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserDetailedResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="/api/v1/users", tags=["users"])
logger = logging.getLogger(__name__)

# Initialize service
user_service = UserManagementService()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@router.post("/login")
async def login(request: Request, credentials: LoginRequest):
    """
    Login with username and password
    """

    try:
        user = await user_service.authenticate_user(
            credentials.username, credentials.password
        )

        if not user:
            logger.warning(f"Failed login attempt for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # NEW: Check if 2FA is enabled
        if user.get("is_2fa_enabled"):
            return {
                "requires_2fa": True,
                "username": user["username"],
                "message": "Two-factor authentication required"
            }

        # Normal login (no 2FA)
        session = await user_service.create_session(
            user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )

@router.post("/login-2fa", response_model=TokenResponse)
async def login_with_2fa(request: Request, username: str, code: str):
    """
    Complete login using OTP
    """

    try:
        result = (
            user_service.supabase
            .table("users")
            .select("*")
            .eq("username", username)
            .eq("is_active", True)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        user = result.data[0]

        if not user.get("is_2fa_enabled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA not enabled for this user",
            )

        from app.services.two_factor.totp_service import TOTPService

        secret = user.get("totp_secret")

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA secret missing",
            )

        if not TOTPService.verify_code(secret, code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP code",
            )

        session = await user_service.create_session(
            user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA login failed",
        )


@router.post("/refresh-token", response_model=dict)
async def refresh_token(data: TokenRefreshRequest) -> dict:
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
async def logout(request: Request, user: dict = Depends(get_current_user)) -> dict:
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
async def get_current_user_profile(user: dict = Depends(get_current_user)) -> dict:
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
) -> dict:
    """
    Create a new user (admin only)
    
    Users cannot register themselves. Only admins can create users.
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

        # Log audit
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
) -> dict:
    """
    List all users (admin only)
    """
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
) -> dict:
    """
    Get user details with junction access (admin only)
    """
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
) -> dict:
    """
    Update user details (admin only)
    """
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

        # Log audit
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
) -> dict:
    """
    Change user password (admin only)
    """
    try:
        success = await user_service.change_password(
            user_id, password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Log audit
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


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Deactivate a user account (admin only)
    """
    try:
        success = await user_service.deactivate_user(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Log audit
        await user_service.log_audit(
            user_id=admin["id"],
            action="DEACTIVATE_USER",
            resource=f"user_{user_id}",
        )

        return {"message": "User deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user",
        )


# ============================================================================
# JUNCTION ACCESS MANAGEMENT ENDPOINTS
# ============================================================================


@router.get("/{user_id}/junctions")
async def get_user_junctions(
    user_id: int,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Get all junctions a user has access to (admin only)
    """
    try:
        junctions = user_service.get_user_junctions(user_id)

        return {
            "user_id": user_id,
            "junction_ids": junctions,
            "count": len(junctions),
        }
    except Exception as e:
        logger.error(f"Error fetching user junctions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user junctions",
        )


@router.post("/{user_id}/junctions/{junction_id}/grant-access")
async def grant_junction_access(
    user_id: int,
    junction_id: int,
    access_data: JunctionAccessCreate,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Grant a user access to a junction (admin only)
    
    Access levels:
    - OPERATOR: Can view and control the junction
    - OBSERVER: Can view the junction only
    """
    try:
        success = await user_service.grant_junction_access(
            user_id=user_id,
            junction_id=junction_id,
            access_level=access_data.access_level,
            granted_by_user_id=admin["id"],
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to grant junction access",
            )

        return {
            "message": f"Access granted to user {user_id} for junction {junction_id}",
            "access_level": access_data.access_level,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant junction access",
        )


@router.post("/{user_id}/junctions/{junction_id}/revoke-access")
async def revoke_junction_access(
    user_id: int,
    junction_id: int,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Revoke a user's access to a junction (admin only)
    """
    try:
        success = await user_service.revoke_junction_access(
            user_id=user_id,
            junction_id=junction_id,
            revoked_by_user_id=admin["id"],
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User access not found",
            )

        return {
            "message": f"Access revoked for user {user_id} from junction {junction_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking junction access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke junction access",
        )


@router.post("/{user_id}/junctions/bulk-grant")
async def bulk_grant_access(
    user_id: int,
    bulk_grant: AdminBulkAccessGrant,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Grant a user access to multiple junctions at once (admin only)
    """
    try:
        successful, failed = await user_service.bulk_grant_access(
            user_id=user_id,
            junction_ids=bulk_grant.junction_ids,
            access_level=bulk_grant.access_level,
            granted_by_user_id=admin["id"],
        )

        return {
            "message": "Bulk grant operation completed",
            "successful": successful,
            "failed": failed,
            "total": len(bulk_grant.junction_ids),
        }
    except Exception as e:
        logger.error(f"Error in bulk grant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk grant operation failed",
        )


@router.post("/{user_id}/junctions/bulk-revoke")
async def bulk_revoke_access(
    user_id: int,
    bulk_revoke: AdminBulkAccessRevoke,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Revoke a user's access to multiple junctions at once (admin only)
    """
    try:
        successful, failed = await user_service.bulk_revoke_access(
            user_id=user_id,
            junction_ids=bulk_revoke.junction_ids,
            revoked_by_user_id=admin["id"],
        )

        return {
            "message": "Bulk revoke operation completed",
            "successful": successful,
            "failed": failed,
            "total": len(bulk_revoke.junction_ids),
        }
    except Exception as e:
        logger.error(f"Error in bulk revoke: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk revoke operation failed",
        )
