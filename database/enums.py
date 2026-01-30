"""
Enumerations for the Chameleon Workflow Engine Database Schema.

This module defines all the enumeration types used across both Tier 1 (Templates)
and Tier 2 (Instance) database tiers.
"""

from enum import Enum


class RoleType(str, Enum):
    """
    Functional classification of roles within the workflow engine.

    Based on Constitution Article V.
    """

    ALPHA = "ALPHA"  # The Origin - instantiates the Base UOW
    BETA = "BETA"  # The Processor - decomposes Base UOW into Child UOWs
    OMEGA = "OMEGA"  # The Terminal - reconciles and finalizes the complete UOW set
    EPSILON = (
        "EPSILON"  # The Physician - error handling role for remediating explicit data failures
    )
    TAU = "TAU"  # The Chronometer - timeout role for managing stale or expired tokens


class DecompositionStrategy(str, Enum):
    """
    Strategy for how Beta roles decompose tasks.

    Based on Constitution Article V.
    """

    HOMOGENEOUS = "HOMOGENEOUS"  # All Child UOWs must be of the same type
    HETEROGENEOUS = "HETEROGENEOUS"  # Allows diverse UOW types within a single set


class ComponentDirection(str, Enum):
    """
    Direction of data flow relative to a role.
    """

    INBOUND = "INBOUND"  # Flow into the role
    OUTBOUND = "OUTBOUND"  # Flow out of the role


class GuardianType(str, Enum):
    """
    Type of guardian logic gate.

    Based on Constitution Articles VI, VII, IX.
    """

    CERBERUS = "CERBERUS"  # Three-headed synchronization check for parent-child UOW sets
    PASS_THRU = "PASS_THRU"  # Identity-only validation for rapid transit
    CRITERIA_GATE = "CRITERIA_GATE"  # Data-driven threshold enforcement
    DIRECTIONAL_FILTER = "DIRECTIONAL_FILTER"  # Routes UOW sets based on attribute results
    TTL_CHECK = "TTL_CHECK"  # Time-to-live validation based on age of UOW
    COMPOSITE = "COMPOSITE"  # Chains multiple guard checks with AND/OR logic
    CONDITIONAL_INJECTOR = "CONDITIONAL_INJECTOR"  # Dynamic Context Injection - mutates execution context at runtime


class InstanceStatus(str, Enum):
    """
    Deployment health status for an instance.
    """

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class ActorType(str, Enum):
    """
    Type of actor operating within the instance.

    Based on Constitution Article II.
    """

    HUMAN = "HUMAN"
    AI_AGENT = "AI_AGENT"
    SYSTEM = "SYSTEM"  # Auto role


class AssignmentStatus(str, Enum):
    """
    Status of actor-role assignments.
    """

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class UOWStatus(str, Enum):
    """
    Current state of a Unit of Work.
    
    Constitutional References:
    - PENDING_PILOT_APPROVAL: Article XV (Pilot Management & Oversight)
    - ZOMBIED_SOFT, ZOMBIED_DEAD: Article XII & XIII (Token Reclamation)
    - PAUSED: Article XV (Emergency pause via kill_switch)
    - FAILED_SECURITY_BREACH: Article XVII (State hash mismatch detection)
    - ARCHIVED: Article IV (Final lifecycle state post-REFINEMENT_ANALYSIS)
    """

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PENDING_PILOT_APPROVAL = "PENDING_PILOT_APPROVAL"  # High-risk transition awaiting Pilot approval
    ZOMBIED_SOFT = "ZOMBIED_SOFT"  # Recoverable: transient failure or ambiguity lock
    ZOMBIED_DEAD = "ZOMBIED_DEAD"  # Terminal: fatal error, requires manual intervention
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"  # Manually paused by Pilot kill_switch
    FAILED_SECURITY_BREACH = "FAILED_SECURITY_BREACH"  # State hash mismatch detected
    ARCHIVED = "ARCHIVED"  # Post-refinement analysis, audit retention


# ============================================================================
# Phase 3: Guard-Persistence Integration - Exception Classes
# ============================================================================

class ConstitutionalViolation(Exception):
    """
    Base exception for Constitutional violations.
    
    Raised when the Chameleon Workflow Constitution is violated.
    Implements Article I (The Guard's Mandate) enforcement.
    """
    pass


class GuardLayerBypassException(ConstitutionalViolation):
    """
    Raised when Article I, Section 3 (Guard Mandate) is violated.
    
    Indicates that a UOW operation attempted to bypass Guard authorization.
    The Guard acts as the supreme filter - no UOW state transition occurs
    without Guard approval.
    """
    pass


class GuardStateDriftException(ConstitutionalViolation):
    """
    Raised when Article XVII (Atomic Traceability) State Drift is detected.
    
    Indicates that a UOW's content_hash does not match its current attributes,
    suggesting unauthorized modification or system corruption.
    """
    pass
