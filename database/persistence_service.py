"""
Persistence & Traceability Service Layer

Implements Article XVII (Atomic Traceability) and Continuous Learning pillars
by providing high-performance, non-blocking persistence operations.

This service layer provides:
1. Atomic UOW save operations with automatic content_hash and heartbeat updates
2. Append-only UOW history tracking with state transition verification
3. High-performance telemetry buffering for non-blocking shadow logger writes
4. X-Content-Hash computation and verification for state drift detection
5. Guard Context abstraction for authorization and violation handling

All operations maintain ACID guarantees and are transaction-safe.
"""

import uuid
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from queue import Queue
from threading import Lock
from sqlalchemy.orm import Session

from database.models_instance import (
    UnitsOfWork,
    UnitsOfWorkHistory,
    UOW_Attributes,
    Interaction_Logs,
    Local_Interactions,
)
from database.enums import GuardLayerBypassException, GuardStateDriftException
from chameleon_workflow_engine.semantic_guard import StateVerifier


@dataclass
class TelemetryEntry:
    """
    Represents a single telemetry event waiting to be persisted.
    Used by the TelemetryBuffer for high-performance, non-blocking writes.
    """
    instance_id: uuid.UUID
    uow_id: uuid.UUID
    actor_id: uuid.UUID
    role_id: uuid.UUID
    interaction_id: uuid.UUID
    log_type: str = "TELEMETRY"
    event_details: Optional[Dict[str, Any]] = None
    error_metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class UOWStateTransition:
    """
    Represents a UOW state transition for history tracking.
    Includes state hashes, interaction changes, and reasoning.
    """
    uow_id: uuid.UUID
    instance_id: uuid.UUID
    previous_status: str
    new_status: str
    previous_state_hash: Optional[str]
    new_state_hash: str
    previous_interaction_id: Optional[uuid.UUID]
    new_interaction_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class ViolationPacket:
    """
    Standardized violation packet emitted when Guard detects a breach.
    
    Implements Guard Behavior Spec Section 1.1: Violation Reporting.
    Contains all necessary context for violation handling, logging, and remediation.
    """
    rule_id: str
    severity: str  # "CRITICAL", "WARNING", "INFO"
    violation_type: str
    uow_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    remedy_suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert violation packet to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of the violation
        """
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "violation_type": self.violation_type,
            "uow_id": self.uow_id,
            "raw_data": self.raw_data,
            "remedy_suggestion": self.remedy_suggestion,
            "timestamp": self.timestamp.isoformat(),
        }


class GuardContext(ABC):
    """
    Abstract base for Guard context (injected by routing engine).
    
    Implements Article I, Section 3: "The Guard's Mandate: The WorkflowGuardian
    acts as the supreme filter over all UOW transitions. No transition occurs
    without Guard authorization."
    
    Subclasses must implement authorization, pilot communication, and violation
    emission to enforce Constitutional compliance.
    """

    @abstractmethod
    def is_authorized(
        self, actor_id: Optional[uuid.UUID], uow_id: uuid.UUID
    ) -> bool:
        """
        Check if an actor is authorized to perform operations on a UOW.
        
        Args:
            actor_id: The actor attempting the operation (may be None for system)
            uow_id: The UOW being operated on
        
        Returns:
            True if authorized, False otherwise
        """
        pass

    @abstractmethod
    def wait_for_pilot(
        self, uow_id: uuid.UUID, reason: str, timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Wait for Pilot (human) approval on a high-risk UOW transition.
        
        Used for transitions marked as requiring manual approval.
        
        Args:
            uow_id: The UOW requiring approval
            reason: Human-readable reason for pilot intervention
            timeout_seconds: Maximum time to wait for response (default 300s)
        
        Returns:
            Dictionary with keys:
            - approved (bool): Whether pilot approved
            - waiver_issued (bool): Whether constitutional waiver was issued
            - waiver_reason (Optional[str]): Reason for waiver if issued
            - rejection_reason (Optional[str]): Reason for rejection if denied
        """
        pass

    @abstractmethod
    def emit_violation(self, packet: ViolationPacket) -> None:
        """
        Emit a violation packet when Guard detects a breach.
        
        Allows Guard to report violations to monitoring/alerting systems.
        
        Args:
            packet: The violation packet to emit
        """
        pass


class UOWPersistenceService:
    """
    Atomic persistence operations for Units of Work.
    
    Ensures that every UOW state change is:
    1. Authorized by the Guard (Article I)
    2. Stamped with the current state hash (X-Content-Hash)
    3. Recorded in the append-only history table
    4. Marked with the heartbeat timestamp
    5. Traceable to the actor responsible
    
    Implements Article XVII (Atomic Traceability).
    """

    @staticmethod
    def save_uow(
        session: Session,
        uow: UnitsOfWork,
        guard_context: GuardContext,
        new_status: Optional[str] = None,
        new_interaction_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UnitsOfWork:
        """
        Atomically save a UOW with automatic state tracking and Guard authorization.
        
        STEP 0 (Guard Authorization Check):
        Before any state modification, this method checks with the Guard context
        to ensure the actor is authorized to modify this UOW. If authorization
        fails, a ViolationPacket is emitted and GuardLayerBypassException is raised.
        
        Then:
        1. Computes X-Content-Hash of current attributes
        2. Updates last_heartbeat_at to current UTC time
        3. Creates a history entry if status or interaction changed
        4. Maintains append-only traceability
        
        Args:
            session: SQLAlchemy session for persistence
            uow: The Unit of Work to save
            guard_context: REQUIRED. Guard context for authorization check.
                          Implements Article I, Section 3 (Guard Mandate).
            new_status: Optional new status (PENDING, ACTIVE, COMPLETED, FAILED)
            new_interaction_id: Optional new interaction location
            actor_id: Optional UUID of actor responsible for this change
            reasoning: Optional explanation of why this change occurred
            metadata: Optional additional context (e.g., error details)
        
        Returns:
            The updated UOW object
        
        Raises:
            GuardLayerBypassException: If Guard denies authorization
            ValueError: If state transition is invalid
        """
        # STEP 0: Guard Authorization Check (BEFORE any state modification)
        is_authorized = guard_context.is_authorized(actor_id, uow.uow_id)
        if not is_authorized:
            violation = ViolationPacket(
                rule_id="ARTICLE_I_GUARD_AUTHORIZATION",
                severity="CRITICAL",
                violation_type="UNAUTHORIZED_UOW_MODIFICATION",
                uow_id=str(uow.uow_id),
                raw_data={
                    "attempted_actor": str(actor_id) if actor_id else "SYSTEM",
                    "new_status": new_status,
                    "new_interaction_id": str(new_interaction_id) if new_interaction_id else None,
                },
                remedy_suggestion=(
                    "This UOW modification requires Guard approval. "
                    "Verify actor credentials and check Guard rules."
                ),
            )
            guard_context.emit_violation(violation)
            raise GuardLayerBypassException(
                f"Guard authorization failed for UOW {uow.uow_id} by actor {actor_id}"
            )

        # 1. Get all current attributes and compute state hash
        current_attributes = {}
        for attr in uow.attributes:
            if attr.key not in current_attributes:
                current_attributes[attr.key] = attr.value

        new_state_hash = StateVerifier.compute_hash(current_attributes)

        # 2. Store previous state hash before update
        previous_state_hash = uow.content_hash
        previous_status = uow.status
        previous_interaction_id = uow.current_interaction_id

        # 3. Update UOW with new state
        if new_status:
            uow.status = new_status
        if new_interaction_id:
            uow.current_interaction_id = new_interaction_id

        # 4. Update heartbeat and content hash atomically
        uow.last_heartbeat_at = datetime.now(timezone.utc)
        uow.content_hash = new_state_hash

        # 5. Create history entry if status or interaction changed
        if (new_status and new_status != previous_status) or \
           (new_interaction_id and new_interaction_id != previous_interaction_id):
            
            history_entry = UnitsOfWorkHistory(
                history_id=uuid.uuid4(),
                instance_id=uow.instance_id,
                uow_id=uow.uow_id,
                previous_status=previous_status,
                new_status=uow.status,
                previous_state_hash=previous_state_hash,
                new_state_hash=new_state_hash,
                previous_interaction_id=previous_interaction_id,
                new_interaction_id=uow.current_interaction_id,
                actor_id=actor_id,
                transition_timestamp=datetime.now(timezone.utc),
                reasoning=reasoning,
                metadata=metadata,
            )
            session.add(history_entry)

        # 6. Flush to database (transactional)
        session.add(uow)
        session.flush()

        return uow
        # 1. Get all current attributes and compute state hash
        current_attributes = {}
        for attr in uow.attributes:
            if attr.key not in current_attributes:
                current_attributes[attr.key] = attr.value

        new_state_hash = StateVerifier.compute_hash(current_attributes)

        # 2. Store previous state hash before update
        previous_state_hash = uow.content_hash
        previous_status = uow.status
        previous_interaction_id = uow.current_interaction_id

        # 3. Update UOW with new state
        if new_status:
            uow.status = new_status
        if new_interaction_id:
            uow.current_interaction_id = new_interaction_id

        # 4. Update heartbeat and content hash atomically
        uow.last_heartbeat_at = datetime.now(timezone.utc)
        uow.content_hash = new_state_hash

        # 5. Create history entry if status or interaction changed
        if (new_status and new_status != previous_status) or \
           (new_interaction_id and new_interaction_id != previous_interaction_id):
            
            history_entry = UnitsOfWorkHistory(
                history_id=uuid.uuid4(),
                instance_id=uow.instance_id,
                uow_id=uow.uow_id,
                previous_status=previous_status,
                new_status=uow.status,
                previous_state_hash=previous_state_hash,
                new_state_hash=new_state_hash,
                previous_interaction_id=previous_interaction_id,
                new_interaction_id=uow.current_interaction_id,
                actor_id=actor_id,
                transition_timestamp=datetime.now(timezone.utc),
                reasoning=reasoning,
                metadata=metadata,
            )
            session.add(history_entry)

        # 6. Flush to database (transactional)
        session.add(uow)
        session.flush()

        return uow

    @staticmethod
    def get_uow_history(
        session: Session,
        uow_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> List[UnitsOfWorkHistory]:
        """
        Retrieve the complete state transition history for a UOW.
        
        Returns entries in chronological order (oldest to newest),
        showing the full audit trail of state changes.
        
        Args:
            session: SQLAlchemy session
            uow_id: The UOW ID to get history for
            limit: Optional limit on number of entries to return
        
        Returns:
            List of UnitsOfWorkHistory entries in chronological order
        """
        query = session.query(UnitsOfWorkHistory) \
            .filter(UnitsOfWorkHistory.uow_id == uow_id) \
            .order_by(UnitsOfWorkHistory.transition_timestamp.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def verify_state_hash(
        session: Session,
        uow: UnitsOfWork,
        emit_violation: bool = False,
        guard_context: Optional[GuardContext] = None,
    ) -> Union[bool, Dict[str, Any]]:
        """
        Verify that the UOW's content_hash matches its current attributes.
        
        Detects state drift or unauthorized attribute modifications.
        Implements Article XVII (Atomic Traceability).
        
        Args:
            session: SQLAlchemy session
            uow: The UOW to verify
            emit_violation: If True, emit ViolationPacket on drift (requires guard_context)
            guard_context: Required if emit_violation=True. Guard context for violation emission.
        
        Returns:
            If emit_violation=False: bool indicating whether hash matches
            If emit_violation=True: Dict with keys:
                - is_valid (bool): Whether hash matches
                - stored_hash (str): The stored content_hash
                - current_hash (str): The computed hash of current attributes
                - violation_packet (Optional[Dict]): Violation details if drift detected
        
        Raises:
            GuardStateDriftException: Only if emit_violation=True and guard_context is set
        """
        current_attributes = {}
        for attr in uow.attributes:
            if attr.key not in current_attributes:
                current_attributes[attr.key] = attr.value

        expected_hash = StateVerifier.compute_hash(current_attributes)
        is_valid = uow.content_hash == expected_hash

        # Backward compatibility: simple boolean return
        if not emit_violation:
            return is_valid

        # Enhanced return with violation details
        result = {
            "is_valid": is_valid,
            "stored_hash": uow.content_hash,
            "current_hash": expected_hash,
            "violation_packet": None,
        }

        if not is_valid:
            violation = ViolationPacket(
                rule_id="ARTICLE_XVII_STATE_DRIFT",
                severity="CRITICAL",
                violation_type="STATE_HASH_MISMATCH",
                uow_id=str(uow.uow_id),
                raw_data={
                    "stored_hash": uow.content_hash,
                    "computed_hash": expected_hash,
                    "attributes_count": len(current_attributes),
                },
                remedy_suggestion=(
                    "State drift detected! Remediation options:\n"
                    "1. ROLLBACK: Revert attributes to match stored hash\n"
                    "2. QUARANTINE: Isolate UOW for manual inspection\n"
                    "3. CONSTITUTIONAL_WAIVER: Issue waiver and proceed (requires Pilot approval)"
                ),
            )
            result["violation_packet"] = violation.to_dict()

            if guard_context:
                guard_context.emit_violation(violation)
                # Note: We don't raise here - caller decides action

        return result

    @staticmethod
    def heartbeat_uow(session: Session, uow_id: uuid.UUID) -> bool:
        """
        Update UOW heartbeat timestamp to signal continued liveness.
        
        Implements Article XI, Section 3 (Zombie Actor Protocol):
        Actors must call this method periodically to signal they are still
        processing. The TAU role monitors heartbeats and reclaims stale tokens
        after a configurable timeout (default 5 minutes).
        
        Args:
            session: SQLAlchemy session
            uow_id: The UOW ID to heartbeat
        
        Returns:
            True if heartbeat was recorded, False if UOW not found or inactive
        """
        uow = session.query(UnitsOfWork).filter(
            UnitsOfWork.uow_id == uow_id
        ).first()

        if not uow:
            return False

        # Protocol requirement: only ACTIVE UOWs can heartbeat
        if uow.status != "ACTIVE":
            return False

        # Update heartbeat timestamp
        uow.last_heartbeat_at = datetime.now(timezone.utc)
        session.flush()
        return True

    @staticmethod
    def save_uow_with_pilot_check(
        session: Session,
        uow: UnitsOfWork,
        guard_context: GuardContext,
        new_status: str,
        new_interaction_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        reasoning: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        high_risk_transitions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save UOW with mandatory Pilot (human) check-in for high-risk transitions.
        
        Implements UOW Lifecycle Spec (Pilot Pulse): Critical transitions like
        COMPLETED and FAILED require Pilot approval before they are persisted.
        
        This ensures human oversight of important decisions and provides
        Constitutional Waiver capability for exceptional cases.
        
        Args:
            session: SQLAlchemy session
            uow: The UOW to save
            guard_context: REQUIRED. Guard context for pilot communication
            new_status: The target status
            new_interaction_id: The target interaction
            actor_id: Optional actor responsible for change
            reasoning: Optional explanation
            metadata: Optional additional context
            high_risk_transitions: List of statuses requiring pilot approval
                                 (default: ["COMPLETED", "FAILED"])
        
        Returns:
            Dict with keys:
            - success (bool): Whether save succeeded
            - pilot_approved (bool): Whether pilot approved (if high-risk)
            - waiver_issued (bool): Whether constitutional waiver was issued
            - uow (UnitsOfWork): The saved UOW (if successful)
            - blocked_by (Optional[str]): Reason for block if not successful
            - error (Optional[str]): Error message if operation failed
        
        Raises:
            GuardLayerBypassException: If Guard authorization fails
        """
        if high_risk_transitions is None:
            high_risk_transitions = ["COMPLETED", "FAILED"]

        result = {
            "success": False,
            "pilot_approved": False,
            "waiver_issued": False,
            "uow": None,
            "blocked_by": None,
            "error": None,
        }

        # Check if this is a high-risk transition
        is_high_risk = new_status in high_risk_transitions

        if is_high_risk:
            # Require Pilot approval for high-risk transitions
            reason_msg = f"UOW {uow.uow_id} transitioning to {new_status}. Reason: {reasoning}"
            pilot_decision = guard_context.wait_for_pilot(
                uow_id=uow.uow_id,
                reason=reason_msg,
                timeout_seconds=300,
            )

            if not pilot_decision.get("approved", False):
                if not pilot_decision.get("waiver_issued", False):
                    result["blocked_by"] = "PILOT_APPROVAL_REQUIRED"
                    result["error"] = (
                        f"Pilot rejected transition to {new_status}: "
                        f"{pilot_decision.get('rejection_reason', 'No reason provided')}"
                    )
                    return result
                else:
                    # Waiver issued - allowed to proceed
                    result["waiver_issued"] = True
                    if metadata is None:
                        metadata = {}
                    metadata["constitutional_waiver"] = {
                        "issued": True,
                        "reason": pilot_decision.get("waiver_reason", ""),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            else:
                result["pilot_approved"] = True

        # Proceed with save
        try:
            updated_uow = UOWPersistenceService.save_uow(
                session=session,
                uow=uow,
                guard_context=guard_context,
                new_status=new_status,
                new_interaction_id=new_interaction_id,
                actor_id=actor_id,
                reasoning=reasoning,
                metadata=metadata,
            )
            result["success"] = True
            result["uow"] = updated_uow
        except Exception as e:
            result["error"] = str(e)
            result["blocked_by"] = "GUARD_EXCEPTION"

        return result


class TelemetryBuffer:
    """
    High-performance, non-blocking telemetry buffering service.
    
    Implements the Silent Failure Protocol by asynchronously capturing
    interaction metadata, errors, and guardian decisions without blocking
    the main execution flow.
    
    Features:
    - Thread-safe, lock-based queueing
    - Batch writes for efficiency (configurable)
    - FIFO ordering guarantee
    - Automatic timestamp injection
    - Type-safe entries with dataclasses
    
    Usage:
        buffer = TelemetryBuffer(batch_size=100)
        buffer.record(TelemetryEntry(...))
        written = buffer.flush(session)  # Non-blocking flush
    """

    def __init__(self, max_queue_size: int = 10000, batch_size: int = 100):
        """
        Initialize the telemetry buffer.
        
        Args:
            max_queue_size: Maximum entries before blocking (defensive against memory overflow)
            batch_size: Target batch size for flush operations
        """
        self.queue: Queue = Queue(maxsize=max_queue_size)
        self.batch_size = batch_size
        self._lock = Lock()
        self._pending_count = 0

    def record(self, entry: TelemetryEntry) -> bool:
        """
        Record a telemetry entry (non-blocking, returns immediately).
        
        If queue is full, returns False (backpressure).
        
        Args:
            entry: The TelemetryEntry to record
        
        Returns:
            True if recorded, False if queue full (backpressure)
        """
        try:
            self.queue.put_nowait(entry)
            with self._lock:
                self._pending_count += 1
            return True
        except:
            # Queue full - return False to signal backpressure
            return False

    def get_pending_count(self) -> int:
        """
        Get the number of pending telemetry entries awaiting flush.
        
        Returns:
            Count of entries in buffer
        """
        with self._lock:
            return self._pending_count

    def flush(self, session: Session, max_entries: Optional[int] = None) -> int:
        """
        Flush pending telemetry entries to the database.
        
        This operation:
        1. Extracts up to batch_size entries from the queue
        2. Creates Interaction_Logs entries
        3. Commits to database in a single transaction
        4. Maintains FIFO ordering and reliability
        
        Args:
            session: SQLAlchemy session for persistence
            max_entries: Override batch size for this flush
        
        Returns:
            Number of entries actually written
        """
        flush_count = max_entries if max_entries else self.batch_size
        entries_to_write = []

        # Extract entries from queue (non-blocking)
        while len(entries_to_write) < flush_count and not self.queue.empty():
            try:
                entry = self.queue.get_nowait()
                entries_to_write.append(entry)
            except:
                break

        # Convert to database entries
        logs = []
        for entry in entries_to_write:
            log = Interaction_Logs(
                log_id=str(uuid.uuid4()),
                instance_id=str(entry.instance_id),
                uow_id=str(entry.uow_id),
                actor_id=str(entry.actor_id),
                role_id=str(entry.role_id),
                interaction_id=str(entry.interaction_id),
                timestamp=entry.timestamp or datetime.now(timezone.utc),
                log_type=entry.log_type,
                event_details=entry.event_details,
                error_metadata=entry.error_metadata,
            )
            logs.append(log)

        # Batch insert
        if logs:
            session.bulk_save_objects(logs)
            session.flush()

        # Update counter
        with self._lock:
            self._pending_count = max(0, self._pending_count - len(entries_to_write))

        return len(entries_to_write)

    def flush_all(self, session: Session) -> int:
        """
        Flush all pending entries to the database.
        
        Args:
            session: SQLAlchemy session
        
        Returns:
            Total number of entries written
        """
        total_written = 0
        while not self.queue.empty():
            written = self.flush(session, max_entries=self.batch_size)
            total_written += written
            if written == 0:
                break
        return total_written


class ShadowLoggerTelemetryAdapter:
    """
    Adapter that bridges the Semantic Guard's ShadowLogger with the TelemetryBuffer.
    
    Converts Shadow Logger error entries to TelemetryBuffer entries and provides
    high-performance error capture without blocking the main routing logic.
    
    Usage:
        adapter = ShadowLoggerTelemetryAdapter(buffer)
        adapter.capture_shadow_log_errors(uow, error_logs)
    """

    def __init__(self, buffer: TelemetryBuffer, instance_id: uuid.UUID):
        """
        Initialize the adapter.
        
        Args:
            buffer: The TelemetryBuffer to write to
            instance_id: The instance ID for all captured events
        """
        self.buffer = buffer
        self.instance_id = instance_id

    def capture_shadow_log_error(
        self,
        uow_id: uuid.UUID,
        role_id: uuid.UUID,
        interaction_id: uuid.UUID,
        actor_id: Optional[uuid.UUID],
        error_message: str,
        condition: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Capture a shadow logger error entry to telemetry buffer.
        
        Converts error context into a TelemetryEntry and records it non-blocking.
        
        Args:
            uow_id: The UOW where error occurred
            role_id: The role context
            interaction_id: The interaction context
            actor_id: The actor responsible (may be None)
            error_message: The error message from evaluator
            condition: The condition being evaluated (optional)
            variables: The variable context (optional)
        
        Returns:
            True if successfully recorded, False if buffer full
        """
        entry = TelemetryEntry(
            instance_id=self.instance_id,
            uow_id=uow_id,
            actor_id=actor_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            role_id=role_id,
            interaction_id=interaction_id,
            log_type="ERROR",
            error_metadata={
                "error_message": error_message,
                "condition": condition,
                "variables": variables,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return self.buffer.record(entry)

    def capture_guardian_decision(
        self,
        uow_id: uuid.UUID,
        role_id: uuid.UUID,
        interaction_id: uuid.UUID,
        actor_id: Optional[uuid.UUID],
        guardian_name: str,
        condition: str,
        decision: str,
        matched_branch_index: Optional[int] = None,
    ) -> bool:
        """
        Capture a guardian decision to telemetry buffer.
        
        Records routing decisions for learning and observability.
        
        Args:
            uow_id: The UOW being routed
            role_id: The role context
            interaction_id: The interaction context
            actor_id: The actor (may be None)
            guardian_name: Name of the guardian that decided
            condition: The condition expression
            decision: The routing decision (interaction name or error)
            matched_branch_index: Index of matched branch (optional)
        
        Returns:
            True if recorded, False if buffer full
        """
        entry = TelemetryEntry(
            instance_id=self.instance_id,
            uow_id=uow_id,
            actor_id=actor_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            role_id=role_id,
            interaction_id=interaction_id,
            log_type="GUARDIAN_DECISION",
            event_details={
                "guardian_name": guardian_name,
                "condition": condition,
                "decision": decision,
                "matched_branch_index": matched_branch_index,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return self.buffer.record(entry)


# Global telemetry buffer instance (singleton pattern)
_global_telemetry_buffer = TelemetryBuffer(max_queue_size=10000, batch_size=100)


def get_telemetry_buffer() -> TelemetryBuffer:
    """
    Get the global telemetry buffer instance.
    
    Returns:
        The singleton TelemetryBuffer
    """
    return _global_telemetry_buffer


def reset_telemetry_buffer() -> TelemetryBuffer:
    """
    Reset the global telemetry buffer (for testing).
    
    Returns:
        A fresh TelemetryBuffer instance
    """
    global _global_telemetry_buffer
    _global_telemetry_buffer = TelemetryBuffer(max_queue_size=10000, batch_size=100)
    return _global_telemetry_buffer
