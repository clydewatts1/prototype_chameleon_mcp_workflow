"""
Tier 2 Models: The Instance-Store (Runtime Engine)

This module defines the database models for the runtime instance tier.
These models represent the complete, self-contained universe for a running workflow.
All tables are read/write accessible by the engine and must include instance_id for isolation.

All tables use InstanceBase to ensure complete isolation from template models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, BigInteger, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from .enums import (
    RoleType, DecompositionStrategy, ComponentDirection, GuardianType,
    InstanceStatus, ActorType, AssignmentStatus, UOWStatus
)

# Separate declarative base for Instance tier (Tier 2)
InstanceBase = declarative_base()


class Instance_Context(InstanceBase):
    """
    Represents the 'World' or 'Tenant' for this deployment. It is the root of the isolation boundary.
    """
    __tablename__ = "instance_context"
    __table_args__ = {
        "comment": "Represents the 'World' or 'Tenant' for this deployment. It is the root of the isolation boundary."
    }

    instance_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="The Global ID for this specific deployment."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Finance_Dept_Instance')."
    )
    description = Column(
        Text,
        comment="Operational notes."
    )
    status = Column(
        String(50),
        nullable=False,
        default=InstanceStatus.ACTIVE.value,
        comment="Deployment health (ACTIVE, PAUSED, ARCHIVED)."
    )
    deployment_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this instance was cloned from the meta-store."
    )

    # Relationships
    workflows = relationship("Local_Workflows", back_populates="instance", cascade="all, delete-orphan")
    actors = relationship("Local_Actors", back_populates="instance", cascade="all, delete-orphan")
    role_attributes = relationship("Local_Role_Attributes", back_populates="instance", cascade="all, delete-orphan")
    units_of_work = relationship("UnitsOfWork", back_populates="instance", cascade="all, delete-orphan")
    uow_attributes = relationship("UOW_Attributes", back_populates="instance", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="instance", cascade="all, delete-orphan")


class Local_Workflows(InstanceBase):
    """
    A specific workflow definition active within this instance. Can be a Master or a Child dependency.
    """
    __tablename__ = "local_workflows"
    __table_args__ = {
        "comment": "A specific workflow definition active within this instance. Can be a Master or a Child dependency."
    }

    local_workflow_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique ID for this workflow within this instance."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The parent container."
    )
    original_workflow_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Traceability link to the source blueprint."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Local name of the workflow."
    )
    description = Column(
        Text,
        comment="Local description."
    )
    ai_context = Column(
        JSON,
        comment="Localized AI prompts."
    )
    version = Column(
        Integer,
        nullable=False,
        comment="The version of the blueprint used for this snapshot."
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Controls execution eligibility."
    )
    is_master = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Only one workflow in the instance can be True. This is the entry point."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="workflows")
    roles = relationship(
        "Local_Roles",
        foreign_keys="Local_Roles.local_workflow_id",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    interactions = relationship("Local_Interactions", back_populates="workflow", cascade="all, delete-orphan")
    components = relationship("Local_Components", back_populates="workflow", cascade="all, delete-orphan")
    guardians = relationship("Local_Guardians", back_populates="workflow", cascade="all, delete-orphan")
    units_of_work = relationship("UnitsOfWork", back_populates="workflow", cascade="all, delete-orphan")


class Local_Roles(InstanceBase):
    """
    The execution logic nodes. Cloned from Template_Roles.
    """
    __tablename__ = "local_roles"
    __table_args__ = {
        "comment": "The execution logic nodes. Cloned from Template_Roles."
    }

    role_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Role Name."
    )
    description = Column(
        Text,
        comment="Description."
    )
    ai_context = Column(
        JSON,
        comment="AI Instructions."
    )
    role_type = Column(
        String(50),
        nullable=False,
        comment="Functional classification (ALPHA, BETA, OMEGA, EPSILON, TAU)."
    )
    decomposition_strategy = Column(
        String(50),
        comment="How this role breaks down tasks."
    )
    is_recursive_gateway = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flag if this role spawns a sub-workflow."
    )
    linked_local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="SET NULL"),
        nullable=True,
        comment="Points to the Child Workflow hosted in this same instance if recursive."
    )

    # Relationships
    workflow = relationship(
        "Local_Workflows",
        foreign_keys=[local_workflow_id],
        back_populates="roles"
    )
    linked_workflow = relationship(
        "Local_Workflows",
        foreign_keys=[linked_local_workflow_id],
        post_update=True
    )
    components = relationship("Local_Components", back_populates="role", cascade="all, delete-orphan")
    assignments = relationship("Local_Actor_Role_Assignments", back_populates="role", cascade="all, delete-orphan")
    role_attributes = relationship("Local_Role_Attributes", back_populates="role", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="role", cascade="all, delete-orphan")


class Local_Interactions(InstanceBase):
    """
    The execution holding areas. Cloned from Template_Interactions.
    """
    __tablename__ = "local_interactions"
    __table_args__ = {
        "comment": "The execution holding areas. Cloned from Template_Interactions."
    }

    interaction_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Interaction Name."
    )
    description = Column(
        Text,
        comment="Description."
    )
    ai_context = Column(
        JSON,
        comment="AI Context."
    )
    stale_token_limit_seconds = Column(
        Integer,
        comment="Runtime configuration for Timeout (Chronos) logic."
    )

    # Relationships
    workflow = relationship("Local_Workflows", back_populates="interactions")
    components = relationship("Local_Components", back_populates="interaction", cascade="all, delete-orphan")
    units_of_work = relationship("UnitsOfWork", back_populates="current_interaction", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="interaction", cascade="all, delete-orphan")


class Local_Components(InstanceBase):
    """
    The execution connections. Cloned from Template_Components.
    """
    __tablename__ = "local_components"
    __table_args__ = {
        "comment": "The execution connections. Cloned from Template_Components."
    }

    component_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="Connection Endpoint A."
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="Connection Endpoint B."
    )
    direction = Column(
        String(50),
        nullable=False,
        comment="Flow direction."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Component Name."
    )
    description = Column(
        Text,
        comment="Description."
    )
    ai_context = Column(
        JSON,
        comment="AI Context."
    )

    # Relationships
    workflow = relationship("Local_Workflows", back_populates="components")
    interaction = relationship("Local_Interactions", back_populates="components")
    role = relationship("Local_Roles", back_populates="components")
    guardians = relationship("Local_Guardians", back_populates="component", cascade="all, delete-orphan")


class Local_Guardians(InstanceBase):
    """
    The active security gates. Cloned from Template_Guardians.
    """
    __tablename__ = "local_guardians"
    __table_args__ = {
        "comment": "The active security gates. Cloned from Template_Guardians."
    }

    guardian_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    component_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_components.component_id", ondelete="CASCADE"),
        nullable=False,
        comment="The pipe being guarded."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Guard Name."
    )
    description = Column(
        Text,
        comment="Description."
    )
    ai_context = Column(
        JSON,
        comment="AI Context."
    )
    type = Column(
        String(50),
        nullable=False,
        comment="Logic Class (CERBERUS, PASS_THRU, etc.)."
    )
    attributes = Column(
        JSON,
        comment="The runtime configuration logic (e.g., criteria rules)."
    )

    # Relationships
    workflow = relationship("Local_Workflows", back_populates="guardians")
    component = relationship("Local_Components", back_populates="guardians")


class Local_Actors(InstanceBase):
    """
    Identities authorized to operate within this specific Instance Context.
    """
    __tablename__ = "local_actors"
    __table_args__ = {
        "comment": "Identities authorized to operate within this specific Instance Context."
    }

    actor_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique ID for the actor in this instance."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    identity_key = Column(
        String(255),
        nullable=False,
        comment="External reference ID (e.g., email or system-agent-ID)."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Display name."
    )
    description = Column(
        Text,
        comment="Description of capabilities."
    )
    ai_context = Column(
        JSON,
        comment="System prompts or Persona definitions specific to this instance."
    )
    type = Column(
        String(50),
        nullable=False,
        comment="Type of actor (HUMAN, AI_AGENT, SYSTEM)."
    )
    capabilities = Column(
        JSON,
        comment="Dictionary of tools/skills the actor possesses."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="actors")
    assignments = relationship("Local_Actor_Role_Assignments", back_populates="actor", cascade="all, delete-orphan")
    role_attributes = relationship("Local_Role_Attributes", back_populates="actor", cascade="all, delete-orphan")
    uow_attributes = relationship("UOW_Attributes", back_populates="actor", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="actor", cascade="all, delete-orphan")


class Local_Actor_Role_Assignments(InstanceBase):
    """
    Mapping table defining which Actors can perform which Roles.
    """
    __tablename__ = "local_actor_role_assignments"
    __table_args__ = {
        "comment": "Mapping table defining which Actors can perform which Roles."
    }

    assignment_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        comment="The Actor."
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The Role they are allowed to assume."
    )
    status = Column(
        String(50),
        nullable=False,
        default=AssignmentStatus.ACTIVE.value,
        comment="Assignment status (ACTIVE, REVOKED)."
    )

    # Relationships
    actor = relationship("Local_Actors", back_populates="assignments")
    role = relationship("Local_Roles", back_populates="assignments")


class Local_Role_Attributes(InstanceBase):
    """
    The persistent knowledge base (Article III). Stores both shared Blueprints and private Playbooks.
    """
    __tablename__ = "local_role_attributes"
    __table_args__ = {
        "comment": "The persistent knowledge base (Article III). Stores both shared Blueprints and private Playbooks."
    }

    memory_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The Role context this memory applies to."
    )
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_actors.actor_id", ondelete="SET NULL"),
        nullable=True,
        comment="If NULL: Global Blueprint (Shared knowledge). If SET: Personal Playbook (Private knowledge)."
    )
    key = Column(
        String(255),
        nullable=False,
        comment="Retrieval key."
    )
    value = Column(
        JSON,
        comment="The stored knowledge/configuration."
    )
    is_toxic = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flagged by Omega/Epsilon if this memory led to failure (Article XX)."
    )
    last_accessed_at = Column(
        DateTime(timezone=True),
        comment="Used for pruning decay."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="role_attributes")
    role = relationship("Local_Roles", back_populates="role_attributes")
    actor = relationship("Local_Actors", back_populates="role_attributes")


class UnitsOfWork(InstanceBase):
    """
    The atomic token representing a task or data packet moving through the graph.
    """
    __tablename__ = "units_of_work"
    __table_args__ = {
        "comment": "The atomic token representing a task or data packet moving through the graph."
    }

    uow_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    local_workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Identifies which specific process this token is traversing."
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units_of_work.uow_id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to the Base UOW if this is a Child."
    )
    current_interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="Physical location of the token."
    )
    status = Column(
        String(50),
        nullable=False,
        default=UOWStatus.PENDING.value,
        comment="Current state (PENDING, ACTIVE, COMPLETED, FAILED)."
    )
    child_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total children generated (Optimization for Cerberus)."
    )
    finished_child_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total children completed (Optimization for Cerberus)."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="units_of_work")
    workflow = relationship("Local_Workflows", back_populates="units_of_work")
    current_interaction = relationship("Local_Interactions", back_populates="units_of_work")
    parent = relationship("UnitsOfWork", remote_side=[uow_id], backref="children")
    attributes = relationship("UOW_Attributes", back_populates="unit_of_work", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="unit_of_work", cascade="all, delete-orphan")


class UOW_Attributes(InstanceBase):
    """
    The specific data payload of a Unit of Work. Immutable/Versioned.
    """
    __tablename__ = "uow_attributes"
    __table_args__ = {
        "comment": "The specific data payload of a Unit of Work. Immutable/Versioned."
    }

    attribute_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    uow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units_of_work.uow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The parent token."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    key = Column(
        String(255),
        nullable=False,
        comment="Data label."
    )
    value = Column(
        JSON,
        comment="Data payload."
    )
    version = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Version number (increments on updates)."
    )
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        comment="Who made this change."
    )
    reasoning = Column(
        Text,
        comment="The 'Why' or 'Intent' behind this data change (traceability)."
    )

    # Relationships
    unit_of_work = relationship("UnitsOfWork", back_populates="attributes")
    instance = relationship("Instance_Context", back_populates="uow_attributes")
    actor = relationship("Local_Actors", back_populates="uow_attributes")


class Interaction_Logs(InstanceBase):
    """
    The immutable ledger of every movement in the system.
    """
    __tablename__ = "interaction_logs"
    __table_args__ = {
        "comment": "The immutable ledger of every movement in the system."
    }

    log_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Sequence number."
    )
    instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    uow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units_of_work.uow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The token moved."
    )
    actor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        comment="The actor responsible."
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The active role context."
    )
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="The location involved."
    )
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When the event occurred."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="interaction_logs")
    unit_of_work = relationship("UnitsOfWork", back_populates="interaction_logs")
    actor = relationship("Local_Actors", back_populates="interaction_logs")
    role = relationship("Local_Roles", back_populates="interaction_logs")
    interaction = relationship("Local_Interactions", back_populates="interaction_logs")
