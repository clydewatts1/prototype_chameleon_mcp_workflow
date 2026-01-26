"""
Tier 1 Models: The Meta-Store (Templates)

This module defines the database models for the template blueprint tier.
These models represent the read-only source of truth for workflow structures
that are used during the instantiation phase.

All tables use TemplateBase to ensure complete isolation from instance models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.orm import declarative_base, relationship
from .enums import RoleType, DecompositionStrategy, ComponentDirection, GuardianType


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

# Separate declarative base for Template tier (Tier 1)
TemplateBase = declarative_base()


class Template_Workflows(TemplateBase):
    """
    Defines the high-level container for a workflow blueprint.
    """
    __tablename__ = "template_workflows"
    __table_args__ = {
        "comment": "Defines the high-level container for a workflow blueprint."
    }

    workflow_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the blueprint."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable system name (e.g., 'Invoice_Approval_Flow')."
    )
    description = Column(
        Text,
        comment="Detailed documentation of what this workflow achieves."
    )
    ai_context = Column(
        JSON,
        comment="Model-specific prompts/descriptions used to prime AI agents about the overall workflow goal."
    )
    version = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Incremental version number; updated whenever the structure (roles, edges) changes."
    )
    schema_json = Column(
        JSON,
        comment="A serialized, cached representation of the full graph (Nodes+Edges) to speed up the cloning process."
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="UTC timestamp of creation."
    )

    # Relationships
    roles = relationship(
        "Template_Roles",
        foreign_keys="Template_Roles.workflow_id",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    interactions = relationship("Template_Interactions", back_populates="workflow", cascade="all, delete-orphan")
    components = relationship("Template_Components", foreign_keys="Template_Components.workflow_id", back_populates="workflow", cascade="all, delete-orphan")
    guardians = relationship("Template_Guardians", foreign_keys="Template_Guardians.workflow_id", back_populates="workflow", cascade="all, delete-orphan")


class Template_Roles(TemplateBase):
    """
    Defines the functional agents or steps within a blueprint.
    """
    __tablename__ = "template_roles"
    __table_args__ = (
        UniqueConstraint('workflow_id', 'name', name='uq_template_roles_workflow_name'),
        {
            "comment": "Defines the functional agents or steps within a blueprint."
        }
    )

    role_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier for the role definition."
    )
    workflow_id = Column(
        UUID(),
        ForeignKey("template_workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The blueprint this role belongs to."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Display name of the role (e.g., 'Senior_Auditor')."
    )
    description = Column(
        Text,
        comment="Human-readable description of responsibilities."
    )
    ai_context = Column(
        JSON,
        comment="Specific instructions for AI agents assigned to this role (e.g., 'You are a skeptical auditor...')."
    )
    role_type = Column(
        String(50),
        nullable=False,
        comment="Functional classification (ALPHA, BETA, OMEGA, EPSILON, TAU)."
    )
    strategy = Column(
        String(50),
        comment="Decomposition strategy (HOMOGENEOUS/HETEROGENEOUS) for Beta roles."
    )
    child_workflow_id = Column(
        UUID(),
        ForeignKey("template_workflows.workflow_id", ondelete="SET NULL"),
        nullable=True,
        comment="If set, this Role acts as a Recursive Gateway triggering this referenced blueprint."
    )

    # Relationships
    workflow = relationship(
        "Template_Workflows",
        foreign_keys=[workflow_id],
        back_populates="roles"
    )
    child_workflow = relationship(
        "Template_Workflows",
        foreign_keys=[child_workflow_id],
        post_update=True,
        lazy='select'
    )
    components = relationship("Template_Components", back_populates="role", cascade="all, delete-orphan")


class Template_Interactions(TemplateBase):
    """
    Defines the passive holding areas (waiting rooms) between roles.
    """
    __tablename__ = "template_interactions"
    __table_args__ = (
        UniqueConstraint('workflow_id', 'name', name='uq_template_interactions_workflow_name'),
        {
            "comment": "Defines the passive holding areas (waiting rooms) between roles."
        }
    )

    interaction_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    workflow_id = Column(
        UUID(),
        ForeignKey("template_workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent blueprint."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="System name (e.g., 'Pending_Approval_Queue')."
    )
    description = Column(
        Text,
        comment="Documentation of what UOW state resides here."
    )
    ai_context = Column(
        JSON,
        comment="Context for agents observing this interaction."
    )

    # Relationships
    workflow = relationship("Template_Workflows", back_populates="interactions")
    components = relationship("Template_Components", back_populates="interaction", cascade="all, delete-orphan")


class Template_Components(TemplateBase):
    """
    Defines the topology (directional pipes) linking Roles and Interactions.
    """
    __tablename__ = "template_components"
    __table_args__ = (
        UniqueConstraint('workflow_id', 'name', name='uq_template_components_workflow_name'),
        {
            "comment": "Defines the topology (directional pipes) linking Roles and Interactions."
        }
    )

    component_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    workflow_id = Column(
        UUID(),
        ForeignKey("template_workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The blueprint this component belongs to (Added for Namespace Scope)."
    )
    interaction_id = Column(
        UUID(),
        ForeignKey("template_interactions.interaction_id", ondelete="CASCADE"),
        nullable=False,
        comment="The interaction endpoint."
    )
    role_id = Column(
        UUID(),
        ForeignKey("template_roles.role_id", ondelete="CASCADE"),
        nullable=False,
        comment="The role endpoint."
    )
    direction = Column(
        String(50),
        nullable=False,
        comment="Flow direction relative to the Role (INBOUND/OUTBOUND)."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Descriptive name of the connection path."
    )
    description = Column(
        Text,
        comment="Documentation of the data flow."
    )
    ai_context = Column(
        JSON,
        comment="Semantic description of this specific data pipe."
    )

    # Relationships
    workflow = relationship("Template_Workflows", foreign_keys=[workflow_id], back_populates="components")
    interaction = relationship("Template_Interactions", back_populates="components")
    role = relationship("Template_Roles", back_populates="components")
    guardians = relationship("Template_Guardians", back_populates="component", cascade="all, delete-orphan")


class Template_Guardians(TemplateBase):
    """
    Defines the active logic gates attached to components.
    """
    __tablename__ = "template_guardians"
    __table_args__ = (
        UniqueConstraint('workflow_id', 'name', name='uq_template_guardians_workflow_name'),
        {
            "comment": "Defines the active logic gates attached to components."
        }
    )

    guardian_id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier."
    )
    workflow_id = Column(
        UUID(),
        ForeignKey("template_workflows.workflow_id", ondelete="CASCADE"),
        nullable=False,
        comment="The blueprint this guardian belongs to (Added for Namespace Scope)."
    )
    component_id = Column(
        UUID(),
        ForeignKey("template_components.component_id", ondelete="CASCADE"),
        nullable=False,
        comment="The specific pipe this guard protects."
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Name of the guard logic."
    )
    description = Column(
        Text,
        comment="Explanation of the gating criteria."
    )
    ai_context = Column(
        JSON,
        comment="Instructions for AI agents acting as the guard."
    )
    type = Column(
        String(50),
        nullable=False,
        comment="Logic type (CERBERUS, PASS_THRU, CRITERIA_GATE, etc.)."
    )
    config = Column(
        JSON,
        comment="Configuration payload (e.g., {'criteria': 'amount > 1000'})."
    )

    # Relationships
    workflow = relationship("Template_Workflows", foreign_keys=[workflow_id], back_populates="guardians")
    component = relationship("Template_Components", back_populates="guardians")
