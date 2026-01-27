"""
Tests for Guard Logic (Criteria Filtering) in the Chameleon Engine.

This test suite validates:
1. PASS_THRU guard behavior
2. CRITERIA_GATE with different operators (GT, LT, EQ, IN)
3. TTL_CHECK with timestamp validation
4. COMPOSITE with AND logic
5. COMPOSITE with OR logic
6. Guard rejection routing to Epsilon
"""

import sys
from pathlib import Path
import tempfile
import os
import uuid
from datetime import datetime, timezone, timedelta

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
    Local_Guardians,
    Local_Actors,
    UnitsOfWork,
    UOW_Attributes,
    # Enums
    RoleType,
    ComponentDirection,
    GuardianType,
    UOWStatus,
)
from sqlalchemy import and_
from chameleon_workflow_engine.engine import ChameleonEngine


def create_template_with_guard(
    manager: DatabaseManager, 
    guard_type: str, 
    guard_config: dict
) -> uuid.UUID:
    """
    Create a template workflow with a specific guard configuration.
    Returns the template workflow_id.
    """
    with manager.get_template_session() as session:
        # Create workflow
        workflow = Template_Workflows(
            name=f"Guard_Test_{guard_type}",
            description=f"Testing {guard_type} guard",
            ai_context={},
            version=1,
            schema_json={}
        )
        session.add(workflow)
        session.flush()
        workflow_id = workflow.workflow_id
        
        # Create roles: Alpha -> Beta -> Omega + Epsilon
        alpha_role = Template_Roles(
            workflow_id=workflow_id,
            name="Initiator",
            role_type=RoleType.ALPHA.value,
            ai_context={}
        )
        session.add(alpha_role)
        session.flush()
        
        beta_role = Template_Roles(
            workflow_id=workflow_id,
            name="Processor",
            role_type=RoleType.BETA.value,
            ai_context={}
        )
        session.add(beta_role)
        session.flush()
        
        epsilon_role = Template_Roles(
            workflow_id=workflow_id,
            name="ErrorHandler",
            role_type=RoleType.EPSILON.value,
            ai_context={}
        )
        session.add(epsilon_role)
        session.flush()
        
        # Create interactions
        alpha_out = Template_Interactions(
            workflow_id=workflow_id,
            name="Alpha_Output",
            ai_context={}
        )
        session.add(alpha_out)
        session.flush()
        
        epsilon_in = Template_Interactions(
            workflow_id=workflow_id,
            name="Epsilon_Input",
            ai_context={}
        )
        session.add(epsilon_in)
        session.flush()
        
        # Create components
        # Alpha -> Alpha_Output (OUTBOUND)
        comp_alpha_out = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_out.interaction_id,
            role_id=alpha_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Alpha_to_AlphaOut"
        )
        session.add(comp_alpha_out)
        session.flush()
        
        # Beta <- Alpha_Output (INBOUND) - with guard
        comp_beta_in = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_out.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="AlphaOut_to_Beta"
        )
        session.add(comp_beta_in)
        session.flush()
        
        # Epsilon <- Epsilon_Input (INBOUND)
        comp_epsilon_in = Template_Components(
            workflow_id=workflow_id,
            interaction_id=epsilon_in.interaction_id,
            role_id=epsilon_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="EpsilonIn_to_Epsilon"
        )
        session.add(comp_epsilon_in)
        session.flush()
        
        # Add the guard to Beta's inbound component
        guard = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp_beta_in.component_id,
            name=f"{guard_type}_Guard",
            description=f"Guard testing {guard_type}",
            type=guard_type,
            config=guard_config
        )
        session.add(guard)
        
        session.commit()
        
        return workflow_id


def test_pass_thru_guard():
    """Test PASS_THRU guard always allows passage."""
    print("\n=== Testing PASS_THRU Guard ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with PASS_THRU guard
        template_id = create_template_with_guard(
            manager, 
            GuardianType.PASS_THRU.value, 
            {}
        )
        
        engine = ChameleonEngine(manager)
        
        # Instantiate workflow
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"test": "data"}
        )
        
        # Create actor and get beta role
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
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        # Checkout work - should succeed because PASS_THRU always passes
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "PASS_THRU guard should allow work"
        print("✓ PASS_THRU guard allowed work checkout")
        
    finally:
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


def test_criteria_gate_gt():
    """Test CRITERIA_GATE with GT (greater than) operator."""
    print("\n=== Testing CRITERIA_GATE with GT operator ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with CRITERIA_GATE (amount > 1000)
        template_id = create_template_with_guard(
            manager,
            GuardianType.CRITERIA_GATE.value,
            {
                "field": "amount",
                "operator": "GT",
                "threshold": 1000
            }
        )
        
        engine = ChameleonEngine(manager)
        
        # Test 1: Amount > 1000 (should pass)
        instance_id_pass = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 2000}
        )
        
        actor_id = uuid.uuid4()
        with manager.get_instance_session() as session:
            actor = Local_Actors(
                actor_id=actor_id,
                instance_id=instance_id_pass,
                identity_key="test_actor",
                name="Test Actor",
                type="HUMAN"
            )
            session.add(actor)
            session.commit()
            
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_pass
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "Guard should pass when amount > 1000"
        print("✓ Guard passed for amount = 2000 (> 1000)")
        
        # Test 2: Amount <= 1000 (should fail and route to Epsilon)
        instance_id_fail = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 500}
        )
        
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_fail
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is None, "Guard should reject when amount <= 1000"
        print("✓ Guard rejected for amount = 500 (<= 1000)")
        
        # Verify UOW was routed to Epsilon
        with manager.get_instance_session() as session:
            uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.instance_id == instance_id_fail
            ).first()
            
            assert uow.status == UOWStatus.FAILED.value, "UOW should be marked as FAILED"
            print("✓ Rejected UOW marked as FAILED")
            
            # Check if routed to Epsilon interaction
            epsilon_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == uow.local_workflow_id,
                    Local_Roles.role_type == RoleType.EPSILON.value
                )
            ).first()
            
            if epsilon_role:
                epsilon_component = session.query(Local_Components).filter(
                    and_(
                        Local_Components.role_id == epsilon_role.role_id,
                        Local_Components.direction == ComponentDirection.INBOUND.value
                    )
                ).first()
                
                if epsilon_component:
                    assert uow.current_interaction_id == epsilon_component.interaction_id
                    print("✓ Rejected UOW routed to Epsilon interaction")
        
    finally:
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


def test_criteria_gate_in():
    """Test CRITERIA_GATE with IN operator."""
    print("\n=== Testing CRITERIA_GATE with IN operator ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with CRITERIA_GATE (region IN ["US", "EU", "UK"])
        template_id = create_template_with_guard(
            manager,
            GuardianType.CRITERIA_GATE.value,
            {
                "field": "region",
                "operator": "IN",
                "threshold": ["US", "EU", "UK"]
            }
        )
        
        engine = ChameleonEngine(manager)
        
        # Test 1: Valid region (should pass)
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"region": "US"}
        )
        
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
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "Guard should pass for region in list"
        print("✓ Guard passed for region = 'US' (in allowed list)")
        
    finally:
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


def test_ttl_check():
    """Test TTL_CHECK guard with timestamp validation."""
    print("\n=== Testing TTL_CHECK Guard ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with TTL_CHECK (max_age = 300 seconds)
        template_id = create_template_with_guard(
            manager,
            GuardianType.TTL_CHECK.value,
            {
                "reference_field": "created_at",
                "max_age_seconds": 300  # 5 minutes
            }
        )
        
        engine = ChameleonEngine(manager)
        
        # Test 1: Recent timestamp (should pass)
        now = datetime.now(timezone.utc)
        instance_id_pass = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"created_at": now.isoformat()}
        )
        
        actor_id = uuid.uuid4()
        with manager.get_instance_session() as session:
            actor = Local_Actors(
                actor_id=actor_id,
                instance_id=instance_id_pass,
                identity_key="test_actor",
                name="Test Actor",
                type="HUMAN"
            )
            session.add(actor)
            session.commit()
            
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_pass
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "Guard should pass for recent timestamp"
        print("✓ Guard passed for recent timestamp")
        
        # Test 2: Old timestamp (should fail)
        old_time = now - timedelta(seconds=600)  # 10 minutes ago
        instance_id_fail = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"created_at": old_time.isoformat()}
        )
        
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_fail
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is None, "Guard should reject old timestamp"
        print("✓ Guard rejected old timestamp (> 300 seconds)")
        
    finally:
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


def test_composite_and_logic():
    """Test COMPOSITE guard with AND logic."""
    print("\n=== Testing COMPOSITE Guard with AND Logic ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with COMPOSITE guard (amount > 1000 AND region IN ["US", "EU"])
        template_id = create_template_with_guard(
            manager,
            GuardianType.COMPOSITE.value,
            {
                "logic": "AND",
                "steps": [
                    {
                        "type": GuardianType.CRITERIA_GATE.value,
                        "config": {
                            "field": "amount",
                            "operator": "GT",
                            "threshold": 1000
                        }
                    },
                    {
                        "type": GuardianType.CRITERIA_GATE.value,
                        "config": {
                            "field": "region",
                            "operator": "IN",
                            "threshold": ["US", "EU"]
                        }
                    }
                ]
            }
        )
        
        engine = ChameleonEngine(manager)
        
        # Test 1: Both conditions pass
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 2000, "region": "US"}
        )
        
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
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "AND guard should pass when all conditions pass"
        print("✓ AND guard passed (amount > 1000 AND region in list)")
        
        # Test 2: One condition fails (amount OK, region not in list)
        instance_id_fail = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 2000, "region": "CN"}
        )
        
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_fail
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is None, "AND guard should reject when any condition fails"
        print("✓ AND guard rejected (region not in list)")
        
    finally:
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


def test_composite_or_logic():
    """Test COMPOSITE guard with OR logic."""
    print("\n=== Testing COMPOSITE Guard with OR Logic ===")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp1:
        template_db = tmp1.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp2:
        instance_db = tmp2.name
    
    try:
        manager = DatabaseManager(
            template_url=f"sqlite:///{template_db}",
            instance_url=f"sqlite:///{instance_db}"
        )
        manager.create_template_schema()
        manager.create_instance_schema()
        
        # Create template with COMPOSITE guard (amount < 100 OR vip = True)
        template_id = create_template_with_guard(
            manager,
            GuardianType.COMPOSITE.value,
            {
                "logic": "OR",
                "steps": [
                    {
                        "type": GuardianType.CRITERIA_GATE.value,
                        "config": {
                            "field": "amount",
                            "operator": "LT",
                            "threshold": 100
                        }
                    },
                    {
                        "type": GuardianType.CRITERIA_GATE.value,
                        "config": {
                            "field": "vip",
                            "operator": "EQ",
                            "threshold": True
                        }
                    }
                ]
            }
        )
        
        engine = ChameleonEngine(manager)
        
        # Test 1: First condition passes (amount < 100)
        instance_id = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 50, "vip": False}
        )
        
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
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "OR guard should pass when any condition passes"
        print("✓ OR guard passed (amount < 100)")
        
        # Test 2: Second condition passes (vip = True)
        instance_id2 = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 5000, "vip": True}
        )
        
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id2
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is not None, "OR guard should pass when any condition passes"
        print("✓ OR guard passed (vip = True)")
        
        # Test 3: Both conditions fail
        instance_id_fail = engine.instantiate_workflow(
            template_id=template_id,
            initial_context={"amount": 5000, "vip": False}
        )
        
        with manager.get_instance_session() as session:
            beta_role = session.query(Local_Roles).filter(
                and_(
                    Local_Roles.local_workflow_id == 
                        session.query(Local_Workflows).filter(
                            Local_Workflows.instance_id == instance_id_fail
                        ).first().local_workflow_id,
                    Local_Roles.role_type == RoleType.BETA.value
                )
            ).first()
            beta_role_id = beta_role.role_id
        
        result = engine.checkout_work(actor_id=actor_id, role_id=beta_role_id)
        assert result is None, "OR guard should reject when all conditions fail"
        print("✓ OR guard rejected (both conditions failed)")
        
    finally:
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
    print("CHAMELEON ENGINE - GUARD LOGIC TESTS")
    print("=" * 70)
    
    try:
        # Run all guard tests
        test_pass_thru_guard()
        test_criteria_gate_gt()
        test_criteria_gate_in()
        test_ttl_check()
        test_composite_and_logic()
        test_composite_or_logic()
        
        print("\n" + "=" * 70)
        print("✅ ALL GUARD TESTS PASSED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
