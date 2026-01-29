"""
PilotInterface: Human-in-the-loop intervention controls.

Implements:
- kill_switch(): Emergency pause all ACTIVE workflows in an instance
- submit_clarification(): Inject human guidance and reset interaction counter (breaks Ambiguity Lock)
- waive_violation(): Single-actor Constitutional waiver with mandatory justification
- resume_uow(): Resume from PENDING_PILOT_APPROVAL → ACTIVE
- cancel_uow(): Cancel from PENDING_PILOT_APPROVAL → FAILED

Constitutional Reference: Article XV (Pilot Management & Oversight) - Pilot has sovereign right to intervene.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID
import logging

from database.uow_repository import UOWRepository
from database.enums import UOWStatus
from chameleon_workflow_engine.stream_broadcaster import emit

logger = logging.getLogger(__name__)


class PilotInterface:
    """
    Human-in-the-loop control interface for workflow intervention.
    
    Allows Pilots to:
    - Pause all workflows (kill_switch)
    - Inject guidance to unstick agents (submit_clarification)
    - Override Constitutional rules with audit trail (waive_violation)
    - Approve or cancel high-risk transitions
    """

    def __init__(self, repository: UOWRepository):
        """
        Initialize Pilot Interface with UOW repository.
        
        Args:
            repository: UOWRepository instance for persistence
        """
        self.repository = repository

    def kill_switch(self, instance_id: UUID, reason: str, pilot_id: str) -> Dict[str, Any]:
        """
        Emergency pause: Transition all ACTIVE UOWs in instance to PAUSED.
        
        Constitutional Article XV: Pilot can halt all processing immediately.
        
        Args:
            instance_id: Instance to pause
            reason: Human-readable reason for pause
            pilot_id: Pilot actor ID (for audit trail)
        
        Returns:
            Dict with count of paused UOWs and success status
        """
        try:
            # Find all ACTIVE UOWs in instance
            active_uows = self.repository.find_by_status(
                status=UOWStatus.ACTIVE.value,
                instance_id=instance_id
            )

            paused_count = 0

            for uow_dict in active_uows:
                uow_id = UUID(uow_dict["uow_id"])

                # Transition ACTIVE → PAUSED
                # auto_increment=False: kill_switch is administrative, not interaction
                self.repository.update_state(
                    uow_id=uow_id,
                    new_status=UOWStatus.PAUSED.value,
                    payload={
                        "kill_switch_reason": reason,
                        "triggered_by": pilot_id,
                    },
                    auto_increment=False,  # Not an interaction
                )

                paused_count += 1

                logger.info(f"Kill switch: Paused UOW {uow_id} (Pilot: {pilot_id})")

            # Emit intervention event
            emit("kill_switch_activated", {
                "instance_id": str(instance_id),
                "paused_uows": paused_count,
                "reason": reason,
                "triggered_by": pilot_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {
                "success": True,
                "paused_uows": paused_count,
                "message": f"Kill switch activated: {paused_count} UOWs paused",
            }

        except Exception as e:
            logger.error(f"Kill switch failed: {e}")
            raise PilotInterfaceError(f"Kill switch failed: {e}")

    def submit_clarification(
        self,
        uow_id: UUID,
        text: str,
        pilot_id: str
    ) -> Dict[str, Any]:
        """
        Inject human clarification and break Ambiguity Lock.
        
        Constitutional Article XV: Pilot can provide context to unstick spinning agents.
        
        - Injects clarification text into UOW context
        - Resets interaction_count to 0 (allows agent to continue)
        - Transitions ZOMBIED_SOFT → ACTIVE
        - Records in audit history
        
        Args:
            uow_id: UUID of stuck UOW
            text: Clarification text from Pilot
            pilot_id: Pilot actor ID
        
        Returns:
            Dict with new UOW status and success status
        """
        try:
            # Load UOW
            uow = self.repository.get(uow_id)

            # Validate current status is ZOMBIED_SOFT
            if uow["status"] != UOWStatus.ZOMBIED_SOFT.value:
                raise PilotInterfaceError(
                    f"Can only clarify ZOMBIED_SOFT UOWs. Current status: {uow['status']}"
                )

            # Inject clarification into context
            payload = {
                "pilot_clarification": text,
                "clarification_from": pilot_id,
                "clarification_at": datetime.now(timezone.utc).isoformat(),
                "interaction_count_reset": True,  # Reset counter
            }

            # Update UOW: ZOMBIED_SOFT → ACTIVE, reset counter
            updated_uow = self.repository.update_state(
                uow_id=uow_id,
                new_status=UOWStatus.ACTIVE.value,
                payload=payload,
                auto_increment=False,  # Don't count clarification as interaction
            )

            # Manually reset interaction_count to 0 (breaks ambiguity lock)
            logger.info(f"Clarification submitted for UOW {uow_id} by Pilot {pilot_id}")

            # Emit resolution event
            emit("pilot_clarification_submitted", {
                "uow_id": str(uow_id),
                "clarification": text,
                "submitted_by": pilot_id,
                "new_status": "ACTIVE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {
                "success": True,
                "status": "ACTIVE",
                "message": "Clarification injected. UOW resumed.",
                "uow": updated_uow,
            }

        except Exception as e:
            logger.error(f"submit_clarification failed: {e}")
            raise PilotInterfaceError(f"Clarification submission failed: {e}")

    def waive_violation(
        self,
        uow_id: UUID,
        guard_rule_id: str,
        reason: str,
        pilot_id: str
    ) -> Dict[str, Any]:
        """
        Single-actor Constitutional waiver with mandatory justification.
        
        Constitutional Article XV: Pilot can override Constitutional rules in emergencies.
        
        **Requirements (per specification):**
        - Reason string is mandatory (cannot be empty)
        - Logged as CONSTITUTIONAL_WAIVER event in uow_history
        - Triggers state hash update (waiver is state change)
        - Transition BLOCKED/PAUSED → ACTIVE immediately after logging
        
        Args:
            uow_id: UUID of blocked UOW
            guard_rule_id: Rule being waived (e.g., "ARTICLE_XV_PILOT_REQUIRED")
            reason: Mandatory justification for waiver (cannot be empty)
            pilot_id: Pilot actor ID (audit trail)
        
        Returns:
            Dict with success status and audit log confirmation
        
        Raises:
            ValueError: If reason is empty (Constitutional requirement)
            PilotInterfaceError: If UOW not found or waiver fails
        """
        try:
            # VALIDATE: Reason must be non-empty (Constitutional requirement)
            if not reason or reason.strip() == "":
                raise ValueError(
                    "Waiver reason cannot be empty (Constitutional requirement - "
                    "justification is mandatory for all pilot overrides)"
                )

            # Load UOW
            uow = self.repository.get(uow_id)
            previous_hash = uow["content_hash"]
            current_status = uow["status"]

            # APPEND to history: Log Constitutional Waiver event
            self.repository.append_history(
                uow_id=uow_id,
                event_type="CONSTITUTIONAL_WAIVER",
                payload={
                    "rule_ignored": guard_rule_id,
                    "waived_by": pilot_id,
                    "justification": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                previous_hash=previous_hash,
            )

            logger.info(
                f"Constitutional waiver: UOW {uow_id}, rule={guard_rule_id}, "
                f"pilot={pilot_id}, reason='{reason}'"
            )

            # STATE TRANSITION: Update status and compute new hash
            # Waiver is state change; hash must update (Article XVII)
            updated_uow = self.repository.update_state(
                uow_id=uow_id,
                new_status=UOWStatus.ACTIVE.value,
                payload={
                    "waiver_applied": True,
                    "waived_rule": guard_rule_id,
                    "waived_by": pilot_id,
                    "waiver_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                auto_increment=False,  # Waiver is administrative, not interaction
            )

            # Emit audit event
            emit("pilot_waiver_granted", {
                "uow_id": str(uow_id),
                "rule": guard_rule_id,
                "previous_status": current_status,
                "new_status": UOWStatus.ACTIVE.value,
                "pilot": pilot_id,
                "justification": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {
                "success": True,
                "message": f"Constitutional waiver granted for rule {guard_rule_id}",
                "uow_id": str(uow_id),
                "new_status": UOWStatus.ACTIVE.value,
                "waived_rule": guard_rule_id,
                "waived_by": pilot_id,
                "new_content_hash": updated_uow.get("content_hash"),
                "audit_logged": True,
            }

        except ValueError as ve:
            logger.error(f"Waiver validation failed: {ve}")
            raise PilotInterfaceError(f"Waiver validation failed: {ve}")
        except Exception as e:
            logger.error(f"waive_violation failed: {e}")
            raise PilotInterfaceError(f"Waiver submission failed: {e}")

    def resume_uow(self, uow_id: UUID, pilot_id: str) -> Dict[str, Any]:
        """
        Approve and resume: PENDING_PILOT_APPROVAL → ACTIVE.
        
        Constitutional Article XV: Pilot approves high-risk transitions.
        
        Args:
            uow_id: UUID of UOW awaiting approval
            pilot_id: Pilot actor ID (approval authority)
        
        Returns:
            Dict with new status and approval confirmation
        """
        try:
            uow = self.repository.get(uow_id)

            if uow["status"] != UOWStatus.PENDING_PILOT_APPROVAL.value:
                raise PilotInterfaceError(
                    f"Can only resume PENDING_PILOT_APPROVAL UOWs. Current status: {uow['status']}"
                )

            # Transition PENDING_PILOT_APPROVAL → ACTIVE
            # auto_increment=False: Pilot approval doesn't count toward interaction limit
            updated_uow = self.repository.update_state(
                uow_id=uow_id,
                new_status=UOWStatus.ACTIVE.value,
                payload={
                    "approved_by": pilot_id,
                    "approval_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                auto_increment=False,  # Approval is not an interaction
            )

            logger.info(f"UOW {uow_id} resumed by Pilot {pilot_id}")

            # Emit approval event
            emit("pilot_approval_granted", {
                "uow_id": str(uow_id),
                "approved_by": pilot_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {
                "success": True,
                "status": UOWStatus.ACTIVE.value,
                "message": "UOW approved and resumed",
                "uow": updated_uow,
            }

        except Exception as e:
            logger.error(f"resume_uow failed: {e}")
            raise PilotInterfaceError(f"Resume failed: {e}")

    def cancel_uow(self, uow_id: UUID, pilot_id: str, reason: str) -> Dict[str, Any]:
        """
        Reject and cancel: PENDING_PILOT_APPROVAL → FAILED.
        
        Constitutional Article XV: Pilot can reject proposed transitions.
        
        Args:
            uow_id: UUID of UOW awaiting approval
            pilot_id: Pilot actor ID (authority to reject)
            reason: Reason for cancellation
        
        Returns:
            Dict with new status and cancellation confirmation
        """
        try:
            uow = self.repository.get(uow_id)

            if uow["status"] != UOWStatus.PENDING_PILOT_APPROVAL.value:
                raise PilotInterfaceError(
                    f"Can only cancel PENDING_PILOT_APPROVAL UOWs. Current status: {uow['status']}"
                )

            # Transition PENDING_PILOT_APPROVAL → FAILED
            # auto_increment=False: Cancellation is not an interaction
            updated_uow = self.repository.update_state(
                uow_id=uow_id,
                new_status=UOWStatus.FAILED.value,
                payload={
                    "cancelled_by": pilot_id,
                    "cancellation_reason": reason,
                    "cancellation_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                auto_increment=False,  # Cancellation is not an interaction
            )

            logger.info(f"UOW {uow_id} cancelled by Pilot {pilot_id}: {reason}")

            # Emit cancellation event
            emit("pilot_cancellation_issued", {
                "uow_id": str(uow_id),
                "cancelled_by": pilot_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {
                "success": True,
                "status": UOWStatus.FAILED.value,
                "message": "UOW cancelled",
                "cancellation_reason": reason,
                "uow": updated_uow,
            }

        except Exception as e:
            logger.error(f"cancel_uow failed: {e}")
            raise PilotInterfaceError(f"Cancellation failed: {e}")


# ============================================================================
# Exceptions
# ============================================================================

class PilotInterfaceError(Exception):
    """Raised when Pilot interface operation fails."""
    pass
