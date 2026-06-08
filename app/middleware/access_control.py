"""
Junction-level access control middleware
Ensures users can only access junctions they have been granted access to
"""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from app.middleware.auth_middleware import (
    get_current_user,
    get_optional_user,
    require_admin,
    require_operator_or_admin,
)

logger = logging.getLogger(__name__)


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
    if user.get("role", "").lower() == "admin":
        return []

    return user.get("token_data", {}).get("junction_ids", [])
