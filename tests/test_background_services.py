"""
Tests for Background Services: Zombie Protocol, Memory Decay, and Toxic Knowledge Filter.

This test suite validates:
1. run_zombie_protocol - Zombie Actor Protocol (Article XI.3)
2. run_memory_decay - Memory Decay / The Janitor (Article XX.3)
3. mark_memory_toxic - Toxic Knowledge Filter (Article XX.1)
4. Admin endpoints for triggering these services
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
    # Tier 2 Models
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Actors,
    UnitsOfWork,
    Local_Role_Attributes,
    Interaction_Logs,
    # Enums
    RoleType,
    ComponentDirection,
    UOWStatus,
)
from chameleon_workflow_engine.engine import ChameleonEngine
from fastapi.testclient import TestClient


def setup_test_database():
    """Create a test database with sample data for background services testing"""
    # Create temporary SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    db_url = f"sqlite:///{db_path}"
    manager = DatabaseManager(instance_url=db_url)
    manager.create_instance_schema()
    
    # Create test data
    with manager.get_instance_session() as session:
        # Create instance context
        instance = Instance_Context(
            instance_id=uuid.uuid4(),
            name="Test Instance",
            status="ACTIVE"
        )
        session.add(instance)
        session.flush()
        
        # Create system actor
        from chameleon_workflow_engine.engine import SYSTEM_ACTOR_ID
        system_actor = Local_Actors(
            actor_id=SYSTEM_ACTOR_ID,
            instance_id=instance.instance_id,
            identity_key="SYSTEM",
            name="System Actor",
            type="SYSTEM"
        )
        session.add(system_actor)
        session.flush()
        
        # Create workflow
        workflow = Local_Workflows(
            local_workflow_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            original_workflow_id=uuid.uuid4(),
            name="Test Workflow",
            version=1
        )
        session.add(workflow)
        session.flush()
        
        # Create interactions
        standard_interaction = Local_Interactions(
            interaction_id=uuid.uuid4(),
            local_workflow_id=workflow.local_workflow_id,
            name="Standard Interaction"
        )
        session.add(standard_interaction)
        
        chronos_interaction = Local_Interactions(
            interaction_id=uuid.uuid4(),
            local_workflow_id=workflow.local_workflow_id,
            name="Chronos Interaction"
        )
        session.add(chronos_interaction)
        session.flush()
        
        # Create Tau role
        tau_role = Local_Roles(
            role_id=uuid.uuid4(),
            local_workflow_id=workflow.local_workflow_id,
            name="Tau Role",
            description="Timeout handler",
            role_type=RoleType.TAU.value
        )
        session.add(tau_role)
        session.flush()
        
        # Create component connecting Chronos interaction to Tau role (INBOUND)
        chronos_component = Local_Components(
            component_id=uuid.uuid4(),
            local_workflow_id=workflow.local_workflow_id,
            interaction_id=chronos_interaction.interaction_id,
            role_id=tau_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Chronos to Tau"
        )
        session.add(chronos_component)
        session.flush()
        
        # Create Beta role for memory testing
        beta_role = Local_Roles(
            role_id=uuid.uuid4(),
            local_workflow_id=workflow.local_workflow_id,
            name="Beta Role",
            description="Processing role",
            role_type=RoleType.BETA.value
        )
        session.add(beta_role)
        session.flush()
        
        # Create UOWs for testing
        # 1. Fresh UOW with recent heartbeat (should NOT be reclaimed)
        fresh_uow = UnitsOfWork(
            uow_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            local_workflow_id=workflow.local_workflow_id,
            current_interaction_id=standard_interaction.interaction_id,
            status=UOWStatus.ACTIVE.value,
            last_heartbeat=datetime.now(timezone.utc) - timedelta(minutes=2)
        )
        session.add(fresh_uow)
        
        # 2. Zombie UOW with old heartbeat (10 minutes ago) - should be reclaimed
        zombie_uow = UnitsOfWork(
            uow_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            local_workflow_id=workflow.local_workflow_id,
            current_interaction_id=standard_interaction.interaction_id,
            status=UOWStatus.ACTIVE.value,
            last_heartbeat=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        session.add(zombie_uow)
        
        # 3. UOW without heartbeat (should NOT be reclaimed)
        no_heartbeat_uow = UnitsOfWork(
            uow_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            local_workflow_id=workflow.local_workflow_id,
            current_interaction_id=standard_interaction.interaction_id,
            status=UOWStatus.ACTIVE.value,
            last_heartbeat=None
        )
        session.add(no_heartbeat_uow)
        
        # 4. Completed UOW with old heartbeat (should NOT be reclaimed)
        completed_uow = UnitsOfWork(
            uow_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            local_workflow_id=workflow.local_workflow_id,
            current_interaction_id=standard_interaction.interaction_id,
            status=UOWStatus.COMPLETED.value,
            last_heartbeat=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        session.add(completed_uow)
        session.flush()
        
        # Create memory entries for testing
        # 1. Fresh memory (should NOT be deleted)
        fresh_memory = Local_Role_Attributes(
            memory_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            role_id=beta_role.role_id,
            context_type="GLOBAL",
            context_id="GLOBAL",
            key="recent_pattern",
            value={"data": "fresh"},
            last_accessed_at=datetime.now(timezone.utc) - timedelta(days=30)
        )
        session.add(fresh_memory)
        
        # 2. Stale memory (100 days old) - should be deleted
        stale_memory = Local_Role_Attributes(
            memory_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            role_id=beta_role.role_id,
            context_type="GLOBAL",
            context_id="GLOBAL",
            key="old_pattern",
            value={"data": "stale"},
            last_accessed_at=datetime.now(timezone.utc) - timedelta(days=100)
        )
        session.add(stale_memory)
        
        # 3. Memory without last_accessed_at (should NOT be deleted)
        no_access_memory = Local_Role_Attributes(
            memory_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            role_id=beta_role.role_id,
            context_type="GLOBAL",
            context_id="GLOBAL",
            key="never_accessed",
            value={"data": "no_access"},
            last_accessed_at=None
        )
        session.add(no_access_memory)
        
        # 4. Memory for toxic testing
        test_memory = Local_Role_Attributes(
            memory_id=uuid.uuid4(),
            instance_id=instance.instance_id,
            role_id=beta_role.role_id,
            context_type="GLOBAL",
            context_id="GLOBAL",
            key="test_toxic_pattern",
            value={"data": "to_be_marked_toxic"},
            is_toxic=False
        )
        session.add(test_memory)
        session.flush()
        
        session.commit()
        
        test_data = {
            'db_path': db_path,
            'db_url': db_url,
            'manager': manager,
            'instance_id': instance.instance_id,
            'workflow_id': workflow.local_workflow_id,
            'standard_interaction_id': standard_interaction.interaction_id,
            'chronos_interaction_id': chronos_interaction.interaction_id,
            'tau_role_id': tau_role.role_id,
            'beta_role_id': beta_role.role_id,
            'fresh_uow_id': fresh_uow.uow_id,
            'zombie_uow_id': zombie_uow.uow_id,
            'no_heartbeat_uow_id': no_heartbeat_uow.uow_id,
            'completed_uow_id': completed_uow.uow_id,
            'fresh_memory_id': fresh_memory.memory_id,
            'stale_memory_id': stale_memory.memory_id,
            'no_access_memory_id': no_access_memory.memory_id,
            'test_memory_id': test_memory.memory_id,
        }
        
        return test_data


def cleanup_database(test_data):
    """Cleanup test database"""
    try:
        test_data['manager'].close()
    except Exception:
        pass
    import time
    time.sleep(0.1)
    if os.path.exists(test_data['db_path']):
        try:
            os.unlink(test_data['db_path'])
        except PermissionError:
            pass


def test_zombie_protocol():
    """Test the Zombie Actor Protocol (run_zombie_protocol method)"""
    print("\n=== Testing Zombie Actor Protocol ===")
    
    test_data = setup_test_database()
    
    try:
        # Create engine
        engine = ChameleonEngine(test_data['manager'])
        
        # Verify initial state
        with test_data['manager'].get_instance_session() as session:
            fresh_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['fresh_uow_id']
            ).first()
            zombie_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['zombie_uow_id']
            ).first()
            no_heartbeat_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['no_heartbeat_uow_id']
            ).first()
            
            assert fresh_uow.status == UOWStatus.ACTIVE.value
            assert zombie_uow.status == UOWStatus.ACTIVE.value
            assert no_heartbeat_uow.status == UOWStatus.ACTIVE.value
            print("✓ Initial UOW states verified")
        
        # Run zombie protocol with 5-minute threshold
        with test_data['manager'].get_instance_session() as session:
            zombies_reclaimed = engine.run_zombie_protocol(session, timeout_seconds=300)
        
        # Should find exactly 1 zombie
        assert zombies_reclaimed == 1, f"Expected 1 zombie, found {zombies_reclaimed}"
        print(f"✓ Found and reclaimed {zombies_reclaimed} zombie UOW")
        
        # Verify final state
        with test_data['manager'].get_instance_session() as session:
            fresh_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['fresh_uow_id']
            ).first()
            zombie_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['zombie_uow_id']
            ).first()
            no_heartbeat_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['no_heartbeat_uow_id']
            ).first()
            completed_uow = session.query(UnitsOfWork).filter(
                UnitsOfWork.uow_id == test_data['completed_uow_id']
            ).first()
            
            assert fresh_uow.status == UOWStatus.ACTIVE.value, "Fresh UOW should remain ACTIVE"
            assert zombie_uow.status == UOWStatus.FAILED.value, "Zombie UOW should be FAILED"
            assert zombie_uow.current_interaction_id == test_data['chronos_interaction_id'], \
                "Zombie UOW should be routed to Chronos interaction"
            assert zombie_uow.last_heartbeat is None, "Zombie UOW heartbeat should be cleared"
            assert no_heartbeat_uow.status == UOWStatus.ACTIVE.value, "No-heartbeat UOW should remain ACTIVE"
            assert completed_uow.status == UOWStatus.COMPLETED.value, "Completed UOW should remain COMPLETED"
            print("✓ Final UOW states verified")
            
            # Note: Interaction log checking skipped due to SQLite autoincrement limitations with BigInteger
            # In production with PostgreSQL, interaction logs would be properly created
        
        print("✓ Zombie Protocol test passed")
        
    finally:
        cleanup_database(test_data)


def test_memory_decay():
    """Test Memory Decay / The Janitor (run_memory_decay method)"""
    print("\n=== Testing Memory Decay ===")
    
    test_data = setup_test_database()
    
    try:
        # Create engine
        engine = ChameleonEngine(test_data['manager'])
        
        # Verify initial state
        with test_data['manager'].get_instance_session() as session:
            all_memories = session.query(Local_Role_Attributes).all()
            print(f"Initial memory count: {len(all_memories)}")
            assert len(all_memories) == 4, "Should have 4 memory entries initially"
        
        # Run memory decay with 90-day retention
        with test_data['manager'].get_instance_session() as session:
            memories_deleted = engine.run_memory_decay(session, retention_days=90)
        
        # Should delete exactly 1 stale memory
        assert memories_deleted == 1, f"Expected 1 memory deleted, got {memories_deleted}"
        print(f"✓ Deleted {memories_deleted} stale memory entries")
        
        # Verify final state
        with test_data['manager'].get_instance_session() as session:
            fresh_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['fresh_memory_id']
            ).first()
            stale_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['stale_memory_id']
            ).first()
            no_access_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['no_access_memory_id']
            ).first()
            test_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['test_memory_id']
            ).first()
            
            assert fresh_memory is not None, "Fresh memory should still exist"
            assert stale_memory is None, "Stale memory should be deleted"
            assert no_access_memory is not None, "No-access memory should still exist"
            assert test_memory is not None, "Test memory should still exist"
            print("✓ Memory retention verified")
            
            all_memories = session.query(Local_Role_Attributes).all()
            assert len(all_memories) == 3, "Should have 3 memory entries remaining"
            print(f"✓ Final memory count: {len(all_memories)}")
        
        print("✓ Memory Decay test passed")
        
    finally:
        cleanup_database(test_data)


def test_mark_memory_toxic():
    """Test Toxic Knowledge Filter (mark_memory_toxic method)"""
    print("\n=== Testing Toxic Knowledge Filter ===")
    
    test_data = setup_test_database()
    
    try:
        # Create engine
        engine = ChameleonEngine(test_data['manager'])
        
        # Verify initial state
        with test_data['manager'].get_instance_session() as session:
            test_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['test_memory_id']
            ).first()
            assert test_memory.is_toxic is False, "Memory should not be toxic initially"
            print("✓ Initial memory state verified (not toxic)")
        
        # Mark memory as toxic
        success = engine.mark_memory_toxic(
            memory_id=test_data['test_memory_id'],
            reason="Test: Memory led to incorrect results"
        )
        
        assert success is True, "Should return True on success"
        print("✓ mark_memory_toxic returned success")
        
        # Verify memory is now toxic
        with test_data['manager'].get_instance_session() as session:
            test_memory = session.query(Local_Role_Attributes).filter(
                Local_Role_Attributes.memory_id == test_data['test_memory_id']
            ).first()
            assert test_memory.is_toxic is True, "Memory should now be toxic"
            print("✓ Memory successfully marked as toxic")
        
        # Test with non-existent memory ID
        try:
            engine.mark_memory_toxic(
                memory_id=uuid.uuid4(),
                reason="Test: Non-existent memory"
            )
            assert False, "Should raise ValueError for non-existent memory"
        except ValueError as e:
            assert "not found" in str(e).lower()
            print("✓ Correctly raises ValueError for non-existent memory")
        
        print("✓ Toxic Knowledge Filter test passed")
        
    finally:
        cleanup_database(test_data)


def test_admin_endpoints():
    """Test the admin endpoints for background services"""
    print("\n=== Testing Admin Endpoints ===")
    
    test_data = setup_test_database()
    
    try:
        # Set environment variable for the test database
        os.environ['INSTANCE_DB_URL'] = test_data['db_url']
        
        # Import and manually initialize the app
        from chameleon_workflow_engine import server
        server.db_manager = test_data['manager']
        
        # Create TestClient
        client = TestClient(server.app)
        
        # Test POST /admin/run-zombie-protocol
        response = client.post(
            "/admin/run-zombie-protocol",
            json={"timeout_seconds": 300}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data['success'] is True
        assert data['zombies_reclaimed'] == 1
        print(f"✓ Zombie protocol endpoint: {data}")
        
        # Test POST /admin/run-memory-decay
        response = client.post(
            "/admin/run-memory-decay",
            json={"retention_days": 90}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data['success'] is True
        assert data['memories_deleted'] == 1
        print(f"✓ Memory decay endpoint: {data}")
        
        # Test POST /admin/mark-toxic
        response = client.post(
            "/admin/mark-toxic",
            json={
                "memory_id": str(test_data['test_memory_id']),
                "reason": "Test endpoint call"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data['success'] is True
        print(f"✓ Mark toxic endpoint: {data}")
        
        # Test with invalid memory ID
        response = client.post(
            "/admin/mark-toxic",
            json={
                "memory_id": "00000000-0000-0000-0000-000000000000",
                "reason": "Should fail"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Mark toxic endpoint returns 404 for non-existent memory")
        
        print("✓ Admin endpoints test passed")
        
    finally:
        cleanup_database(test_data)


def run_all_tests():
    """Run all background services tests"""
    print("=" * 60)
    print("Background Services Test Suite")
    print("=" * 60)
    
    try:
        test_zombie_protocol()
        test_memory_decay()
        test_mark_memory_toxic()
        test_admin_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
