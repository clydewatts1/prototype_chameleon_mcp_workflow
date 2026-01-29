"""
UOWRepository: Abstract interface for database-agnostic UOW persistence.

This abstraction enables support for PostgreSQL, Snowflake, Databricks, and SQLite
without coupling the business logic (Guard, Engine, PilotInterface) to any specific database driver.

Constitutional Reference: Article XVII (Atomic Traceability) - Every save must include state hash verification.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from uuid import UUID


class UOWRepository(ABC):
    """
    Abstract base class for Unit of Work persistence.
    
    All implementations must ensure:
    1. **Atomic Hashing:** Every save() call computes and records content_hash
    2. **Append-Only History:** append_history() never updates/deletes existing records
    3. **Database Agnosticism:** Works with PostgreSQL, Snowflake, Databricks, SQLite
    """

    @abstractmethod
    def create(self, uow_data: Dict[str, Any]) -> str:
        """
        Create a new UOW.
        
        Args:
            uow_data: Dict containing uow_id, instance_id, local_workflow_id, attributes, interaction_policy, etc.
        
        Returns:
            uow_id (str)
        
        Raises:
            ValueError: If required fields missing or invalid
        """
        pass

    @abstractmethod
    def get(self, uow_id: UUID) -> Dict[str, Any]:
        """
        Retrieve UOW by ID.
        
        Args:
            uow_id: UUID of the UOW
        
        Returns:
            Dict with full UOW data: status, attributes, content_hash, interaction_count, interaction_policy, etc.
        
        Raises:
            NotFoundError: If UOW does not exist
        """
        pass

    @abstractmethod
    def update_state(
        self,
        uow_id: UUID,
        new_status: str,
        payload: Dict[str, Any],
        interaction_policy: Optional[Dict[str, Any]] = None,
        auto_increment: bool = True
    ) -> Dict[str, Any]:
        """
        Update UOW state with automatic state hash computation.
        
        **Constitutional Requirement (Article XVII):**
        - Computes content_hash = SHA-256(normalized attributes)
        - Records previous_state_hash before update
        - Appends to uow_history (immutable audit trail)
        - Conditionally increments interaction_count based on auto_increment flag
        
        **Constitutional Requirement (Article IX):**
        - interaction_policy is immutable after creation; attempts to modify are ignored
        
        Args:
            uow_id: UUID of the UOW
            new_status: New status (e.g., "ACTIVE", "COMPLETED", "PENDING_PILOT_APPROVAL")
            payload: Dict of attributes to merge into UOW.attributes
            interaction_policy: IGNORED - immutable after creation (Constitutional Article IX)
            auto_increment: If True, increment interaction_count. If False (for resume/clarification),
                          keep count unchanged. Only Guard evaluation auto-increments.
        
        Returns:
            Updated UOW dict with new content_hash and status
        
        Raises:
            NotFoundError: If UOW does not exist
            StateDriftException: If content_hash verification fails
        """
        pass

    @abstractmethod
    def append_history(
        self,
        uow_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
        previous_hash: str
    ) -> None:
        """
        Append immutable history record.
        
        **Constitutional Requirement (Article XVII):**
        - Append-only; never update/delete existing records
        - Records previous_state_hash for drift detection
        - Includes event_type, payload, timestamp
        
        Args:
            uow_id: UUID of the UOW
            event_type: Type of event (e.g., "STATE_TRANSITION", "CONSTITUTIONAL_WAIVER", "PILOT_OVERRIDE")
            payload: Event metadata
            previous_hash: Hash before this event (for audit trail)
        
        Raises:
            NotFoundError: If UOW does not exist
        """
        pass

    @abstractmethod
    def find_by_status(self, status: str, instance_id: Optional[UUID] = None) -> list:
        """
        Find all UOWs with given status.
        
        Args:
            status: Status to filter by (e.g., "ACTIVE", "PENDING_PILOT_APPROVAL")
            instance_id: Optional filter by instance
        
        Returns:
            List of UOW dicts
        """
        pass

    @abstractmethod
    def find_by_interaction_limit(self, instance_id: UUID) -> list:
        """
        Find all UOWs that have exceeded max_interactions (Ambiguity Lock).
        
        Returns:
            List of UOWs with interaction_count >= max_interactions
        """
        pass

    @abstractmethod
    def get_history(self, uow_id: UUID, limit: int = 100) -> list:
        """
        Retrieve history for a UOW.
        
        Args:
            uow_id: UUID of the UOW
            limit: Max records to return (default 100)
        
        Returns:
            List of history records, ordered by timestamp (newest last)
        """
        pass
