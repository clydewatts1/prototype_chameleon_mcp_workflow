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
    BETA = "BETA"    # The Processor - decomposes Base UOW into Child UOWs
    OMEGA = "OMEGA"  # The Terminal - reconciles and finalizes the complete UOW set
    EPSILON = "EPSILON"  # The Physician - error handling role for remediating explicit data failures
    TAU = "TAU"      # The Chronometer - timeout role for managing stale or expired tokens



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
    INBOUND = "INBOUND"    # Flow into the role
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
    """
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
