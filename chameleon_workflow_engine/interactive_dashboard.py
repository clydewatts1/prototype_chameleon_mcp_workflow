"""
Interactive Dashboard Backend: Real-Time Pilot Intervention API

Provides:
1. WebSocket endpoint for real-time intervention request updates
2. RESTful endpoints for intervention history and analytics
3. Dashboard-ready JSON structures for UI consumption
4. Integration with Pilot endpoints (JWT + RBAC)

Constitutional Reference: Article XV (Pilot Sovereignty) - Real-time intervention management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import logging
import json
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


# ============================================================================
# Dashboard Data Models
# ============================================================================


class InterventionStatus(str, Enum):
    """Status of an intervention request."""
    PENDING = "PENDING"      # Awaiting pilot action
    APPROVED = "APPROVED"    # Pilot approved
    REJECTED = "REJECTED"    # Pilot rejected
    EXPIRED = "EXPIRED"      # Request timed out
    IN_PROGRESS = "IN_PROGRESS"  # Pilot actively working
    COMPLETED = "COMPLETED"  # Pilot completed action


class InterventionType(str, Enum):
    """Type of intervention needed."""
    KILL_SWITCH = "kill_switch"       # Emergency stop
    CLARIFICATION = "clarification"    # Need pilot clarity
    WAIVE_VIOLATION = "waive_violation"  # Override violation
    RESUME = "resume"                  # Resume paused UOW
    CANCEL = "cancel"                  # Cancel UOW


@dataclass
class InterventionRequest:
    """Intervention request data structure."""
    
    request_id: str
    uow_id: str
    intervention_type: InterventionType
    status: InterventionStatus
    priority: str  # "critical", "high", "normal", "low"
    
    # Request content
    title: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Pilot info
    required_role: str = "OPERATOR"  # Minimum role required
    assigned_to: Optional[str] = None  # Assigned pilot
    
    # Action info
    action_reason: Optional[str] = None  # Why pilot took action
    action_timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            k: v.value if isinstance(v, Enum) else v
            for k, v in asdict(self).items()
        }
    
    def is_expired(self) -> bool:
        """Check if request has expired."""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expires
        except (ValueError, AttributeError):
            return False


@dataclass
class DashboardMetrics:
    """Dashboard metrics for analytics."""
    
    total_interventions: int = 0
    pending_interventions: int = 0
    approved_interventions: int = 0
    rejected_interventions: int = 0
    avg_resolution_time_seconds: float = 0.0
    
    # By type
    by_type: Dict[str, int] = field(default_factory=dict)
    
    # By priority
    by_priority: Dict[str, int] = field(default_factory=dict)
    
    # Pilot stats
    top_pilots: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return asdict(self)


# ============================================================================
# Intervention Request Store (In-Memory for Now, upgradeable to DB)
# ============================================================================


class InterventionStore:
    """
    Central store for intervention requests.
    
    In-memory implementation for Phase 2.
    Future: Store in database (UnitsOfWork + custom tables).
    """

    def __init__(self):
        """Initialize empty store."""
        self.requests: Dict[str, InterventionRequest] = {}
        self.history: List[InterventionRequest] = []

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
            context: Additional context (UOW attributes, etc.)
            required_role: Minimum role required
            expires_in_seconds: How long until request expires
        
        Returns:
            InterventionRequest instance
        """
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_seconds:
            expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
        
        request = InterventionRequest(
            request_id=request_id,
            uow_id=uow_id,
            intervention_type=intervention_type,
            status=InterventionStatus.PENDING,
            priority=priority,
            title=title,
            description=description,
            context=context or {},
            required_role=required_role,
            expires_at=expires_at,
            created_at=now.isoformat(),
        )
        
        self.requests[request_id] = request
        logger.info(f"Intervention request created: {request_id} (type={intervention_type})")
        
        return request

    def get_request(self, request_id: str) -> Optional[InterventionRequest]:
        """Get request by ID."""
        return self.requests.get(request_id)

    def update_request(
        self,
        request_id: str,
        status: InterventionStatus,
        action_reason: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Optional[InterventionRequest]:
        """
        Update request status.
        
        Args:
            request_id: Request ID
            status: New status
            action_reason: Why pilot took action
            assigned_to: Pilot ID (if assigning)
        
        Returns:
            Updated InterventionRequest or None
        """
        request = self.requests.get(request_id)
        if not request:
            return None
        
        request.status = status
        request.updated_at = datetime.now(timezone.utc).isoformat()
        request.action_reason = action_reason
        request.action_timestamp = datetime.now(timezone.utc).isoformat()
        
        if assigned_to:
            request.assigned_to = assigned_to
        
        logger.info(f"Intervention request updated: {request_id} → {status}")
        
        # Move to history if terminal state
        if status in [InterventionStatus.APPROVED, InterventionStatus.REJECTED, InterventionStatus.COMPLETED]:
            self.history.append(request)
            del self.requests[request_id]
        
        return request

    def get_pending_requests(
        self,
        pilot_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[InterventionRequest]:
        """
        Get pending intervention requests.
        
        Args:
            pilot_id: Filter by assigned pilot (None = all)
            limit: Maximum results
        
        Returns:
            List of pending InterventionRequest
        """
        requests = [
            r for r in self.requests.values()
            if r.status == InterventionStatus.PENDING
        ]
        
        if pilot_id:
            requests = [r for r in requests if r.assigned_to == pilot_id]
        
        # Sort by priority and age
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        requests.sort(
            key=lambda r: (
                priority_order.get(r.priority, 999),
                r.created_at,
            )
        )
        
        return requests[:limit]

    def get_metrics(self) -> DashboardMetrics:
        """
        Calculate dashboard metrics.
        
        Returns:
            DashboardMetrics with aggregated stats
        """
        all_requests = list(self.requests.values()) + self.history
        
        metrics = DashboardMetrics()
        metrics.total_interventions = len(all_requests)
        
        # Count by status
        metrics.pending_interventions = len([r for r in self.requests.values() if r.status == InterventionStatus.PENDING])
        metrics.approved_interventions = len([r for r in all_requests if r.status == InterventionStatus.APPROVED])
        metrics.rejected_interventions = len([r for r in all_requests if r.status == InterventionStatus.REJECTED])
        
        # By type
        for request in all_requests:
            key = request.intervention_type.value
            metrics.by_type[key] = metrics.by_type.get(key, 0) + 1
        
        # By priority
        for request in all_requests:
            metrics.by_priority[request.priority] = metrics.by_priority.get(request.priority, 0) + 1
        
        # Resolution time
        resolved = [r for r in all_requests if r.action_timestamp]
        if resolved:
            times = []
            for r in resolved:
                try:
                    created = datetime.fromisoformat(r.created_at.replace("Z", "+00:00"))
                    action = datetime.fromisoformat(r.action_timestamp.replace("Z", "+00:00"))
                    times.append((action - created).total_seconds())
                except (ValueError, AttributeError):
                    pass
            
            if times:
                metrics.avg_resolution_time_seconds = sum(times) / len(times)
        
        # Top pilots
        pilot_counts: Dict[str, int] = {}
        for r in all_requests:
            if r.assigned_to:
                pilot_counts[r.assigned_to] = pilot_counts.get(r.assigned_to, 0) + 1
        
        metrics.top_pilots = [
            {"pilot_id": pid, "interventions": count}
            for pid, count in sorted(
                pilot_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]
        
        return metrics


# ============================================================================
# Global Intervention Store
# ============================================================================

_global_intervention_store: Optional[InterventionStore] = None


def initialize_intervention_store(store: Optional[InterventionStore] = None) -> InterventionStore:
    """
    Initialize the global intervention store.
    
    Args:
        store: Store instance to use. If None, creates default in-memory store.
    
    Returns:
        The initialized store.
    """
    global _global_intervention_store
    _global_intervention_store = store or InterventionStore()
    return _global_intervention_store


def get_intervention_store() -> InterventionStore:
    """Get global intervention store."""
    if _global_intervention_store is None:
        initialize_intervention_store()
    return _global_intervention_store


def set_intervention_store(store: InterventionStore) -> None:
    """Set global intervention store (for testing or runtime switching)."""
    global _global_intervention_store
    _global_intervention_store = store


# ============================================================================
# Dashboard Response Models
# ============================================================================


class DashboardResponse:
    """Base response model for dashboard API."""
    
    @staticmethod
    def pending_requests(
        requests: List[InterventionRequest],
        total: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Format pending requests response."""
        return {
            "success": True,
            "data": {
                "requests": [r.to_dict() for r in requests],
                "total": total,
                "count": len(requests),
                "limit": limit,
            }
        }

    @staticmethod
    def request_detail(request: InterventionRequest) -> Dict[str, Any]:
        """Format single request response."""
        return {
            "success": True,
            "data": request.to_dict()
        }

    @staticmethod
    def metrics(metrics: DashboardMetrics) -> Dict[str, Any]:
        """Format metrics response."""
        return {
            "success": True,
            "data": metrics.to_dict()
        }

    @staticmethod
    def action_result(
        request_id: str,
        status: InterventionStatus,
        message: str,
    ) -> Dict[str, Any]:
        """Format action result response."""
        return {
            "success": True,
            "data": {
                "request_id": request_id,
                "status": status.value,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

    @staticmethod
    def error(message: str, code: str = "ERROR") -> Dict[str, Any]:
        """Format error response."""
        return {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            }
        }


# ============================================================================
# WebSocket Message Handler
# ============================================================================


class WebSocketMessageHandler:
    """Handles WebSocket messages for real-time dashboard."""

    def __init__(self, store: Optional[InterventionStore] = None):
        """Initialize handler."""
        self.store = store or get_intervention_store()

    def handle_message(
        self,
        message_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle incoming WebSocket message.
        
        Message Types:
        - subscribe: Subscribe to updates
        - get_pending: Fetch pending requests
        - get_metrics: Fetch metrics
        - request_detail: Get single request details
        
        Args:
            message_type: Type of message
            payload: Message payload
        
        Returns:
            Response dict (will be JSON-serialized and sent to client)
        """
        try:
            if message_type == "subscribe":
                return self._handle_subscribe(payload)
            elif message_type == "get_pending":
                return self._handle_get_pending(payload)
            elif message_type == "get_metrics":
                return self._handle_get_metrics(payload)
            elif message_type == "request_detail":
                return self._handle_request_detail(payload)
            else:
                return DashboardResponse.error(f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            return DashboardResponse.error(f"Server error: {str(e)}")

    def _handle_subscribe(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscribe message (for future streaming)."""
        pilot_id = payload.get("pilot_id")
        return {
            "success": True,
            "data": {
                "subscribed": True,
                "pilot_id": pilot_id,
                "message": "Subscribed to intervention updates"
            }
        }

    def _handle_get_pending(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_pending message."""
        pilot_id = payload.get("pilot_id")
        limit = payload.get("limit", 50)
        
        requests = self.store.get_pending_requests(pilot_id, limit)
        
        # Get total count - support both in-memory and database stores
        if hasattr(self.store, 'requests'):
            # In-memory store
            total = len(self.store.requests)
        else:
            # Database store - get from metrics
            metrics = self.store.get_metrics()
            total = metrics.pending_interventions
        
        return DashboardResponse.pending_requests(
            requests,
            total,
            limit
        )

    def _handle_get_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_metrics message."""
        metrics = self.store.get_metrics()
        return DashboardResponse.metrics(metrics)

    def _handle_request_detail(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request_detail message."""
        request_id = payload.get("request_id")
        
        request = self.store.get_request(request_id)
        if not request:
            return DashboardResponse.error(f"Request not found: {request_id}", "NOT_FOUND")
        
        return DashboardResponse.request_detail(request)


# ============================================================================
# Example Usage
# ============================================================================


def example_dashboard_usage():
    """
    Example: Using the interactive dashboard backend.
    
    In FastAPI server.py:
    
        from chameleon_workflow_engine.interactive_dashboard import (
            get_intervention_store,
            InterventionType,
            InterventionStatus,
            WebSocketMessageHandler
        )
        
        # Create intervention request when ambiguity detected
        store = get_intervention_store()
        request = store.create_request(
            request_id="req-001",
            uow_id="uow-uuid",
            intervention_type=InterventionType.CLARIFICATION,
            title="Invoice Clarification Needed",
            description="Cannot determine vendor from invoice",
            priority="high",
            context={"invoice_id": "INV-12345", "extracted_vendor": None}
        )
        
        # Pilot gets pending requests
        requests = store.get_pending_requests(pilot_id="pilot-001")
        
        # WebSocket handler processes messages
        handler = WebSocketMessageHandler()
        response = handler.handle_message(
            "get_pending",
            {"pilot_id": "pilot-001", "limit": 20}
        )
        
        # Pilot approves clarification
        store.update_request(
            "req-001",
            InterventionStatus.APPROVED,
            action_reason="Vendor identified from email domain",
            assigned_to="pilot-001"
        )
        
        # Get metrics
        metrics = store.get_metrics()
        print(f"Pending: {metrics.pending_interventions}, Approved: {metrics.approved_interventions}")
    """
    pass
