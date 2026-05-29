"""
User Management Service
Handles user creation, authentication, and junction access control
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from supabase import Client, create_client

from app.config import settings


class UserManagementService:
    """
    User Management Service for FlexTraff
    
    Features:
    - User creation and management (admin only)
    - Username/password authentication
    - JWT token generation with junction access
    - Junction access control (users can only access assigned junctions)
    - Session management
    - Audit logging
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = not (
            settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY
        )
        self.supabase: Optional[Client] = None

        if not self.mock_mode:
            self.supabase = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
            )
        else:
            self.logger.warning(
                "UserManagementService initialized in mock mode "
                "(Supabase credentials not configured)"
            )

        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # JWT Settings
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    def _get_supabase(self) -> Client:
        """Return the initialized Supabase client or raise a clear error."""
        if self.supabase is None:
            raise RuntimeError(
                "User management service is running in mock mode because "
                "Supabase credentials are not configured"
            )
        return self.supabase

    # =========================================================================
    # PASSWORD HANDLING (ADMIN CONTROLLED)
    # =========================================================================

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    # =========================================================================
    # JUNCTION MANAGEMENT (ADMIN ONLY)
    # =========================================================================

    async def list_junctions(self, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """List all junctions with pagination"""
        try:
            count_result = self._get_supabase().table("traffic_junctions").select("id", count="exact").execute()
            total = count_result.count or 0
            result = (
                self._get_supabase()
                .table("traffic_junctions")
                .select("*")
                .order("id", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data or [], total
        except Exception as e:
            self.logger.error(f"Error listing junctions: {str(e)}")
            return [], 0

    async def get_junction_by_id(self, junction_id: int) -> Optional[Dict[str, Any]]:
        """Get junction by ID"""
        try:
            result = (
                self._get_supabase()
                .table("traffic_junctions")
                .select("*")
                .eq("id", junction_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Error fetching junction: {str(e)}")
            return None

    async def create_junction(
        self,
        junction_name: str,
        latitude: float,
        longitude: float,
        city: str,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new junction"""
        try:
            data = {
                "junction_name": junction_name,
                "latitude":      latitude,
                "longitude":     longitude,
                "location":      city,
            }
            if description:
                data["algorithm_config"] = description
            result = self._get_supabase().table("traffic_junctions").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Error creating junction: {str(e)}")
            return None

    async def update_junction(
        self,
        junction_id: int,
        junction_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update junction details"""
        try:
            data = {}
            if junction_name is not None: data["junction_name"] = junction_name
            if latitude      is not None: data["latitude"]      = latitude
            if longitude     is not None: data["longitude"]     = longitude
            if city          is not None: data["location"]      = city
            if description   is not None: data["algorithm_config"]   = description
            if is_active     is not None: data["is_active"]     = is_active
            if not data:
                return None
            result = (
                self._get_supabase()
                .table("traffic_junctions")
                .update(data)
                .eq("id", junction_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(f"Error updating junction: {str(e)}")
            return None

    async def delete_junction(self, junction_id: int) -> bool:
        """Delete a junction"""
        try:
            self._get_supabase().table("traffic_junctions").delete().eq("id", junction_id).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error deleting junction: {str(e)}")
            return False

    # =========================================================================
    # JUNCTION ACCESS MANAGEMENT
    # =========================================================================

    def get_user_junctions(self, user_id: int) -> List[int]:
        """Get all junctions a user has access to"""
        try:
            result = (
                self._get_supabase()
                .table("user_junctions")
                .select("junction_id")
                .eq("user_id", user_id)
                .execute()
            )
            return [row["junction_id"] for row in result.data] if result.data else []
        except Exception as e:
            self.logger.error(f"Error fetching user junctions for user {user_id}: {str(e)}")
            return []

    def get_user_junction_access(self, user_id: int, junction_id: int) -> Optional[Dict[str, Any]]:
        """Get specific junction access record for a user"""
        try:
            result = (
                self._get_supabase()
                .table("user_junctions")
                .select("*")
                .eq("user_id", user_id)
                .eq("junction_id", junction_id)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self.logger.error(
                f"Error fetching junction access for user {user_id}, junction {junction_id}: {str(e)}"
            )
            return None

    async def get_user_junctions_with_access_levels(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get all junctions a user has access to with their access levels"""
        try:
            result = (
                self._get_supabase()
                .table("user_junctions")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            if result.data is None:
                return None
            junction_ids  = [r["junction_id"] for r in result.data]
            access_levels = {r["junction_id"]: r["access_level"] for r in result.data}
            return {
                "user_id":       user_id,
                "junctions":     junction_ids,
                "access_levels": access_levels,
            }
        except Exception as e:
            self.logger.error(f"Error fetching user junctions with access levels: {str(e)}")
            return None

    async def grant_junction_access(
        self,
        user_id: int,
        junction_id: int,
        access_level: str,
        granted_by_user_id: int,
    ) -> bool:
        """Grant a user access to a junction"""
        try:
            existing = self.get_user_junction_access(user_id, junction_id)
            if existing:
                self._get_supabase().table("user_junctions").update(
                    {"access_level": access_level}
                ).eq("user_id", user_id).eq("junction_id", junction_id).execute()
                self.logger.info(f"Updated junction access for user {user_id} to junction {junction_id}: {access_level}")
            else:
                access_data = {
                    "user_id":      user_id,
                    "junction_id":  junction_id,
                    "access_level": access_level,
                    "granted_by":   granted_by_user_id,
                }
                self._get_supabase().table("user_junctions").insert(access_data).execute()
                self.logger.info(f"Granted junction access for user {user_id} to junction {junction_id}: {access_level}")

            await self.log_audit(
                user_id=granted_by_user_id,
                junction_id=junction_id,
                action="GRANT_ACCESS",
                resource=f"user_{user_id}",
                details={"access_level": access_level},
            )
            return True
        except Exception as e:
            self.logger.error(f"Error granting junction access: {str(e)}")
            return False

    async def grant_bulk_junction_access(
        self,
        user_id: int,
        junction_ids: List[int],
        access_level: str,
        granted_by: int,
    ) -> List[Dict[str, Any]]:
        """Grant a user access to multiple junctions"""
        results = []
        for junction_id in junction_ids:
            success = await self.grant_junction_access(
                user_id=user_id,
                junction_id=junction_id,
                access_level=access_level,
                granted_by_user_id=granted_by,
            )
            results.append({"junction_id": junction_id, "success": success})
        return results

    async def revoke_junction_access(
        self,
        user_id: int,
        junction_id: int,
        revoked_by_user_id: int,
    ) -> bool:
        """Revoke a user's access to a junction"""
        try:
            self._get_supabase().table("user_junctions").delete().eq(
                "user_id", user_id
            ).eq("junction_id", junction_id).execute()
            self.logger.info(f"Revoked junction access for user {user_id} from junction {junction_id}")
            await self.log_audit(
                user_id=revoked_by_user_id,
                junction_id=junction_id,
                action="REVOKE_ACCESS",
                resource=f"user_{user_id}",
            )
            return True
        except Exception as e:
            self.logger.error(f"Error revoking junction access: {str(e)}")
            return False

    async def revoke_bulk_junction_access(
        self,
        user_id: int,
        junction_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """Revoke a user's access to multiple junctions"""
        results = []
        for junction_id in junction_ids:
            success = await self.revoke_junction_access(
                user_id=user_id,
                junction_id=junction_id,
                revoked_by_user_id=user_id,
            )
            results.append({"junction_id": junction_id, "success": success})
        return results

    async def bulk_grant_access(
        self,
        user_id: int,
        junction_ids: List[int],
        access_level: str,
        granted_by_user_id: int,
    ) -> Tuple[int, int]:
        successful = 0
        failed = 0
        for junction_id in junction_ids:
            if await self.grant_junction_access(user_id, junction_id, access_level, granted_by_user_id):
                successful += 1
            else:
                failed += 1
        return successful, failed

    async def bulk_revoke_access(
        self,
        user_id: int,
        junction_ids: List[int],
        revoked_by_user_id: int,
    ) -> Tuple[int, int]:
        successful = 0
        failed = 0
        for junction_id in junction_ids:
            if await self.revoke_junction_access(user_id, junction_id, revoked_by_user_id):
                successful += 1
            else:
                failed += 1
        return successful, failed

    # =========================================================================
    # AUTHENTICATION
    # =========================================================================

    async def authenticate_user(self, username: str, password: str):
        try:
            print("\n=== LOGIN DEBUG START ===")
            print("Entered Username:", username)
            print("Entered Password:", password)

            result = (
                self._get_supabase()
                .table("users")
                .select("*")
                .eq("username", username)
                .eq("is_active", True)
                .execute()
            )

            print("DB RESULT:", result.data)

            if not result.data:
                print("❌ USER NOT FOUND")
                return None

            user = result.data[0]
            print("Stored Hash:", user["password_hash"])

            verify = self.verify_password(password, user["password_hash"])
            print("Password Verify Result:", verify)

            if not verify:
                print("❌ PASSWORD MISMATCH")
                return None

            print("✅ LOGIN SUCCESS")

            self._get_supabase().table("users").update(
                {"last_login": datetime.utcnow().isoformat()}
            ).eq("id", user["id"]).execute()

            return user

        except Exception as e:
            print("❌ ERROR:", str(e))
            return None

    # =========================================================================
    # JWT TOKEN CREATION
    # =========================================================================

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token with user data and junction access"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        junction_ids = self.get_user_junctions(user_data["id"])
        payload = {
            "sub":         str(user_data["id"]),
            "username":    user_data["username"],
            "role":        user_data["role"],
            "junction_ids": junction_ids,
            "exp":         expire,
            "type":        "access",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub":  str(user_data["id"]),
            "exp":  expire,
            "type": "refresh",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    async def create_session(
        self,
        user: Dict[str, Any],
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Create a new user session"""
        try:
            access_token  = self.create_access_token(user)
            refresh_token = self.create_refresh_token(user)
            session_token = secrets.token_urlsafe(32)

            session_data = {
                "user_id":       user["id"],
                "session_token": session_token,
                "refresh_token": refresh_token,
                "expires_at": (
                    datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
                ).isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }

            self._get_supabase().table("user_sessions").insert(session_data).execute()

            await self.log_audit(
                user_id=user["id"],
                action="LOGIN",
                resource="session",
                ip_address=ip_address,
            )

            return {
                "access_token":  access_token,
                "refresh_token": refresh_token,
                "session_token": session_token,
                "token_type":    "bearer",
                "expires_in":    self.access_token_expire_minutes * 60,
                "user": {
                    "id":        user["id"],
                    "username":  user["username"],
                    "full_name": user["full_name"],
                    "role":      user["role"],
                },
            }
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            raise

    # =========================================================================
    # TOKEN VERIFICATION
    # =========================================================================

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            if not user_id:
                return None
            result = (
                self._get_supabase()
                .table("users")
                .select("*")
                .eq("id", int(user_id))
                .eq("is_active", True)
                .execute()
            )
            if not result.data:
                return None
            user = result.data[0]
            user["token_data"] = payload
            return user
        except JWTError:
            return None
        except Exception as e:
            self.logger.error(f"Token verification error: {str(e)}")
            return None

    # =========================================================================
    # TOKEN REFRESH
    # =========================================================================

    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "refresh":
                return None
            user_id = payload.get("sub")
            session = (
                self._get_supabase()
                .table("user_sessions")
                .select("*")
                .eq("refresh_token", refresh_token)
                .eq("user_id", int(user_id))
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )
            if not session.data:
                return None
            user = (
                self._get_supabase()
                .table("users")
                .select("*")
                .eq("id", int(user_id))
                .eq("is_active", True)
                .execute()
            ).data[0]
            new_access_token = self.create_access_token(user)
            self._get_supabase().table("user_sessions").update(
                {"last_used": datetime.utcnow().isoformat()}
            ).eq("refresh_token", refresh_token).execute()
            return {
                "access_token": new_access_token,
                "token_type":   "bearer",
                "expires_in":   self.access_token_expire_minutes * 60,
            }
        except Exception:
            return None

    # =========================================================================
    # LOGOUT
    # =========================================================================

    async def logout(self, session_token: str, user_id: int) -> bool:
        """Logout user and invalidate session"""
        try:
            self._get_supabase().table("user_sessions").delete().eq(
                "session_token", session_token
            ).execute()
            await self.log_audit(user_id=user_id, action="LOGOUT", resource="session")
            return True
        except Exception as e:
            self.logger.error(f"Error logging out: {str(e)}")
            return False

    # =========================================================================
    # USER MANAGEMENT (ADMIN ONLY)
    # =========================================================================

    async def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: str,
        email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user (admin only)"""
        if role not in ["ADMIN", "OPERATOR", "OBSERVER"]:
            raise ValueError("Invalid role")

        password_hash = self.hash_password(password)
        user_data = {
            "username":      username,
            "password_hash": password_hash,
            "full_name":     full_name,
            "role":          role,
            "email":         email,
            "is_active":     True,
        }
        try:
            result = self._get_supabase().table("users").insert(user_data).execute()
            if not result.data:
                return None
            user = result.data[0]
            user.pop("password_hash", None)
            self.logger.info(f"Created user: {username} with role {role}")
            return user
        except Exception as e:
            self.logger.error(f"Error creating user: {str(e)}")
            return None

    async def update_user(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update user details"""
        try:
            update_data = {}
            if full_name is not None: update_data["full_name"] = full_name
            if email     is not None: update_data["email"]     = email
            if is_active is not None: update_data["is_active"] = is_active
            if role is not None and role in ["ADMIN", "OPERATOR", "OBSERVER"]:
                update_data["role"] = role
            if not update_data:
                return None
            result = self._get_supabase().table("users").update(update_data).eq("id", user_id).execute()
            if result.data:
                user = result.data[0]
                user.pop("password_hash", None)
                self.logger.info(f"Updated user {user_id}")
                return user
            return None
        except Exception as e:
            self.logger.error(f"Error updating user: {str(e)}")
            return None

    async def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password (admin only)"""
        try:
            password_hash = self.hash_password(new_password)
            self._get_supabase().table("users").update(
                {"password_hash": password_hash}
            ).eq("id", user_id).execute()
            self.logger.info(f"Password changed for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error changing password: {str(e)}")
            return False

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account"""
        try:
            self._get_supabase().table("users").update(
                {"is_active": False}
            ).eq("id", user_id).execute()
            self.logger.info(f"Deactivated user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deactivating user: {str(e)}")
            return False

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = (
                self._get_supabase()
                .table("users")
                .select("*")
                .eq("id", user_id)
                .execute()
            )
            if result.data:
                user = result.data[0]
                user.pop("password_hash", None)
                return user
            return None
        except Exception as e:
            self.logger.error(f"Error fetching user: {str(e)}")
            return None

    async def list_users(
        self, limit: int = 10, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List all users with pagination"""
        try:
            count_result = self._get_supabase().table("users").select("id", count="exact").execute()
            total = count_result.count or 0
            result = (
                self._get_supabase()
                .table("users")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            users = []
            for user in result.data:
                user.pop("password_hash", None)
                users.append(user)
            return users, total
        except Exception as e:
            self.logger.error(f"Error listing users: {str(e)}")
            return [], 0

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    async def log_audit(
        self,
        action: str,
        resource: str,
        user_id: Optional[int] = None,
        junction_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Log user action for audit purposes"""
        try:
            audit_data = {
                "user_id":     user_id,
                "junction_id": junction_id,
                "action":      action,
                "resource":    resource,
                "details":     details,
                "ip_address":  ip_address,
            }
            self._get_supabase().table("user_audit_logs").insert(audit_data).execute()
            return True
        except Exception as e:
            self.logger.error(f"Error logging audit: {str(e)}")
            return False