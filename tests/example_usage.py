"""
Example usage of the Chameleon Workflow Engine Database.

This script demonstrates:
1. Creating separate Tier 1 and Tier 2 databases
2. Creating a template workflow in Tier 1
3. Creating an instance and instantiating data in Tier 2
4. Proper air-gapped isolation
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database import (
    DatabaseManager,
    # Tier 1 Models
    Template_Workflows,
    Template_Roles,
    # Tier 2 Models
    Instance_Context,
    Local_Workflows,
    Local_Actors,
    # Enums
    RoleType,
    ActorType,
    InstanceStatus,
)


def example_usage():
    """Demonstrate basic usage of the database system."""
    
    print("=" * 70)
    print("CHAMELEON WORKFLOW ENGINE - DATABASE USAGE EXAMPLE")
    print("=" * 70)
    
    # Step 1: Create databases
    print("\n1. Creating air-gapped databases...")
    manager = DatabaseManager(
        template_url="sqlite:///tier1_templates.db",
        instance_url="sqlite:///tier2_instance.db",
        echo=False  # Set to True to see SQL statements
    )
    
    # Initialize schemas
    manager.create_template_schema()
    manager.create_instance_schema()
    print("   ✓ Tier 1 (Templates) database created")
    print("   ✓ Tier 2 (Instance) database created")
    
    # Step 2: Create a template workflow in Tier 1
    print("\n2. Creating template workflow in Tier 1...")
    with manager.get_template_session() as session:
        # Create a simple workflow blueprint
        workflow = Template_Workflows(
            name="Simple_Approval_Flow",
            description="A basic approval workflow for demonstration",
            ai_context={
                "purpose": "Demonstrate the workflow engine capabilities",
                "domain": "General Purpose"
            },
            version=1,
            schema_json={
                "nodes": ["Alpha", "Omega"],
                "edges": [{"from": "Alpha", "to": "Omega"}]
            }
        )
        session.add(workflow)
        session.flush()  # Get the workflow_id
        
        workflow_id = workflow.workflow_id
        print(f"   ✓ Created template workflow: {workflow.name}")
        print(f"     ID: {workflow_id}")
        
        # Create roles
        alpha_role = Template_Roles(
            workflow_id=workflow_id,
            name="Initiator",
            description="Creates the initial work item",
            role_type=RoleType.ALPHA.value,
            ai_context={"instructions": "Start the workflow"}
        )
        
        omega_role = Template_Roles(
            workflow_id=workflow_id,
            name="Finalizer",
            description="Completes the work item",
            role_type=RoleType.OMEGA.value,
            ai_context={"instructions": "Finalize and close the workflow"}
        )
        
        session.add_all([alpha_role, omega_role])
        print(f"   ✓ Created {RoleType.ALPHA.value} role: {alpha_role.name}")
        print(f"   ✓ Created {RoleType.OMEGA.value} role: {omega_role.name}")
    
    # Step 3: Create an instance in Tier 2
    print("\n3. Creating instance in Tier 2...")
    with manager.get_instance_session() as session:
        # Create instance context
        instance = Instance_Context(
            name="Production_Environment",
            description="Production deployment of the workflow engine",
            status=InstanceStatus.ACTIVE.value
        )
        session.add(instance)
        session.flush()
        
        instance_id = instance.instance_id
        print(f"   ✓ Created instance: {instance.name}")
        print(f"     ID: {instance_id}")
        print(f"     Status: {instance.status}")
        
        # Clone workflow from Tier 1 to Tier 2
        local_workflow = Local_Workflows(
            instance_id=instance_id,
            original_workflow_id=workflow_id,  # Reference to template
            name="Simple_Approval_Flow",
            description="Local copy of approval workflow",
            ai_context={"localized": True},
            version=1,
            is_active=True,
            is_master=True  # This is the entry point
        )
        session.add(local_workflow)
        print(f"   ✓ Instantiated workflow from template")
        
        # Create an actor
        actor = Local_Actors(
            instance_id=instance_id,
            identity_key="user@example.com",
            name="Test User",
            description="Human operator",
            type=ActorType.HUMAN.value,
            ai_context={"role": "operator"},
            capabilities={"approve": True, "reject": True}
        )
        session.add(actor)
        print(f"   ✓ Created actor: {actor.name} ({actor.type})")
    
    # Step 4: Verify isolation
    print("\n4. Verifying air-gapped isolation...")
    
    with manager.get_template_session() as t1_session:
        template_count = t1_session.query(Template_Workflows).count()
        print(f"   ✓ Tier 1 contains {template_count} template workflow(s)")
    
    with manager.get_instance_session() as t2_session:
        instance_count = t2_session.query(Instance_Context).count()
        local_workflow_count = t2_session.query(Local_Workflows).count()
        actor_count = t2_session.query(Local_Actors).count()
        print(f"   ✓ Tier 2 contains {instance_count} instance(s)")
        print(f"   ✓ Tier 2 contains {local_workflow_count} local workflow(s)")
        print(f"   ✓ Tier 2 contains {actor_count} actor(s)")
    
    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nKey Points Demonstrated:")
    print("  ✓ Air-gapped two-tier architecture")
    print("  ✓ Template blueprints in Tier 1 (Read-only source)")
    print("  ✓ Runtime instances in Tier 2 (Read/write engine)")
    print("  ✓ Traceability via original_workflow_id")
    print("  ✓ UUID-based primary keys generated Python-side")
    print("  ✓ Complete isolation between tiers")
    
    print("\nDatabase files created:")
    print("  - tier1_templates.db (Template blueprints)")
    print("  - tier2_instance.db (Runtime instance)")
    
    # Cleanup
    manager.close()


if __name__ == "__main__":
    try:
        example_usage()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
