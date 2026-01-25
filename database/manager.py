"""
Database Manager for the Chameleon Workflow Engine.

This module provides the DatabaseManager class that manages connections
to both Tier 1 (Templates) and Tier 2 (Instance) databases, ensuring
complete air-gapped isolation between the two tiers.
"""

from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models_template import TemplateBase
from .models_instance import InstanceBase


class DatabaseManager:
    """
    Manages database connections for both Template and Instance tiers.
    
    This manager ensures air-gapped isolation by maintaining separate
    engines and session factories for each tier.
    """

    def __init__(
        self,
        template_url: Optional[str] = None,
        instance_url: Optional[str] = None,
        echo: bool = False
    ):
        """
        Initialize the Database Manager.

        Args:
            template_url: Connection URL for Tier 1 (Templates) database.
                         If None, no template engine is created.
            instance_url: Connection URL for Tier 2 (Instance) database.
                         If None, no instance engine is created.
            echo: Whether to echo SQL statements for debugging.
        """
        self._template_engine: Optional[Engine] = None
        self._instance_engine: Optional[Engine] = None
        self._template_session_factory: Optional[sessionmaker] = None
        self._instance_session_factory: Optional[sessionmaker] = None
        self._echo = echo

        if template_url:
            self.initialize_template_engine(template_url)

        if instance_url:
            self.initialize_instance_engine(instance_url)

    def initialize_template_engine(self, url: str) -> Engine:
        """
        Initialize the Tier 1 (Templates) database engine.

        Args:
            url: Database connection URL for the template database.

        Returns:
            The created SQLAlchemy Engine.
        """
        self._template_engine = create_engine(url, echo=self._echo)
        self._template_session_factory = sessionmaker(bind=self._template_engine)
        return self._template_engine

    def initialize_instance_engine(self, url: str) -> Engine:
        """
        Initialize the Tier 2 (Instance) database engine.

        Args:
            url: Database connection URL for the instance database.

        Returns:
            The created SQLAlchemy Engine.
        """
        self._instance_engine = create_engine(url, echo=self._echo)
        self._instance_session_factory = sessionmaker(bind=self._instance_engine)
        return self._instance_engine

    @property
    def template_engine(self) -> Engine:
        """Get the template database engine."""
        if self._template_engine is None:
            raise RuntimeError("Template engine not initialized. Call initialize_template_engine() first.")
        return self._template_engine

    @property
    def instance_engine(self) -> Engine:
        """Get the instance database engine."""
        if self._instance_engine is None:
            raise RuntimeError("Instance engine not initialized. Call initialize_instance_engine() first.")
        return self._instance_engine

    @contextmanager
    def get_template_session(self) -> Session:
        """
        Get a session for the Tier 1 (Templates) database.

        Yields:
            A SQLAlchemy Session for the template database.

        Raises:
            RuntimeError: If the template engine is not initialized.
        """
        if self._template_session_factory is None:
            raise RuntimeError("Template engine not initialized. Call initialize_template_engine() first.")

        session = self._template_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def get_instance_session(self) -> Session:
        """
        Get a session for the Tier 2 (Instance) database.

        Yields:
            A SQLAlchemy Session for the instance database.

        Raises:
            RuntimeError: If the instance engine is not initialized.
        """
        if self._instance_session_factory is None:
            raise RuntimeError("Instance engine not initialized. Call initialize_instance_engine() first.")

        session = self._instance_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_template_schema(self, engine: Optional[Engine] = None) -> None:
        """
        Create all Tier 1 (Template) tables in the database.

        Args:
            engine: Optional engine to use. If None, uses the manager's template engine.

        Raises:
            RuntimeError: If no engine is available.
        """
        target_engine = engine or self._template_engine
        if target_engine is None:
            raise RuntimeError("No engine available. Provide an engine or initialize template engine first.")

        TemplateBase.metadata.create_all(target_engine)

    def create_instance_schema(self, engine: Optional[Engine] = None) -> None:
        """
        Create all Tier 2 (Instance) tables in the database.

        Args:
            engine: Optional engine to use. If None, uses the manager's instance engine.

        Raises:
            RuntimeError: If no engine is available.
        """
        target_engine = engine or self._instance_engine
        if target_engine is None:
            raise RuntimeError("No engine available. Provide an engine or initialize instance engine first.")

        InstanceBase.metadata.create_all(target_engine)

    def drop_template_schema(self, engine: Optional[Engine] = None) -> None:
        """
        Drop all Tier 1 (Template) tables from the database.

        WARNING: This will delete all template data!

        Args:
            engine: Optional engine to use. If None, uses the manager's template engine.

        Raises:
            RuntimeError: If no engine is available.
        """
        target_engine = engine or self._template_engine
        if target_engine is None:
            raise RuntimeError("No engine available. Provide an engine or initialize template engine first.")

        TemplateBase.metadata.drop_all(target_engine)

    def drop_instance_schema(self, engine: Optional[Engine] = None) -> None:
        """
        Drop all Tier 2 (Instance) tables from the database.

        WARNING: This will delete all instance data!

        Args:
            engine: Optional engine to use. If None, uses the manager's instance engine.

        Raises:
            RuntimeError: If no engine is available.
        """
        target_engine = engine or self._instance_engine
        if target_engine is None:
            raise RuntimeError("No engine available. Provide an engine or initialize instance engine first.")

        InstanceBase.metadata.drop_all(target_engine)

    def close(self) -> None:
        """
        Close all database connections.
        """
        if self._template_engine:
            self._template_engine.dispose()
        if self._instance_engine:
            self._instance_engine.dispose()
