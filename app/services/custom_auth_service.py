import logging
import secrets
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from supabase import Client, create_client

from app.services.database_service import DatabaseService

# Load environment variables
load_dotenv()


class CustomAuthService:
    """
    Custom Username/Password Authentication Service for FlexTraff

    RULES:
    - Users CANNOT self-register
    - Passwords are ADMIN controlled
    - Roles allowed: OPERATOR, OBSERVER
    - Junction-level access enforced via JWT
    """

    def __init__(self):
        # Load env vars
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        
        # Determine if we're in mock mode (missing credentials)
        self.mock_mode = not (self.supabase_url and self.supabase_service_key and self.secret_key)
        
        self.logger = logging.getLogger("CustomAuthService")
        
        # Only initialize Supabase and database if credentials are available
        if not self.mock_mode:
            self.supabase: Client = create_client(
                self.supabase_url,
                self.supabase_service_key,
            )
            self.db_service = DatabaseService()
        else:
            self.supabase = None
            self.db_service = None
            self.logger.warning("CustomAuthService initialized in mock mode (Supabase credentials not configured)")

        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # JWT settings
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    # ------------------------------------------------------------------
    # PASSWORD HANDLING
    # ------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    # ------------------------------------------------------------------
    # JUNCTION ACCESS
    # ------------------------------------------------------------------

    def get_user_junctions(self, user_id: int) -> List[int]:
        result = (
            self.supabase
            .table("user_junctions")
            .select("junction_id")
            .eq("user_id", user_id)
            .execute()
        )
        return [row["junction_id"] for row in result.data] if result.data else []

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        try:
            result = (
                self.supabase
                .table("users")
                .select("*")
                .eq("username", username)
                .eq("is_active", True)
                .execute()
            )

            if not result.data:
                await self.db_service.log_system_event(
                    message=f"Login failed: user not found ({username})",
                    log_level="WARNING",
                    component="auth",
                )
                return None

            user = result.data[0]

            if not self.verify_password(password, user["password_hash"]):
                await self.db_service.log_system_event(
                    message=f"Login failed: invalid password ({username})",
                    log_level="WARNING",
                    component="auth",
                )
                return None

            # Update last login
            self.supabase.table("users").update(
                {"last_login": datetime.utcnow().isoformat()}
            ).eq("id", user["id"]).execute()

            await self.db_service.log_system_event(
                message=f"User logged in: {username}",
                component="auth",
            )

            return user

        except Exception as e:
            await self.db_service.log_system_event(
                message=f"Authentication error: {str(e)}",
                log_level="ERROR",
                component="auth",
            )
            return None

    # ------------------------------------------------------------------
    # JWT TOKEN CREATION
    # ------------------------------------------------------------------

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        expire = datetime.utcnow() + timedelta(
            minutes=self.access_token_expire_minutes
        )

        junction_ids = self.get_user_junctions(user_data["id"])

        payload = {
            "sub": str(user_data["id"]),
            "username": user_data["username"],
            "role": user_data["role"],
            "junction_ids": junction_ids,
            "exp": expire,
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        expire = datetime.utcnow() + timedelta(
            days=self.refresh_token_expire_days
        )

        payload = {
            "sub": str(user_data["id"]),
            "exp": expire,
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    # ------------------------------------------------------------------
    # SESSION MANAGEMENT
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:

        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        session_token = secrets.token_urlsafe(32)

        session_data = {
            "user_id": user["id"],
            "session_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": (
                datetime.utcnow()
                + timedelta(days=self.refresh_token_expire_days)
            ).isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        self.supabase.table("user_sessions").insert(session_data).execute()

        await self.db_service.log_system_event(
            message=f"Session created for user_id={user['id']}",
            component="auth_session",
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_token": session_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
            },
        }

    # ------------------------------------------------------------------
    # TOKEN VERIFICATION
    # ------------------------------------------------------------------

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            user_id = payload.get("sub")
            if not user_id:
                return None

            result = (
                self.supabase
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
            await self.db_service.log_system_event(
                message=f"Token verification error: {str(e)}",
                log_level="ERROR",
                component="auth",
            )
            return None

    # ------------------------------------------------------------------
    # TOKEN REFRESH
    # ------------------------------------------------------------------

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(
                refresh_token, self.secret_key, algorithms=[self.algorithm]
            )

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("sub")

            session = (
                self.supabase
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
                self.supabase
                .table("users")
                .select("*")
                .eq("id", int(user_id))
                .eq("is_active", True)
                .execute()
            ).data[0]

            new_access_token = self.create_access_token(user)

            self.supabase.table("user_sessions").update(
                {"last_used": datetime.utcnow().isoformat()}
            ).eq("refresh_token", refresh_token).execute()

            await self.db_service.log_system_event(
                message=f"Access token refreshed for user_id={user_id}",
                component="auth_session",
            )

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
            }

        except Exception:
            return None

    # ------------------------------------------------------------------
    # LOGOUT
    # ------------------------------------------------------------------

    async def logout(self, session_token: str) -> bool:
        try:
            self.supabase.table("user_sessions").delete().eq(
                "session_token", session_token
            ).execute()

            await self.db_service.log_system_event(
                message=f"User logged out (session revoked)",
                component="auth_session",
            )

            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # ADMIN: CREATE USER
    # ------------------------------------------------------------------

    async def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: str,
    ) -> Optional[Dict[str, Any]]:

        if role not in ["OPERATOR", "OBSERVER"]:
            raise ValueError("Invalid role")

        password_hash = self.hash_password(password)

        user_data = {
            "username": username,
            "password_hash": password_hash,
            "full_name": full_name,
            "role": role,
            "is_active": True,
        }

        result = self.supabase.table("users").insert(user_data).execute()

        if not result.data:
            return None

        await self.db_service.log_system_event(
            message=f"Admin created user: {username} ({role})",
            component="auth_admin",
        )

        user = result.data[0]
        user.pop("password_hash", None)
        return user
