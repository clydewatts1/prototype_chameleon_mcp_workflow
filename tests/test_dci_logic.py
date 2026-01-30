"""
Tests for Dynamic Context Injection (DCI) Logic.

Verifies that CONDITIONAL_INJECTOR guards correctly evaluate conditions
and apply mutations (model_override, instructions, knowledge_fragments)
to Units of Work at runtime.

Constitutional Reference: Article XX (Model Orchestration & DCI)
"""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.manager import DatabaseManager
from database.models_instance import (
    InstanceBase,
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Components,
    Local_Guardians,
    Local_Interactions,
    UnitsOfWork,
    UOW_Attributes,
)
from database.enums import (
    InstanceStatus,
    RoleType,
    ComponentDirection,
    GuardianType,
    UOWStatus,
)
from chameleon_workflow_engine.engine import ChameleonEngine
from chameleon_workflow_engine.provider_router import ProviderRouter, initialize_provider_router


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    InstanceBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def test_instance(in_memory_db):
    """Create a test instance context."""
    instance = Instance_Context(
        instance_id=uuid.uuid4(),
        name="DCI_Test_Instance",
        description="Test instance for DCI mutations",
        status=InstanceStatus.ACTIVE.value,
    )
    in_memory_db.add(instance)
    in_memory_db.flush()
    return instance


@pytest.fixture
def test_workflow(in_memory_db, test_instance):
    """Create a test workflow."""
    workflow = Local_Workflows(
        local_workflow_id=uuid.uuid4(),
        instance_id=test_instance.instance_id,
        original_workflow_id=uuid.uuid4(),
        name="Credit_Check_Workflow",
        version=1,
        is_master=True,
    )
    in_memory_db.add(workflow)
    in_memory_db.flush()
    return workflow


@pytest.fixture
def test_role(in_memory_db, test_workflow):
    """Create a test role (BETA processor)."""
    role = Local_Roles(
        role_id=uuid.uuid4(),
        local_workflow_id=test_workflow.local_workflow_id,
        name="Credit_Analyst",
        role_type=RoleType.BETA.value,
    )
    in_memory_db.add(role)
    in_memory_db.flush()
    return role


@pytest.fixture
def inbound_component(in_memory_db, test_role, test_workflow):
    """Create an INBOUND component with DCI guard."""
    # Create an interaction first
    interaction = Local_Interactions(
        interaction_id=uuid.uuid4(),
        local_workflow_id=test_workflow.local_workflow_id,
        name="Credit_Check_Interaction",
    )
    in_memory_db.add(interaction)
    in_memory_db.flush()
    
    component = Local_Components(
        component_id=uuid.uuid4(),
        local_workflow_id=test_role.local_workflow_id,
        role_id=test_role.role_id,
        interaction_id=interaction.interaction_id,
        name="Credit_Check_Input",
        direction=ComponentDirection.INBOUND.value,
    )
    in_memory_db.add(component)
    in_memory_db.flush()
    return component


@pytest.fixture
def dci_guard_low_score(in_memory_db, inbound_component):
    """
    Create a CONDITIONAL_INJECTOR guard for low credit scores.
    
    Rule: If credit_score < 100, use gpt-4 model with special instructions.
    """
    guard = Local_Guardians(
        guardian_id=uuid.uuid4(),
        local_workflow_id=inbound_component.local_workflow_id,
        component_id=inbound_component.component_id,
        name="Low_Credit_Score_Handler",
        description="Upgrades to premium model for risky cases",
        type=GuardianType.CONDITIONAL_INJECTOR.value,
        attributes={
            "scope": "pre_execution",
            "rules": [
                {
                    "condition": "credit_score < 100",
                    "action": "mutate",
                    "payload": {
                        "model_override": "gpt-4",
                        "instructions": "ALERT: Low credit score detected. Apply strict verification protocol.",
                        "knowledge_fragments": ["credit_risk_policies_v2"]
                    }
                }
            ]
        }
    )
    in_memory_db.add(guard)
    in_memory_db.flush()
    return guard


@pytest.fixture
def test_uow(in_memory_db, test_workflow, test_role, inbound_component):
    """Create a test Unit of Work."""
    uow = UnitsOfWork(
        uow_id=uuid.uuid4(),
        instance_id=test_workflow.instance_id,
        local_workflow_id=test_workflow.local_workflow_id,
        current_interaction_id=inbound_component.interaction_id,
        status=UOWStatus.PENDING.value,
        last_heartbeat=datetime.now(timezone.utc),
    )
    in_memory_db.add(uow)
    in_memory_db.flush()
    return uow


@pytest.fixture
def test_uow_attributes_low_score(in_memory_db, test_uow):
    """Create UOW attributes with low credit score."""
    attr = UOW_Attributes(
        attribute_id=uuid.uuid4(),
        uow_id=test_uow.uow_id,
        instance_id=test_uow.instance_id,
        key="credit_score",
        value=50,  # Low score - should trigger DCI mutation
        version=1,
        actor_id=uuid.uuid4(),
    )
    in_memory_db.add(attr)
    in_memory_db.flush()
    return attr


class TestDCIBasicFunctionality:
    """Test basic DCI mutation capabilities."""
    
    def test_model_override_applied(
        self, in_memory_db, test_uow, test_role, dci_guard_low_score, test_uow_attributes_low_score
    ):
        """Test that model_override is applied when condition matches."""
        # Initialize provider router
        router = ProviderRouter()
        initialize_provider_router(router)
        
        # Build UOW attributes dictionary
        uow_attributes = {"credit_score": 50}
        
        # Create a minimal engine to test _apply_dci_mutations
        # Note: We can't fully test checkout_work without full database setup
        # So we test the mutation method directly
        from chameleon_workflow_engine.engine import ChameleonEngine
        
        # Create mock database manager
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        
        # Apply DCI mutations
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Verify model_id was set
        assert test_uow.model_id == "gpt-4", f"Expected model_id='gpt-4', got {test_uow.model_id}"
        
        # Verify mutation_audit_log was created
        assert test_uow.mutation_audit_log is not None
        assert len(test_uow.mutation_audit_log) == 1
        
        mutation = test_uow.mutation_audit_log[0]
        assert mutation['guard_name'] == "Low_Credit_Score_Handler"
        assert mutation['condition'] == "credit_score < 100"
        assert mutation['model_override'] == "gpt-4"
    
    def test_instructions_injection(
        self, in_memory_db, test_uow, test_role, dci_guard_low_score, test_uow_attributes_low_score
    ):
        """Test that instructions are injected when condition matches."""
        router = ProviderRouter()
        initialize_provider_router(router)
        
        uow_attributes = {"credit_score": 50}
        
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Verify instructions were injected
        assert test_uow.injected_instructions is not None
        assert "Low credit score detected" in test_uow.injected_instructions
        assert "strict verification protocol" in test_uow.injected_instructions
    
    def test_knowledge_fragments_injection(
        self, in_memory_db, test_uow, test_role, dci_guard_low_score, test_uow_attributes_low_score
    ):
        """Test that knowledge fragments are injected when condition matches."""
        router = ProviderRouter()
        initialize_provider_router(router)
        
        uow_attributes = {"credit_score": 50}
        
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Verify knowledge fragments were injected
        assert test_uow.knowledge_fragment_refs is not None
        assert len(test_uow.knowledge_fragment_refs) == 1
        assert "credit_risk_policies_v2" in test_uow.knowledge_fragment_refs


class TestDCIConditionEvaluation:
    """Test condition evaluation logic."""
    
    def test_no_mutation_when_condition_false(self, in_memory_db, test_uow, test_role, dci_guard_low_score):
        """Test that no mutation occurs when condition doesn't match."""
        router = ProviderRouter()
        initialize_provider_router(router)
        
        # High credit score - should NOT trigger mutation
        uow_attributes = {"credit_score": 750}
        
        # Add UOW attribute for high score
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=test_uow.uow_id,
            instance_id=test_uow.instance_id,
            key="credit_score",
            value=750,
            version=1,
            actor_id=uuid.uuid4(),
        )
        in_memory_db.add(attr)
        in_memory_db.flush()
        
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Verify NO mutations were applied
        assert test_uow.model_id is None
        assert test_uow.injected_instructions is None
        assert test_uow.knowledge_fragment_refs is None
        assert test_uow.mutation_audit_log is None or len(test_uow.mutation_audit_log) == 0


class TestDCIWhitelistEnforcement:
    """Test model whitelist validation."""
    
    def test_invalid_model_uses_failover(self, in_memory_db, test_uow, test_role, inbound_component):
        """Test that invalid model IDs trigger failover."""
        router = ProviderRouter()
        initialize_provider_router(router)
        
        # Create guard with invalid model
        guard = Local_Guardians(
            guardian_id=uuid.uuid4(),
            local_workflow_id=inbound_component.local_workflow_id,
            component_id=inbound_component.component_id,
            name="Invalid_Model_Guard",
            type=GuardianType.CONDITIONAL_INJECTOR.value,
            attributes={
                "scope": "pre_execution",
                "rules": [
                    {
                        "condition": "always_true == True",
                        "action": "mutate",
                        "payload": {
                            "model_override": "malicious-model-999",
                        }
                    }
                ]
            }
        )
        in_memory_db.add(guard)
        in_memory_db.flush()
        
        # Add attribute
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=test_uow.uow_id,
            instance_id=test_uow.instance_id,
            key="always_true",
            value=True,
            version=1,
            actor_id=uuid.uuid4(),
        )
        in_memory_db.add(attr)
        in_memory_db.flush()
        
        uow_attributes = {"always_true": True}
        
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Verify failover model was used (gemini-flash)
        assert test_uow.model_id == "gemini-flash"
        
        # Verify failover was logged
        assert test_uow.mutation_audit_log is not None
        mutation = test_uow.mutation_audit_log[0]
        assert mutation.get('failover_used') == True
        assert mutation.get('failover_model') == "gemini-flash"


class TestProviderRouter:
    """Test ProviderRouter functionality."""
    
    def test_resolve_model_openai(self):
        """Test resolving OpenAI models."""
        router = ProviderRouter()
        config = router.resolve_model("gpt-4")
        
        assert config['provider'] == "openai"
        assert config['model'] == "gpt-4"
    
    def test_resolve_model_anthropic(self):
        """Test resolving Anthropic models."""
        router = ProviderRouter()
        config = router.resolve_model("claude-3-sonnet")
        
        assert config['provider'] == "anthropic"
        assert config['model'] == "claude-3-sonnet"
    
    def test_whitelist_validation(self):
        """Test model whitelist validation."""
        router = ProviderRouter()
        
        assert router.validate_model_whitelist("gpt-4") == True
        assert router.validate_model_whitelist("claude-3-sonnet") == True
        assert router.validate_model_whitelist("invalid-model") == False
    
    def test_failover_model(self):
        """Test failover model retrieval."""
        router = ProviderRouter()
        failover = router.get_failover_model("invalid-model")
        
        assert failover == "gemini-flash"
    
    def test_get_model_config(self):
        """Test complete model configuration."""
        router = ProviderRouter()
        config = router.get_model_config("gpt-4")
        
        assert config['model_id'] == "gpt-4"
        assert config['provider'] == "openai"
        assert config['is_whitelisted'] == True
        assert config['is_failover'] == False


class TestDCIRuleOrdering:
    """Test rule evaluation order (last match wins)."""
    
    def test_last_match_wins(self, in_memory_db, test_uow, test_role, inbound_component):
        """Test that last matching rule's model_override wins."""
        router = ProviderRouter()
        initialize_provider_router(router)
        
        # Create guard with multiple rules
        guard = Local_Guardians(
            guardian_id=uuid.uuid4(),
            local_workflow_id=inbound_component.local_workflow_id,
            component_id=inbound_component.component_id,
            name="Multi_Rule_Guard",
            type=GuardianType.CONDITIONAL_INJECTOR.value,
            attributes={
                "scope": "pre_execution",
                "rules": [
                    {
                        "condition": "score < 100",
                        "action": "mutate",
                        "payload": {"model_override": "gpt-3.5-turbo"}
                    },
                    {
                        "condition": "score < 50",
                        "action": "mutate",
                        "payload": {"model_override": "gpt-4"}  # Should win
                    }
                ]
            }
        )
        in_memory_db.add(guard)
        in_memory_db.flush()
        
        # Add attribute with score=30 (matches both conditions)
        attr = UOW_Attributes(
            attribute_id=uuid.uuid4(),
            uow_id=test_uow.uow_id,
            instance_id=test_uow.instance_id,
            key="score",
            value=30,
            version=1,
            actor_id=uuid.uuid4(),
        )
        in_memory_db.add(attr)
        in_memory_db.flush()
        
        uow_attributes = {"score": 30}
        
        class MockDBManager:
            def __init__(self, session):
                self.session = session
        
        engine = ChameleonEngine(MockDBManager(in_memory_db))
        engine._apply_dci_mutations(
            session=in_memory_db,
            uow=test_uow,
            role=test_role,
            uow_attributes=uow_attributes
        )
        
        # Last matching rule should win (gpt-4, not gpt-3.5-turbo)
        assert test_uow.model_id == "gpt-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
