"""
Database package for the Chameleon Workflow Engine.

This package implements an air-gapped two-tier database architecture:
- Tier 1 (Templates): Read-only blueprints in the Meta-Store
- Tier 2 (Instance): Runtime engine in the Instance-Store

Each tier uses its own declarative_base to ensure complete isolation.
"""

# Enums
from .enums import (
    RoleType,
    DecompositionStrategy,
    ComponentDirection,
    GuardianType,
    InstanceStatus,
    ActorType,
    AssignmentStatus,
    UOWStatus,
)

# Tier 1 Models (Templates)
from .models_template import (
    TemplateBase,
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
)

# Tier 2 Models (Instance)
from .models_instance import (
    InstanceBase,
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Guardians,
    Local_Actors,
    Local_Actor_Role_Assignments,
    Local_Role_Attributes,
    UnitsOfWork,
    UOW_Attributes,
    Interaction_Logs,
)

# Database Manager
from .manager import DatabaseManager

__all__ = [
    # Enums
    "RoleType",
    "DecompositionStrategy",
    "ComponentDirection",
    "GuardianType",
    "InstanceStatus",
    "ActorType",
    "AssignmentStatus",
    "UOWStatus",
    # Tier 1
    "TemplateBase",
    "Template_Workflows",
    "Template_Roles",
    "Template_Interactions",
    "Template_Components",
    "Template_Guardians",
    # Tier 2
    "InstanceBase",
    "Instance_Context",
    "Local_Workflows",
    "Local_Roles",
    "Local_Interactions",
    "Local_Components",
    "Local_Guardians",
    "Local_Actors",
    "Local_Actor_Role_Assignments",
    "Local_Role_Attributes",
    "UnitsOfWork",
    "UOW_Attributes",
    "Interaction_Logs",
    # Manager
    "DatabaseManager",
]
