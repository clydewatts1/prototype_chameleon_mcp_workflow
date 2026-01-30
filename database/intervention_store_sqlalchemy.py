"""
Phase 3: SQLAlchemy Intervention Store Adapter

Implements the InterventionStore interface using SQLAlchemy for persistence.
Drop-in replacement for the in-memory store used in Phase 2.

This adapter:
- Provides CRUD operations for interventions
- Supports filtering by status, priority, pilot, and type
- Implements pagination for large result sets
- Calculates metrics from persisted data
- Maintains compatibility with Phase 2 API
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from chameleon_workflow_engine.interactive_dashboard import (
    InterventionRequest,
    InterventionStatus,
    InterventionType,
    DashboardMetrics,
)
from database.models_phase3 import Intervention, InterventionHistory


class InterventionStoreSQLAlchemy:
    """
    SQLAlchemy-backed implementation of InterventionStore.
    
    Provides persistence while maintaining compatibility with the Phase 2 in-memory API.
    """

    def __init__(self, session: Session):
        """
        Initialize with database session.
        
        Args:
            session: SQLAlchemy Session for database operations
        """
        self.session = session

    # ========================================================================
    # CRUD Operations
    # ========================================================================

    def create_request(
        self,
        request_id: str,
        uow_id: str,
        intervention_type: InterventionType,
        title: str,
        description: str,
        priority: str = "normal",
        context: Optional[Dict[str, Any]] = None,
        required_role: str = "OPERATOR",
        expires_in_seconds: int = 3600,
    ) -> InterventionRequest:
        """
        Create a new intervention request.
        
        Args:
            request_id: Unique request ID
            uow_id: Associated UOW ID
            intervention_type: Type of intervention
            title: Human-readable title
            description: Detailed description
            priority: "critical", "high", "normal", "low"
            context: Additional context (JSON)
            required_role: Minimum role required
            expires_in_seconds: Expiration timeout in seconds
        
        Returns:
            InterventionRequest dataclass
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_seconds:
            expires_at = now + timedelta(seconds=expires_in_seconds)

        # Convert to UTC-naive for SQLite compatibility
        now_naive = now.replace(tzinfo=None)
        expires_at_naive = expires_at.replace(tzinfo=None) if expires_at else None

        # Create database record
        db_intervention = Intervention(
            request_id=request_id,
            uow_id=uow_id,
            intervention_type=(
                intervention_type.value
                if isinstance(intervention_type, InterventionType)
                else intervention_type
            ),
            status="PENDING",
            priority=priority,
            title=title,
            description=description,
            context=context or {},
            required_role=required_role,
            expires_at=expires_at_naive,
            created_at=now_naive,
        )

        self.session.add(db_intervention)
        self.session.commit()

        return self._db_to_request(db_intervention)

    def get_request(self, request_id: str) -> Optional[InterventionRequest]:
        """
        Get intervention request by ID.
        
        Args:
            request_id: Request ID to retrieve
        
        Returns:
            InterventionRequest or None if not found
        """
        db_intervention = self.session.query(Intervention).filter(
            Intervention.request_id == request_id
        ).first()

        if not db_intervention:
            return None

        return self._db_to_request(db_intervention)

    def update_request(
        self,
        request_id: str,
        status: InterventionStatus,
        action_reason: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Optional[InterventionRequest]:
        """
        Update intervention request status.
        
        Args:
            request_id: Request ID to update
            status: New status
            action_reason: Reason for action
            assigned_to: Assigned pilot ID
        
        Returns:
            Updated InterventionRequest or None
        """
        db_intervention = self.session.query(Intervention).filter(
            Intervention.request_id == request_id
        ).first()

        if not db_intervention:
            return None

        now = datetime.now(timezone.utc)
        now_naive = now.replace(tzinfo=None)
        db_intervention.status = (
            status.value if isinstance(status, InterventionStatus) else status
        )
        db_intervention.updated_at = now_naive
        db_intervention.action_reason = action_reason
        db_intervention.action_timestamp = now_naive

        if assigned_to:
            db_intervention.assigned_to = assigned_to

        # Move to history if terminal state
        if status in [
            InterventionStatus.APPROVED,
            InterventionStatus.REJECTED,
            InterventionStatus.COMPLETED,
        ]:
            # Create history record
            resolution_seconds = None
            if db_intervention.created_at:
                resolution_seconds = (now_naive - db_intervention.created_at).total_seconds()
            
            history = InterventionHistory(
                request_id=db_intervention.request_id,
                uow_id=db_intervention.uow_id,
                status=db_intervention.status,
                priority=db_intervention.priority,
                created_at=db_intervention.created_at,
                completed_at=now_naive,
                resolution_time_seconds=resolution_seconds,
                assigned_to=assigned_to,
                action_reason=action_reason,
            )
            self.session.add(history)

            # Mark as archived
            db_intervention.is_archived = True

        self.session.commit()
        return self._db_to_request(db_intervention)

    # ========================================================================
    # Query Operations
    # ========================================================================

    def get_pending_requests(
        self,
        pilot_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[InterventionRequest]:
        """
        Get pending intervention requests.
        
        Args:
            pilot_id: Filter by assigned pilot (None = all)
            limit: Maximum results to return
        
        Returns:
            List of pending InterventionRequest (sorted by priority, then age)
        """
        query = self.session.query(Intervention).filter(
            and_(
                Intervention.status == "PENDING",
                Intervention.is_archived == False,
            )
        )

        if pilot_id:
            query = query.filter(Intervention.assigned_to == pilot_id)

        # Sort by priority (critical first) then by created_at (oldest first)
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}

        db_interventions = query.all()

        # Python-side sorting for priority
        db_interventions.sort(
            key=lambda r: (
                priority_order.get(r.priority, 999),
                r.created_at or datetime.now(timezone.utc),
            )
        )

        return [
            self._db_to_request(db_int) for db_int in db_interventions[:limit]
        ]

    def get_requests_by_status(
        self,
        status: InterventionStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InterventionRequest]:
        """
        Get requests filtered by status.
        
        Args:
            status: Status to filter by
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of InterventionRequest matching status
        """
        db_interventions = (
            self.session.query(Intervention)
            .filter(
                Intervention.status == (
                    status.value if isinstance(status, InterventionStatus) else status
                )
            )
            .order_by(Intervention.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [self._db_to_request(db_int) for db_int in db_interventions]

    def get_requests_by_priority(
        self,
        priority: str,
        limit: int = 50,
    ) -> List[InterventionRequest]:
        """
        Get requests filtered by priority.
        
        Args:
            priority: Priority level to filter
            limit: Maximum results
        
        Returns:
            List of InterventionRequest with matching priority
        """
        db_interventions = (
            self.session.query(Intervention)
            .filter(Intervention.priority == priority)
            .order_by(Intervention.created_at.desc())
            .limit(limit)
            .all()
        )

        return [self._db_to_request(db_int) for db_int in db_interventions]

    def get_requests_by_pilot(
        self,
        pilot_id: str,
        status: Optional[InterventionStatus] = None,
        limit: int = 50,
    ) -> List[InterventionRequest]:
        """
        Get requests assigned to specific pilot.
        
        Args:
            pilot_id: Pilot ID to filter
            status: Optional status filter
            limit: Maximum results
        
        Returns:
            List of InterventionRequest assigned to pilot
        """
        query = self.session.query(Intervention).filter(
            Intervention.assigned_to == pilot_id
        )

        if status:
            query = query.filter(
                Intervention.status == (
                    status.value if isinstance(status, InterventionStatus) else status
                )
            )

        db_interventions = (
            query.order_by(Intervention.created_at.desc())
            .limit(limit)
            .all()
        )

        return [self._db_to_request(db_int) for db_int in db_interventions]

    # ========================================================================
    # Metrics and Analytics
    # ========================================================================

    def get_metrics(self) -> DashboardMetrics:
        """
        Calculate dashboard metrics from persisted data.
        
        Returns:
            DashboardMetrics with aggregated statistics
        """
        # Count by status (pending only from active table)
        pending_count = self.session.query(func.count(Intervention.id)).filter(
            Intervention.status == "PENDING"
        ).scalar() or 0

        # Count from history (completed requests)
        approved_count = self.session.query(func.count(InterventionHistory.id)).filter(
            InterventionHistory.status == "APPROVED"
        ).scalar() or 0

        rejected_count = self.session.query(func.count(InterventionHistory.id)).filter(
            InterventionHistory.status == "REJECTED"
        ).scalar() or 0

        total = pending_count + approved_count + rejected_count

        # By type (from active interventions)
        by_type_query = (
            self.session.query(
                Intervention.intervention_type, func.count(Intervention.id)
            )
            .group_by(Intervention.intervention_type)
            .all()
        )
        by_type = {type_name: count for type_name, count in by_type_query}

        # By priority (from active interventions)
        by_priority_query = (
            self.session.query(Intervention.priority, func.count(Intervention.id))
            .group_by(Intervention.priority)
            .all()
        )
        by_priority = {priority: count for priority, count in by_priority_query}

        # Calculate average resolution time
        avg_resolution = (
            self.session.query(func.avg(InterventionHistory.resolution_time_seconds))
            .scalar()
        )
        avg_resolution_seconds = float(avg_resolution) if avg_resolution else 0.0

        # Top pilots (by number of resolved interventions)
        top_pilots_query = (
            self.session.query(
                InterventionHistory.assigned_to,
                func.count(InterventionHistory.id).label("intervention_count"),
            )
            .filter(InterventionHistory.assigned_to.isnot(None))
            .group_by(InterventionHistory.assigned_to)
            .order_by(func.count(InterventionHistory.id).desc())
            .limit(10)
            .all()
        )

        top_pilots = [
            {
                "pilot_id": pilot_id,
                "interventions": count,
            }
            for pilot_id, count in top_pilots_query
        ]

        return DashboardMetrics(
            total_interventions=total,
            pending_interventions=pending_count,
            approved_interventions=approved_count,
            rejected_interventions=rejected_count,
            avg_resolution_time_seconds=avg_resolution_seconds,
            by_type=by_type,
            by_priority=by_priority,
            top_pilots=top_pilots,
        )

    # ========================================================================
    # Bulk Operations
    # ========================================================================

    def mark_expired(self) -> int:
        """
        Mark all expired interventions as EXPIRED.
        
        Returns:
            Number of interventions marked as expired
        """
        now = datetime.now(timezone.utc)
        now_naive = now.replace(tzinfo=None)

        expired = self.session.query(Intervention).filter(
            and_(
                Intervention.expires_at.isnot(None),
                Intervention.expires_at <= now_naive,
                Intervention.status == "PENDING",
            )
        ).all()

        count = 0
        for intervention in expired:
            intervention.status = "EXPIRED"
            intervention.updated_at = now_naive
            count += 1

        self.session.commit()
        return count

    def clear_archived(self, days: int = 90) -> int:
        """
        Delete archived interventions older than specified days.
        
        Args:
            days: Only delete records older than this many days
        
        Returns:
            Number of records deleted
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)

        count = (
            self.session.query(InterventionHistory)
            .filter(InterventionHistory.archived_at < cutoff_date)
            .delete()
        )

        self.session.commit()
        return count

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _db_to_request(self, db_intervention: Intervention) -> InterventionRequest:
        """
        Convert database model to InterventionRequest dataclass.
        
        Args:
            db_intervention: Intervention database model
        
        Returns:
            InterventionRequest dataclass
        """
        return InterventionRequest(
            request_id=db_intervention.request_id,
            uow_id=db_intervention.uow_id,
            intervention_type=InterventionType(db_intervention.intervention_type),
            status=InterventionStatus(db_intervention.status),
            priority=db_intervention.priority,
            title=db_intervention.title,
            description=db_intervention.description,
            context=db_intervention.context or {},
            created_at=db_intervention.created_at.isoformat(),
            expires_at=db_intervention.expires_at.isoformat()
            if db_intervention.expires_at
            else None,
            updated_at=db_intervention.updated_at.isoformat()
            if db_intervention.updated_at
            else None,
            required_role=db_intervention.required_role,
            assigned_to=db_intervention.assigned_to,
            action_reason=db_intervention.action_reason,
            action_timestamp=db_intervention.action_timestamp.isoformat()
            if db_intervention.action_timestamp
            else None,
        )


__all__ = ["InterventionStoreSQLAlchemy"]
