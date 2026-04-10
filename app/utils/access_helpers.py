"""
Access Control Helpers
Utilities for adding access control to existing API endpoints
"""

from fastapi import HTTPException, status
from typing import List, Optional


class JunctionAccessChecker:
    """Helper class for junction access validation"""

    @staticmethod
    def check_user_access(
        user: dict,
        junction_id: int,
        required_role: Optional[str] = None,
    ) -> bool:
        """
        Check if user has access to a junction
        
        Args:
            user: User data from JWT token
            junction_id: Junction ID to check access for
            required_role: Optional required role (OPERATOR, OBSERVER, ADMIN)
            
        Returns:
            bool: True if user has access
        """
        # ADMIN has access to everything
        if user.get("role") == "ADMIN":
            if required_role:
                return user.get("role") == required_role or required_role == "ADMIN"
            return True

        # Check junction access
        junction_ids = user.get("token_data", {}).get("junction_ids", [])
        
        if junction_id not in junction_ids:
            return False

        # Check role requirement if specified
        if required_role:
            user_role = user.get("role")
            if required_role == "OPERATOR" and user_role not in ["OPERATOR", "ADMIN"]:
                return False
            elif required_role == "OBSERVER" and user_role not in ["OBSERVER", "OPERATOR", "ADMIN"]:
                return False

        return True

    @staticmethod
    def assert_junction_access(
        user: dict,
        junction_id: int,
        required_role: Optional[str] = None,
    ) -> None:
        """
        Assert user has access to junction, raise HTTPException if not
        
        Args:
            user: User data from JWT token
            junction_id: Junction ID to check access for
            required_role: Optional required role
            
        Raises:
            HTTPException: If access denied
        """
        if not JunctionAccessChecker.check_user_access(user, junction_id, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to junction {junction_id}",
            )

    @staticmethod
    def filter_junctions(
        user: dict,
        junction_ids: List[int],
    ) -> List[int]:
        """
        Filter junction IDs to only those user has access to
        
        Args:
            user: User data from JWT token
            junction_ids: List of junction IDs to filter
            
        Returns:
            List[int]: Filtered junction IDs user has access to
        """
        # ADMIN has access to all
        if user.get("role") == "ADMIN":
            return junction_ids

        user_junctions = user.get("token_data", {}).get("junction_ids", [])
        return [jid for jid in junction_ids if jid in user_junctions]


# Quick helper functions
def check_access(user: dict, junction_id: int, required_role: Optional[str] = None) -> bool:
    """Quick access check"""
    # ADMIN bypasses all role requirements
    if user.get("role") == "ADMIN":
        return True
    return JunctionAccessChecker.check_user_access(user, junction_id, required_role)


def assert_access(user: dict, junction_id: int, required_role: Optional[str] = None) -> None:
    """Quick access assertion"""
    return JunctionAccessChecker.assert_junction_access(user, junction_id, required_role)


def filter_junctions(user: dict, junction_ids: List[int]) -> List[int]:
    """Quick junction filtering"""
    return JunctionAccessChecker.filter_junctions(user, junction_ids)
