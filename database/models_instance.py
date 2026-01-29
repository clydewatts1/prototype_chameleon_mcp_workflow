"""
Tier 2 Models: The Instance-Store (Runtime Engine)

This module defines the database models for the runtime instance tier.
These models represent the complete, self-contained universe for a running workflow.
All tables are read/write accessible by the engine and must include instance_id for isolation.

All tables use InstanceBase to ensure complete isolation from template models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, BigInteger, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.orm import declarative_base, relationship
from .enums import (
    RoleType, DecompositionStrategy, ComponentDirection, GuardianType,
    InstanceStatus, ActorType, AssignmentStatus, UOWStatus
)


# Database-agnostic UUID type (compatible with SQLite, PostgreSQL, MySQL, etc.)
class UUID(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36) storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value)

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
        UUID(),
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
    uow_history = relationship("UnitsOfWorkHistory", back_populates="instance", cascade="all, delete-orphan")


class Local_Workflows(InstanceBase):
    """
    A specific workflow definition active within this instance. Can be a Master or a Child dependency.
    """
    __tablename__ = "local_workflows"
    __table_args__ = (
        UniqueConstraint('instance_id', 'name', name='uq_local_workflows_instance_name'),
        {
            "comment": "A specific workflow definition active within this instance. Can be a Master or a Child dependency."
        }
    )

    local_workflow_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique ID for this workflow within this instance."
    )
    instance_id = Column(
        UUID(),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The parent container."
    )
    original_workflow_id = Column(
        UUID(),
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
    __table_args__ = (
        UniqueConstraint('local_workflow_id', 'name', name='uq_local_roles_workflow_name'),
        {
            "comment": "The execution logic nodes. Cloned from Template_Roles."
        }
    )

    role_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(),
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
        UUID(),
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
        post_update=True,
        lazy='select'
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
    __table_args__ = (
        UniqueConstraint('local_workflow_id', 'name', name='uq_local_interactions_workflow_name'),
        {
            "comment": "The execution holding areas. Cloned from Template_Interactions."
        }
    )

    interaction_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(),
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
    __table_args__ = (
        UniqueConstraint('local_workflow_id', 'name', name='uq_local_components_workflow_name'),
        {
            "comment": "The execution connections. Cloned from Template_Components."
        }
    )

    component_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    interaction_id = Column(
        UUID(),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="Connection Endpoint A."
    )
    role_id = Column(
        UUID(),
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
    __table_args__ = (
        UniqueConstraint('local_workflow_id', 'name', name='uq_local_guardians_workflow_name'),
        {
            "comment": "The active security gates. Cloned from Template_Guardians."
        }
    )

    guardian_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Local unique identifier."
    )
    local_workflow_id = Column(
        UUID(),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent local workflow."
    )
    component_id = Column(
        UUID(),
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
    __table_args__ = (
        UniqueConstraint('instance_id', 'name', name='uq_local_actors_instance_name'),
        {
            "comment": "Identities authorized to operate within this specific Instance Context."
        }
    )

    actor_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique ID for the actor in this instance."
    )
    instance_id = Column(
        UUID(),
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
    uow_history = relationship("UnitsOfWorkHistory", back_populates="actor", cascade="all, delete-orphan")


class Local_Actor_Role_Assignments(InstanceBase):
    """
    Mapping table defining which Actors can perform which Roles.
    """
    __tablename__ = "local_actor_role_assignments"
    __table_args__ = {
        "comment": "Mapping table defining which Actors can perform which Roles."
    }

    assignment_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    actor_id = Column(
        UUID(),
        ForeignKey("local_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        comment="The Actor."
    )
    role_id = Column(
        UUID(),
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
    Memory & Learning Specs: Section 4 (Schema) and Section 5 (Access).
    """
    __tablename__ = "local_role_attributes"
    __table_args__ = {
        "comment": "The persistent knowledge base (Article III). Stores both shared Blueprints and private Playbooks."
    }

    memory_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    instance_id = Column(
        UUID(),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    role_id = Column(
        UUID(),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The Role context this memory applies to."
    )
    context_type = Column(
        String(20),
        nullable=False,
        comment="Context discriminator: 'GLOBAL' for shared blueprints, 'ACTOR' for personal playbooks."
    )
    context_id = Column(
        String(255),
        nullable=False,
        comment="Context identifier: 'GLOBAL' for blueprints, or Actor UUID string representation (with hyphens) for personal playbooks."
    )
    actor_id = Column(
        UUID(),
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
    confidence_score = Column(
        Integer,
        default=50,
        nullable=False,
        comment="Confidence level (0-100) for this memory attribute."
    )
    is_toxic = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Flagged by Omega/Epsilon if this memory led to failure (Article XX)."
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this memory was created."
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
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    instance_id = Column(
        UUID(),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    local_workflow_id = Column(
        UUID(),
        ForeignKey("local_workflows.local_workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Identifies which specific process this token is traversing."
    )
    parent_id = Column(
        UUID(),
        ForeignKey("units_of_work.uow_id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to the Base UOW if this is a Child."
    )
    current_interaction_id = Column(
        UUID(),
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
    last_heartbeat = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last active signal from Actor. Used by Tau for Zombie detection."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="units_of_work")
    workflow = relationship("Local_Workflows", back_populates="units_of_work")
    current_interaction = relationship("Local_Interactions", back_populates="units_of_work")
    parent = relationship("UnitsOfWork", remote_side=[uow_id], backref="children")
    attributes = relationship("UOW_Attributes", back_populates="unit_of_work", cascade="all, delete-orphan")
    interaction_logs = relationship("Interaction_Logs", back_populates="unit_of_work", cascade="all, delete-orphan")
    history = relationship("UnitsOfWorkHistory", back_populates="unit_of_work", cascade="all, delete-orphan")
    content_hash = Column(
        String(64),
        nullable=True,
        comment="X-Content-Hash (SHA256) of the UOW attributes at last state. Used for state verification."
    )
    last_heartbeat_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp of last heartbeat from the assigned actor. Used by Tau for liveness detection."
    )
    interaction_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of times this UOW has been processed/evaluated. Incremented on each state transition."
    )
    max_interactions = Column(
        Integer,
        nullable=True,
        comment="Maximum allowed interactions before UOW becomes ZOMBIED_SOFT. Null = no limit (Constitutional Article XIII)."
    )
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of retries attempted for ZOMBIED_SOFT recovery. Incremented on each retry."
    )
    interaction_policy = Column(
        JSON,
        nullable=True,
        comment="Immutable snapshot of Guardian interaction_policy at UOW creation time. Used for deterministic routing evaluation (Constitutional Article IX)."
    )


class UnitsOfWorkHistory(InstanceBase):
    """
    Append-only historical ledger of UOW state transitions.
    
    Each row represents a point-in-time snapshot of a UOW's state,
    including the hash of attributes before the transition and after.
    Used for Continuous Learning and Atomic Traceability.
    
    Implements Article XVII (Atomic Traceability) and supports
    state drift detection via X-Content-Hash verification.
    """
    __tablename__ = "uow_history"
    __table_args__ = {
        "comment": "Append-only historical ledger of UOW state transitions with X-Content-Hash tracking."
    }

    history_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for this history entry."
    )
    instance_id = Column(
        UUID(),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container (for efficient querying and isolation)."
    )
    uow_id = Column(
        UUID(),
        ForeignKey("units_of_work.uow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The UOW this history entry tracks."
    )
    previous_status = Column(
        String(50),
        nullable=False,
        comment="The UOW status before this transition (PENDING, ACTIVE, COMPLETED, FAILED)."
    )
    new_status = Column(
        String(50),
        nullable=False,
        comment="The UOW status after this transition."
    )
    previous_state_hash = Column(
        String(64),
        nullable=True,
        comment="X-Content-Hash (SHA256) of attributes before transition. Null for first entry."
    )
    new_state_hash = Column(
        String(64),
        nullable=False,
        comment="X-Content-Hash (SHA256) of attributes after transition."
    )
    previous_interaction_id = Column(
        UUID(),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=True,
        comment="The interaction where the UOW was before (null for first transition)."
    )
    new_interaction_id = Column(
        UUID(),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="The interaction where the UOW is after the transition."
    )
    actor_id = Column(
        UUID(),
        ForeignKey("local_actors.actor_id", ondelete="SET NULL"),
        nullable=True,
        comment="The actor responsible for this state transition."
    )
    transition_timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="UTC timestamp of when this transition occurred (append-only guarantee)."
    )
    reasoning = Column(
        Text,
        nullable=True,
        comment="The 'Why' or 'Intent' behind this state change (traceability for learning)."
    )
    transition_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional context for this transition (e.g., error details, guardian decisions, attribute diffs)."
    )
    event_type = Column(
        String(100),
        nullable=False,
        default="STATE_TRANSITION",
        comment="Type of event: STATE_TRANSITION, CONSTITUTIONAL_WAIVER, UOW_CREATED, PILOT_OVERRIDE, etc."
    )
    payload = Column(
        JSON,
        nullable=True,
        comment="Event-specific payload (e.g., for CONSTITUTIONAL_WAIVER: {rule_ignored, waived_by, justification})."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="uow_history")
    unit_of_work = relationship("UnitsOfWork", back_populates="history")
    previous_interaction = relationship(
        "Local_Interactions",
        foreign_keys=[previous_interaction_id],
        post_update=True,
        backref="history_from_interactions"
    )
    new_interaction = relationship(
        "Local_Interactions",
        foreign_keys=[new_interaction_id],
        backref="history_to_interactions"
    )
    actor = relationship("Local_Actors", back_populates="uow_history")


class UOW_Attributes(InstanceBase):
    """
    The specific data payload of a Unit of Work. Immutable/Versioned.
    """
    __tablename__ = "uow_attributes"
    __table_args__ = {
        "comment": "The specific data payload of a Unit of Work. Immutable/Versioned."
    }

    attribute_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    uow_id = Column(
        UUID(),
        ForeignKey("units_of_work.uow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The parent token."
    )
    instance_id = Column(
        UUID(),
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
        UUID(),
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
    
    Supports both interaction movement tracking and high-performance telemetry buffering
    for the Shadow Logger and error metadata via non-blocking writes.
    
    Implements Article XVII (Atomic Traceability) for complete system observability.
    """
    __tablename__ = "interaction_logs"
    __table_args__ = {
        "comment": "The immutable ledger of every movement in the system with telemetry support."
    }

    log_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Sequence number."
    )
    instance_id = Column(
        UUID(),
        ForeignKey("instance_context.instance_id", ondelete="CASCADE"),
        nullable=False,
        comment="The container."
    )
    uow_id = Column(
        UUID(),
        ForeignKey("units_of_work.uow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The token moved."
    )
    actor_id = Column(
        UUID(),
        ForeignKey("local_actors.actor_id", ondelete="CASCADE"),
        nullable=False,
        comment="The actor responsible."
    )
    role_id = Column(
        UUID(),
        ForeignKey("local_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The active role context."
    )
    interaction_id = Column(
        UUID(),
        ForeignKey("local_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="The location involved."
    )
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When the event occurred (UTC)."
    )
    log_type = Column(
        String(50),
        default="INTERACTION",
        nullable=False,
        comment="Type of log entry (INTERACTION, TELEMETRY, ERROR, GUARDIAN_DECISION, STATE_TRANSITION)."
    )
    event_details = Column(
        JSON,
        nullable=True,
        comment="Event-specific metadata (e.g., error stack, guardian decision rationale, timing info)."
    )
    error_metadata = Column(
        JSON,
        nullable=True,
        comment="Error-specific information (error type, message, context) for failed operations."
    )

    # Relationships
    instance = relationship("Instance_Context", back_populates="interaction_logs")
    unit_of_work = relationship("UnitsOfWork", back_populates="interaction_logs")
    actor = relationship("Local_Actors", back_populates="interaction_logs")
    role = relationship("Local_Roles", back_populates="interaction_logs")
    interaction = relationship("Local_Interactions", back_populates="interaction_logs")
