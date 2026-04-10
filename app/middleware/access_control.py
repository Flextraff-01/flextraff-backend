"""
Junction-level access control middleware
Ensures users can only access junctions they have been granted access to
"""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.custom_auth_service import CustomAuthService

security = HTTPBearer()
auth_service = CustomAuthService()
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        user_data = await auth_service.verify_token(token)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication middleware error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Optional authentication for public endpoints"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# This function can be used to delete junction ids or update info only by the admins and will give error to regular users.
async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require ADMIN role"""
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def require_operator_or_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require OPERATOR or ADMIN role"""
    role = user.get("role")
    if role not in ["ADMIN", "OPERATOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required",
        )
    return user


async def check_junction_access(
    user: dict = Depends(get_current_user),
    junction_id: int = None,
) -> dict:
    """
    Verify user has access to the specified junction.
    
    Args:
        user: Current authenticated user
        junction_id: Junction ID to check access for
        
    Returns:
        dict: User data if authorized
        
    Raises:
        HTTPException: If user doesn't have access to the junction
    """
    if not junction_id:
        return user

    # ADMIN has access to all junctions
    if user.get("role") == "ADMIN":
        return user

    # Check if user has access to this junction
    junction_ids = user.get("token_data", {}).get("junction_ids", [])
    
    if junction_id not in junction_ids:
        logger.warning(
            f"Access denied: User {user.get('id')} attempting to access junction {junction_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have access to junction {junction_id}",
        )

    return user


async def filter_user_junctions(
    user: dict = Depends(get_current_user),
) -> List[int]:
    """
    Get list of junctions the user has access to.
    
    Args:
        user: Current authenticated user
        
    Returns:
        List[int]: List of junction IDs user can access
    """
    # ADMIN has access to all junctions - return empty list to indicate all
    if user.get("role") == "ADMIN":
        return []

    return user.get("token_data", {}).get("junction_ids", [])
