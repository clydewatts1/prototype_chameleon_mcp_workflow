"""
RBAC (Role-Based Access Control) for Pilot Authorization (Phase 2)

Implements role-based permission enforcement for Pilot endpoints.
Ensures only authorized Pilots can invoke specific interventions.

Pilot Roles:
- ADMIN: Full access to all Pilot endpoints
- OPERATOR: Access to intervention endpoints (clarification, waive, etc.)
- VIEWER: Read-only access (future: view workflow status, history)

Constitutional Reference: Article XV (Pilot Sovereignty)
"""

from enum import Enum
from typing import Set, List, Optional
from functools import lru_cache

from loguru import logger


class PilotRole(str, Enum):
    """Pilot authorization roles."""
    
    ADMIN = "ADMIN"           # Full access
    OPERATOR = "OPERATOR"     # Standard operations
    VIEWER = "VIEWER"         # Read-only (future)


# Permission definitions per endpoint
ENDPOINT_PERMISSIONS = {
    # Kill switch: requires ADMIN (emergency authority)
    "/pilot/kill-switch": {PilotRole.ADMIN},
    
    # Clarification: OPERATOR+ (standard recovery)
    "/pilot/clarification": {PilotRole.ADMIN, PilotRole.OPERATOR},
    
    # Waiver: ADMIN only (override decisions)
    "/pilot/waive": {PilotRole.ADMIN},
    
    # Resume: OPERATOR+ (approve transitions)
    "/pilot/resume": {PilotRole.ADMIN, PilotRole.OPERATOR},
    
    # Cancel: OPERATOR+ (reject transitions)
    "/pilot/cancel": {PilotRole.ADMIN, PilotRole.OPERATOR},
}


class RBACError(Exception):
    """RBAC authorization error."""
    pass


class InsufficientPermissionsError(RBACError):
    """Pilot lacks required role for operation."""
    pass


class InvalidRoleError(RBACError):
    """Invalid or unknown role."""
    pass


class PilotAuthContext:
    """
    Authentication and authorization context for a Pilot request.
    
    Extracted from JWT claims during request processing.
    """
    
    def __init__(self, pilot_id: str, role: str):
        """
        Initialize Pilot auth context.
        
        Args:
            pilot_id: Pilot identifier (from JWT 'sub' claim)
            role: Pilot role (from JWT 'role' claim)
        """
        self.pilot_id = pilot_id
        
        # Validate role
        try:
            self.role = PilotRole(role)
        except ValueError:
            raise InvalidRoleError(f"Unknown role: {role}")
    
    def has_permission(self, endpoint: str) -> bool:
        """
        Check if Pilot has permission for endpoint.
        
        Args:
            endpoint: Endpoint path (e.g., "/pilot/kill-switch")
            
        Returns:
            True if authorized, False otherwise
        """
        required_roles = ENDPOINT_PERMISSIONS.get(endpoint)
        if required_roles is None:
            # Unknown endpoint - deny by default
            logger.warning(f"Unknown endpoint in RBAC check: {endpoint}")
            return False
        
        return self.role in required_roles
    
    def require_permission(self, endpoint: str) -> None:
        """
        Enforce permission check, raising if unauthorized.
        
        Args:
            endpoint: Endpoint path
            
        Raises:
            InsufficientPermissionsError: If not authorized
        """
        if not self.has_permission(endpoint):
            error_msg = (
                f"Pilot {self.pilot_id} lacks permission for {endpoint}. "
                f"Required role: {self._required_roles_for_endpoint(endpoint)}, "
                f"actual role: {self.role.value}"
            )
            logger.warning(error_msg)
            raise InsufficientPermissionsError(error_msg)
    
    def _required_roles_for_endpoint(self, endpoint: str) -> str:
        """Get human-readable required roles for endpoint."""
        required_roles = ENDPOINT_PERMISSIONS.get(endpoint, set())
        return "/".join(role.value for role in sorted(required_roles))
    
    def is_admin(self) -> bool:
        """Check if Pilot has ADMIN role."""
        return self.role == PilotRole.ADMIN
    
    def is_operator(self) -> bool:
        """Check if Pilot has OPERATOR role or higher."""
        return self.role in {PilotRole.ADMIN, PilotRole.OPERATOR}
    
    def is_viewer(self) -> bool:
        """Check if Pilot has at least VIEWER role."""
        return self.role in {PilotRole.ADMIN, PilotRole.OPERATOR, PilotRole.VIEWER}
    
    def __repr__(self):
        return f"PilotAuthContext(pilot_id={self.pilot_id}, role={self.role.value})"


def check_permission(auth_context: PilotAuthContext, endpoint: str) -> None:
    """
    Convenience function to check permission and raise if denied.
    
    Args:
        auth_context: Pilot authentication context
        endpoint: Endpoint path
        
    Raises:
        InsufficientPermissionsError: If not authorized
    """
    auth_context.require_permission(endpoint)


def log_authorization_attempt(
    pilot_id: str,
    endpoint: str,
    authorized: bool,
    role: Optional[str] = None,
) -> None:
    """
    Log authorization attempt for audit trail.
    
    Args:
        pilot_id: Pilot identifier
        endpoint: Endpoint attempted
        authorized: Whether authorization succeeded
        role: Pilot role (optional)
    """
    status = "ALLOWED" if authorized else "DENIED"
    logger.info(
        f"PILOT_AUTH: {status} | pilot_id={pilot_id} | endpoint={endpoint} | role={role or 'UNKNOWN'}"
    )
