"""
Pytest Configuration and Shared Fixtures

Provides:
1. MockGuardContext fixture for Phase 3 testing
2. Shared database and instance fixtures
3. Test configuration
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.persistence_service import GuardContext, ViolationPacket


class MockGuardContext(GuardContext):
    """
    Mock implementation of GuardContext for testing Phase 3 features.
    
    Allows tests to:
    - Control authorization results
    - Track emitted violations
    - Simulate pilot decisions
    - Verify Guard behavior
    """

    def __init__(self):
        """Initialize mock with default permissive behavior."""
        self.is_authorized_result = True
        self.violations_emitted: list = []
        self.pilot_approvals: Dict[str, Dict[str, Any]] = {}

    def is_authorized(
        self, actor_id: Optional[uuid.UUID], uow_id: uuid.UUID
    ) -> bool:
        """
        Return pre-configured authorization result.
        
        Allows tests to simulate both authorized and unauthorized scenarios.
        """
        return self.is_authorized_result

    def wait_for_pilot(
        self, uow_id: uuid.UUID, reason: str, timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Return pre-configured pilot decision.
        
        Tests can set different decisions for different UOWs using set_pilot_decision().
        """
        uow_key = str(uow_id)
        if uow_key in self.pilot_approvals:
            return self.pilot_approvals[uow_key]
        
        # Default: auto-approve
        return {
            "approved": True,
            "waiver_issued": False,
            "waiver_reason": None,
            "rejection_reason": None,
        }

    def emit_violation(self, packet: ViolationPacket) -> None:
        """
        Record violation packet for test assertions.
        
        Tests can call get_violations() to verify violations were emitted.
        """
        self.violations_emitted.append(packet)

    def get_violations(self) -> list:
        """
        Get list of violations emitted during test.
        
        Returns:
            List of ViolationPacket objects
        """
        return self.violations_emitted

    def set_authorized(self, value: bool) -> None:
        """
        Set whether future is_authorized() calls return True or False.
        
        Args:
            value: True to authorize, False to deny
        """
        self.is_authorized_result = value

    def set_pilot_decision(
        self, uow_id: uuid.UUID, decision: Dict[str, Any]
    ) -> None:
        """
        Set the pilot decision for a specific UOW.
        
        Args:
            uow_id: The UOW ID
            decision: Dict with keys: approved, waiver_issued, waiver_reason, rejection_reason
        
        Example:
            mock_guard.set_pilot_decision(
                uow_id=my_uow.uow_id,
                decision={
                    "approved": False,
                    "waiver_issued": False,
                    "rejection_reason": "Amount exceeds threshold"
                }
            )
        """
        self.pilot_approvals[str(uow_id)] = decision

    def clear_violations(self) -> None:
        """Clear the violations list (for multi-test scenarios)."""
        self.violations_emitted = []


@pytest.fixture
def mock_guard_context():
    """
    Provide a MockGuardContext fixture for all Phase 3 tests.
    
    Returns:
        MockGuardContext instance with default permissive behavior
    """
    return MockGuardContext()
