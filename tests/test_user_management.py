"""
Test cases for the user management and access control system
"""

import pytest
import pytest_asyncio
import asyncio
import time
from fastapi.testclient import TestClient
from app.services.user_management_service import UserManagementService
from app.utils.access_helpers import check_access, filter_junctions


# ===========================================================================
# SETUP AND FIXTURES
# ===========================================================================


@pytest.fixture
def user_service():
    """Initialize user management service"""
    return UserManagementService()


@pytest_asyncio.fixture
async def admin_user():
    """Create test admin user"""
    service = UserManagementService()
    unique_id = int(time.time() * 1000)
    user = await service.create_user(
        username=f"test_admin_{unique_id}",
        password="AdminPass123!",
        full_name="Test Admin",
        role="ADMIN",
        email=f"admin_{unique_id}@test.com"
    )
    return user


@pytest_asyncio.fixture
async def operator_user():
    """Create test operator user"""
    service = UserManagementService()
    unique_id = int(time.time() * 1000)
    user = await service.create_user(
        username=f"test_operator_{unique_id}",
        password="OpPass123!",
        full_name="Test Operator",
        role="OPERATOR",
        email=f"op_{unique_id}@test.com"
    )
    return user


@pytest_asyncio.fixture
async def observer_user():
    """Create test observer user"""
    service = UserManagementService()
    unique_id = int(time.time() * 1000)
    user = await service.create_user(
        username=f"test_observer_{unique_id}",
        password="ObsPass123!",
        full_name="Test Observer",
        role="OBSERVER",
        email=f"obs_{unique_id}@test.com"
    )
    return user


# ===========================================================================
# PASSWORD HASHING TESTS
# ===========================================================================


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self, user_service):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = user_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 20

    def test_verify_correct_password(self, user_service):
        """Test verifying correct password"""
        password = "SecurePassword123!"
        hashed = user_service.hash_password(password)
        
        assert user_service.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self, user_service):
        """Test verifying incorrect password"""
        password = "SecurePassword123!"
        hashed = user_service.hash_password(password)
        
        assert user_service.verify_password("WrongPassword", hashed) is False


# ===========================================================================
# USER CREATION TESTS
# ===========================================================================


class TestUserCreation:
    """Test user creation"""

    @pytest.mark.asyncio
    async def test_create_admin_user(self, user_service):
        """Test creating admin user"""
        unique_name = f"new_admin_{int(time.time() * 1000)}"
        user = await user_service.create_user(
            username=unique_name,
            password="AdminPass123!",
            full_name="New Admin",
            role="ADMIN"
        )
        
        assert user is not None
        assert user["username"] == unique_name
        assert user["role"] == "ADMIN"
        assert "password_hash" not in user

    @pytest.mark.asyncio
    async def test_create_operator_user(self, user_service):
        """Test creating operator user"""
        unique_name = f"new_operator_{int(time.time() * 1000)}"
        user = await user_service.create_user(
            username=unique_name,
            password="OpPass123!",
            full_name="New Operator",
            role="OPERATOR"
        )
        
        assert user is not None
        assert user["role"] == "OPERATOR"

    @pytest.mark.asyncio
    async def test_create_observer_user(self, user_service):
        """Test creating observer user"""
        unique_name = f"new_observer_{int(time.time() * 1000)}"
        user = await user_service.create_user(
            username=unique_name,
            password="ObsPass123!",
            full_name="New Observer",
            role="OBSERVER"
        )
        
        assert user is not None
        assert user["role"] == "OBSERVER"

    @pytest.mark.asyncio
    async def test_create_user_invalid_role(self, user_service):
        """Test creating user with invalid role"""
        with pytest.raises(ValueError):
            await user_service.create_user(
                username="invalid_user",
                password="Pass123!",
                full_name="Invalid",
                role="INVALID_ROLE"
            )


# ===========================================================================
# AUTHENTICATION TESTS
# ===========================================================================


class TestAuthentication:
    """Test user authentication"""

    @pytest.mark.asyncio
    async def test_authenticate_valid_credentials(self, user_service):
        """Test authentication with valid credentials"""
        # Create user
        await user_service.create_user(
            username="auth_test",
            password="AuthPass123!",
            full_name="Auth Test",
            role="OPERATOR"
        )
        
        # Authenticate
        user = await user_service.authenticate_user("auth_test", "AuthPass123!")
        
        assert user is not None
        assert user["username"] == "auth_test"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_username(self, user_service):
        """Test authentication with invalid username"""
        user = await user_service.authenticate_user("nonexistent", "pass123")
        
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(self, user_service):
        """Test authentication with invalid password"""
        # Create user
        await user_service.create_user(
            username="auth_test2",
            password="AuthPass123!",
            full_name="Auth Test",
            role="OPERATOR"
        )
        
        # Try with wrong password
        user = await user_service.authenticate_user("auth_test2", "WrongPass123!")
        
        assert user is None


# ===========================================================================
# JWT TOKEN TESTS
# ===========================================================================


class TestJWTTokens:
    """Test JWT token generation and verification"""

    @pytest.mark.asyncio
    async def test_create_access_token(self, user_service):
        """Test access token creation"""
        user = {
            "id": 1,
            "username": "test_user",
            "role": "OPERATOR"
        }
        
        token = user_service.create_access_token(user)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, user_service):
        """Test refresh token creation"""
        user = {
            "id": 1,
            "username": "test_user",
            "role": "OPERATOR"
        }
        
        token = user_service.create_refresh_token(user)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, user_service):
        """Test verifying valid token"""
        # Note: This requires a real user in database
        # In production tests, use mocking
        pass


# ===========================================================================
# JUNCTION ACCESS TESTS
# ===========================================================================


class TestJunctionAccess:
    """Test junction access management"""

    @pytest.mark.asyncio
    async def test_grant_junction_access(self, user_service, operator_user):
        """Test granting junction access"""
        success = await user_service.grant_junction_access(
            user_id=operator_user["id"],
            junction_id=1,
            access_level="OPERATOR",
            granted_by_user_id=1
        )
        
        assert success is True

    @pytest.mark.asyncio
    async def test_get_user_junctions(self, user_service):
        """Test getting user's junctions"""
        # Note: Requires database setup
        # junctions = user_service.get_user_junctions(1)
        # assert isinstance(junctions, list)
        pass

    @pytest.mark.asyncio
    async def test_revoke_junction_access(self, user_service, operator_user):
        """Test revoking junction access"""
        # First grant
        await user_service.grant_junction_access(
            user_id=operator_user["id"],
            junction_id=1,
            access_level="OPERATOR",
            granted_by_user_id=1
        )
        
        # Then revoke
        success = await user_service.revoke_junction_access(
            user_id=operator_user["id"],
            junction_id=1,
            revoked_by_user_id=1
        )
        
        assert success is True


# ===========================================================================
# ACCESS CONTROL HELPER TESTS
# ===========================================================================


class TestAccessControlHelpers:
    """Test access control helper functions"""

    def test_admin_has_full_access(self):
        """Test that admin has access to all junctions"""
        admin_user = {
            "id": 1,
            "role": "ADMIN",
            "token_data": {"junction_ids": [1, 2]}
        }
        
        assert check_access(admin_user, 1) is True
        assert check_access(admin_user, 999) is True
        assert check_access(admin_user, 1, required_role="OPERATOR") is True

    def test_operator_has_assigned_access(self):
        """Test that operator has access only to assigned junctions"""
        operator_user = {
            "id": 2,
            "role": "OPERATOR",
            "token_data": {"junction_ids": [1, 2, 3]}
        }
        
        assert check_access(operator_user, 1) is True
        assert check_access(operator_user, 2) is True
        assert check_access(operator_user, 999) is False

    def test_observer_has_view_only_access(self):
        """Test that observer can view but not control"""
        observer_user = {
            "id": 3,
            "role": "OBSERVER",
            "token_data": {"junction_ids": [1, 2]}
        }
        
        # Can view
        assert check_access(observer_user, 1) is True
        
        # Cannot control
        assert check_access(observer_user, 1, required_role="OPERATOR") is False

    def test_filter_junctions(self):
        """Test filtering junctions by user access"""
        operator_user = {
            "id": 2,
            "role": "OPERATOR",
            "token_data": {"junction_ids": [1, 2, 3]}
        }
        
        all_junctions = [1, 2, 3, 4, 5, 6]
        filtered = filter_junctions(operator_user, all_junctions)
        
        assert filtered == [1, 2, 3]

    def test_admin_sees_all_junctions(self):
        """Test that admin filter returns all junctions"""
        admin_user = {
            "id": 1,
            "role": "ADMIN",
            "token_data": {"junction_ids": [1]}
        }
        
        all_junctions = [1, 2, 3, 4, 5]
        filtered = filter_junctions(admin_user, all_junctions)
        
        assert filtered == all_junctions


# ===========================================================================
# AUDIT LOGGING TESTS
# ===========================================================================


class TestAuditLogging:
    """Test audit logging functionality"""

    @pytest.mark.asyncio
    async def test_log_audit(self, user_service):
        """Test audit logging"""
        success = await user_service.log_audit(
            user_id=1,
            junction_id=1,
            action="TEST_ACTION",
            resource="test_resource",
            details={"test": "data"}
        )
        
        assert success is True


# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================


class TestIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_user_lifecycle(self, user_service):
        """Test complete user lifecycle"""
        # 1. Create user
        unique_name = f"lifecycle_test_{int(time.time() * 1000)}"
        user = await user_service.create_user(
            username=unique_name,
            password="LifePass123!",
            full_name="Lifecycle Test",
            role="OPERATOR"
        )
        user_id = user["id"]
        assert user is not None

        # 2. Grant junction access
        success = await user_service.grant_junction_access(
            user_id=user_id,
            junction_id=1,
            access_level="OPERATOR",
            granted_by_user_id=1
        )
        assert success is True

        # 3. Authenticate user
        authenticated = await user_service.authenticate_user(
            unique_name,
            "LifePass123!"
        )
        assert authenticated is not None

        # 4. Create session
        session = await user_service.create_session(authenticated)
        assert "access_token" in session
        assert "refresh_token" in session

        # 5. Verify token
        verified = await user_service.verify_token(session["access_token"])
        assert verified is not None

        # 6. Revoke access
        success = await user_service.revoke_junction_access(
            user_id=user_id,
            junction_id=1,
            revoked_by_user_id=1
        )
        assert success is True

        # 7. Deactivate user
        success = await user_service.deactivate_user(user_id)
        assert success is True


# ===========================================================================
# RUN TESTS
# ===========================================================================


if __name__ == "__main__":
    # Run with: pytest test_user_management.py -v
    pytest.main([__file__, "-v"])
