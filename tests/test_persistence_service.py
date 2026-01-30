"""
Tests for Persistence & Traceability Service Layer

Tests cover:
1. Atomic UOW save operations with state hashing
2. Append-only history tracking
3. High-performance telemetry buffering
4. X-Content-Hash verification
5. State drift detection
6. Shadow logger integration
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.models_instance import (
    InstanceBase,
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Guardians,
    Local_Actors,
    UnitsOfWork,
    UnitsOfWorkHistory,
    UOW_Attributes,
    Interaction_Logs,
)
from database.enums import (
    InstanceStatus,
    RoleType,
    ComponentDirection,
    ActorType,
    UOWStatus,
)
from database.persistence_service import (
    UOWPersistenceService,
    TelemetryBuffer,
    TelemetryEntry,
    ShadowLoggerTelemetryAdapter,
    get_telemetry_buffer,
    reset_telemetry_buffer,
    GuardContext,
)


class MockGuardContext(GuardContext):
    """Mock GuardContext for testing that always authorizes."""
    
    def is_authorized(self, actor_id, uow_id):
        """Always return True for testing."""
        return True
    
    def wait_for_pilot(self, uow_id, reason, timeout_seconds=300):
        """Return mock approval immediately."""
        return {"approved": True, "pilot_id": "test-pilot"}
    
    def emit_violation(self, violation_packet):
        """Silently ignore violations for testing."""
        pass


@pytest.fixture
def guard_context():
    """Create a mock guard context for tests."""
    return MockGuardContext()


@pytest.fixture
def db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    InstanceBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def instance_context(db):
    """Create a test instance context."""
    instance = Instance_Context(
        instance_id=uuid.uuid4(),
        name="Test_Instance",
        description="Test instance for persistence tests",
        status=InstanceStatus.ACTIVE.value,
    )
    db.add(instance)
    db.flush()
    return instance


@pytest.fixture
def workflow(db, instance_context):
    """Create a test workflow."""
    workflow = Local_Workflows(
        local_workflow_id=uuid.uuid4(),
        instance_id=instance_context.instance_id,
        original_workflow_id=uuid.uuid4(),
        name="Test_Workflow",
        version=1,
        is_master=True,
    )
    db.add(workflow)
    db.flush()
    return workflow


@pytest.fixture
def actor(db, instance_context):
    """Create a test actor."""
    actor = Local_Actors(
        actor_id=uuid.uuid4(),
        instance_id=instance_context.instance_id,
        identity_key="test-actor",
        name="Test Actor",
        type=ActorType.HUMAN.value,
    )
    db.add(actor)
    db.flush()
    return actor


@pytest.fixture
def interaction(db, workflow):
    """Create a test interaction."""
    interaction = Local_Interactions(
        interaction_id=uuid.uuid4(),
        local_workflow_id=workflow.local_workflow_id,
        name="Test_Interaction",
    )
    db.add(interaction)
    db.flush()
    return interaction


@pytest.fixture
def role(db, workflow):
    """Create a test role."""
    role = Local_Roles(
        role_id=uuid.uuid4(),
        local_workflow_id=workflow.local_workflow_id,
        name="Test_Role",
        role_type=RoleType.BETA.value,
    )
    db.add(role)
    db.flush()
    return role


@pytest.fixture
def uow(db, instance_context, workflow, interaction):
    """Create a test UOW."""
    uow = UnitsOfWork(
        uow_id=uuid.uuid4(),
        instance_id=instance_context.instance_id,
        local_workflow_id=workflow.local_workflow_id,
        current_interaction_id=interaction.interaction_id,
        status=UOWStatus.PENDING.value,
    )
    db.add(uow)
    db.flush()
    return uow


class TestUOWPersistenceService:
    """Tests for UOWPersistenceService."""

    def test_save_uow_with_attributes(self, db, uow, actor, guard_context):
        """Test saving UOW computes and stores content hash."""
        # Add attributes
        attr1 = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="amount",
            value=100000,
            version=1,
        )
        attr2 = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="priority",
            value=5,
            version=1,
        )
        db.add_all([attr1, attr2])
        db.flush()

        # Save UOW
        updated_uow = UOWPersistenceService.save_uow(
            session=db,
            uow=uow,
            guard_context=guard_context,
            new_status=UOWStatus.ACTIVE.value,
            actor_id=actor.actor_id,
            reasoning="Starting processing",
        )

        # Verify content hash was computed
        assert updated_uow.content_hash is not None
        assert len(updated_uow.content_hash) == 64  # SHA256 hex

        # Verify heartbeat was set
        assert updated_uow.last_heartbeat_at is not None

        # Verify status changed
        assert updated_uow.status == UOWStatus.ACTIVE.value

    def test_save_uow_creates_history(self, db, uow, actor, interaction, guard_context):
        """Test that status change creates a history entry."""
        # Add attributes
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="test",
            value="value",
            version=1,
        )
        db.add(attr)
        db.flush()

        # Save with status change
        UOWPersistenceService.save_uow(
            session=db,
            uow=uow,
            guard_context=guard_context,
            new_status=UOWStatus.ACTIVE.value,
            actor_id=actor.actor_id,
            reasoning="Test transition",
        )

        # Verify history was created
        history = db.query(UnitsOfWorkHistory).filter(
            UnitsOfWorkHistory.uow_id == uow.uow_id
        ).all()

        assert len(history) == 1
        assert history[0].previous_status == UOWStatus.PENDING.value
        assert history[0].new_status == UOWStatus.ACTIVE.value
        assert history[0].reasoning == "Test transition"

    def test_save_uow_no_history_without_change(self, db, uow, actor, guard_context):
        """Test that saving without change doesn't create history."""
        # Add attributes
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="test",
            value="value",
            version=1,
        )
        db.add(attr)
        db.flush()

        # Save without status change
        UOWPersistenceService.save_uow(
            session=db,
            uow=uow,
            guard_context=guard_context,
            actor_id=actor.actor_id,
        )

        # Verify no history created
        history = db.query(UnitsOfWorkHistory).filter(
            UnitsOfWorkHistory.uow_id == uow.uow_id
        ).all()
        assert len(history) == 0

    def test_get_uow_history_chronological(self, db, uow, actor, interaction, guard_context):
        """Test retrieving UOW history in chronological order."""
        # Add attributes
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="test",
            value="value",
            version=1,
        )
        db.add(attr)
        db.flush()

        # Make multiple transitions
        statuses = [UOWStatus.ACTIVE.value, UOWStatus.COMPLETED.value]
        for status in statuses:
            UOWPersistenceService.save_uow(
                session=db,
                uow=uow,
                guard_context=guard_context,
                new_status=status,
                actor_id=actor.actor_id,
            )

        # Retrieve history
        history = UOWPersistenceService.get_uow_history(db, uow.uow_id)

        assert len(history) == 2
        assert history[0].new_status == UOWStatus.ACTIVE.value
        assert history[1].new_status == UOWStatus.COMPLETED.value

    def test_verify_state_hash_valid(self, db, uow, actor, guard_context):
        """Test state hash verification with valid attributes."""
        # Add attributes
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="amount",
            value=50000,
            version=1,
        )
        db.add(attr)
        db.flush()

        # Save UOW (computes hash)
        UOWPersistenceService.save_uow(db, uow, guard_context=guard_context, actor_id=actor.actor_id)

        # Verify hash matches
        is_valid = UOWPersistenceService.verify_state_hash(db, uow)
        assert is_valid is True

    def test_verify_state_hash_drift_detection(self, db, uow, actor, guard_context):
        """Test state hash verification detects attribute modification."""
        # Add initial attribute
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=uow.uow_id,
            instance_id=uow.instance_id,
            actor_id=actor.actor_id,
            key="amount",
            value=50000,
            version=1,
        )
        db.add(attr)
        db.flush()

        # Save UOW
        UOWPersistenceService.save_uow(db, uow, guard_context=guard_context, actor_id=actor.actor_id)
        original_hash = uow.content_hash

        # Modify attribute value (simulate drift)
        attr.value = 60000
        db.flush()

        # Verify hash mismatch
        is_valid = UOWPersistenceService.verify_state_hash(db, uow)
        assert is_valid is False


class TestTelemetryBuffer:
    """Tests for TelemetryBuffer."""

    def test_record_entry(self):
        """Test recording a telemetry entry."""
        buffer = TelemetryBuffer(batch_size=10)
        entry = TelemetryEntry(
            instance_id=uuid.uuid4(),
            uow_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            interaction_id=uuid.uuid4(),
        )

        recorded = buffer.record(entry)
        assert recorded is True
        assert buffer.get_pending_count() == 1

    def test_pending_count(self):
        """Test pending count tracking."""
        buffer = TelemetryBuffer()
        assert buffer.get_pending_count() == 0

        # Add entries
        for _ in range(5):
            entry = TelemetryEntry(
                instance_id=uuid.uuid4(),
                uow_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                interaction_id=uuid.uuid4(),
            )
            buffer.record(entry)

        assert buffer.get_pending_count() == 5

    def test_flush_writes_to_database(self, db, instance_context):
        """Test flush writes entries to database."""
        buffer = TelemetryBuffer(batch_size=100)

        # Add entries
        for i in range(3):
            entry = TelemetryEntry(
                instance_id=instance_context.instance_id,
                uow_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                interaction_id=uuid.uuid4(),
                log_type="TELEMETRY",
            )
            buffer.record(entry)

        # Flush
        written = buffer.flush(db)
        assert written == 3

        # Verify in database
        logs = db.query(Interaction_Logs).all()
        assert len(logs) == 3

    def test_flush_respects_batch_size(self, db, instance_context):
        """Test that flush respects batch size."""
        buffer = TelemetryBuffer(batch_size=2)

        # Add 5 entries
        for _ in range(5):
            entry = TelemetryEntry(
                instance_id=instance_context.instance_id,
                uow_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                interaction_id=uuid.uuid4(),
            )
            buffer.record(entry)

        # First flush gets batch_size entries
        written1 = buffer.flush(db)
        assert written1 == 2

        # Second flush gets remaining
        written2 = buffer.flush(db)
        assert written2 == 2

        # Third flush gets last one
        written3 = buffer.flush(db)
        assert written3 == 1

    def test_flush_all(self, db, instance_context):
        """Test flush_all drains the entire buffer."""
        buffer = TelemetryBuffer(batch_size=2)

        # Add 5 entries
        for _ in range(5):
            entry = TelemetryEntry(
                instance_id=instance_context.instance_id,
                uow_id=uuid.uuid4(),
                actor_id=uuid.uuid4(),
                role_id=uuid.uuid4(),
                interaction_id=uuid.uuid4(),
            )
            buffer.record(entry)

        # Flush all
        written = buffer.flush_all(db)
        assert written == 5
        assert buffer.get_pending_count() == 0


class TestShadowLoggerTelemetryAdapter:
    """Tests for ShadowLoggerTelemetryAdapter."""

    def test_capture_shadow_log_error(self, instance_context):
        """Test capturing a shadow logger error."""
        buffer = reset_telemetry_buffer()
        adapter = ShadowLoggerTelemetryAdapter(buffer, instance_context.instance_id)

        recorded = adapter.capture_shadow_log_error(
            uow_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            interaction_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            error_message="Undefined variable: x",
            condition="x > 10",
            variables={"y": 5},
        )

        assert recorded is True
        assert buffer.get_pending_count() == 1

    def test_capture_guardian_decision(self, instance_context):
        """Test capturing a guardian decision."""
        buffer = reset_telemetry_buffer()
        adapter = ShadowLoggerTelemetryAdapter(buffer, instance_context.instance_id)

        recorded = adapter.capture_guardian_decision(
            uow_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            interaction_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            guardian_name="RiskRouter",
            condition="amount > 50000",
            decision="HighValueProcessing",
            matched_branch_index=0,
        )

        assert recorded is True
        assert buffer.get_pending_count() == 1


class TestGlobalTelemetryBuffer:
    """Tests for global telemetry buffer singleton."""

    def test_get_telemetry_buffer(self):
        """Test getting global telemetry buffer."""
        buffer = get_telemetry_buffer()
        assert buffer is not None

    def test_reset_telemetry_buffer(self):
        """Test resetting global telemetry buffer."""
        # Reset first to clear state from previous tests
        reset_telemetry_buffer()
        
        # Add entry to current
        current = get_telemetry_buffer()
        entry = TelemetryEntry(
            instance_id=uuid.uuid4(),
            uow_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
            role_id=uuid.uuid4(),
            interaction_id=uuid.uuid4(),
        )
        current.record(entry)
        assert current.get_pending_count() == 1

        # Reset
        new_buffer = reset_telemetry_buffer()
        assert new_buffer.get_pending_count() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
