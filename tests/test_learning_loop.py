"""
Tests for the Learning Loop (Experience Extraction) functionality.

This test suite validates:
1. The _harvest_experience method extracts learning from completed work
2. The submit_work method triggers learning without breaking on failure
3. The get_memory method retrieves learned patterns correctly
"""

import sys
from pathlib import Path
import tempfile
import os
import uuid

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import (
    DatabaseManager,
    # Tier 1 Models
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    # Tier 2 Models
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Actors,
    UnitsOfWork,
    UOW_Attributes,
    Local_Role_Attributes,
    # Enums
    RoleType,
    ComponentDirection,
    UOWStatus,
)
from sqlalchemy import and_
from chameleon_workflow_engine.engine import ChameleonEngine


def create_simple_template_workflow(manager: DatabaseManager) -> uuid.UUID:
    """
    Create a simple template workflow with Alpha -> Beta -> Omega flow.
    Returns the template workflow_id.
    """
    with manager.get_template_session() as session:
        # Create workflow
        workflow = Template_Workflows(
            name="Learning_Test_Flow",
            description="A workflow for testing learning",
            ai_context={"purpose": "Testing learning loop"},
            version=1,
            schema_json={}
        )
        session.add(workflow)
        session.flush()
        workflow_id = workflow.workflow_id
        
        # Create roles
        alpha_role = Template_Roles(
            workflow_id=workflow_id,
            name="Initiator",
            description="Start the workflow",
            role_type=RoleType.ALPHA.value,
            ai_context={}
        )
        session.add(alpha_role)
        session.flush()
        
        beta_role = Template_Roles(
            workflow_id=workflow_id,
            name="Processor",
            description="Process the work",
            role_type=RoleType.BETA.value,
            ai_context={}
        )
        session.add(beta_role)
        session.flush()
        
        omega_role = Template_Roles(
            workflow_id=workflow_id,
            name="Finalizer",
            description="Finalize the work",
            role_type=RoleType.OMEGA.value,
            ai_context={}
        )
        session.add(omega_role)
        session.flush()
        
        # Create interactions
        intake = Template_Interactions(
            workflow_id=workflow_id,
            name="Intake",
            description="Initial queue",
            ai_context={}
        )
        processing = Template_Interactions(
            workflow_id=workflow_id,
            name="Processing",
            description="Processing queue",
            ai_context={}
        )
        complete = Template_Interactions(
            workflow_id=workflow_id,
            name="Complete",
            description="Completion queue",
            ai_context={}
        )
        session.add_all([intake, processing, complete])
        session.flush()
        
        # Create components (connections)
        # Alpha OUTBOUND -> Intake
        comp1 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=intake.interaction_id,
            role_id=alpha_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Alpha_to_Intake",
            description="Alpha outputs to Intake"
        )
        # Intake -> Beta INBOUND
        comp2 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=intake.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Intake_to_Beta",
            description="Beta reads from Intake"
        )
        # Beta OUTBOUND -> Processing
        comp3 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=processing.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_to_Processing",
            description="Beta outputs to Processing"
        )
        # Processing -> Omega INBOUND
        comp4 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=processing.interaction_id,
            role_id=omega_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Processing_to_Omega",
            description="Omega reads from Processing"
        )
        # Omega OUTBOUND -> Complete
        comp5 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=complete.interaction_id,
            role_id=omega_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Omega_to_Complete",
            description="Omega outputs to Complete"
        )
        session.add_all([comp1, comp2, comp3, comp4, comp5])
        session.commit()
        
        return workflow_id


def test_harvest_experience_creates_memory():
    """Test that _harvest_experience creates new memory records."""
    print("\n=== Testing Experience Harvesting (Create New Memory) ===")
    
    # Create temporary databases
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        # Initialize and create workflow
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        template_id = create_simple_template_workflow(manager)
        engine = ChameleonEngine(manager)
        
        initial_context = {"invoice_amount": 450}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        print(f"✓ Workflow instantiated: {instance_id}")
        
        # Create test actor
        actor_id = uuid.uuid4()
        
        with manager.get_instance_session() as session:
            actor = Local_Actors(
                actor_id=actor_id,
                instance_id=instance_id,
                identity_key="test_actor",
                name="Test Actor",
                type="HUMAN"
            )
            session.add(actor)
            session.commit()
        
        print(f"✓ Test actor created: {actor_id}")
        
        # Get the Beta role ID
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                Local_Roles.role_type == RoleType.BETA.value
            ).first()
            beta_role_id = beta_role.role_id
        
        print(f"✓ Beta role found: {beta_role_id}")
        
        # Checkout work
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None
        uow_id = result["uow_id"]
        print(f"✓ Work checked out: {uow_id}")
        
        # Submit work with a learned rule
        result_attributes = {
            "invoice_amount": 450,
            "status": "processed",
            "_learned_rule": {
                "key": "invoice_limit",
                "value": 500
            }
        }
        
        success = engine.submit_work(
            uow_id=uow_id,
            actor_id=actor_id,
            result_attributes=result_attributes,
            reasoning="Processed invoice and learned approval limit"
        )
        
        assert success, "Work submission failed"
        print(f"✓ Work submitted with learning")
        
        # Verify memory was created
        with manager.get_instance_session() as session:
            actor_id_str = str(actor_id)
            memory = session.query(Local_Role_Attributes).filter(
                and_(
                    Local_Role_Attributes.role_id == beta_role_id,
                    Local_Role_Attributes.context_type == "ACTOR",
                    Local_Role_Attributes.context_id == actor_id_str,
                    Local_Role_Attributes.key == "invoice_limit"
                )
            ).first()
            
            assert memory is not None, "Memory was not created"
            assert memory.value == 500
            assert memory.confidence_score == 100  # User-taught, 100% confidence
            assert memory.is_toxic is False
            print(f"✓ Memory created: key='{memory.key}', value={memory.value}, confidence={memory.confidence_score}")
        
        # Verify _learned_rule was NOT saved to UOW attributes
        with manager.get_instance_session() as session:
            learned_rule_attr = session.query(UOW_Attributes).filter(
                and_(
                    UOW_Attributes.uow_id == uow_id,
                    UOW_Attributes.key == "_learned_rule"
                )
            ).first()
            
            assert learned_rule_attr is None, "_learned_rule should not be saved to UOW attributes"
            print(f"✓ _learned_rule was correctly filtered out from UOW attributes")
        
        print("\n✅ Experience harvesting (create) test PASSED")
        return True
        
    finally:
        # Clean up
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)
        if os.path.exists(template_db):
            try:
                os.remove(template_db)
            except PermissionError:
                pass
        if os.path.exists(instance_db):
            try:
                os.remove(instance_db)
            except PermissionError:
                pass


def test_harvest_experience_updates_memory():
    """Test that _harvest_experience updates existing memory records."""
    print("\n=== Testing Experience Harvesting (Update Existing Memory) ===")
    
    # Create temporary databases
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        # Initialize and create workflow
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        template_id = create_simple_template_workflow(manager)
        engine = ChameleonEngine(manager)
        
        initial_context = {"invoice_amount": 450}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        # Create test actor
        actor_id = uuid.uuid4()
        
        with manager.get_instance_session() as session:
            actor = Local_Actors(
                actor_id=actor_id,
                instance_id=instance_id,
                identity_key="test_actor",
                name="Test Actor",
                type="HUMAN"
            )
            session.add(actor)
            
            # Get Beta role
            beta_role = session.query(Local_Roles).filter(
                Local_Roles.role_type == RoleType.BETA.value
            ).first()
            beta_role_id = beta_role.role_id
            
            # Pre-create a memory with initial value
            actor_id_str = str(actor_id)
            initial_memory = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="ACTOR",
                context_id=actor_id_str,
                actor_id=actor_id,
                key="invoice_limit",
                value=300,  # Initial value
                confidence_score=50,  # Low confidence
                is_toxic=False
            )
            session.add(initial_memory)
            session.commit()
        
        print(f"✓ Pre-created memory with value=300, confidence=50")
        
        # Checkout and submit work with updated learning
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None
        uow_id = result["uow_id"]
        
        result_attributes = {
            "invoice_amount": 450,
            "status": "processed",
            "_learned_rule": {
                "key": "invoice_limit",
                "value": 600  # Updated value
            }
        }
        
        success = engine.submit_work(
            uow_id=uow_id,
            actor_id=actor_id,
            result_attributes=result_attributes,
            reasoning="Updated invoice limit learning"
        )
        
        assert success, "Work submission failed"
        print(f"✓ Work submitted with updated learning")
        
        # Verify memory was updated (not duplicated)
        with manager.get_instance_session() as session:
            actor_id_str = str(actor_id)
            memories = session.query(Local_Role_Attributes).filter(
                and_(
                    Local_Role_Attributes.role_id == beta_role_id,
                    Local_Role_Attributes.context_type == "ACTOR",
                    Local_Role_Attributes.context_id == actor_id_str,
                    Local_Role_Attributes.key == "invoice_limit"
                )
            ).all()
            
            assert len(memories) == 1, f"Expected 1 memory record, found {len(memories)}"
            memory = memories[0]
            assert memory.value == 600, f"Expected value=600, got {memory.value}"
            assert memory.confidence_score == 100, f"Expected confidence=100, got {memory.confidence_score}"
            print(f"✓ Memory updated: value={memory.value}, confidence={memory.confidence_score}")
        
        print("\n✅ Experience harvesting (update) test PASSED")
        return True
        
    finally:
        # Clean up
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)
        if os.path.exists(template_db):
            try:
                os.remove(template_db)
            except PermissionError:
                pass
        if os.path.exists(instance_db):
            try:
                os.remove(instance_db)
            except PermissionError:
                pass


def test_get_memory():
    """Test the get_memory method."""
    print("\n=== Testing get_memory Method ===")
    
    # Create temporary databases
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        # Initialize and create workflow
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        template_id = create_simple_template_workflow(manager)
        engine = ChameleonEngine(manager)
        
        initial_context = {}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        # Create test actors
        actor1_id = uuid.uuid4()
        actor2_id = uuid.uuid4()
        
        with manager.get_instance_session() as session:
            actor1 = Local_Actors(
                actor_id=actor1_id,
                instance_id=instance_id,
                identity_key="test_actor_1",
                name="Test Actor 1",
                type="HUMAN"
            )
            actor2 = Local_Actors(
                actor_id=actor2_id,
                instance_id=instance_id,
                identity_key="test_actor_2",
                name="Test Actor 2",
                type="HUMAN"
            )
            session.add_all([actor1, actor2])
            
            # Get Beta role
            beta_role = session.query(Local_Roles).filter(
                Local_Roles.role_type == RoleType.BETA.value
            ).first()
            beta_role_id = beta_role.role_id
            
            # Create various memory records
            # 1. Global memory
            global_memory = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="GLOBAL",
                context_id="GLOBAL",
                actor_id=None,
                key="global_invoice_policy",
                value={"max_amount": 1000},
                confidence_score=80,
                is_toxic=False
            )
            
            # 2. Actor1-specific memory
            actor1_memory = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="ACTOR",
                context_id=str(actor1_id),
                actor_id=actor1_id,
                key="personal_invoice_limit",
                value=500,
                confidence_score=100,
                is_toxic=False
            )
            
            # 3. Actor2-specific memory (should not be visible to actor1)
            actor2_memory = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="ACTOR",
                context_id=str(actor2_id),
                actor_id=actor2_id,
                key="personal_vendor_preference",
                value="Vendor X",
                confidence_score=90,
                is_toxic=False
            )
            
            # 4. Toxic memory (should be filtered out)
            toxic_memory = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="GLOBAL",
                context_id="GLOBAL",
                actor_id=None,
                key="bad_policy",
                value="bad value",
                confidence_score=50,
                is_toxic=True
            )
            
            session.add_all([global_memory, actor1_memory, actor2_memory, toxic_memory])
            session.commit()
        
        print(f"✓ Created test memories (2 global, 2 actor-specific, 1 toxic)")
        
        # Test 1: Get all memories for actor1 (should see global + actor1-specific)
        memories = engine.get_memory(actor_id=actor1_id, role_id=beta_role_id)
        
        assert len(memories) == 2, f"Expected 2 memories, got {len(memories)}"
        keys = [m["key"] for m in memories]
        assert "global_invoice_policy" in keys
        assert "personal_invoice_limit" in keys
        assert "personal_vendor_preference" not in keys  # Actor2's memory
        assert "bad_policy" not in keys  # Toxic memory
        print(f"✓ Actor1 sees {len(memories)} memories (global + personal)")
        
        # Test 2: Search with query
        memories = engine.get_memory(actor_id=actor1_id, role_id=beta_role_id, query="invoice")
        
        assert len(memories) == 2, f"Expected 2 memories matching 'invoice', got {len(memories)}"
        keys = [m["key"] for m in memories]
        assert all("invoice" in key.lower() for key in keys)
        print(f"✓ Search for 'invoice' returned {len(memories)} results")
        
        # Test 3: Search with specific query
        memories = engine.get_memory(actor_id=actor1_id, role_id=beta_role_id, query="personal")
        
        assert len(memories) == 1, f"Expected 1 memory matching 'personal', got {len(memories)}"
        assert memories[0]["key"] == "personal_invoice_limit"
        print(f"✓ Search for 'personal' returned correct result")
        
        # Test 4: Actor2 sees different memories
        memories = engine.get_memory(actor_id=actor2_id, role_id=beta_role_id)
        
        assert len(memories) == 2, f"Expected 2 memories for actor2, got {len(memories)}"
        keys = [m["key"] for m in memories]
        assert "global_invoice_policy" in keys
        assert "personal_vendor_preference" in keys
        assert "personal_invoice_limit" not in keys  # Actor1's memory
        print(f"✓ Actor2 sees {len(memories)} memories (global + personal)")
        
        print("\n✅ get_memory test PASSED")
        return True
        
    finally:
        # Clean up
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)
        if os.path.exists(template_db):
            try:
                os.remove(template_db)
            except PermissionError:
                pass
        if os.path.exists(instance_db):
            try:
                os.remove(instance_db)
            except PermissionError:
                pass


def test_learning_doesnt_break_submission():
    """Test that learning failures don't prevent work submission."""
    print("\n=== Testing Learning Failure Isolation ===")
    
    # Create temporary databases
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        # Initialize and create workflow
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        template_id = create_simple_template_workflow(manager)
        engine = ChameleonEngine(manager)
        
        initial_context = {"test": "value"}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        # Create test actor
        actor_id = uuid.uuid4()
        
        with manager.get_instance_session() as session:
            actor = Local_Actors(
                actor_id=actor_id,
                instance_id=instance_id,
                identity_key="test_actor",
                name="Test Actor",
                type="HUMAN"
            )
            session.add(actor)
            session.commit()
            
            beta_role = session.query(Local_Roles).filter(
                Local_Roles.role_type == RoleType.BETA.value
            ).first()
            beta_role_id = beta_role.role_id
        
        # Checkout work
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None
        uow_id = result["uow_id"]
        
        # Submit work with invalid _learned_rule (should be ignored gracefully)
        result_attributes = {
            "status": "processed",
            "_learned_rule": "invalid_format_not_a_dict"  # Invalid format
        }
        
        # This should succeed despite invalid learning format
        success = engine.submit_work(
            uow_id=uow_id,
            actor_id=actor_id,
            result_attributes=result_attributes,
            reasoning="Testing with invalid learning format"
        )
        
        assert success, "Work submission should succeed despite invalid learning"
        print(f"✓ Work submission succeeded with invalid learning format")
        
        # Verify UOW status is COMPLETED
        with manager.get_instance_session() as session:
            uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == uow_id
            ).first()
            assert uow.status == UOWStatus.COMPLETED.value
            print(f"✓ UOW status is COMPLETED")
        
        print("\n✅ Learning failure isolation test PASSED")
        return True
        
    finally:
        # Clean up
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)
        if os.path.exists(template_db):
            try:
                os.remove(template_db)
            except PermissionError:
                pass
        if os.path.exists(instance_db):
            try:
                os.remove(instance_db)
            except PermissionError:
                pass


if __name__ == "__main__":
    print("=" * 80)
    print("LEARNING LOOP TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Harvest Experience (Create)", test_harvest_experience_creates_memory),
        ("Harvest Experience (Update)", test_harvest_experience_updates_memory),
        ("Get Memory", test_get_memory),
        ("Learning Failure Isolation", test_learning_doesnt_break_submission),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 80}")
            print(f"Running: {test_name}")
            print(f"{'=' * 80}")
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        sys.exit(1)
