"""
Pydantic models for user management and authentication
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """Model for creating a new user (admin only)"""
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(ADMIN|OPERATOR|OBSERVER)$")


class UserUpdate(BaseModel):
    """Model for updating user details"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(ADMIN|OPERATOR|OBSERVER)$")


class UserResponse(UserBase):
    """User response model (password excluded)"""
    id: int
    role: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailedResponse(UserResponse):
    """User response with junction access info"""
    junctions: List["JunctionAccessResponse"] = []

    class Config:
        from_attributes = True


# ============================================================================
# AUTHENTICATION MODELS
# ============================================================================


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Access token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Password change request (admin only)"""
    user_id: int
    new_password: str = Field(..., min_length=8)


# ============================================================================
# JUNCTION ACCESS MODELS
# ============================================================================


class JunctionAccessCreate(BaseModel):
    """Model for granting user access to a junction"""
    user_id: int
    junction_id: int
    access_level: str = Field(..., pattern="^(OPERATOR|OBSERVER)$")


class JunctionAccessUpdate(BaseModel):
    """Model for updating user access level"""
    access_level: str = Field(..., pattern="^(OPERATOR|OBSERVER)$")


class JunctionAccessResponse(BaseModel):
    """User's junction access response"""
    id: int
    junction_id: int
    access_level: str
    granted_at: datetime
    granted_by: Optional[int] = None


class UserJunctionsResponse(BaseModel):
    """User's accessible junctions"""
    user_id: int
    junctions: List[int]
    access_levels: dict  # {junction_id: access_level}


# ============================================================================
# AUDIT LOG MODELS
# ============================================================================


class AuditLogCreate(BaseModel):
    """Model for audit log entries"""
    user_id: Optional[int] = None
    junction_id: Optional[int] = None
    action: str
    resource: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None


class AuditLogResponse(AuditLogCreate):
    """Audit log response model"""
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ADMIN MODELS
# ============================================================================


class AdminBulkAccessGrant(BaseModel):
    """Model for granting access to multiple junctions"""
    user_id: int
    junction_ids: List[int]
    access_level: str = Field(..., pattern="^(OPERATOR|OBSERVER)$")


class AdminBulkAccessRevoke(BaseModel):
    """Model for revoking access to multiple junctions"""
    user_id: int
    junction_ids: List[int]


class UserListResponse(BaseModel):
    """Paginated user list response"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
