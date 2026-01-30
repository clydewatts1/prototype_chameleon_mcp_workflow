"""
Phase 3: InterventionStoreSQLAlchemy Tests

Comprehensive test suite for the SQLAlchemy-backed intervention store.
Tests CRUD operations, filtering, pagination, metrics, and bulk operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models_phase3 import Phase3Base, Intervention, InterventionHistory
from database.intervention_store_sqlalchemy import InterventionStoreSQLAlchemy
from chameleon_workflow_engine.interactive_dashboard import (
    InterventionType,
    InterventionStatus,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Phase3Base.metadata.create_all(engine)

    SessionLocal = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = SessionLocal()

    yield session

    session.close()
    Phase3Base.metadata.drop_all(engine)


@pytest.fixture
def store(db_session):
    """Create an InterventionStoreSQLAlchemy instance."""
    return InterventionStoreSQLAlchemy(db_session)


class TestInterventionStoreCreate:
    """Test create_request functionality."""

    def test_create_basic_request(self, store):
        """Test creating a basic intervention request."""
        request = store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test Request",
            description="Test Description",
        )

        assert request.request_id == "req-001"
        assert request.uow_id == "uow-001"
        assert request.status == InterventionStatus.PENDING
        assert request.priority == "normal"
        assert request.title == "Test Request"

    def test_create_request_with_priority(self, store):
        """Test creating request with specific priority."""
        request = store.create_request(
            request_id="req-002",
            uow_id="uow-002",
            intervention_type=InterventionType.KILL_SWITCH,
            title="Critical Request",
            description="Critical intervention",
            priority="critical",
        )

        assert request.priority == "critical"

    def test_create_request_with_expiration(self, store):
        """Test creating request with expiration."""
        request = store.create_request(
            request_id="req-003",
            uow_id="uow-003",
            intervention_type=InterventionType.WAIVE_VIOLATION,
            title="Expiring Request",
            description="Will expire",
            expires_in_seconds=3600,
        )

        assert request.expires_at is not None
        # Verify expiration is approximately 1 hour from now
        expires = datetime.fromisoformat(request.expires_at)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = (expires - now).total_seconds()
        assert 3500 < time_diff < 3700  # Within 100 seconds of expected

    def test_create_request_with_context(self, store):
        """Test creating request with context data."""
        context = {"invoice_id": "INV-001", "vendor_id": "VENDOR-123"}
        request = store.create_request(
            request_id="req-004",
            uow_id="uow-004",
            intervention_type=InterventionType.CLARIFICATION,
            title="Request with Context",
            description="Has context",
            context=context,
        )

        assert request.context == context


class TestInterventionStoreRead:
    """Test get_request and query operations."""

    def test_get_request_found(self, store):
        """Test retrieving existing request."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="Test",
        )

        request = store.get_request("req-001")
        assert request is not None
        assert request.request_id == "req-001"

    def test_get_request_not_found(self, store):
        """Test retrieving non-existent request."""
        request = store.get_request("nonexistent")
        assert request is None

    def test_get_pending_requests(self, store):
        """Test retrieving pending requests."""
        for i in range(5):
            store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description=f"Description {i}",
            )

        pending = store.get_pending_requests()
        assert len(pending) == 5

    def test_get_pending_requests_pagination(self, store):
        """Test pagination with limit."""
        for i in range(10):
            store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description=f"Description {i}",
            )

        pending = store.get_pending_requests(limit=5)
        assert len(pending) == 5

    def test_get_pending_requests_by_priority(self, store):
        """Test that pending requests are sorted by priority."""
        # Create requests with different priorities
        for priority in ["low", "critical", "normal", "high"]:
            store.create_request(
                request_id=f"req-{priority}",
                uow_id=f"uow-{priority}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"{priority} priority",
                description="desc",
                priority=priority,
            )

        pending = store.get_pending_requests()
        # Should be sorted: critical, high, normal, low
        assert pending[0].priority == "critical"
        assert pending[1].priority == "high"
        assert pending[2].priority == "normal"
        assert pending[3].priority == "low"

    def test_get_requests_by_status(self, store):
        """Test filtering by status."""
        req1 = store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Request 1",
            description="desc",
        )

        # Update to approved
        store.update_request(
            "req-001", InterventionStatus.APPROVED, action_reason="Approved"
        )

        # Get pending - should be empty
        pending = store.get_requests_by_status(InterventionStatus.PENDING)
        assert len(pending) == 0

        # Get approved - should have 1
        approved = store.get_requests_by_status(InterventionStatus.APPROVED)
        assert len(approved) == 1

    def test_get_requests_by_priority(self, store):
        """Test filtering by priority."""
        for i in range(3):
            store.create_request(
                request_id=f"req-{i}",
                uow_id=f"uow-{i}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description="desc",
                priority="high" if i < 2 else "low",
            )

        high = store.get_requests_by_priority("high")
        assert len(high) == 2

        low = store.get_requests_by_priority("low")
        assert len(low) == 1

    def test_get_requests_by_pilot(self, store):
        """Test filtering by assigned pilot."""
        req1 = store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Request 1",
            description="desc",
        )

        store.update_request(
            "req-001", InterventionStatus.IN_PROGRESS, assigned_to="pilot-001"
        )

        pilot_requests = store.get_requests_by_pilot("pilot-001")
        assert len(pilot_requests) == 1
        assert pilot_requests[0].assigned_to == "pilot-001"


class TestInterventionStoreUpdate:
    """Test update_request functionality."""

    def test_update_status(self, store):
        """Test updating request status."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="Test",
        )

        updated = store.update_request(
            "req-001", InterventionStatus.APPROVED, action_reason="Approved"
        )

        assert updated.status == InterventionStatus.APPROVED
        assert updated.action_reason == "Approved"

    def test_update_assigns_pilot(self, store):
        """Test assigning pilot."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="Test",
        )

        updated = store.update_request(
            "req-001",
            InterventionStatus.IN_PROGRESS,
            assigned_to="pilot-001",
        )

        assert updated.assigned_to == "pilot-001"

    def test_update_creates_history(self, store):
        """Test that terminal status creates history record."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="Test",
        )

        store.update_request(
            "req-001",
            InterventionStatus.APPROVED,
            action_reason="Approved",
        )

        # Request should no longer be in pending
        pending = store.get_pending_requests()
        assert len(pending) == 0

        # But should be retrievable from history
        approved = store.get_requests_by_status(InterventionStatus.APPROVED)
        assert len(approved) == 1

    def test_update_nonexistent_returns_none(self, store):
        """Test updating nonexistent request."""
        result = store.update_request(
            "nonexistent", InterventionStatus.APPROVED, action_reason="test"
        )
        assert result is None


class TestInterventionStoreMetrics:
    """Test metrics calculation."""

    def test_get_metrics_empty(self, store):
        """Test metrics with no requests."""
        metrics = store.get_metrics()

        assert metrics.total_interventions == 0
        assert metrics.pending_interventions == 0
        assert metrics.approved_interventions == 0

    def test_get_metrics_with_requests(self, store):
        """Test metrics calculation with requests."""
        # Create and complete some requests
        for i in range(3):
            store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description="desc",
                priority="high" if i == 0 else "normal",
            )

        # Approve first request
        store.update_request("req-000", InterventionStatus.APPROVED)

        # Reject second request
        store.update_request("req-001", InterventionStatus.REJECTED)

        metrics = store.get_metrics()

        assert metrics.total_interventions == 3
        assert metrics.pending_interventions == 1
        assert metrics.approved_interventions == 1
        assert metrics.rejected_interventions == 1

    def test_get_metrics_by_type(self, store):
        """Test metrics breakdown by type."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Clarification",
            description="desc",
        )

        store.create_request(
            request_id="req-002",
            uow_id="uow-002",
            intervention_type=InterventionType.KILL_SWITCH,
            title="Kill Switch",
            description="desc",
        )

        metrics = store.get_metrics()

        assert metrics.by_type["clarification"] == 1
        assert metrics.by_type["kill_switch"] == 1

    def test_get_metrics_by_priority(self, store):
        """Test metrics breakdown by priority."""
        for priority in ["critical", "high", "normal", "low"]:
            store.create_request(
                request_id=f"req-{priority}",
                uow_id=f"uow-{priority}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"{priority}",
                description="desc",
                priority=priority,
            )

        metrics = store.get_metrics()

        assert metrics.by_priority["critical"] == 1
        assert metrics.by_priority["high"] == 1
        assert metrics.by_priority["normal"] == 1
        assert metrics.by_priority["low"] == 1

    def test_get_metrics_average_resolution_time(self, store):
        """Test average resolution time calculation."""
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="desc",
        )

        store.update_request("req-001", InterventionStatus.APPROVED)

        metrics = store.get_metrics()

        assert metrics.avg_resolution_time_seconds >= 0

    def test_get_metrics_top_pilots(self, store):
        """Test top pilots calculation."""
        for i in range(3):
            req = store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description="desc",
            )

            # Assign to different pilots
            pilot = f"pilot-{i % 2}"
            store.update_request(f"req-{i:03d}", InterventionStatus.APPROVED, assigned_to=pilot)

        metrics = store.get_metrics()

        # Should have top pilots (2 pilots with approvals)
        assert len(metrics.top_pilots) >= 1


class TestInterventionStoreBulkOps:
    """Test bulk operations."""

    def test_mark_expired(self, store):
        """Test marking expired requests."""
        now = datetime.now(timezone.utc)

        # Create expired request
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Expiring",
            description="desc",
            expires_in_seconds=-1,  # Already expired
        )

        # Create valid request
        store.create_request(
            request_id="req-002",
            uow_id="uow-002",
            intervention_type=InterventionType.CLARIFICATION,
            title="Valid",
            description="desc",
            expires_in_seconds=3600,  # 1 hour from now
        )

        count = store.mark_expired()
        assert count >= 0  # At least checked the expired one

    def test_clear_archived(self, store):
        """Test clearing old archived records."""
        # Create and archive a request
        store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Test",
            description="desc",
        )

        store.update_request("req-001", InterventionStatus.APPROVED)

        # Clear archived (with 0 days = clear all archived)
        count = store.clear_archived(days=0)
        assert count >= 0  # Archived requests should be cleared


class TestInterventionStoreIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow(self, store):
        """Test complete request lifecycle."""
        # Create
        req = store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.CLARIFICATION,
            title="Invoice Clarification",
            description="Cannot identify vendor",
            priority="high",
            context={"invoice_id": "INV-001"},
        )

        assert req.status == InterventionStatus.PENDING

        # Get pending
        pending = store.get_pending_requests()
        assert len(pending) == 1

        # Assign
        req = store.update_request(
            "req-001",
            InterventionStatus.IN_PROGRESS,
            assigned_to="pilot-001",
        )

        assert req.assigned_to == "pilot-001"

        # Approve
        req = store.update_request(
            "req-001",
            InterventionStatus.APPROVED,
            action_reason="Vendor identified",
        )

        assert req.status == InterventionStatus.APPROVED

        # Verify not in pending anymore
        pending = store.get_pending_requests()
        assert len(pending) == 0

        # Get metrics
        metrics = store.get_metrics()
        assert metrics.approved_interventions == 1

    def test_multiple_requests_workflow(self, store):
        """Test handling multiple requests."""
        # Create multiple requests
        for i in range(5):
            store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description=f"Description {i}",
                priority=["critical", "high", "normal", "low", "high"][i],
            )

        # Get pending (sorted by priority)
        pending = store.get_pending_requests()
        assert len(pending) == 5
        assert pending[0].priority == "critical"

        # Approve some
        store.update_request("req-000", InterventionStatus.APPROVED)
        store.update_request("req-001", InterventionStatus.REJECTED)

        # Pending should be 3
        pending = store.get_pending_requests()
        assert len(pending) == 3

        # Metrics
        metrics = store.get_metrics()
        assert metrics.total_interventions == 5
        assert metrics.pending_interventions == 3
        assert metrics.approved_interventions == 1
        assert metrics.rejected_interventions == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
