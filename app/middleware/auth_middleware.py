import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.custom_auth_service import CustomAuthService

security = HTTPBearer()
logger = logging.getLogger(__name__)

# Lazy initialization of auth_service singleton
_auth_service = None

def get_auth_service() -> CustomAuthService:
    """Get or initialize the auth service singleton"""
    global _auth_service
    if _auth_service is None:
        _auth_service = CustomAuthService()
    return _auth_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        auth_service = get_auth_service()
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


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def require_operator_or_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require operator or admin role"""
    if current_user.get("role") not in ["admin", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required",
        )
    return current_user
