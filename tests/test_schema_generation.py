"""
Schema Generation and Validation Test for Chameleon Workflow Engine.

This test validates that:
1. Tier 1 (Template) and Tier 2 (Instance) schemas can be created
2. All expected tables exist in their respective databases
3. Table comments are properly set
4. Key columns exist with correct properties
5. The two tiers are properly isolated
"""

import sys
from pathlib import Path
import tempfile
import os

# Add project root to path for imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import inspect, text
from database import (
    DatabaseManager,
    TemplateBase,
    InstanceBase,
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
    Local_Actor_Role_Assignments,
    Local_Role_Attributes,
    UnitsOfWork,
    UOW_Attributes,
    Interaction_Logs,
)


def test_tier1_schema_creation():
    """Test that Tier 1 (Template) schema can be created successfully."""
    print("\n=== Testing Tier 1 (Template) Schema Creation ===")
    
    # Create temporary SQLite database for Tier 1
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tier1_db_path = tmp.name
    
    try:
        tier1_url = f"sqlite:///{tier1_db_path}"
        
        # Initialize manager and create schema
        manager = DatabaseManager(template_url=tier1_url)
        manager.create_template_schema()
        
        # Verify tables exist
        inspector = inspect(manager.template_engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "template_workflows",
            "template_roles",
            "template_interactions",
            "template_components",
            "template_guardians",
        ]
        
        print(f"Found tables: {tables}")
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in Tier 1 database"
            print(f"✓ Table '{table}' exists")
        
        # Verify specific columns exist
        print("\n--- Verifying key columns ---")
        
        # Template_Workflows columns
        workflows_columns = [col['name'] for col in inspector.get_columns('template_workflows')]
        assert 'workflow_id' in workflows_columns, "workflow_id not found in template_workflows"
        assert 'name' in workflows_columns, "name not found in template_workflows"
        assert 'ai_context' in workflows_columns, "ai_context not found in template_workflows"
        print("✓ Template_Workflows has required columns")
        
        # Template_Roles columns
        roles_columns = [col['name'] for col in inspector.get_columns('template_roles')]
        assert 'role_id' in roles_columns, "role_id not found in template_roles"
        assert 'workflow_id' in roles_columns, "workflow_id not found in template_roles"
        assert 'role_type' in roles_columns, "role_type not found in template_roles"
        assert 'child_workflow_id' in roles_columns, "child_workflow_id not found in template_roles"
        print("✓ Template_Roles has required columns")
        
        manager.close()
        print("\n✓ Tier 1 Schema Creation: SUCCESS")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(tier1_db_path):
            os.unlink(tier1_db_path)


def test_tier2_schema_creation():
    """Test that Tier 2 (Instance) schema can be created successfully."""
    print("\n=== Testing Tier 2 (Instance) Schema Creation ===")
    
    # Create temporary SQLite database for Tier 2
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tier2_db_path = tmp.name
    
    try:
        tier2_url = f"sqlite:///{tier2_db_path}"
        
        # Initialize manager and create schema
        manager = DatabaseManager(instance_url=tier2_url)
        manager.create_instance_schema()
        
        # Verify tables exist
        inspector = inspect(manager.instance_engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "instance_context",
            "local_workflows",
            "local_roles",
            "local_interactions",
            "local_components",
            "local_guardians",
            "local_actors",
            "local_actor_role_assignments",
            "local_role_attributes",
            "units_of_work",
            "uow_attributes",
            "interaction_logs",
        ]
        
        print(f"Found tables: {tables}")
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in Tier 2 database"
            print(f"✓ Table '{table}' exists")
        
        # Verify specific columns exist
        print("\n--- Verifying key columns ---")
        
        # Instance_Context columns
        context_columns = [col['name'] for col in inspector.get_columns('instance_context')]
        assert 'instance_id' in context_columns, "instance_id not found in instance_context"
        assert 'status' in context_columns, "status not found in instance_context"
        print("✓ Instance_Context has required columns")
        
        # Local_Roles columns (verify linked_local_workflow_id)
        roles_columns = [col['name'] for col in inspector.get_columns('local_roles')]
        assert 'role_id' in roles_columns, "role_id not found in local_roles"
        assert 'local_workflow_id' in roles_columns, "local_workflow_id not found in local_roles"
        assert 'linked_local_workflow_id' in roles_columns, "linked_local_workflow_id not found in local_roles"
        assert 'is_recursive_gateway' in roles_columns, "is_recursive_gateway not found in local_roles"
        print("✓ Local_Roles has required columns including linked_local_workflow_id")
        
        # Local_Actors columns
        actors_columns = [col['name'] for col in inspector.get_columns('local_actors')]
        assert 'actor_id' in actors_columns, "actor_id not found in local_actors"
        assert 'instance_id' in actors_columns, "instance_id not found in local_actors"
        print("✓ Local_Actors has required columns")
        
        # Local_Actor_Role_Assignments columns
        assignments_columns = [col['name'] for col in inspector.get_columns('local_actor_role_assignments')]
        assert 'assignment_id' in assignments_columns, "assignment_id not found"
        assert 'actor_id' in assignments_columns, "actor_id not found in local_actor_role_assignments"
        assert 'role_id' in assignments_columns, "role_id not found in local_actor_role_assignments"
        print("✓ Local_Actor_Role_Assignments has required columns")
        
        # Local_Role_Attributes columns (verify Memory Hierarchy support)
        memory_columns = [col['name'] for col in inspector.get_columns('local_role_attributes')]
        assert 'memory_id' in memory_columns, "memory_id not found in local_role_attributes"
        assert 'instance_id' in memory_columns, "instance_id not found in local_role_attributes"
        assert 'role_id' in memory_columns, "role_id not found in local_role_attributes"
        assert 'actor_id' in memory_columns, "actor_id not found in local_role_attributes (required for hierarchy)"
        assert 'is_toxic' in memory_columns, "is_toxic not found in local_role_attributes"
        print("✓ Local_Role_Attributes has required columns for Memory Hierarchy")
        
        # UnitsOfWork columns (verify child tracking fields)
        uow_columns = [col['name'] for col in inspector.get_columns('units_of_work')]
        assert 'uow_id' in uow_columns, "uow_id not found in units_of_work"
        assert 'instance_id' in uow_columns, "instance_id not found in units_of_work"
        assert 'parent_id' in uow_columns, "parent_id not found in units_of_work"
        assert 'child_count' in uow_columns, "child_count not found in units_of_work"
        assert 'finished_child_count' in uow_columns, "finished_child_count not found in units_of_work"
        print("✓ UnitsOfWork has required columns including child tracking")
        
        manager.close()
        print("\n✓ Tier 2 Schema Creation: SUCCESS")
        return True
        
    finally:
        # Cleanup
        if os.path.exists(tier2_db_path):
            os.unlink(tier2_db_path)


def test_air_gapped_isolation():
    """Test that Tier 1 and Tier 2 use separate declarative bases."""
    print("\n=== Testing Air-Gapped Isolation ===")
    
    # Verify that TemplateBase and InstanceBase are different
    assert TemplateBase is not InstanceBase, "TemplateBase and InstanceBase must be separate!"
    print("✓ Separate declarative bases confirmed")
    
    # Verify metadata is separate
    template_tables = set(TemplateBase.metadata.tables.keys())
    instance_tables = set(InstanceBase.metadata.tables.keys())
    
    print(f"Template tables: {template_tables}")
    print(f"Instance tables: {instance_tables}")
    
    # Verify no overlap
    overlap = template_tables & instance_tables
    assert len(overlap) == 0, f"Tables should not overlap between tiers! Found: {overlap}"
    print("✓ No table overlap between tiers")
    
    print("\n✓ Air-Gapped Isolation: SUCCESS")
    return True


def test_instance_id_in_tier2():
    """Verify that all Tier 2 tables have instance_id for strict isolation."""
    print("\n=== Testing Instance ID Isolation ===")
    
    # Tables that should have instance_id (excluding the root Instance_Context)
    tables_requiring_instance_id = [
        Local_Workflows,
        Local_Role_Attributes,
        UnitsOfWork,
        UOW_Attributes,
        Interaction_Logs,
        Local_Actors,
    ]
    
    for model in tables_requiring_instance_id:
        columns = [col.name for col in model.__table__.columns]
        assert 'instance_id' in columns, f"{model.__tablename__} missing instance_id column!"
        print(f"✓ {model.__tablename__} has instance_id")
    
    print("\n✓ Instance ID Isolation: SUCCESS")
    return True


def test_comments_exist():
    """Verify that table and column comments are defined for AI introspection."""
    print("\n=== Testing AI Introspection (Comments) ===")
    
    # Test a few key tables for comments
    tier1_tables = [Template_Workflows, Template_Roles, Template_Guardians]
    tier2_tables = [Instance_Context, Local_Roles, UnitsOfWork, Local_Role_Attributes]
    
    for model in tier1_tables:
        assert model.__table__.comment is not None, f"{model.__tablename__} missing table comment"
        print(f"✓ {model.__tablename__} has table comment")
        
        # Check some columns have comments
        columns_with_comments = [col for col in model.__table__.columns if col.comment]
        assert len(columns_with_comments) > 0, f"{model.__tablename__} has no column comments"
        print(f"  - {len(columns_with_comments)} columns with comments")
    
    for model in tier2_tables:
        assert model.__table__.comment is not None, f"{model.__tablename__} missing table comment"
        print(f"✓ {model.__tablename__} has table comment")
        
        # Check some columns have comments
        columns_with_comments = [col for col in model.__table__.columns if col.comment]
        assert len(columns_with_comments) > 0, f"{model.__tablename__} has no column comments"
        print(f"  - {len(columns_with_comments)} columns with comments")
    
    print("\n✓ AI Introspection Comments: SUCCESS")
    return True


def run_all_tests():
    """Run all validation tests."""
    print("=" * 70)
    print("CHAMELEON WORKFLOW ENGINE - DATABASE SCHEMA VALIDATION")
    print("=" * 70)
    
    tests = [
        ("Air-Gapped Isolation", test_air_gapped_isolation),
        ("Instance ID in Tier 2", test_instance_id_in_tier2),
        ("Comments for AI Introspection", test_comments_exist),
        ("Tier 1 Schema Creation", test_tier1_schema_creation),
        ("Tier 2 Schema Creation", test_tier2_schema_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, True, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n✗ {test_name}: FAILED - {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"  Error: {error}")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Schema Validation Successful! 🎉")
        print("\nAll requirements met:")
        print("  ✓ Air-gapped two-tier architecture")
        print("  ✓ Separate declarative bases")
        print("  ✓ Strict isolation with instance_id")
        print("  ✓ AI introspection via comments")
        print("  ✓ All tables created successfully")
        print("  ✓ Key columns verified")
        return True
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
