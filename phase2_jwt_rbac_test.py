"""
Phase 2 JWT Authentication Testing Utilities

Quick test helpers to generate JWT tokens and verify RBAC enforcement.
"""

from chameleon_workflow_engine.jwt_utils import (
    create_token, JWTValidator, JWTConfig
)
from chameleon_workflow_engine.rbac import PilotAuthContext, PilotRole


def create_test_token(
    pilot_id: str = "pilot-admin-001",
    role: str = "ADMIN",
    expires_minutes: int = 60,
) -> str:
    """
    Create a test JWT token.
    
    Args:
        pilot_id: Pilot identifier
        role: Pilot role (ADMIN, OPERATOR, VIEWER)
        expires_minutes: Token lifetime
        
    Returns:
        JWT token string (ready to use in 'Authorization: Bearer <token>' header)
    """
    return create_token(pilot_id, role, expires_minutes)


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded claims dict
    """
    config = JWTConfig()
    validator = JWTValidator(config)
    
    return validator.decode_token(token)


def test_rbac_permissions():
    """Test RBAC enforcement."""
    print("\n=== RBAC Permission Tests ===\n")
    
    # Test ADMIN role
    admin_auth = PilotAuthContext("admin-001", "ADMIN")
    print(f"Admin auth: {admin_auth}")
    print(f"  Can kill-switch: {admin_auth.has_permission('/pilot/kill-switch')}")
    print(f"  Can clarify: {admin_auth.has_permission('/pilot/clarification')}")
    print(f"  Can waive: {admin_auth.has_permission('/pilot/waive')}")
    print(f"  Can resume: {admin_auth.has_permission('/pilot/resume')}")
    print(f"  Can cancel: {admin_auth.has_permission('/pilot/cancel')}")
    
    # Test OPERATOR role
    print()
    operator_auth = PilotAuthContext("operator-001", "OPERATOR")
    print(f"Operator auth: {operator_auth}")
    print(f"  Can kill-switch: {operator_auth.has_permission('/pilot/kill-switch')}")
    print(f"  Can clarify: {operator_auth.has_permission('/pilot/clarification')}")
    print(f"  Can waive: {operator_auth.has_permission('/pilot/waive')}")
    print(f"  Can resume: {operator_auth.has_permission('/pilot/resume')}")
    print(f"  Can cancel: {operator_auth.has_permission('/pilot/cancel')}")
    
    # Test VIEWER role
    print()
    viewer_auth = PilotAuthContext("viewer-001", "VIEWER")
    print(f"Viewer auth: {viewer_auth}")
    print(f"  Can kill-switch: {viewer_auth.has_permission('/pilot/kill-switch')}")
    print(f"  Can clarify: {viewer_auth.has_permission('/pilot/clarification')}")
    print(f"  Can waive: {viewer_auth.has_permission('/pilot/waive')}")
    print(f"  Can resume: {viewer_auth.has_permission('/pilot/resume')}")
    print(f"  Can cancel: {viewer_auth.has_permission('/pilot/cancel')}")


def generate_test_tokens():
    """Generate test tokens for different roles."""
    print("\n=== Test JWT Tokens ===\n")
    
    admin_token = create_test_token("pilot-admin", "ADMIN")
    operator_token = create_test_token("pilot-operator", "OPERATOR")
    viewer_token = create_test_token("pilot-viewer", "VIEWER")
    
    print("ADMIN Token:")
    print(f"  {admin_token}\n")
    
    print("OPERATOR Token:")
    print(f"  {operator_token}\n")
    
    print("VIEWER Token:")
    print(f"  {viewer_token}\n")
    
    print("Usage: curl -H 'Authorization: Bearer <token>' http://localhost:8000/pilot/kill-switch")
    
    return {
        "admin": admin_token,
        "operator": operator_token,
        "viewer": viewer_token,
    }


if __name__ == "__main__":
    print("Phase 2 JWT & RBAC Testing Utilities\n")
    print("=" * 50)
    
    # Show RBAC permissions matrix
    test_rbac_permissions()
    
    # Generate test tokens
    tokens = generate_test_tokens()
    
    print("\n" + "=" * 50)
    print("\nPhase 2 JWT Authentication Ready!")
    print("  • JWT token creation")
    print("  • RBAC role-based access control")
    print("  • All 5 Pilot endpoints with role enforcement")
