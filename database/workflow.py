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



# Base class for models
Base = declarative_base()

class WorkflowModel(Base):
    """
    SQLAlchemy Model representing the 'wf_workflows' table.
    """
    __tablename__ = "wf_workflows"   
    __table_args__ = {"comment": "Table storing workflow definitions"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique workflow identifier")
    name: Mapped[str] = mapped_column(String, nullable=False,comment="Human-readable name of the workflow")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the workflow")
    status: Mapped[str] = mapped_column(String, default="created", comment="Processing status of the workflow")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the workflow was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the workflow was last updated")

class WorkflowModelAttribute(Base):
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

class WorkflowInteraction(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the interaction was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the interaction was last updated")

class WorkflowInteractionComponent(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the component was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the component was last updated")

class WorkflowRole(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the role was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the role was last updated")

class WorkflowRoleAttribute(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was last updated")

class WorkflowInstance(Base):
    """
    SQLAlchemy Model representing the 'wf_workflow_instances' table.
    """
    __tablename__ = "wf_workflow_instances"
    __table_args__ = {"comment": "Table storing workflow instances"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique instance identifier")
    workflow_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, comment="Associated workflow identifier (optional)")
    status: Mapped[str] = mapped_column(String, default="initialized", comment="Current status of the instance")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the instance was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the instance was last updated")
 
class WorkflowInstanceAttribute(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was last updated")

class WorkflowUnitOfWorkType(Base):
    """
    SQLAlchemy Model representing the 'wf_workflow_unit_of_work_types' table.
    """
    __tablename__ = "wf_workflow_unit_of_work_types"
    __table_args__ = {"comment": "Table storing workflow unit of work types"}

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, comment="Unique unit of work type identifier")
    name: Mapped[str] = mapped_column(String, nullable=False, comment="Name of the unit of work type")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Detailed description of the unit of work type")
    uow_class: Mapped[str] = mapped_column(String, nullable=False, comment="Class of the unit of work (e.g., atomic, set, tuple)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the unit of work type was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the unit of work type was last updated")

class WorkflowUnitOfWork(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the unit of work was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the unit of work was last updated")

class WorkflowUnitOfWorkAttribute(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="Timestamp when the attribute was last updated")


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
    
    fetched_workflow = db_manager.get_workflow("wf_001")
    print("Fetched Workflow:", fetched_workflow)
    
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