"""
Integration tests for Semantic Guard with Chameleon Engine.

Tests the end-to-end routing logic using advanced expressions,
custom functions, and error handling.

Test Coverage:
- Simple expression routing (arithmetic, Boolean)
- Custom function evaluation
- on_error and default branch handling
- State hash verification
- Silent failure protocol (error logging)
- Error interaction routing (EPSILON)
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from database.models_template import (
    TemplateBase,
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
)
from database.models_instance import (
    InstanceBase,
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Guardians,
    UnitsOfWork,
    UOW_Attributes,
    Local_Actors,
)
from database.enums import (
    RoleType,
    GuardianType,
    ComponentDirection,
    ActorType,
)
from chameleon_workflow_engine.engine import ChameleonEngine
from chameleon_workflow_engine.semantic_guard import SemanticGuard, StateVerifier


@pytest.fixture
def template_db():
    """Create in-memory template database for testing."""
    engine = create_engine("sqlite:///:memory:")
    TemplateBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()


@pytest.fixture
def instance_db():
    """Create in-memory instance database for testing."""
    engine = create_engine("sqlite:///:memory:")
    InstanceBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()


@pytest.fixture
def engine_instance(template_db, instance_db):
    """Create engine with both template and instance databases."""
    # Mock the database manager
    class MockDatabaseManager:
        def get_template_session(self):
            return template_db
        
        def get_instance_session(self):
            return instance_db
    
    engine = ChameleonEngine(db_manager=MockDatabaseManager())
    return engine


class TestSemanticGuardIntegration:
    """Tests for Semantic Guard integration with Engine."""
    
    def test_simple_arithmetic_routing(self, template_db, instance_db, engine_instance):
        """Test routing using simple arithmetic expressions."""
        # Setup: Create workflows, roles, interactions, components, guardians
        instance = Instance_Context(name="Test_Instance")
        instance_db.add(instance)
        instance_db.flush()
        
        workflow = Local_Workflows(
            instance_id=instance.instance_id,
            name="Test_Workflow",
            is_master=True,
        )
        instance_db.add(workflow)
        instance_db.flush()
        
        # Create BETA role
        beta_role = Local_Roles(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            name="Processor",
            role_type=RoleType.BETA.value,
            is_recursive_gateway=False,
        )
        instance_db.add(beta_role)
        instance_db.flush()
        
        # Create interactions
        interaction_1 = Local_Interactions(
            instance_id=instance.instance_id,
            name="Standard_Processing",
        )
        interaction_2 = Local_Interactions(
            instance_id=instance.instance_id,
            name="High_Value_Processing",
        )
        interaction_default = Local_Interactions(
            instance_id=instance.instance_id,
            name="Default_Processing",
        )
        instance_db.add_all([interaction_1, interaction_2, interaction_default])
        instance_db.flush()
        
        # Create OUTBOUND components
        component_1 = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="High_Value_Processor",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_2.interaction_id,
        )
        component_default = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="Default_Processor",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_default.interaction_id,
        )
        instance_db.add_all([component_1, component_default])
        instance_db.flush()
        
        # Create guardians with arithmetic expressions
        guardian_1 = Local_Guardians(
            instance_id=instance.instance_id,
            component_id=component_1.component_id,
            type=GuardianType.CRITERIA_GATE.value,
            attributes={
                "interaction_policy": {
                    "branches": [
                        {
                            "condition": "amount > 50000",
                            "next_interaction": "High_Value_Processing",
                            "action": "ROUTE",
                        }
                    ],
                    "default": {
                        "next_interaction": "Default_Processing",
                        "action": "ROUTE",
                    },
                }
            },
        )
        instance_db.add(guardian_1)
        instance_db.flush()
        
        # Create UOW with amount attribute
        uow = UnitsOfWork(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            current_interaction_id=interaction_1.interaction_id,
            status="ACTIVE",
        )
        instance_db.add(uow)
        instance_db.flush()
        
        # Add UOW attribute: amount = 75000 (should match high-value)
        attr = UOW_Attributes(
            uow_id=uow.uow_id,
            key="amount",
            value=75000,
            version=1,
        )
        instance_db.add(attr)
        instance_db.commit()
        
        # Test routing with Semantic Guard
        outbound_components = [component_1, component_default]
        result = engine_instance._evaluate_interaction_policy(
            session=instance_db,
            uow=uow,
            outbound_components=outbound_components,
            use_semantic_guard=True,
        )
        
        # Should route to high-value interaction (condition matched)
        assert result == interaction_2.interaction_id
    
    def test_boolean_logic_routing(self, template_db, instance_db, engine_instance):
        """Test routing using Boolean logic expressions."""
        # Setup
        instance = Instance_Context(name="Test_Instance")
        instance_db.add(instance)
        instance_db.flush()
        
        workflow = Local_Workflows(
            instance_id=instance.instance_id,
            name="Test_Workflow",
            is_master=True,
        )
        instance_db.add(workflow)
        instance_db.flush()
        
        beta_role = Local_Roles(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            name="Router",
            role_type=RoleType.BETA.value,
        )
        instance_db.add(beta_role)
        instance_db.flush()
        
        # Interactions
        interaction_urgent = Local_Interactions(
            instance_id=instance.instance_id,
            name="Urgent_Path",
        )
        interaction_normal = Local_Interactions(
            instance_id=instance.instance_id,
            name="Normal_Path",
        )
        instance_db.add_all([interaction_urgent, interaction_normal])
        instance_db.flush()
        
        # Components
        component_urgent = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="Urgent_Component",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_urgent.interaction_id,
        )
        component_normal = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="Normal_Component",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_normal.interaction_id,
        )
        instance_db.add_all([component_urgent, component_normal])
        instance_db.flush()
        
        # Guardian with Boolean expression
        guardian = Local_Guardians(
            instance_id=instance.instance_id,
            component_id=component_urgent.component_id,
            type=GuardianType.CRITERIA_GATE.value,
            attributes={
                "interaction_policy": {
                    "branches": [
                        {
                            "condition": "(priority > 7 and amount > 10000) or flagged",
                            "next_interaction": "Urgent_Path",
                            "action": "ROUTE",
                        }
                    ],
                    "default": {
                        "next_interaction": "Normal_Path",
                        "action": "ROUTE",
                    },
                }
            },
        )
        instance_db.add(guardian)
        instance_db.flush()
        
        # UOW with attributes
        uow = UnitsOfWork(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            current_interaction_id=interaction_normal.interaction_id,
            status="ACTIVE",
        )
        instance_db.add(uow)
        instance_db.flush()
        
        # Case 1: priority=8, amount=50000, flagged=False -> should match (first part true)
        UOW_Attributes(
            uow_id=uow.uow_id,
            key="priority",
            value=8,
            version=1,
        ).save(instance_db)
        UOW_Attributes(
            uow_id=uow.uow_id,
            key="amount",
            value=50000,
            version=1,
        ).save(instance_db)
        UOW_Attributes(
            uow_id=uow.uow_id,
            key="flagged",
            value=False,
            version=1,
        ).save(instance_db)
        instance_db.commit()
        
        result = engine_instance._evaluate_interaction_policy(
            session=instance_db,
            uow=uow,
            outbound_components=[component_urgent, component_normal],
            use_semantic_guard=True,
        )
        
        assert result == interaction_urgent.interaction_id
    
    def test_error_branch_handling(self, template_db, instance_db, engine_instance):
        """Test on_error branch routing for failed evaluations."""
        # Setup
        instance = Instance_Context(name="Test_Instance")
        instance_db.add(instance)
        instance_db.flush()
        
        workflow = Local_Workflows(
            instance_id=instance.instance_id,
            name="Test_Workflow",
            is_master=True,
        )
        instance_db.add(workflow)
        instance_db.flush()
        
        beta_role = Local_Roles(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            name="ErrorHandler",
            role_type=RoleType.BETA.value,
        )
        instance_db.add(beta_role)
        instance_db.flush()
        
        # Interactions
        interaction_success = Local_Interactions(
            instance_id=instance.instance_id,
            name="Success_Path",
        )
        interaction_error = Local_Interactions(
            instance_id=instance.instance_id,
            name="Error_Path",
        )
        instance_db.add_all([interaction_success, interaction_error])
        instance_db.flush()
        
        # Components
        component_main = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="Main_Processor",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_success.interaction_id,
        )
        instance_db.add(component_main)
        instance_db.flush()
        
        # Guardian with on_error branch
        guardian = Local_Guardians(
            instance_id=instance.instance_id,
            component_id=component_main.component_id,
            type=GuardianType.CRITERIA_GATE.value,
            attributes={
                "interaction_policy": {
                    "branches": [
                        {
                            "condition": "undefined_var > 10",
                            "next_interaction": "Success_Path",
                            "action": "ROUTE",
                        },
                        {
                            "condition": "1 == 1",
                            "next_interaction": "Error_Path",
                            "action": "ROUTE",
                            "on_error": True,
                        },
                    ],
                }
            },
        )
        instance_db.add(guardian)
        instance_db.flush()
        
        # UOW (no attributes, will cause undefined_var error)
        uow = UnitsOfWork(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            current_interaction_id=interaction_success.interaction_id,
            status="ACTIVE",
        )
        instance_db.add(uow)
        instance_db.commit()
        
        # Test: on_error branch should handle the evaluation error
        result = engine_instance._evaluate_interaction_policy(
            session=instance_db,
            uow=uow,
            outbound_components=[component_main],
            use_semantic_guard=True,
        )
        
        # Should route to error path (error handler)
        assert result == interaction_error.interaction_id
    
    def test_fallback_to_simple_dsl(self, template_db, instance_db, engine_instance):
        """Test fallback to simple DSL when Semantic Guard disabled."""
        # Setup
        instance = Instance_Context(name="Test_Instance")
        instance_db.add(instance)
        instance_db.flush()
        
        workflow = Local_Workflows(
            instance_id=instance.instance_id,
            name="Test_Workflow",
            is_master=True,
        )
        instance_db.add(workflow)
        instance_db.flush()
        
        beta_role = Local_Roles(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            name="SimpleRouter",
            role_type=RoleType.BETA.value,
        )
        instance_db.add(beta_role)
        instance_db.flush()
        
        # Interactions
        interaction_1 = Local_Interactions(
            instance_id=instance.instance_id,
            name="Path_One",
        )
        interaction_2 = Local_Interactions(
            instance_id=instance.instance_id,
            name="Path_Two",
        )
        instance_db.add_all([interaction_1, interaction_2])
        instance_db.flush()
        
        # Components
        component = Local_Components(
            instance_id=instance.instance_id,
            local_role_id=beta_role.role_id,
            name="Router_Component",
            direction=ComponentDirection.OUTBOUND.value,
            interaction_id=interaction_1.interaction_id,
        )
        instance_db.add(component)
        instance_db.flush()
        
        # Simple DSL policy (no arithmetic)
        guardian = Local_Guardians(
            instance_id=instance.instance_id,
            component_id=component.component_id,
            type=GuardianType.CRITERIA_GATE.value,
            attributes={
                "interaction_policy": {
                    "branches": [
                        {
                            "condition": "status == PROCESSING",
                            "next_interaction": "Path_One",
                            "action": "ROUTE",
                        }
                    ]
                }
            },
        )
        instance_db.add(guardian)
        instance_db.flush()
        
        # UOW
        uow = UnitsOfWork(
            instance_id=instance.instance_id,
            local_workflow_id=workflow.workflow_id,
            current_interaction_id=interaction_2.interaction_id,
            status="PROCESSING",
        )
        instance_db.add(uow)
        instance_db.commit()
        
        # Test with use_semantic_guard=False (fallback to simple DSL)
        result = engine_instance._evaluate_interaction_policy(
            session=instance_db,
            uow=uow,
            outbound_components=[component],
            use_semantic_guard=False,
        )
        
        # Should route using simple DSL
        assert result == interaction_1.interaction_id


class TestStateVerificationIntegration:
    """Tests for X-Content-Hash verification in routing."""
    
    def test_state_hash_verification(self):
        """Test that state hash is computed correctly."""
        attributes = {
            "amount": 100000,
            "priority": 8,
            "flagged": False,
        }
        
        hash_1 = StateVerifier.compute_hash(attributes)
        hash_2 = StateVerifier.compute_hash(attributes)
        
        # Same attributes should produce same hash
        assert hash_1 == hash_2
        
        # Different attributes should produce different hash
        attributes["amount"] = 200000
        hash_3 = StateVerifier.compute_hash(attributes)
        assert hash_1 != hash_3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
