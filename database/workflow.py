"""
Database Module for Chameleon Workflow Engine

This module handles all database interactions using SQLAlchemy.
It defines the schema (Models) and the Data Access Object (DatabaseManager).
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from attr import define
from sqlalchemy import Float, create_engine, Column, String, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import MetaData
from contextlib import contextmanager
from functools import wraps
from typing import Callable

# Support running as a script (python database/workflow.py) or as package module
try:  # Package-relative import when executed via `python -m database.workflow`
    from ..common import config as cfg
except ImportError:  # Fallback for direct script execution
    import sys
    from pathlib import Path

    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from common import config as cfg

# Decorators for database Reference Management

def validate_workflow_exists(func: Callable):
    """
    Decorator to ensure the workflow_id exists in the database 
    before executing the decorated method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 1. Extract workflow_id from positional or keyword arguments
        # We assume workflow_id is usually the first argument after 'self'
        workflow_id = kwargs.get('workflow_id') or (args[0] if args else None)
        
        if not workflow_id:
            raise ValueError("Validation Error: workflow_id is required.")

        # 2. Check existence using the existing session logic
        with self.get_session() as session:
            exists = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            if not exists:
                raise ValueError(f"Integrity Error: Workflow '{workflow_id}' not found.")
            
            # You could even add state-checks here:
            if exists.status == "archived":
                raise PermissionError(f"Workflow '{workflow_id}' is archived and read-only.")

        # 3. If all is well, run the original function
        return func(self, *args, **kwargs)
    
    return wrapper

def validate_role_exists(func: Callable):
    """
    Decorator to ensure the role_id exists in the database 
    before executing the decorated method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        role_id = kwargs.get('role_id') or (args[0] if args else None)
        
        if not role_id:
            raise ValueError("Validation Error: role_id is required.")

        with self.get_session() as session:
            exists = session.query(WorkflowRole).filter(WorkflowRole.id == role_id).first()
            if not exists:
                raise ValueError(f"Integrity Error: Role '{role_id}' not found.")

        return func(self, *args, **kwargs)
    return wrapper

def validate_interaction_exists(func: Callable):
    """
    Decorator to ensure the interaction_id exists in the database 
    before executing the decorated method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        interaction_id = kwargs.get('interaction_id') or (args[0] if args else None)
        
        if not interaction_id:
            raise ValueError("Validation Error: interaction_id is required.")

        with self.get_session() as session:
            exists = session.query(WorkflowInteraction).filter(WorkflowInteraction.id == interaction_id).first()
            if not exists:
                raise ValueError(f"Integrity Error: Interaction '{interaction_id}' not found.")

        return func(self, *args, **kwargs)
    return wrapper

def validate_actor_exists(func: Callable):
    """
    Decorator to ensure the actor_id exists in the database 
    before executing the decorated method.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        actor_id = kwargs.get('actor_id') or (args[0] if args else None)
        
        if not actor_id:
            raise ValueError("Validation Error: actor_id is required.")

        with self.get_session() as session:
            exists = session.query(WorkflowActor).filter(WorkflowActor.id == actor_id).first()
            if not exists:
                raise ValueError(f"Integrity Error: Actor '{actor_id}' not found.")

        return func(self, *args, **kwargs)
    return wrapper



# Base class for models
metadata = MetaData()
# TODO: Add naming conventions to metadata if needed , use config settings
Base = declarative_base(metadata=metadata)

class TimestampMixIn:
    """
    MixIn to add standardized timestamps to every table.
    Uses SQLAlchemy's 'func' to let the Database handle the time if preferred,
    or Python's datetime for consistency.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Timestamp when the record was last updated"
    )

class WorkflowModel(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflows' table.
    """
    __tablename__ = "wf_workflows"   
    __table_args__ = {"comment": "Table storing workflow definitions"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique workflow identifier")
    name: Mapped[str] = mapped_column(String, nullable=False,comment="Human-readable name of the workflow")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the workflow")
    status: Mapped[str] = mapped_column(String, default="created", comment="Processing status of the workflow")

class WorkflowModelAttribute(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_attributes' table.
    """
    __tablename__ = "wf_workflow_attributes"
    __table_args__ = {"comment": "Table storing workflow attributes"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique attribute identifier")
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated workflow identifier")
    key: Mapped[str] = mapped_column(String, nullable=False, comment="Attribute key")
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Attribute value")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the attribute")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Contextual information related to the attribute")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was last updated")

class WorkflowInteraction(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_interactions' table.
    """
    __tablename__ = "wf_workflow_interactions"
    __table_args__ = {"comment": "Table storing workflow interactions"}
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique interaction identifier")
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated workflow identifier")
    interaction_type: Mapped[str] = mapped_column(String, nullable=False, comment="Type of interaction")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Human-readable name of the interaction")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the interaction")

class WorkflowInteractionComponent(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_interaction_components' table.
    """
    __tablename__ = "wf_workflow_interaction_components"
    __table_args__ = {"comment": "Table storing components of workflow interactions"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique interaction component identifier")
    interaction_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated interaction identifier")
    role_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated role identifier")
    direction: Mapped[str] = mapped_column(String, nullable=False, comment="Direction of the component, e.g., 'input' or 'output'")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Human-readable name of the component")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the component")

class WorkflowRole(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_roles' table.
    """
    __tablename__ = "wf_workflow_roles"
    __table_args__ = {"comment": "Table storing workflow roles"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique role identifier")
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Associated workflow identifier (optional)")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Human-readable name of the role")
    type: Mapped[str] = mapped_column(String, nullable=False, comment="Type of the role")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the role")

class WorkflowRoleAttribute(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_role_attributes' table.
    """
    __tablename__ = "wf_workflow_role_attributes"
    __table_args__ = {"comment": "Table storing workflow role attributes"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique role attribute identifier")
    role_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated role identifier")
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Associated workflow identifier (optional)")
    key: Mapped[str] = mapped_column(String, nullable=False, comment="Attribute key")
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Attribute value")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the attribute")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context information for the attribute")

class WorkflowInstance(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_instances' table.
    """
    __tablename__ = "wf_workflow_instances"
    __table_args__ = {"comment": "Table storing workflow instances"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique instance identifier")
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Associated workflow identifier (optional)")
    status: Mapped[str] = mapped_column(String, default="initialized", comment="Current status of the instance")

class WorkflowInstanceAttribute(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_instance_attributes' table.
    """
    __tablename__ = "wf_workflow_instance_attributes"
    __table_args__ = {"comment": "Table storing workflow instance attributes"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique instance attribute identifier")
    instance_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated instance identifier")
    key: Mapped[str] = mapped_column(String, nullable=False, comment="Attribute key")
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Attribute value")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the attribute")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context information for the attribute")

class WorkflowUnitOfWorkType(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_unit_of_work_types' table.
    """
    __tablename__ = "wf_workflow_unit_of_work_types"
    __table_args__ = {"comment": "Table storing workflow unit of work types"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique unit of work type identifier")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Name of the unit of work type")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the unit of work type")
    uow_class: Mapped[str] = mapped_column(String, nullable=False, comment="Class of the unit of work (e.g., atomic, set, tuple)")

class WorkflowUnitOfWork(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_units_of_work' table.
    """
    __tablename__ = "wf_workflow_units_of_work"
    __table_args__ = {"comment": "Table storing workflow units of work"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique unit of work identifier")
    instance_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated workflow instance identifier")
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Parent unit of work identifier for hierarchical UoW")
    uow_status: Mapped[str] = mapped_column(String, default="pending", comment="Current status of the unit of work")
    priority: Mapped[float] = mapped_column(Float, default=0.0, comment="Priority of the unit of work")
    status: Mapped[str] = mapped_column(String, default="pending", comment="General status of the unit of work")

class WorkflowUnitOfWorkAttribute(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_unit_of_work_attributes' table.
    """
    __tablename__ = "wf_workflow_unit_of_work_attributes"
    __table_args__ = {"comment": "Table storing workflow unit of work attributes"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique unit of work attribute identifier")
    unit_of_work_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated unit of work identifier")
    key: Mapped[str] = mapped_column(String, nullable=False, comment="Attribute key")
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Attribute value")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the attribute")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context information for the attribute")

class WorkflowActor(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_actors' table.
    """
    __tablename__ = "wf_workflow_actors"
    __table_args__ = {"comment": "Table storing workflow actors"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique actor identifier")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Name of the actor")
    type: Mapped[str] = mapped_column(String, nullable=False, comment="Type of the actor HUMAN,AI_AGENT,SYSTEM")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the actor")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context information for the actor")

class WorkflowActorAttribute(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_actor_attributes' table.
    """
    __tablename__ = "wf_workflow_actor_attributes"
    __table_args__ = {"comment": "Table storing workflow actor attributes"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique actor attribute identifier")
    actor_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated actor identifier")
    key: Mapped[str] = mapped_column(String, nullable=False, comment="Attribute key")
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Attribute value")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the attribute")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Context information for the attribute")

class WorkflowActorRoleAssignment(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_actor_role_assignments' table.
    """
    __tablename__ = "wf_workflow_actor_role_assignments"
    __table_args__ = {"comment": "Table storing workflow actor role assignments"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique actor role assignment identifier")
    actor_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated actor identifier")
    role_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated role identifier")
    status: Mapped[str] = mapped_column(String, default="active", comment="Status of the role assignment")
    priority_weight: Mapped[float] = mapped_column(Float, default=1.0, comment="Priority weight of the role assignment")


class WorkflowGuardian(Base, TimestampMixIn):
    """
    SQLAlchemy Model representing the 'wf_workflow_guardians' table.
    This is between the inbound/outbound  interactions and role. This defines what UOW can flow between an interaction and a role.
    """
    __tablename__ = "wf_workflow_guardians"
    __table_args__ = {"comment": "Table storing workflow guardians"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique guardian identifier")
    workflow_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated workflow identifier")
    interaction_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated interaction identifier")
    role_id: Mapped[str] = mapped_column(String, nullable=False, comment="Associated role identifier")
    direction: Mapped[str] = mapped_column(String, nullable=False, comment="Direction of the guardian, e.g., 'inbound' or 'outbound'")
    type: Mapped[str] = mapped_column(String, nullable=False, comment="Type of guardian, e.g., 'hard' or 'soft'")
    attributes: Mapped[Optional[str]] = mapped_column(JSON , nullable=True, comment="Additional attributes for the guardian in JSON format")

class DatabaseManager:
    """
    Manager class for database access. 
    Provides getters, setters, and process functions.
    """
    
    def __init__(self, database_url: str=None):
        """
        Initialize the database connection.
        """
        # connect_args is needed for SQLite to allow multi-threaded access
        connect_args = {"check_same_thread": False} if "sqlite" in (database_url or cfg.DATABASE_URL) else {}
        
        self.engine = create_engine(database_url or cfg.DATABASE_URL, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self):
        """Helper to get a safe database session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # --- Getters ---

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single workflow by ID."""
        with self.get_session() as session:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            if workflow:
                return self._to_dict(workflow)
            return None

    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """Retrieve all workflows."""
        with self.get_session() as session:
            workflows = session.query(WorkflowModel).all()
            return [self._to_dict(w) for w in workflows]
        
    def get_workflow_attributes(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Retrieve all attributes for a given workflow."""
        with self.get_session() as session:
            attributes = session.query(WorkflowModelAttribute).filter(WorkflowModelAttribute.workflow_id == workflow_id).all()
            return [self._to_dict(attr) for attr in attributes]
    
    def get_workflow_attribute(self, workflow_id: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific attribute for a given workflow by key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowModelAttribute).filter(
                WorkflowModelAttribute.workflow_id == workflow_id,
                WorkflowModelAttribute.key == key
            ).first()
            if attribute:
                return self._to_dict(attribute)
            return None
        
    def get_workflow_interactions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Retrieve all interactions for a given workflow."""
        with self.get_session() as session:
            interactions = session.query(WorkflowInteraction).filter(WorkflowInteraction.workflow_id == workflow_id).all()
            return [self._to_dict(inter) for inter in interactions]
    
    def get_workflow_interaction(self, workflow_id: str, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific interaction for a given workflow by interaction ID."""
        with self.get_session() as session:
            interaction = session.query(WorkflowInteraction).filter(
                WorkflowInteraction.workflow_id == workflow_id,
                WorkflowInteraction.id == interaction_id
            ).first()
            if interaction:
                return self._to_dict(interaction)
            return None
        
    def get_workflow_interaction_components(self, interaction_id: str) -> List[Dict[str, Any]]:
        """Retrieve all components for a given interaction."""
        with self.get_session() as session:
            components = session.query(WorkflowInteractionComponent).filter(WorkflowInteractionComponent.interaction_id == interaction_id).all()
            return [self._to_dict(comp) for comp in components]
        
    def get_workflow_interaction_component(self, interaction_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific component for a given interaction by role ID."""
        with self.get_session() as session:
            component = session.query(WorkflowInteractionComponent).filter(
                WorkflowInteractionComponent.interaction_id == interaction_id,
                WorkflowInteractionComponent.role_id == role_id
            ).first()
            if component:
                return self._to_dict(component)
            return None
        
    def get_workflow_interaction_components_by_role(self, interaction_id: str, role_id: str) -> List[Dict[str, Any]]:
        """Retrieve all components for a given interaction by role ID."""
        with self.get_session() as session:
            components = session.query(WorkflowInteractionComponent).filter(
                WorkflowInteractionComponent.interaction_id == interaction_id,
                WorkflowInteractionComponent.role_id == role_id
            ).all()
            return [self._to_dict(comp) for comp in components]
        
    def get_workflow_roles(self) -> List[Dict[str, Any]]:
        """Retrieve all workflow roles."""
        with self.get_session() as session:
            roles = session.query(WorkflowRole).all()
            return [self._to_dict(role) for role in roles]
        
    def get_workflow_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific workflow role by ID."""
        with self.get_session() as session:
            role = session.query(WorkflowRole).filter(WorkflowRole.id == role_id).first()
            if role:
                return self._to_dict(role)
            return None

    def get_workflow_role_attributes(self, role_id: str) -> List[Dict[str, Any]]:
        """Retrieve all attributes for a given workflow role."""
        with self.get_session() as session:
            attributes = session.query(WorkflowRoleAttribute).filter(WorkflowRoleAttribute.role_id == role_id).all()
            return [self._to_dict(attr) for attr in attributes]
        
    def get_workflow_role_attribute(self, role_id: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific attribute for a given workflow role by key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowRoleAttribute).filter(
                WorkflowRoleAttribute.role_id == role_id,
                WorkflowRoleAttribute.key == key
            ).first()
            if attribute:
                return self._to_dict(attribute)
            return None
        
    def get_workflow_instances(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Retrieve all instances for a given workflow."""
        with self.get_session() as session:
            instances = session.query(WorkflowInstance).filter(WorkflowInstance.workflow_id == workflow_id).all()
            return [self._to_dict(inst) for inst in instances]      
        
    def get_workflow_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific workflow instance by ID."""
        with self.get_session() as session:
            instance = session.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
            if instance:
                return self._to_dict(instance)
            return None    
        
    def get_workflow_instance_attributes(self, instance_id: str) -> List[Dict[str, Any]]:
        """Retrieve all attributes for a given workflow instance."""
        with self.get_session() as session:
            attributes = session.query(WorkflowInstanceAttribute).filter(WorkflowInstanceAttribute.instance_id == instance_id).all()
            return [self._to_dict(attr) for attr in attributes]
    
    def get_workflow_instance_attribute(self, instance_id: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific attribute for a given workflow instance by key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowInstanceAttribute).filter(
                WorkflowInstanceAttribute.instance_id == instance_id,
                WorkflowInstanceAttribute.key == key
            ).first()
            if attribute:
                return self._to_dict(attribute)
            return None
        
    def get_workflow_unit_of_work_types(self) -> List[Dict[str, Any]]:
        """Retrieve all workflow unit of work types."""
        with self.get_session() as session:
            uow_types = session.query(WorkflowUnitOfWorkType).all()
            return [self._to_dict(uow_type) for uow_type in uow_types]
        
    def get_workflow_unit_of_work_type(self, uow_type_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific workflow unit of work type by ID."""
        with self.get_session() as session:
            uow_type = session.query(WorkflowUnitOfWorkType).filter(WorkflowUnitOfWorkType.id == uow_type_id).first()
            if uow_type:
                return self._to_dict(uow_type)
            return None
    
    def get_workflow_unit_of_works(self, instance_id: str) -> List[Dict[str, Any]]:
        """Retrieve all units of work for a given workflow instance."""
        with self.get_session() as session:
            uows = session.query(WorkflowUnitOfWork).filter(WorkflowUnitOfWork.instance_id == instance_id).all()
            return [self._to_dict(uow) for uow in uows]
    
    def get_workflow_unit_of_work(self, uow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific workflow unit of work by ID."""
        with self.get_session() as session:
            uow = session.query(WorkflowUnitOfWork).filter(WorkflowUnitOfWork.id == uow_id).first()
            if uow:
                return self._to_dict(uow)
            return None
        
    def get_workflow_unit_of_work_attributes(self, uow_id: str) -> List[Dict[str, Any]]:
        """Retrieve all attributes for a given workflow unit of work."""
        with self.get_session() as session:
            attributes = session.query(WorkflowUnitOfWorkAttribute).filter(WorkflowUnitOfWorkAttribute.unit_of_work_id == uow_id).all()
            return [self._to_dict(attr) for attr in attributes]
        
    def get_workflow_unit_of_work_attribute(self, uow_id: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific attribute for a given workflow unit of work by key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowUnitOfWorkAttribute).filter(
                WorkflowUnitOfWorkAttribute.unit_of_work_id == uow_id,
                WorkflowUnitOfWorkAttribute.key == key
            ).first()
            if attribute:
                return self._to_dict(attribute)
            return None
    def get_workflow_actors(self) -> List[Dict[str, Any]]:
        """Retrieve all workflow actors."""
        with self.get_session() as session:
            actors = session.query(WorkflowActor).all()
            return [self._to_dict(actor) for actor in actors]
    
    def get_workflow_actor(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific workflow actor by ID."""
        with self.get_session() as session:
            actor = session.query(WorkflowActor).filter(WorkflowActor.id == actor_id).first()
            if actor:
                return self._to_dict(actor)
            return None
    # --- Helper Methods ---
    # --- Setters / Creators ---

    def create_workflow(self, workflow_id: str, name: str, description: str) -> Dict[str, Any]:
        """Create and save a new workflow."""
        with self.get_session() as session:
            new_workflow = WorkflowModel(
                id=workflow_id,
                name=name,
                description=description,
                status="created"
            )
            session.add(new_workflow)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_workflow)
            return self._to_dict(new_workflow)

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID."""
        with self.get_session() as session:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            if workflow:
                session.delete(workflow)
                return True
            return False
        
    @validate_workflow_exists
    def create_workflow_attribute(self, workflow_id: str, key: str, value: str, description: str = "", context: str = "") -> Dict[str, Any]:
        """Create and save a new workflow attribute."""
        with self.get_session() as session:
            new_attribute = WorkflowModelAttribute(
                id=f"{workflow_id}_{key}",
                workflow_id=workflow_id,
                key=key,
                value=value,
                description=description,
                context=context
            )
            session.add(new_attribute)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_attribute)
            return self._to_dict(new_attribute)
        
    def delete_workflow_attribute(self, workflow_id: str, key: str) -> bool:
        """Delete a workflow attribute by workflow ID and key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowModelAttribute).filter(
                WorkflowModelAttribute.workflow_id == workflow_id,
                WorkflowModelAttribute.key == key
            ).first()
            if attribute:
                session.delete(attribute)
                return True
            return False
        

    def create_workflow_interaction(self, workflow_id: str, interaction_id: str, interaction_type: str, name: str, description: str = "") -> Dict[str, Any]:
        """Create and save a new workflow interaction."""
        with self.get_session() as session:
            new_interaction = WorkflowInteraction(
                id=interaction_id,
                workflow_id=workflow_id,
                interaction_type=interaction_type,
                name=name,
                description=description
            )
            session.add(new_interaction)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_interaction)
            return self._to_dict(new_interaction)
        
    def delete_workflow_interaction(self, workflow_id: str, interaction_id: str) -> bool:
        """Delete a workflow interaction by workflow ID and interaction ID."""
        with self.get_session() as session:
            interaction = session.query(WorkflowInteraction).filter(
                WorkflowInteraction.workflow_id == workflow_id,
                WorkflowInteraction.id == interaction_id
            ).first()
            if interaction:
                session.delete(interaction)
                return True
            return False
        
    @validate_workflow_exists   
    def create_workflow_interaction_component(self, interaction_id: str, role_id: str, direction: str, name: str, description: str = "") -> Dict[str, Any]:
        """Create and save a new workflow interaction component."""
        with self.get_session() as session:
            new_component = WorkflowInteractionComponent(
                id=f"{interaction_id}_{role_id}",
                interaction_id=interaction_id,
                role_id=role_id,
                direction=direction,
                name=name,
                description=description
            )
            session.add(new_component)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_component)
            return self._to_dict(new_component)
        
    def delete_workflow_interaction_component(self, interaction_id: str, role_id: str) -> bool:
        """Delete a workflow interaction component by interaction ID and role ID."""
        with self.get_session() as session:
            component = session.query(WorkflowInteractionComponent).filter(
                WorkflowInteractionComponent.interaction_id == interaction_id,
                WorkflowInteractionComponent.role_id == role_id
            ).first()
            if component:
                session.delete(component)
                return True
            return False

    def create_workflow_role(self, role_id: str, name: str, type: str, description: str = "") -> Dict[str, Any]:
        """Create and save a new workflow role."""
        with self.get_session() as session:
            new_role = WorkflowRole(
                id=role_id,
                name=name,
                type=type,
                description=description
            )
            session.add(new_role)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_role)
            return self._to_dict(new_role)
    
    def delete_workflow_role(self, role_id: str) -> bool:
        """Delete a workflow role by ID."""
        with self.get_session() as session:
            role = session.query(WorkflowRole).filter(WorkflowRole.id == role_id).first()
            if role:
                session.delete(role)
                return True
            return False
            
    def create_workflow_role_attribute(self, role_id: str, key: str, value: str, description: str = "", context: str = "") -> Dict[str, Any]:
        """Create and save a new workflow role attribute."""
        with self.get_session() as session:
            new_attribute = WorkflowRoleAttribute(
                id=f"{role_id}_{key}",
                role_id=role_id,
                key=key,
                value=value,
                description=description,
                context=context
            )
            session.add(new_attribute)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_attribute)
            return self._to_dict(new_attribute)
        
    def delete_workflow_role_attribute(self, role_id: str, key: str) -> bool:
        """Delete a workflow role attribute by role ID and key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowRoleAttribute).filter(
                WorkflowRoleAttribute.role_id == role_id,
                WorkflowRoleAttribute.key == key
            ).first()
            if attribute:
                session.delete(attribute)
                return True
            return False
    
    def create_workflow_instance(self, instance_id: str, workflow_id: str, status: str = "initialized") -> Dict[str, Any]:
        """Create and save a new workflow instance."""
        with self.get_session() as session:
            new_instance = WorkflowInstance(
                id=instance_id,
                workflow_id=workflow_id,
                status=status
            )
            session.add(new_instance)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_instance)
            return self._to_dict(new_instance)
    
    def delete_workflow_instance(self, instance_id: str) -> bool:
        """Delete a workflow instance by ID."""
        with self.get_session() as session:
            instance = session.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
            if instance:
                session.delete(instance)
                return True
            return False

    def create_workflow_instance_attribute(self, instance_id: str, key: str, value: str, description: str = "", context: str = "") -> Dict[str, Any]:   
        """Create and save a new workflow instance attribute."""
        with self.get_session() as session:
            new_attribute = WorkflowInstanceAttribute(
                id=f"{instance_id}_{key}",
                instance_id=instance_id,
                key=key,
                value=value,
                description=description,
                context=context
            )
            session.add(new_attribute)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_attribute)
            return self._to_dict(new_attribute)
        
    def delete_workflow_instance_attribute(self, instance_id: str, key: str) -> bool:
        """Delete a workflow instance attribute by instance ID and key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowInstanceAttribute).filter(
                WorkflowInstanceAttribute.instance_id == instance_id,
                WorkflowInstanceAttribute.key == key
            ).first()
            if attribute:
                session.delete(attribute)
                return True
            return False
        
    def create_workflow_unit_of_work_type(self, uow_type_id: str, name: str, description: str, uow_class: str) -> Dict[str, Any]:
        """Create and save a new workflow unit of work type."""
        with self.get_session() as session:
            new_uow_type = WorkflowUnitOfWorkType(
                id=uow_type_id,
                name=name,
                description=description,
                uow_class=uow_class
            )
            session.add(new_uow_type)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_uow_type)
            return self._to_dict(new_uow_type)
    def delete_workflow_unit_of_work_type(self, uow_type_id: str) -> bool:
        """Delete a workflow unit of work type by ID."""
        with self.get_session() as session:
            uow_type = session.query(WorkflowUnitOfWorkType).filter(WorkflowUnitOfWorkType.id == uow_type_id).first()
            if uow_type:
                session.delete(uow_type)
                return True
            return False
        
    def create_workflow_unit_of_work(self, uow_id: str, instance_id: str, parent_id: Optional[str] = None, uow_status: str = "pending", priority: float = 0.0, status: str = "pending") -> Dict[str, Any]:
        """Create and save a new workflow unit of work."""
        with self.get_session() as session:
            new_uow = WorkflowUnitOfWork(
                id=uow_id,
                instance_id=instance_id,
                parent_id=parent_id,
                uow_status=uow_status,
                priority=priority,
                status=status
            )
            session.add(new_uow)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_uow)
            return self._to_dict(new_uow)
    def delete_workflow_unit_of_work(self, uow_id: str) -> bool:
        """Delete a workflow unit of work by ID."""
        with self.get_session() as session:
            uow = session.query(WorkflowUnitOfWork).filter(WorkflowUnitOfWork.id == uow_id).first()
            if uow:
                session.delete(uow)
                return True
            return False
    def create_workflow_unit_of_work_attribute(self, uow_id: str, key: str, value: str, description: str = "", context: str = "") -> Dict[str, Any]:
        """Create and save a new workflow unit of work attribute."""
        with self.get_session() as session:
            new_attribute = WorkflowUnitOfWorkAttribute(
                id=f"{uow_id}_{key}",
                unit_of_work_id=uow_id,
                key=key,
                value=value,
                description=description,
                context=context
            )
            session.add(new_attribute)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_attribute)
            return self._to_dict(new_attribute)
    def delete_workflow_unit_of_work_attribute(self, uow_id: str, key: str) -> bool:
        """Delete a workflow unit of work attribute by unit of work ID and key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowUnitOfWorkAttribute).filter(
                WorkflowUnitOfWorkAttribute.unit_of_work_id == uow_id,
                WorkflowUnitOfWorkAttribute.key == key
            ).first()
            if attribute:
                session.delete(attribute)
                return True
            return False

    def create_workflow_actor(self, actor_id: str, name: str, type: str, description: str = "", context: str = "") -> Dict[str, Any]:
        """Create and save a new workflow actor."""
        with self.get_session() as session:
            new_actor = WorkflowActor(
                id=actor_id,
                name=name,
                type=type,
                description=description,
                context=context
            )
            session.add(new_actor)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_actor)
            return self._to_dict(new_actor)
        
    def delete_workflow_actor(self, actor_id: str) -> bool:
        """Delete a workflow actor by ID."""
        with self.get_session() as session:
            actor = session.query(WorkflowActor).filter(WorkflowActor.id == actor_id).first()
            if actor:
                session.delete(actor)
                return True
            return False
        
    def create_workflow_actor_attribute(self, actor_id: str, key: str, value: str, description: str = "", context: str = "") -> Dict[str, Any]:
        """Create and save a new workflow actor attribute."""
        with self.get_session() as session:
            new_attribute = WorkflowActorAttribute(
                id=f"{actor_id}_{key}",
                actor_id=actor_id,
                key=key,
                value=value,
                description=description,
                context=context
            )
            session.add(new_attribute)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_attribute)
            return self._to_dict(new_attribute)
        
    def delete_workflow_actor_attribute(self, actor_id: str, key: str) -> bool:
        """Delete a workflow actor attribute by actor ID and key."""
        with self.get_session() as session:
            attribute = session.query(WorkflowActorAttribute).filter(
                WorkflowActorAttribute.actor_id == actor_id,
                WorkflowActorAttribute.key == key
            ).first()
            if attribute:
                session.delete(attribute)
                return True
            return False
        
    def create_workflow_actor_role_assignment(self, actor_id: str, role_id: str, status: str = "active") -> Dict[str, Any]:
        """Create and save a new workflow actor role assignment."""
        with self.get_session() as session:
            new_assignment = WorkflowActorRoleAssignment(
                id=f"{actor_id}_{role_id}",
                actor_id=actor_id,
                role_id=role_id,
                status=status
            )
            session.add(new_assignment)
            session.flush()  # Ensure INSERT executes so refresh works
            session.refresh(new_assignment)
            return self._to_dict(new_assignment)
    
    def delete_workflow_actor_role_assignment(self, actor_id: str, role_id: str) -> bool:
        """Delete a workflow actor role assignment by actor ID and role ID."""
        with self.get_session() as session:
            assignment = session.query(WorkflowActorRoleAssignment).filter(
                WorkflowActorRoleAssignment.actor_id == actor_id,
                WorkflowActorRoleAssignment.role_id == role_id
            ).first()
            if assignment:
                session.delete(assignment)
                return True
            return False
    # --- Update Functions ---

    def update_workflow_status(self, workflow_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Update the processing status of a workflow."""
        with self.get_session() as session:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            if workflow:
                workflow.status = new_status
                session.add(workflow) # Mark as modified
                session.flush()
                session.refresh(workflow)
                return self._to_dict(workflow)
            return None

    def update_workflow_attribute(self, workflow_id: str, key: str, new_value: str) -> Optional[Dict[str, Any]]:
        """Update the value of a workflow attribute."""
        with self.get_session() as session:
            attribute = session.query(WorkflowModelAttribute).filter(
                WorkflowModelAttribute.workflow_id == workflow_id,
                WorkflowModelAttribute.key == key
            ).first()
            if attribute:
                attribute.value = new_value
                session.add(attribute) # Mark as modified
                session.flush()
                session.refresh(attribute)
                return self._to_dict(attribute)
            return None

    def update_workflow_interaction(self, workflow_id: str, interaction_id: str, new_name: Optional[str] = None, new_description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update the name and/or description of a workflow interaction."""
        with self.get_session() as session:
            interaction = session.query(WorkflowInteraction).filter(
                WorkflowInteraction.workflow_id == workflow_id,
                WorkflowInteraction.id == interaction_id
            ).first()
            if interaction:
                if new_name is not None:
                    interaction.name = new_name
                if new_description is not None:
                    interaction.description = new_description
                session.add(interaction) # Mark as modified
                session.flush()
                session.refresh(interaction)
                return self._to_dict(interaction)
            return None
        
    def update_workflow_role(self, role_id: str, new_name: Optional[str] = None, new_type: Optional[str] = None, new_description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update the name, type, and/or description of a workflow role."""
        with self.get_session() as session:
            role = session.query(WorkflowRole).filter(WorkflowRole.id == role_id).first()
            if role:
                if new_name is not None:
                    role.name = new_name
                if new_type is not None:
                    role.type = new_type
                if new_description is not None:
                    role.description = new_description
                session.add(role) # Mark as modified
                session.flush()
                session.refresh(role)
                return self._to_dict(role)
            return None
        
    def update_workflow_role_attribute(self, role_id: str, key: str, new_value: str) -> Optional[Dict[str, Any]]:
        """Update the value of a workflow role attribute."""
        with self.get_session() as session:
            attribute = session.query(WorkflowRoleAttribute).filter(
                WorkflowRoleAttribute.role_id == role_id,
                WorkflowRoleAttribute.key == key
            ).first()
            if attribute:
                attribute.value = new_value
                session.add(attribute) # Mark as modified
                session.flush()
                session.refresh(attribute)
                return self._to_dict(attribute)
            return None
    
    def update_workflow_actor_attribute(self, actor_id: str, key: str, new_value: str) -> Optional[Dict[str, Any]]:
        """Update the value of a workflow actor attribute."""
        with self.get_session() as session:
            attribute = session.query(WorkflowActorAttribute).filter(
                WorkflowActorAttribute.actor_id == actor_id,
                WorkflowActorAttribute.key == key
            ).first()
            if attribute:
                attribute.value = new_value
                session.add(attribute) # Mark as modified
                session.flush()
                session.refresh(attribute)
                return self._to_dict(attribute)
            return None
        
    def update_workflow_instance_status(self, instance_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Update the status of a workflow instance."""
        with self.get_session() as session:
            instance = session.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
            if instance:
                instance.status = new_status
                session.add(instance) # Mark as modified
                session.flush()
                session.refresh(instance)
                return self._to_dict(instance)
            return None
        
    def update_workflow_unit_of_work_status(self, uow_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Update the status of a workflow unit of work."""
        with self.get_session() as session:
            uow = session.query(WorkflowUnitOfWork).filter(WorkflowUnitOfWork.id == uow_id).first()
            if uow:
                uow.status = new_status
                session.add(uow) # Mark as modified
                session.flush()
                session.refresh(uow)
                return self._to_dict(uow)
            return None
    

    def _to_dict(self, model) -> Dict[str, Any]:
        """Helper to convert SQLAlchemy model to dictionary."""
        if isinstance(model, WorkflowModel):
            return {
                "id": model.id,
                "name": model.name,
                "description": model.description,
                "status": model.status,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowModelAttribute):
            return {
                "id": model.id,
                "workflow_id": model.workflow_id,
                "key": model.key,
                "value": model.value,
                "description": model.description,
                "context": model.context,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowActorAttribute):
            return {
                "id": model.id,
                "actor_id": model.actor_id,
                "key": model.key,
                "value": model.value,
                "description": model.description,
                "context": model.context,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowRole):
            return {
                "id": model.id,
                "name": model.name,
                "type": model.type,
                "description": model.description,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowInteraction):
            return {
                "id": model.id,
                "workflow_id": model.workflow_id,
                "interaction_type": model.interaction_type,
                "name": model.name,
                "description": model.description,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowInteractionComponent):
            return {
                "id": model.id,
                "interaction_id": model.interaction_id,
                "role_id": model.role_id,
                "direction": model.direction,
                "name": model.name,
                "description": model.description,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        elif isinstance(model, WorkflowInteractionComponent):
            return {
                "id": model.id,
                "interaction_id": model.interaction_id,
                "role_id": model.role_id,
                "direction": model.direction,
                "name": model.name,
                "description": model.description,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None
            }
        else:
            raise ValueError(f"Unknown model type: {type(model)}")
    
if __name__ == "__main__":
    # Simple test code
    db_manager = DatabaseManager()
    
    # Clean up any existing test data
    print("Cleaning up existing test data...")
    db_manager.delete_workflow("wf_001")

    print("Cleanup complete.")
    
    workflow = db_manager.create_workflow(
        workflow_id="wf_001",
        name="Test Workflow",
        description="A workflow for testing"
    )
    print("Created Workflow:", workflow)

    # create attribute
    attribute = db_manager.create_workflow_attribute(
        workflow_id="wf_001",
        key="priority",
        value="high",
        description="Priority of the workflow",
        context="system"
    )

    print("Created Attribute:", attribute)
    
    # Create Role
    role = db_manager.create_workflow_role(
        role_id="role_001",
        name="Test Role",
        type="system",
        description="A role for testing"
    )

    print("Created Role:", role)

    # Create Interaction
    interaction = db_manager.create_workflow_interaction(
        workflow_id="wf_001",
        interaction_id="int_001",
        interaction_type="message",
        name="Test Interaction",
        description="An interaction for testing"
    )
    print("Created Interaction:", interaction)
    fetched_workflow = db_manager.get_workflow("wf_001")
    print("Fetched Workflow:", fetched_workflow)
    
    # Create interaction component
    component = db_manager.create_workflow_interaction_component(
        interaction_id="int_001",
        role_id="role_001",
        direction="inbound",
        name="Test Component",
        description="A component for testing"
    )
    print("Created Interaction Component:", component)

    updated_workflow = db_manager.update_workflow_status("wf_001", "active")
    print("Updated Workflow Status:", updated_workflow)
    
    all_workflows = db_manager.get_all_workflows()
    print("All Workflows:", all_workflows)
    
    # set workflow attribute
    updated_attribute = db_manager.update_workflow_attribute("wf_001", "priority", "medium")
    print("Updated Attribute:", updated_attribute)
    # get workflow attributes
    attributes = db_manager.get_workflow_attributes("wf_001")
    print("Workflow Attributes:", attributes)
    # delete workflow attribute
    deletion_attr_result = db_manager.delete_workflow_attribute("wf_001", "priority")
    print("Deleted Attribute:", deletion_attr_result)

    deletion_result = db_manager.delete_workflow("wf_001")
    print("Deleted Workflow:", deletion_result)