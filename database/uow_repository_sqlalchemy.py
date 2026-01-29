"""
SQLAlchemy UOWRepository: Concrete implementation for PostgreSQL, Snowflake, Databricks, SQLite.

Constitutional Reference: Article XVII (Atomic Traceability) - Every save computes content_hash and records history.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database.models_instance import UnitsOfWork, UnitsOfWorkHistory, UOWStatus
from database.state_hasher import StateHasher
from database.uow_repository import UOWRepository


class UOWRepositorySQLAlchemy(UOWRepository):
    """SQLAlchemy-based UOW repository supporting PostgreSQL, Snowflake, Databricks, SQLite."""

    def __init__(self, session: Session):
        """
        Initialize with SQLAlchemy session.
        
        Args:
            session: SQLAlchemy Session object
        """
        self.session = session

    def create(self, uow_data: Dict[str, Any]) -> str:
        """Create a new UOW with initial state hash."""
        # Extract required fields
        uow_id = uow_data.get("uow_id")
        instance_id = uow_data.get("instance_id")
        local_workflow_id = uow_data.get("local_workflow_id")
        attributes = uow_data.get("attributes", {})
        interaction_policy = uow_data.get("interaction_policy", {})
        max_interactions = uow_data.get("max_interactions")

        if not all([uow_id, instance_id, local_workflow_id]):
            raise ValueError("uow_id, instance_id, local_workflow_id are required")

        # Compute initial state hash
        content_hash = StateHasher.compute_content_hash(attributes)

        # Create UOW
        uow = UnitsOfWork(
            uow_id=uow_id,
            instance_id=instance_id,
            local_workflow_id=local_workflow_id,
            status=UOWStatus.PENDING.value,
            attributes=attributes,
            interaction_policy=interaction_policy,  # Immutable snapshot
            content_hash=content_hash,
            interaction_count=0,
            max_interactions=max_interactions,
            retry_count=0,
            created_at=datetime.now(timezone.utc),
            last_heartbeat_at=datetime.now(timezone.utc),
        )

        self.session.add(uow)
        self.session.flush()

        # Record creation in history
        self.append_history(
            uow_id=uow_id,
            event_type="UOW_CREATED",
            payload={
                "local_workflow_id": str(local_workflow_id),
                "initial_status": UOWStatus.PENDING.value,
            },
            previous_hash="",  # No previous hash on creation
        )

        self.session.commit()
        return str(uow_id)

    def get(self, uow_id: UUID) -> Dict[str, Any]:
        """Retrieve UOW by ID, returning as dict."""
        uow = self.session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uow_id).first()

        if not uow:
            raise NotFoundError(f"UOW {uow_id} not found")

        return self._to_dict(uow)

    def update_state(
        self,
        uow_id: UUID,
        new_status: str,
        payload: Dict[str, Any],
        interaction_policy: Optional[Dict[str, Any]] = None,
        auto_increment: bool = True,
    ) -> Dict[str, Any]:
        """
        Update UOW state with automatic content hash and history recording.
        
        Constitutional Requirements:
        - Article XVII (Atomic Traceability): Computes new content_hash, records previous_state_hash
        - Article IX (Logic-Blind): Immutable interaction_policy snapshot
        
        Args:
            uow_id: UUID of UOW to update
            new_status: New status (e.g., "ACTIVE", "COMPLETED", "PENDING_PILOT_APPROVAL")
            payload: Attributes to merge into UOW
            interaction_policy: IGNORED for Phase 1 (immutable after creation)
            auto_increment: If True, increment interaction_count. If False (for resume/clarification),
                          count stays same. Only Guard evaluation increments counter.
        """
        uow = self.session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uow_id).first()

        if not uow:
            raise NotFoundError(f"UOW {uow_id} not found")

        # Store previous hash for history
        previous_hash = uow.content_hash

        # Merge payload into attributes
        if payload:
            uow.attributes.update(payload)

        # Compute new content hash (Constitutional Article XVII)
        new_hash = StateHasher.compute_content_hash(uow.attributes)

        # Update UOW fields
        uow.status = new_status
        uow.content_hash = new_hash
        uow.last_heartbeat_at = datetime.now(timezone.utc)

        # Conditional auto-increment (Constitutional Article XIII - Ambiguity Lock detection)
        # Only increment on Guard evaluation; resume/clarification don't increment
        if auto_increment:
            uow.interaction_count += 1

        # IMMUTABILITY: interaction_policy is set only at creation; ignore attempts to modify
        if interaction_policy is not None:
            # Log warning but silently ignore (Constitutional Article IX)
            logger.warning(
                f"Attempt to modify immutable interaction_policy on UOW {uow_id}. "
                f"This field is set at creation and never changes. Request ignored."
            )

        self.session.flush()

        # Append to immutable history
        self.append_history(
            uow_id=uow_id,
            event_type="STATE_TRANSITION",
            payload={"new_status": new_status, "transition_reason": payload.get("reasoning", "")},
            previous_hash=previous_hash,
        )

        self.session.commit()
        return self._to_dict(uow)

    def append_history(
        self,
        uow_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
        previous_hash: str,
    ) -> None:
        """
        Append immutable history record.
        
        Constitutional Requirement (Article XVII):
        - Append-only; no updates/deletes
        - Records previous_state_hash
        - Timestamp included automatically
        """
        history = UOWHistory(
            uow_id=uow_id,
            event_type=event_type,
            payload=payload,
            previous_state_hash=previous_hash,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(history)
        self.session.flush()

    def find_by_status(self, status: str, instance_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Find all UOWs with given status."""
        query = self.session.query(UnitsOfWork).filter(UnitsOfWork.status == status)

        if instance_id:
            query = query.filter(UnitsOfWork.instance_id == instance_id)

        uows = query.all()
        return [self._to_dict(uow) for uow in uows]

    def find_by_interaction_limit(self, instance_id: UUID) -> List[Dict[str, Any]]:
        """Find UOWs that exceeded max_interactions (Ambiguity Lock)."""
        uows = self.session.query(UnitsOfWork).filter(
            UnitsOfWork.instance_id == instance_id,
            UnitsOfWork.max_interactions.isnot(None),
            UnitsOfWork.interaction_count >= UnitsOfWork.max_interactions,
        ).all()

        return [self._to_dict(uow) for uow in uows]

    def get_history(self, uow_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve immutable history for UOW."""
        records = (
            self.session.query(UOWHistory)
            .filter(UOWHistory.uow_id == uow_id)
            .order_by(UOWHistory.created_at.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "event_type": r.event_type,
                "payload": r.payload,
                "previous_state_hash": r.previous_state_hash,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]

    @staticmethod
    def _to_dict(uow: UnitsOfWork) -> Dict[str, Any]:
        """Convert UOW ORM object to dict."""
        return {
            "uow_id": str(uow.uow_id),
            "instance_id": str(uow.instance_id),
            "local_workflow_id": str(uow.local_workflow_id),
            "status": uow.status,
            "attributes": uow.attributes or {},
            "interaction_policy": uow.interaction_policy or {},
            "content_hash": uow.content_hash,
            "interaction_count": uow.interaction_count,
            "max_interactions": uow.max_interactions,
            "retry_count": uow.retry_count,
            "created_at": uow.created_at.isoformat() if uow.created_at else None,
            "last_heartbeat_at": uow.last_heartbeat_at.isoformat() if uow.last_heartbeat_at else None,
        }


class NotFoundError(Exception):
    """Raised when UOW not found in repository."""
    pass
