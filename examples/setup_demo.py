#!/usr/bin/env python3
"""
Setup Helper for Mixed Agent Workflow Demo

This script helps set up and run the Chameleon mixed agent workflow demo.
It imports the workflow, retrieves role IDs, and provides commands to run the agents.

Usage:
    python examples/setup_demo.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.manager import DatabaseManager
from database.models_template import Template_Workflows, Template_Roles


def main():
    """Main setup function"""
    print("=" * 80)
    print("Chameleon Workflow Engine - Mixed Agent Demo Setup")
    print("=" * 80)
    print()

    # Check if workflow is already imported
    db = DatabaseManager(template_url="sqlite:///chameleon_workflow.db")

    with db.get_template_session() as session:
        workflow = (
            session.query(Template_Workflows)
            .filter(Template_Workflows.name == "Mixed_Agent_Demo_Workflow")
            .first()
        )

        if not workflow:
            print("❌ Workflow not found in database.")
            print("   Please import the workflow first:")
            print()
            print("   python tools/workflow_manager.py -i -f tools/mixed_agent_workflow.yaml")
            print()
            sys.exit(1)

        print(f"✅ Workflow found: {workflow.name}")
        print(f"   Workflow ID: {workflow.workflow_id}")
        print()

        # Store workflow_id for later use
        workflow_id = str(workflow.workflow_id)

        # Get role IDs
        roles = (
            session.query(Template_Roles)
            .filter(
                Template_Roles.name.in_(["AI_Analyzer", "Auto_Calculator", "Human_Approver"]),
                Template_Roles.workflow_id == workflow.workflow_id,
            )
            .all()
        )

        if len(roles) != 3:
            print("❌ Error: Expected 3 roles, found:", len(roles))
            sys.exit(1)

        role_ids = {role.name: str(role.role_id) for role in roles}

        print("📋 Role IDs:")
        for name, role_id in role_ids.items():
            print(f"   {name:20s}: {role_id}")
        print()

    # Display setup instructions
    print("=" * 80)
    print("🚀 Setup Instructions")
    print("=" * 80)
    print()
    print("1. Start the Chameleon Workflow Engine server:")
    print("   python -m chameleon_workflow_engine.server")
    print()
    print("2. In separate terminal windows, start each agent:")
    print()
    print("   Terminal 1 - AI Agent:")
    print(f"   python examples/ai_agent.py --role-id {role_ids['AI_Analyzer']}")
    print()
    print("   Terminal 2 - Auto Agent:")
    print(f"   python examples/auto_agent.py --role-id {role_ids['Auto_Calculator']}")
    print()
    print("   Terminal 3 - Human Agent:")
    print(f"   python examples/human_agent.py --role-id {role_ids['Human_Approver']}")
    print()
    print("3. Instantiate a workflow instance via the API:")
    print(f"""
   curl -X POST http://localhost:8000/workflow/instantiate \\
     -H "Content-Type: application/json" \\
     -d '{{
       "template_id": "{workflow_id}",
       "initial_context": {{
         "input_text": "The quick brown fox jumps over the lazy dog. This is a test of the Chameleon Workflow Engine with mixed agent types."
       }},
       "instance_name": "Demo Workflow Instance",
       "instance_description": "Testing the mixed agent workflow"
     }}'
""")
    print()
    print("4. Watch the agents process the work!")
    print()
    print("=" * 80)
    print("📚 Additional Resources")
    print("=" * 80)
    print()
    print("   - Agent documentation: examples/README.md")
    print("   - Workflow definition: tools/mixed_agent_workflow.yaml")
    print("   - Server API docs: http://localhost:8000/docs (when running)")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
