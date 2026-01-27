"""
Tests for the Chameleon Engine Core Controller.

This test suite validates:
1. Workflow instantiation from templates
2. Work checkout with transactional locking
3. Work submission with atomic versioning
4. Failure handling and Ate Path routing
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
    Template_Guardians,
    # Tier 2 Models
    Instance_Context,
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
    GuardianType,
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
            name="Simple_Test_Flow",
            description="A simple test workflow",
            ai_context={"purpose": "Testing"},
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
        
        epsilon_role = Template_Roles(
            workflow_id=workflow_id,
            name="ErrorHandler",
            description="Handle errors",
            role_type=RoleType.EPSILON.value,
            ai_context={}
        )
        session.add(epsilon_role)
        session.flush()
        
        # Create interactions
        alpha_out = Template_Interactions(
            workflow_id=workflow_id,
            name="Alpha_Output",
            description="Output from Alpha",
            ai_context={}
        )
        session.add(alpha_out)
        session.flush()
        
        beta_in = Template_Interactions(
            workflow_id=workflow_id,
            name="Beta_Input",
            description="Input to Beta",
            ai_context={}
        )
        session.add(beta_in)
        session.flush()
        
        epsilon_in = Template_Interactions(
            workflow_id=workflow_id,
            name="Epsilon_Input",
            description="Input to Epsilon (Ate)",
            ai_context={}
        )
        session.add(epsilon_in)
        session.flush()
        
        # Create components (connections)
        # Alpha -> Alpha_Output (OUTBOUND)
        comp1 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_out.interaction_id,
            role_id=alpha_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Alpha_to_AlphaOut",
            description="Alpha outbound"
        )
        session.add(comp1)
        session.flush()
        
        # Beta_Input <- Alpha_Output (connect them via shared interaction)
        # Actually, let's use Alpha_Output as Beta's input for simplicity
        # Beta <- Alpha_Output (INBOUND)
        comp2 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_out.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="AlphaOut_to_Beta",
            description="Beta inbound from Alpha"
        )
        session.add(comp2)
        session.flush()
        
        # Epsilon <- Epsilon_Input (INBOUND)
        comp3 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=epsilon_in.interaction_id,
            role_id=epsilon_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="EpsilonIn_to_Epsilon",
            description="Epsilon inbound"
        )
        session.add(comp3)
        session.flush()
        
        # Add simple pass-through guardians
        guard1 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp1.component_id,
            name="Alpha_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={}
        )
        session.add(guard1)
        
        guard2 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp2.component_id,
            name="Beta_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={}
        )
        session.add(guard2)
        
        session.commit()
        
        return workflow_id


def test_instantiate_workflow():
    """Test workflow instantiation from template."""
    print("\n=== Testing Workflow Instantiation ===")
    
    # Create temporary databases
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        # Initialize database manager
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create a simple template
        template_id = create_simple_template_workflow(manager)
        print(f"✓ Created template workflow: {template_id}")
        
        # Initialize the engine
        engine = ChameleonEngine(manager)
        
        # Instantiate the workflow
        initial_context = {
            "customer_id": "CUST-001",
            "amount": 5000,
            "description": "Test transaction"
        }
        
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context,
            instance_name="Test Instance",
            instance_description="A test instance"
        )
        
        print(f"✓ Instantiated workflow with instance_id: {instance_id}")
        
        # Verify the instance was created
        with manager.get_instance_session() as session:
            instance = session.query(Instance_Context).filter(
                Instance_Context.instance_id == instance_id
            ).first()
            
            assert instance is not None, "Instance not found"
            assert instance.name == "Test Instance"
            print(f"✓ Instance context created: {instance.name}")
            
            # Verify local workflow was created
            local_workflow = session.query(Local_Workflows).filter(
                Local_Workflows.instance_id == instance_id
            ).first()
            
            assert local_workflow is not None, "Local workflow not found"
            assert local_workflow.is_master == True
            print(f"✓ Local workflow created: {local_workflow.name}")
            
            # Verify roles were cloned
            roles = session.query(Local_Roles).filter(
                Local_Roles.local_workflow_id == local_workflow.local_workflow_id
            ).all()
            
            assert len(roles) == 4, f"Expected 4 roles, found {len(roles)}"
            role_types = {role.role_type for role in roles}
            assert RoleType.ALPHA.value in role_types
            assert RoleType.BETA.value in role_types
            assert RoleType.OMEGA.value in role_types
            assert RoleType.EPSILON.value in role_types
            print(f"✓ {len(roles)} roles cloned successfully")
            
            # Verify Alpha UOW was created
            uows = session.query(UnitsOfWork).filter(
                UnitsOfWork.instance_id == instance_id
            ).all()
            
            assert len(uows) == 1, f"Expected 1 UOW, found {len(uows)}"
            alpha_uow = uows[0]
            assert alpha_uow.status == UOWStatus.PENDING.value
            assert alpha_uow.parent_id is None
            print(f"✓ Alpha UOW created with status: {alpha_uow.status}")
            
            # Verify initial context was stored
            attrs = session.query(UOW_Attributes).filter(
                UOW_Attributes.uow_id == alpha_uow.uow_id
            ).all()
            
            assert len(attrs) == 3, f"Expected 3 attributes, found {len(attrs)}"
            attr_keys = {attr.key for attr in attrs}
            assert "customer_id" in attr_keys
            assert "amount" in attr_keys
            assert "description" in attr_keys
            print(f"✓ Initial context stored: {attr_keys}")
        
        print("\n✅ Workflow instantiation test PASSED")
        return True
        
    finally:
        # Clean up - dispose engines first to release file locks on Windows
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)  # Brief pause to ensure file handles are released
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


def test_checkout_and_submit_work():
    """Test work checkout and submission."""
    print("\n=== Testing Work Checkout and Submission ===")
    
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
        
        initial_context = {"test_key": "test_value"}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        print(f"✓ Workflow instantiated: {instance_id}")
        
        # Create a test actor
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
        
        # Get the Beta role ID
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        print(f"✓ Beta role found: {beta_role_id}")
        
        # Checkout work
        result = engine.checkout_work(
            actor_id=actor_id,
            role_id=beta_role_id
        )
        
        assert result is not None, "No work available to checkout"
        uow_id = result["uow_id"]
        attributes = result["attributes"]
        context = result["context"]
        print(f"✓ Work checked out: UOW {uow_id}")
        print(f"  Attributes: {attributes}")
        print(f"  Context: {context}")
        
        # Verify UOW is now in ACTIVE status
        with manager.get_instance_session() as session:
            uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == uow_id
            ).first()
            assert uow.status == UOWStatus.ACTIVE.value
            print(f"✓ UOW status is ACTIVE")
        
        # Submit work with modified attributes
        result_attributes = {
            "test_key": "modified_value",
            "new_key": "new_value"
        }
        
        success = engine.submit_work(
            uow_id=uow_id,
            actor_id=actor_id,
            result_attributes=result_attributes,
            reasoning="Work completed successfully"
        )
        
        assert success, "Work submission failed"
        print(f"✓ Work submitted successfully")
        
        # Verify UOW is now COMPLETED
        with manager.get_instance_session() as session:
            uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == uow_id
            ).first()
            assert uow.status == UOWStatus.COMPLETED.value
            print(f"✓ UOW status is COMPLETED")
            
            # Verify attribute versioning
            attrs = session.query(UOW_Attributes).filter(
                UOW_Attributes.uow_id == uow_id
            ).order_by(UOW_Attributes.key, UOW_Attributes.version).all()
            
            # test_key should have 2 versions
            test_key_attrs = [a for a in attrs if a.key == "test_key"]
            assert len(test_key_attrs) == 2, f"Expected 2 versions of test_key, found {len(test_key_attrs)}"
            assert test_key_attrs[0].version == 1
            assert test_key_attrs[1].version == 2
            print(f"✓ Attribute versioning working: test_key has {len(test_key_attrs)} versions")
            
            # new_key should have 1 version
            new_key_attrs = [a for a in attrs if a.key == "new_key"]
            assert len(new_key_attrs) == 1
            print(f"✓ New attribute added: new_key")
        
        print("\n✅ Work checkout and submission test PASSED")
        return True
        
    finally:
        # Clean up - dispose engines first to release file locks on Windows
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)  # Brief pause to ensure file handles are released
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


def test_report_failure():
    """Test failure reporting and Ate Path routing."""
    print("\n=== Testing Failure Reporting ===")
    
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
        
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"test": "data"}
        )
        
        # Create actor and checkout work
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
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None
        uow_id = result["uow_id"]
        print(f"✓ Work checked out: {uow_id}")
        
        # Report failure
        success = engine.report_failure(
            uow_id=uow_id,
            actor_id=actor_id,
            error_code="VALIDATION_ERROR",
            details="Data did not pass validation"
        )
        
        assert success, "Failure reporting failed"
        print(f"✓ Failure reported successfully")
        
        # Verify UOW is now FAILED
        with manager.get_instance_session() as session:
            uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == uow_id
            ).first()
            assert uow.status == UOWStatus.FAILED.value
            print(f"✓ UOW status is FAILED")
            
            # Verify error was logged
            error_attrs = session.query(UOW_Attributes).filter(
                and_(
                    UOW_Attributes.uow_id == uow_id,
                    UOW_Attributes.key == "_error"
                )
            ).all()
            
            assert len(error_attrs) >= 1, "Error not logged"
            error_data = error_attrs[0].value
            assert error_data["error_code"] == "VALIDATION_ERROR"
            print(f"✓ Error logged in attributes: {error_data['error_code']}")
            
            # Verify UOW was moved to Ate interaction
            epsilon_role = session.query(Local_Roles).filter(
                Local_Roles.role_type == RoleType.EPSILON.value
            ).first()
            
            if epsilon_role:
                # Check if UOW is in an interaction that feeds Epsilon
                epsilon_component = session.query(Local_Components).filter(
                    and_(
                        Local_Components.role_id == epsilon_role.role_id,
                        Local_Components.direction == ComponentDirection.INBOUND.value
                    )
                ).first()
                
                if epsilon_component:
                    assert uow.current_interaction_id == epsilon_component.interaction_id
                    print(f"✓ UOW routed to Ate interaction (Epsilon)")
        
        print("\n✅ Failure reporting test PASSED")
        return True
        
    finally:
        # Clean up - dispose engines first to release file locks on Windows
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)  # Brief pause to ensure file handles are released
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


def test_memory_context():
    """Test memory context injection during work checkout."""
    print("\n=== Testing Memory Context Injection ===")
    
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
        
        initial_context = {"test_key": "test_value"}
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context=initial_context
        )
        
        print(f"✓ Workflow instantiated: {instance_id}")
        
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
            session.add(actor1)
            session.add(actor2)
            session.commit()
        
        print(f"✓ Test actors created: {actor1_id}, {actor2_id}")
        
        # Get the Beta role ID
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        print(f"✓ Beta role found: {beta_role_id}")
        
        # Add memory attributes for testing
        with manager.get_instance_session() as session:
            # Global Blueprint (shared across all actors)
            global_memory1 = Local_Role_Attributes(
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="GLOBAL",
                context_id="GLOBAL",
                actor_id=None,
                key="company_policy",
                value={"rule": "Always check tax codes"},
                confidence_score=80,
                is_toxic=False
            )
            
            global_memory2 = Local_Role_Attributes(
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="GLOBAL",
                context_id="GLOBAL",
                actor_id=None,
                key="approval_threshold",
                value={"amount": 10000},
                confidence_score=90,
                is_toxic=False
            )
            
            # Toxic memory (should be filtered out)
            toxic_memory = Local_Role_Attributes(
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="GLOBAL",
                context_id="GLOBAL",
                actor_id=None,
                key="bad_pattern",
                value={"error": "This caused failures"},
                confidence_score=10,
                is_toxic=True
            )
            
            # Personal Playbook for Actor 1 (overrides global)
            personal_memory1 = Local_Role_Attributes(
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="ACTOR",
                context_id=str(actor1_id),
                actor_id=actor1_id,
                key="approval_threshold",  # Overrides global
                value={"amount": 5000},  # Lower threshold for this actor
                confidence_score=95,
                is_toxic=False
            )
            
            personal_memory2 = Local_Role_Attributes(
                instance_id=instance_id,
                role_id=beta_role_id,
                context_type="ACTOR",
                context_id=str(actor1_id),
                actor_id=actor1_id,
                key="personal_preference",
                value={"vendor": "Always use Vendor X"},
                confidence_score=85,
                is_toxic=False
            )
            
            session.add_all([
                global_memory1, global_memory2, toxic_memory,
                personal_memory1, personal_memory2
            ])
            session.commit()
        
        print("✓ Memory attributes created (2 global, 1 toxic, 2 personal)")
        
        # Test 1: Actor 1 checkout - should get global + personal (with override)
        result1 = engine.checkout_work(
            actor_id=actor1_id,
            role_id=beta_role_id
        )
        
        assert result1 is not None, "No work available to checkout"
        context1 = result1["context"]
        print(f"✓ Actor 1 checked out work with context: {context1}")
        
        # Verify context content for Actor 1
        assert "company_policy" in context1, "Global memory not in context"
        assert "approval_threshold" in context1, "Approval threshold not in context"
        assert "personal_preference" in context1, "Personal memory not in context"
        assert "bad_pattern" not in context1, "Toxic memory should be filtered out"
        
        # Verify Actor 1's personal threshold overrides global
        assert context1["approval_threshold"]["amount"] == 5000, \
            "Actor-specific memory should override global (expected 5000)"
        print("✓ Context merge verified: Actor-specific overrides Global")
        
        # Verify toxic filtering
        print("✓ Toxic memory filtered out correctly")
        
        # Verify last_accessed_at was updated
        with manager.get_instance_session() as session:
            memories = session.query(Local_Role_Attributes).filter(
                and_(
                    Local_Role_Attributes.role_id == beta_role_id,
                    Local_Role_Attributes.is_toxic == False
                )
            ).all()
            
            for memory in memories:
                assert memory.last_accessed_at is not None, \
                    f"last_accessed_at not updated for memory {memory.key}"
            
            print("✓ last_accessed_at timestamps updated")
        
        # Submit the work to free up the UOW
        engine.submit_work(
            uow_id=result1["uow_id"],
            actor_id=actor1_id,
            result_attributes={"completed": True},
            reasoning="Test completion"
        )
        
        # Test 2: Actor 2 checkout - should only get global (no personal memory)
        # Need to create another UOW for testing
        with manager.get_instance_session() as session:
            # Re-query beta_role within the session
            beta_role = session.query(Local_Roles).filter(
                Local_Roles.role_id == beta_role_id
            ).first()
            
            # Find an interaction to place a new UOW
            beta_interaction = session.query(Local_Interactions).join(
                Local_Components,
                and_(
                    Local_Components.interaction_id == Local_Interactions.interaction_id,
                    Local_Components.role_id == beta_role_id,
                    Local_Components.direction == ComponentDirection.INBOUND.value
                )
            ).first()
            
            if beta_interaction:
                new_uow = UnitsOfWork(
                    instance_id=instance_id,
                    local_workflow_id=beta_role.local_workflow_id,
                    current_interaction_id=beta_interaction.interaction_id,
                    status=UOWStatus.PENDING.value
                )
                session.add(new_uow)
                session.flush()
                
                # Add initial attributes
                attr = UOW_Attributes(
                    uow_id=new_uow.uow_id,
                    instance_id=instance_id,
                    key="test_key",
                    value="test_value",
                    version=1,
                    actor_id=actor1_id,
                    reasoning="Initial data"
                )
                session.add(attr)
                session.commit()
                
                print("✓ Created second UOW for Actor 2 testing")
                
                # Actor 2 checkout
                result2 = engine.checkout_work(
                    actor_id=actor2_id,
                    role_id=beta_role_id
                )
                
                assert result2 is not None, "No work available for Actor 2"
                context2 = result2["context"]
                print(f"✓ Actor 2 checked out work with context: {context2}")
                
                # Verify context content for Actor 2
                assert "company_policy" in context2, "Global memory not in context"
                assert "approval_threshold" in context2, "Approval threshold not in context"
                assert "personal_preference" not in context2, \
                    "Actor 1's personal memory should not appear for Actor 2"
                
                # Verify Actor 2 gets the global threshold (not Actor 1's override)
                assert context2["approval_threshold"]["amount"] == 10000, \
                    "Actor 2 should get global threshold (expected 10000)"
                print("✓ Context isolation verified: Actor 2 only sees global memory")
        
        print("\n✅ Memory context test PASSED")
        return True
        
    finally:
        # Clean up - dispose engines first to release file locks on Windows
        try:
            manager.close()
        except Exception:
            pass
        import time
        time.sleep(0.1)  # Brief pause to ensure file handles are released
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
    print("=" * 70)
    print("CHAMELEON ENGINE - CORE CONTROLLER TESTS")
    print("=" * 70)
    
    try:
        # Run tests
        test_instantiate_workflow()
        test_checkout_and_submit_work()
        test_report_failure()
        test_memory_context()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
