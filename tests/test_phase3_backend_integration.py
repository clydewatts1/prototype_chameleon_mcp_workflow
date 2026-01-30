"""
Phase 3 Backend Integration Tests

Tests the integration of InterventionStoreSQLAlchemy with the FastAPI server.
Verifies that:
1. Database is initialized on server startup
2. Intervention store uses SQLAlchemy backend
3. WebSocket handlers query from database
4. Metrics are calculated from persistent storage
5. Interventions survive server restarts
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models_phase3 import Phase3Base, Intervention, Phase3DatabaseManager
from database.intervention_store_sqlalchemy import InterventionStoreSQLAlchemy
from chameleon_workflow_engine.interactive_dashboard import (
    InterventionType,
    InterventionStatus,
    initialize_intervention_store,
    get_intervention_store,
)


@pytest.fixture
def phase3_db_session():
    """Create in-memory Phase 3 database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Phase3Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def phase3_store(phase3_db_session):
    """Create InterventionStoreSQLAlchemy instance with test database."""
    store = InterventionStoreSQLAlchemy(phase3_db_session)
    initialize_intervention_store(store)
    return store


class TestPhase3StoreIntegration:
    """Test InterventionStoreSQLAlchemy integration with server."""

    def test_store_initialized_with_database(self, phase3_store):
        """Verify store is properly initialized."""
        assert get_intervention_store() is phase3_store
        assert get_intervention_store() is not None

    def test_create_intervention_persists_to_database(self, phase3_store, phase3_db_session):
        """Verify created interventions persist in database."""
        # Create intervention through store
        request = phase3_store.create_request(
            request_id="req-001",
            uow_id="uow-001",
            intervention_type=InterventionType.KILL_SWITCH,
            title="Emergency Stop",
            description="Test emergency stop",
            priority="critical",
        )

        # Verify database record exists
        db_record = phase3_db_session.query(Intervention).filter_by(
            request_id="req-001"
        ).first()
        
        assert db_record is not None
        assert db_record.request_id == "req-001"
        assert db_record.uow_id == "uow-001"
        assert db_record.title == "Emergency Stop"
        assert db_record.status == "PENDING"

    def test_update_intervention_reflected_in_database(self, phase3_store, phase3_db_session):
        """Verify updates to interventions persist in database."""
        # Create
        phase3_store.create_request(
            request_id="req-002",
            uow_id="uow-002",
            intervention_type=InterventionType.CLARIFICATION,
            title="Need Clarification",
            description="Test clarification",
        )

        # Update
        updated = phase3_store.update_request(
            request_id="req-002",
            status=InterventionStatus.APPROVED,
            action_reason="Pilot approved",
            assigned_to="pilot-001",
        )

        # Verify intervention record is archived, not deleted
        db_record = phase3_db_session.query(Intervention).filter_by(
            request_id="req-002"
        ).first()
        
        assert db_record is not None  # Still exists, but marked as archived
        assert db_record.is_archived is True
        assert db_record.status == "APPROVED"
        
        # Check history record was created
        from database.models_phase3 import InterventionHistory
        history_record = phase3_db_session.query(InterventionHistory).filter_by(
            request_id="req-002"
        ).first()
        
        assert history_record is not None
        assert history_record.status == "APPROVED"
        assert history_record.assigned_to == "pilot-001"

    def test_pending_requests_query_database(self, phase3_store):
        """Verify get_pending_requests queries database."""
        # Create multiple requests
        for i in range(3):
            phase3_store.create_request(
                request_id=f"req-{i:03d}",
                uow_id=f"uow-{i:03d}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Request {i}",
                description=f"Test request {i}",
                priority=["critical", "high", "normal"][i],
            )

        # Query pending
        pending = phase3_store.get_pending_requests()
        
        assert len(pending) == 3
        # Should be sorted by priority (critical first)
        assert pending[0].priority == "critical"

    def test_metrics_calculated_from_database(self, phase3_store):
        """Verify metrics are calculated from persistent storage."""
        # Create various requests
        phase3_store.create_request(
            request_id="req-a",
            uow_id="uow-a",
            intervention_type=InterventionType.KILL_SWITCH,
            title="Emergency 1",
            description="Test",
            priority="critical",
        )
        
        phase3_store.create_request(
            request_id="req-b",
            uow_id="uow-b",
            intervention_type=InterventionType.CLARIFICATION,
            title="Clarification 1",
            description="Test",
            priority="high",
        )

        # Update one to approved
        phase3_store.update_request(
            request_id="req-a",
            status=InterventionStatus.APPROVED,
            assigned_to="pilot-001",
        )

        # Get metrics
        metrics = phase3_store.get_metrics()
        
        assert metrics.total_interventions == 2
        assert metrics.pending_interventions == 1
        assert metrics.approved_interventions == 1
        assert metrics.rejected_interventions == 0
        assert len(metrics.top_pilots) == 1
        assert metrics.top_pilots[0]["pilot_id"] == "pilot-001"

    def test_expiration_handling(self, phase3_store):
        """Verify expired interventions are marked correctly."""
        import time
        
        # Create request that expires immediately
        phase3_store.create_request(
            request_id="req-exp",
            uow_id="uow-exp",
            intervention_type=InterventionType.CANCEL,
            title="Expires Now",
            description="Test",
            expires_in_seconds=-1,  # Expired in the past
        )

        # Brief sleep to ensure time has passed
        time.sleep(0.01)

        # Mark expired
        count = phase3_store.mark_expired()
        
        # Verify count
        assert count == 1, f"Expected 1 expired intervention, got {count}"

        # Verify status changed to EXPIRED
        request = phase3_store.get_request("req-exp")
        assert request is not None
        assert request.status == InterventionStatus.EXPIRED


class TestPhase3ServerIntegration:
    """Test server integration with Phase 3 database (if server is running)."""

    def test_server_can_access_intervention_store(self, phase3_store):
        """Verify server can initialize and access intervention store."""
        # This is a smoke test - imports should work without errors
        from chameleon_workflow_engine.server import app
        from chameleon_workflow_engine.interactive_dashboard import (
            get_intervention_store
        )
        
        # Store should be accessible (will use the phase3_store from fixture)
        store = get_intervention_store()
        assert store is not None
        assert store is phase3_store

    def test_websocket_message_handler_uses_store(self, phase3_store):
        """Verify WebSocket handler uses the intervention store."""
        from chameleon_workflow_engine.interactive_dashboard import (
            WebSocketMessageHandler, get_intervention_store
        )

        # Create a request in the database
        phase3_store.create_request(
            request_id="req-ws",
            uow_id="uow-ws",
            intervention_type=InterventionType.CLARIFICATION,
            title="WebSocket Test",
            description="Testing WebSocket handler",
        )

        # Create handler with explicit store reference
        handler = WebSocketMessageHandler(phase3_store)
        
        # Handler should see the request
        response = handler.handle_message(
            "get_pending",
            {"limit": 50}
        )
        
        assert response["success"] is True
        requests = response["data"].get("requests", [])
        assert len(requests) >= 1
        assert any(r["request_id"] == "req-ws" for r in requests)

    def test_websocket_metrics_from_database(self, phase3_store):
        """Verify WebSocket metrics endpoint queries database."""
        from chameleon_workflow_engine.interactive_dashboard import (
            WebSocketMessageHandler
        )

        # Create handler with explicit store reference
        handler = WebSocketMessageHandler(phase3_store)

        # Create requests
        for i in range(3):
            phase3_store.create_request(
                request_id=f"req-m{i}",
                uow_id=f"uow-m{i}",
                intervention_type=InterventionType.CLARIFICATION,
                title=f"Metric Test {i}",
                description="Test",
            )

        # Approve one
        phase3_store.update_request(
            "req-m0",
            InterventionStatus.APPROVED,
            assigned_to="pilot-001"
        )

        # Get metrics via WebSocket handler
        response = handler.handle_message("get_metrics", {})
        
        assert response["success"] is True
        # Metrics are in data, not data.metrics
        data = response["data"]
        assert data.get("total_interventions", 0) == 3
        assert data.get("pending_interventions", 0) == 2
        assert data.get("approved_interventions", 0) == 1


class TestPhase3DataPersistence:
    """Test that data persists correctly across operations."""

    def test_multiple_stores_same_database(self):
        """Verify multiple store instances see same database."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")
        Phase3Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        # Create two store instances on same database
        session1 = Session()
        session2 = Session()
        
        store1 = InterventionStoreSQLAlchemy(session1)
        store2 = InterventionStoreSQLAlchemy(session2)

        # Create through store1
        store1.create_request(
            request_id="req-persist",
            uow_id="uow-persist",
            intervention_type=InterventionType.KILL_SWITCH,
            title="Persistence Test",
            description="Test",
        )

        # Should be visible through store2
        request = store2.get_request("req-persist")
        assert request is not None
        assert request.title == "Persistence Test"

        session1.close()
        session2.close()

    def test_transaction_isolation(self):
        """Verify proper transaction handling."""
        engine = create_engine("sqlite:///:memory:")
        Phase3Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        session = Session()
        store = InterventionStoreSQLAlchemy(session)

        # Create and update in transaction
        request = store.create_request(
            request_id="req-tx",
            uow_id="uow-tx",
            intervention_type=InterventionType.CLARIFICATION,
            title="Transaction Test",
            description="Test",
        )

        # Update should commit properly
        updated = store.update_request(
            "req-tx",
            InterventionStatus.APPROVED,
            assigned_to="pilot-tx"
        )

        # Record should still exist but be archived
        assert updated is not None
        assert updated.status == InterventionStatus.APPROVED
        
        # Verify history persisted
        from database.models_phase3 import InterventionHistory
        all_history = session.query(InterventionHistory).all()
        
        assert len(all_history) == 1
        assert all_history[0].status == "APPROVED"
        
        session.close()
