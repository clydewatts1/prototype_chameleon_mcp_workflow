"""
Database Module for Chameleon Workflow Engine

This module handles all database interactions using SQLAlchemy.
It defines the schema (Models) and the Data Access Object (DatabaseManager).
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

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

# Base class for models
Base = declarative_base()

class WorkflowModel(Base):
    """
    SQLAlchemy Model representing the 'workflows' table.
    """
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="created")
    steps = Column(JSON, default=list)  # Stores steps as a JSON list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # You can add other fields like 'result', 'current_step_index', etc.

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

    # --- Setters / Creators ---

    def create_workflow(self, workflow_id: str, name: str, description: str, steps: List[str]) -> Dict[str, Any]:
        """Create and save a new workflow."""
        with self.get_session() as session:
            new_workflow = WorkflowModel(
                id=workflow_id,
                name=name,
                description=description,
                steps=steps,
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

    # --- Process Functions ---

    def update_status(self, workflow_id: str, new_status: str) -> Optional[Dict[str, Any]]:
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

    def _to_dict(self, model: WorkflowModel) -> Dict[str, Any]:
        """Helper to convert SQLAlchemy model to dictionary."""
        return {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "status": model.status,
            "steps": model.steps,
            "created_at": model.created_at.isoformat() if model.created_at else None
        }
    
if __name__ == "__main__":
    # Simple test code
    db_manager = DatabaseManager()
    workflow = db_manager.create_workflow(
        workflow_id="wf_001",
        name="Test Workflow",
        description="A workflow for testing",
        steps=["step1", "step2", "step3"]
    )
    print("Created Workflow:", workflow)
    
    fetched_workflow = db_manager.get_workflow("wf_001")
    print("Fetched Workflow:", fetched_workflow)
    
    updated_workflow = db_manager.update_status("wf_001", "in_progress")
    print("Updated Workflow Status:", updated_workflow)
    
    all_workflows = db_manager.get_all_workflows()
    print("All Workflows:", all_workflows)
    
    deletion_result = db_manager.delete_workflow("wf_001")
    print("Deleted Workflow:", deletion_result)