"""
Phase 3: Database Persistence Models

SQLAlchemy models for storing intervention requests in a relational database.
This replaces the in-memory InterventionStore with persistent storage.

Models:
- Intervention: Core intervention request table
- InterventionHistory: Archived/completed interventions
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Integer,
    Float,
    Boolean,
    Index,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Create declarative base for Phase 3 models
Phase3Base = declarative_base()


class Intervention(Phase3Base):
    """
    Core intervention request model.
    
    Represents a single intervention request that requires pilot action.
    Tracks from creation through completion/rejection/expiration.
    """

    __tablename__ = "interventions"
    __table_args__ = (
        Index("idx_request_id", "request_id", unique=True),
        Index("idx_uow_id", "uow_id"),
        Index("idx_status", "status"),
        Index("idx_priority", "priority"),
        Index("idx_created_at", "created_at"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_assigned_to", "assigned_to"),
    )

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Request identification
    request_id = Column(String(255), unique=True, nullable=False, comment="Unique request ID")
    uow_id = Column(String(255), nullable=False, comment="Associated Unit of Work ID")

    # Request type and status
    intervention_type = Column(
        String(50),
        nullable=False,
        comment="Type: kill_switch, clarification, waive_violation, resume, cancel",
    )
    status = Column(
        String(50),
        nullable=False,
        default="PENDING",
        comment="Status: PENDING, IN_PROGRESS, APPROVED, REJECTED, EXPIRED, COMPLETED",
    )
    priority = Column(
        String(20),
        nullable=False,
        default="normal",
        comment="Priority level: critical, high, normal, low",
    )

    # Request content
    title = Column(String(255), nullable=False, comment="Human-readable title")
    description = Column(String(2000), nullable=False, comment="Detailed description")
    context = Column(JSON, default={}, nullable=False, comment="Additional context (JSON)")

    # Timing
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        comment="Request creation timestamp",
    )
    expires_at = Column(
        DateTime,
        nullable=True,
        comment="Request expiration timestamp",
    )
    updated_at = Column(
        DateTime,
        nullable=True,
        comment="Last update timestamp",
    )

    # Pilot/Actor info
    required_role = Column(
        String(50),
        nullable=False,
        default="OPERATOR",
        comment="Minimum role required to take action",
    )
    assigned_to = Column(
        String(255),
        nullable=True,
        comment="Pilot ID this request is assigned to",
    )

    # Action info
    action_reason = Column(
        String(1000),
        nullable=True,
        comment="Reason for pilot's action (approve/reject)",
    )
    action_timestamp = Column(
        DateTime,
        nullable=True,
        comment="When pilot took action",
    )

    # Metadata
    is_archived = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this has been moved to history",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "uow_id": self.uow_id,
            "intervention_type": self.intervention_type,
            "status": self.status,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "context": self.context or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "required_role": self.required_role,
            "assigned_to": self.assigned_to,
            "action_reason": self.action_reason,
            "action_timestamp": (
                self.action_timestamp.isoformat() if self.action_timestamp else None
            ),
        }

    def is_expired(self) -> bool:
        """Check if intervention has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self) -> str:
        return f"<Intervention({self.request_id}, {self.status})>"


class InterventionHistory(Phase3Base):
    """
    Archived intervention history.
    
    Stores completed, rejected, or expired interventions for audit trail.
    This is optional - Intervention table can be used directly with is_archived flag.
    """

    __tablename__ = "intervention_history"
    __table_args__ = (
        Index("idx_history_request_id", "request_id"),
        Index("idx_history_uow_id", "uow_id"),
        Index("idx_history_status", "status"),
        Index("idx_history_completed_at", "completed_at"),
    )

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Request identification (copy from Intervention)
    request_id = Column(String(255), nullable=False, comment="Original request ID")
    uow_id = Column(String(255), nullable=False, comment="Associated UOW ID")

    # Status at archival
    status = Column(String(50), nullable=False, comment="Final status")
    priority = Column(String(20), nullable=False, comment="Priority level at archival")

    # Timing
    created_at = Column(DateTime, nullable=False, comment="Original creation time")
    completed_at = Column(DateTime, nullable=False, comment="Archival timestamp")
    resolution_time_seconds = Column(
        Float,
        nullable=True,
        comment="Time from creation to resolution in seconds",
    )

    # Outcome
    assigned_to = Column(String(255), nullable=True, comment="Assigned pilot")
    action_reason = Column(String(1000), nullable=True, comment="Final action reason")

    # Archive metadata
    archived_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
        comment="When archived",
    )

    def __repr__(self) -> str:
        return f"<InterventionHistory({self.request_id}, {self.status})>"


# Database manager for Phase 3
class Phase3DatabaseManager:
    """Manages Phase 3 intervention database connections."""

    def __init__(self, database_url: str = "sqlite:///interventions.db"):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def create_schema(self) -> None:
        """Create database schema."""
        Phase3Base.metadata.create_all(self.engine)

    def drop_schema(self) -> None:
        """Drop all tables."""
        Phase3Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get new database session."""
        return self.SessionLocal()


__all__ = [
    "Phase3Base",
    "Intervention",
    "InterventionHistory",
    "Phase3DatabaseManager",
]
