"""
Vertical Slice End-to-End Test for the Chameleon Workflow Engine.

This test implements the complete lifecycle validation as specified in:
- Testing Strategy & QA Specs (Section 3: The Vertical Slice Protocol)
- UOW Lifecycle Specs (Valid state transitions)

Test Scenario: Complete UOW Lifecycle from Instantiation to Completion
1. Setup: Load complete_workflow_example.yaml into the DB
2. Instantiate: Call engine.instantiate_workflow() and verify Alpha UOW exists
3. Beta Checkout: Simulate a processor calling checkout_work()
4. Beta Submit: Simulate the processor calling submit_work() with results
5. Verify: Ensure proper state transitions and atomic versioning
"""

import sys
from pathlib import Path
import uuid
from typing import Dict, Any

import pytest

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
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
    UnitsOfWork,
    UOW_Attributes,
    # Enums
    RoleType,
    ComponentDirection,
    GuardianType,
    UOWStatus,
)
from chameleon_workflow_engine.engine import ChameleonEngine


@pytest.fixture
def db_manager():
    """
    Create an in-memory SQLite database for testing.
    
    This fixture provides strict transactional isolation - each test
    gets a fresh database that is disposed after the test completes.
    
    Per Testing Strategy Section 1.1: "In-memory SQLite (sqlite:///:memory:) 
    for fast, isolated execution of integration tests."
    """
    # Create in-memory databases for both template and instance tiers
    manager = DatabaseManager(
        template_url="sqlite:///:memory:",
        instance_url="sqlite:///:memory:",
        echo=False  # Set to True for SQL debugging
    )
    
    # Create schemas
    manager.create_template_schema()
    manager.create_instance_schema()
    
    yield manager
    
    # Cleanup: close all connections
    manager.close()


def create_simple_vertical_slice_template(db_manager: DatabaseManager) -> uuid.UUID:
    """
    Create a simple but complete workflow template for vertical slice testing.
    
    This creates a workflow with:
    - Alpha role (initiator)
    - Beta role (processor) 
    - Omega role (finalizer)
    - Epsilon role (error handler)
    - Tau role (timeout manager)
    - Complete interaction topology
    
    Returns:
        uuid.UUID: The workflow_id of the created template
    """
    with db_manager.get_template_session() as session:
        # Create workflow
        workflow = Template_Workflows(
            name="Vertical_Slice_Test_Workflow",
            description="A simple workflow for vertical slice E2E testing",
            ai_context={"purpose": "E2E Testing", "test_type": "vertical_slice"},
            version=1,
            schema_json={"topology": "simple linear flow"}
        )
        session.add(workflow)
        session.flush()
        workflow_id = workflow.workflow_id
        
        # Create roles - All 5 required role types
        alpha_role = Template_Roles(
            workflow_id=workflow_id,
            name="Initiator",
            description="Start the workflow",
            role_type=RoleType.ALPHA.value,
            ai_context={"persona": "Workflow initiator"}
        )
        session.add(alpha_role)
        session.flush()
        
        beta_role = Template_Roles(
            workflow_id=workflow_id,
            name="Processor",
            description="Process the work",
            role_type=RoleType.BETA.value,
            strategy="HOMOGENEOUS",  # Required for Beta roles
            ai_context={"persona": "Work processor"}
        )
        session.add(beta_role)
        session.flush()
        
        omega_role = Template_Roles(
            workflow_id=workflow_id,
            name="Finalizer",
            description="Finalize the workflow",
            role_type=RoleType.OMEGA.value,
            ai_context={"persona": "Workflow finalizer"}
        )
        session.add(omega_role)
        session.flush()
        
        epsilon_role = Template_Roles(
            workflow_id=workflow_id,
            name="ErrorHandler",
            description="Handle errors",
            role_type=RoleType.EPSILON.value,
            ai_context={"persona": "Error handler"}
        )
        session.add(epsilon_role)
        session.flush()
        
        tau_role = Template_Roles(
            workflow_id=workflow_id,
            name="TimeoutManager",
            description="Manage timeouts",
            role_type=RoleType.TAU.value,
            ai_context={"persona": "Timeout manager"}
        )
        session.add(tau_role)
        session.flush()
        
        # Create interactions (queues)
        alpha_to_beta = Template_Interactions(
            workflow_id=workflow_id,
            name="Alpha_to_Beta_Queue",
            description="Queue from Alpha to Beta",
            ai_context={"purpose": "Alpha output / Beta input"}
        )
        session.add(alpha_to_beta)
        session.flush()
        
        beta_to_omega = Template_Interactions(
            workflow_id=workflow_id,
            name="Beta_to_Omega_Queue",
            description="Queue from Beta to Omega",
            ai_context={"purpose": "Beta output / Omega input"}
        )
        session.add(beta_to_omega)
        session.flush()
        
        error_queue = Template_Interactions(
            workflow_id=workflow_id,
            name="Error_Queue",
            description="Queue for error handling",
            ai_context={"purpose": "Error routing"}
        )
        session.add(error_queue)
        session.flush()
        
        timeout_queue = Template_Interactions(
            workflow_id=workflow_id,
            name="Timeout_Queue",
            description="Queue for timeout handling",
            ai_context={"purpose": "Timeout routing"}
        )
        session.add(timeout_queue)
        session.flush()
        
        # Create components (connections) - Main happy path
        # Alpha -> Alpha_to_Beta_Queue (OUTBOUND)
        comp1 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_to_beta.interaction_id,
            role_id=alpha_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Alpha_Output",
            description="Alpha produces work"
        )
        session.add(comp1)
        session.flush()
        
        # Beta <- Alpha_to_Beta_Queue (INBOUND)
        comp2 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_to_beta.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Beta_Input",
            description="Beta consumes work"
        )
        session.add(comp2)
        session.flush()
        
        # Beta -> Beta_to_Omega_Queue (OUTBOUND)
        comp3 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=beta_to_omega.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_Output",
            description="Beta produces results"
        )
        session.add(comp3)
        session.flush()
        
        # Omega <- Beta_to_Omega_Queue (INBOUND)
        comp4 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=beta_to_omega.interaction_id,
            role_id=omega_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Omega_Input",
            description="Omega consumes results"
        )
        session.add(comp4)
        session.flush()
        
        # Error path: Beta -> Error_Queue (OUTBOUND)
        comp5 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=error_queue.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_Error_Output",
            description="Beta routes errors"
        )
        session.add(comp5)
        session.flush()
        
        # Epsilon <- Error_Queue (INBOUND)
        comp6 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=error_queue.interaction_id,
            role_id=epsilon_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Epsilon_Input",
            description="Epsilon handles errors"
        )
        session.add(comp6)
        session.flush()
        
        # Timeout path: Beta -> Timeout_Queue (OUTBOUND)
        comp7 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=timeout_queue.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_Timeout_Output",
            description="Beta routes timeouts"
        )
        session.add(comp7)
        session.flush()
        
        # Tau <- Timeout_Queue (INBOUND)
        comp8 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=timeout_queue.interaction_id,
            role_id=tau_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Tau_Input",
            description="Tau handles timeouts"
        )
        session.add(comp8)
        session.flush()
        
        # Add simple pass-through guardians for the main path
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
            name="Beta_Input_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={}
        )
        session.add(guard2)
        
        guard3 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp3.component_id,
            name="Beta_Output_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={}
        )
        session.add(guard3)
        
        guard4 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp4.component_id,
            name="Omega_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={}
        )
        session.add(guard4)
        
        session.commit()
        
        return workflow_id


@pytest.fixture
def loaded_workflow_template(db_manager):
    """
    Create and load a simple workflow template into the database.
    
    This fixture creates a minimal but complete workflow template
    that satisfies all Constitutional requirements for E2E testing.
    
    Per Testing Strategy Section 3: The template should support
    a complete vertical slice from Alpha through Beta to Omega.
    
    Returns:
        uuid.UUID: The workflow_id of the loaded template
    """
    return create_simple_vertical_slice_template(db_manager)


def test_vertical_slice_happy_path(db_manager, loaded_workflow_template):
    """
    Test the complete vertical slice of UOW lifecycle: Instantiation → Beta Checkout → Submit → Completed.
    
    This is the primary milestone test as defined in Testing Strategy Section 3:
    "The Vertical Slice Protocol (The First Milestone)".
    
    Test Steps:
    1. Instantiation: Initialize the ChameleonEngine and call instantiate_workflow()
    2. Verification 1 (Alpha): Assert that an "Alpha UOW" exists with status PENDING
    3. Checkout (Beta): Simulate a "Processor" actor calling checkout_work()
    4. Submit (Beta): Simulate the "Processor" actor calling submit_work()
    5. Final Verification: Assert proper state transitions and atomic versioning
    """
    # Step 1: Instantiate the workflow
    # Per Testing Strategy Section 3 Step 2: "Instantiate: Call engine.instantiate_workflow()"
    engine = ChameleonEngine(db_manager)
    
    initial_context = {
        "invoice_number": "INV-2024-001",
        "invoice_total": 5000.00,
        "vendor_name": "Acme Corp",
        "status": "pending_validation"
    }
    
    instance_id = engine.instantiate_workflow(
        template_id=loaded_workflow_template,
        initial_context=initial_context,
        instance_name="Test Invoice Workflow Instance",
        instance_description="E2E test instance for vertical slice validation"
    )
    
    assert instance_id is not None, "Workflow instantiation failed"
    print(f"\n✓ Step 1: Workflow instantiated with instance_id: {instance_id}")
    
    # Step 2: Verification 1 - Assert Alpha UOW exists with PENDING status
    # Per Testing Strategy Section 3 Step 2: "Verify Alpha UOW exists"
    # Per UOW Lifecycle Specs Section 2.2: Alpha UOW starts in INITIALIZED/PENDING state
    alpha_uow_id = None
    with db_manager.get_instance_session() as session:
        # Find the Alpha UOW
        uows = session.query(UnitsOfWork).filter(
            UnitsOfWork.instance_id == instance_id
        ).all()
        
        assert len(uows) == 1, f"Expected 1 Alpha UOW, found {len(uows)}"
        alpha_uow = uows[0]
        alpha_uow_id = alpha_uow.uow_id  # Store the ID, not the object
        
        # Verify status (using PENDING as equivalent to INITIALIZED per engine.py line 282)
        assert alpha_uow.status == UOWStatus.PENDING.value, \
            f"Alpha UOW status should be PENDING, found {alpha_uow.status}"
        assert alpha_uow.parent_id is None, "Alpha UOW should have no parent"
        
        print(f"✓ Step 2 (Verification 1): Alpha UOW exists with status PENDING: {alpha_uow.uow_id}")
        
        # Verify initial context was stored
        attrs = session.query(UOW_Attributes).filter(
            UOW_Attributes.uow_id == alpha_uow.uow_id
        ).all()
        
        assert len(attrs) >= 4, f"Expected at least 4 initial attributes, found {len(attrs)}"
        attr_dict = {attr.key: attr.value for attr in attrs}
        assert "invoice_number" in attr_dict
        assert attr_dict["invoice_number"] == "INV-2024-001"
        
        print(f"✓ Step 2: Initial context verified: {list(attr_dict.keys())}")
    
    # Step 3: Beta Checkout - Actor calls checkout_work()
    # Per Testing Strategy Section 3 Step 4: "Actor Processor_01 calls checkout_work()"
    # Per UOW Lifecycle Specs Section 2.2: Valid Transition PENDING → IN_PROGRESS
    
    # First, we need to find a Beta role ID to checkout from
    with db_manager.get_instance_session() as session:
        # Find the Beta role (Invoice_Validator from the YAML)
        local_workflow = session.query(Local_Workflows).filter(
            Local_Workflows.instance_id == instance_id
        ).first()
        
        beta_role = session.query(Local_Roles).filter(
            Local_Roles.local_workflow_id == local_workflow.local_workflow_id,
            Local_Roles.role_type == RoleType.BETA.value
        ).first()
        
        assert beta_role is not None, "No Beta role found in instantiated workflow"
        beta_role_id = beta_role.role_id
        
        print(f"✓ Step 3: Found Beta role: {beta_role.name} ({beta_role_id})")
    
    # Create a mock actor ID
    processor_actor_id = uuid.uuid4()
    
    # Attempt checkout
    checkout_result = engine.checkout_work(
        actor_id=processor_actor_id,
        role_id=beta_role_id
    )
    
    assert checkout_result is not None, "checkout_work() returned None - no work available"
    
    uow_id, checked_out_attributes = checkout_result
    assert uow_id == alpha_uow_id, "Checked out UOW should be the Alpha UOW"
    
    print(f"✓ Step 3 (Beta Checkout): UOW checked out by actor {processor_actor_id}")
    print(f"  - UOW ID: {uow_id}")
    print(f"  - Attributes: {list(checked_out_attributes.keys())}")
    
    # Verify status is now IN_PROGRESS (ACTIVE in the current enum)
    with db_manager.get_instance_session() as session:
        uow = session.query(UnitsOfWork).filter(
            UnitsOfWork.uow_id == uow_id
        ).first()
        
        assert uow.status == UOWStatus.ACTIVE.value, \
            f"After checkout, UOW status should be ACTIVE (IN_PROGRESS), found {uow.status}"
        assert uow.last_heartbeat is not None, \
            "After checkout, last_heartbeat should be set (lock mechanism)"
        
        print(f"✓ Step 3 (Verification): UOW status is ACTIVE (IN_PROGRESS)")
        print(f"  - Lock timestamp (last_heartbeat): {uow.last_heartbeat}")
    
    # Step 4: Beta Submit - Actor calls submit_work() with results
    # Per Testing Strategy Section 3 Step 5: "Actor Processor_01 calls submit_work()"
    # Per UOW Lifecycle Specs Section 2.2: Valid Transition IN_PROGRESS → COMPLETED
    # Per UOW Lifecycle Specs Section 3: Atomic Versioning (The Data Physics)
    
    result_attributes = {
        "invoice_number": "INV-2024-001",  # Unchanged
        "invoice_total": 5000.00,  # Unchanged
        "vendor_name": "Acme Corp",  # Unchanged
        "status": "validated",  # Updated
        "validation_timestamp": "2024-01-27T06:00:00Z",  # New attribute
        "validator_notes": "All fields verified and correct"  # New attribute
    }
    
    submit_success = engine.submit_work(
        uow_id=uow_id,
        actor_id=processor_actor_id,
        result_attributes=result_attributes,
        reasoning="Invoice validation completed successfully"
    )
    
    assert submit_success is True, "submit_work() should return True on success"
    
    print(f"✓ Step 4 (Beta Submit): Work submitted successfully")
    
    # Step 5: Final Verification - Check state transitions and atomic versioning
    # Per Testing Strategy Section 3 Step 5: "Assert: Status is COMPLETED. History log contains the update."
    # Per Article XVII: Historical Lineage and Attribution
    with db_manager.get_instance_session() as session:
        # Verify UOW status is COMPLETED
        uow = session.query(UnitsOfWork).filter(
            UnitsOfWork.uow_id == uow_id
        ).first()
        
        assert uow.status == UOWStatus.COMPLETED.value, \
            f"After submit, UOW status should be COMPLETED, found {uow.status}"
        assert uow.last_heartbeat is None, \
            "After submit, last_heartbeat should be cleared (lock released)"
        
        print(f"✓ Step 5 (Verification): UOW status is COMPLETED")
        
        # Verify atomic versioning: UOW_Attributes should contain history
        # Per UOW Lifecycle Specs Section 3.2: "Atomic Commit: Write current_attributes 
        # AND history_record in the same transaction"
        all_attrs = session.query(UOW_Attributes).filter(
            UOW_Attributes.uow_id == uow_id
        ).order_by(UOW_Attributes.key, UOW_Attributes.version).all()
        
        # Group by key to see versioning
        attr_versions = {}
        for attr in all_attrs:
            if attr.key not in attr_versions:
                attr_versions[attr.key] = []
            attr_versions[attr.key].append({
                'version': attr.version,
                'value': attr.value,
                'actor_id': attr.actor_id,
                'reasoning': attr.reasoning
            })
        
        print(f"✓ Step 5 (Atomic Versioning): Attribute history records:")
        
        # Verify that changed attributes have multiple versions
        # 'status' should have version 1 (initial) and version 2 (updated)
        assert 'status' in attr_versions, "Status attribute should exist"
        status_versions = attr_versions['status']
        assert len(status_versions) >= 2, \
            f"Status should have at least 2 versions (initial + update), found {len(status_versions)}"
        
        # Verify initial version
        initial_status = next((v for v in status_versions if v['version'] == 1), None)
        assert initial_status is not None, "Should have version 1 of status"
        assert initial_status['value'] == 'pending_validation', \
            f"Initial status should be 'pending_validation', found {initial_status['value']}"
        
        # Verify updated version
        updated_status = next((v for v in status_versions if v['version'] == 2), None)
        assert updated_status is not None, "Should have version 2 of status"
        assert updated_status['value'] == 'validated', \
            f"Updated status should be 'validated', found {updated_status['value']}"
        assert updated_status['actor_id'] == processor_actor_id, \
            "Updated status should be attributed to the processor actor"
        
        print(f"  - 'status': {len(status_versions)} versions")
        print(f"    - v1: '{status_versions[0]['value']}' (initial)")
        print(f"    - v2: '{status_versions[1]['value']}' (updated by {processor_actor_id})")
        
        # Verify new attributes were added
        assert 'validation_timestamp' in attr_versions, "New attribute 'validation_timestamp' should exist"
        assert 'validator_notes' in attr_versions, "New attribute 'validator_notes' should exist"
        
        print(f"  - 'validation_timestamp': {len(attr_versions['validation_timestamp'])} version(s)")
        print(f"  - 'validator_notes': {len(attr_versions['validator_notes'])} version(s)")
        
        # Verify reasoning is stored
        updated_status_reasoning = updated_status.get('reasoning', '')
        assert 'Invoice validation completed successfully' in updated_status_reasoning or \
               'Work submitted by actor' in updated_status_reasoning, \
            "Reasoning should be stored with attribute updates"
        
        print(f"✓ Step 5 (Attribution): Actor attribution and reasoning verified")
        
    print("\n" + "="*70)
    print("✅ VERTICAL SLICE TEST PASSED")
    print("="*70)
    print("\nValidated:")
    print("  1. Workflow instantiation with Alpha UOW in PENDING state")
    print("  2. Beta checkout with transition to IN_PROGRESS (ACTIVE)")
    print("  3. Beta submit with transition to COMPLETED")
    print("  4. Atomic versioning: attribute history maintained")
    print("  5. Actor attribution: all changes tracked to responsible actor")
    print("  6. Constitutional compliance: Article XVII (Historical Lineage)")
    print("="*70)
