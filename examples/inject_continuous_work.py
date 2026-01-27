#!/usr/bin/env python3
"""
Continuous Work Injector for Chameleon

This script injects a continuous stream of work into an EXISTING workflow instance.
It uses the Local Alpha Role ID to locate the entry point (Alpha Outbound Queue)
and deposits new Units of Work directly into the active stream.

Usage:
    python examples/inject_continuous_work.py --role-id <LOCAL_ALPHA_ROLE_ID>
"""

import sys
import time
import uuid
import random
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import INSTANCE_DB_URL
from database.manager import DatabaseManager
from database.models_instance import (
    Local_Roles, 
    Local_Workflows,
    Local_Components, 
    UnitsOfWork, 
    UOW_Attributes
)
from database.enums import ComponentDirection, UOWStatus

# Sample data to randomize inputs
SAMPLE_INPUTS = [
    "Analyze the efficiency of hybrid agent workflows.",
    "The system creates isolation boundaries between templates and instances.",
    "Python 3.9+ is required for the Chameleon Engine.",
    "Topology-based routing ensures work finds the correct agent.",
    "Zombie protocols reclaim tokens from failed actors.",
    "Atomic versioning preserves the history of all data attributes."
]

def get_entry_interaction(session, alpha_role_id):
    """Find the interaction where Alpha outputs work (The entry point for Beta)"""
    # 1. Verify Role Exists
    role = session.query(Local_Roles).filter(
        Local_Roles.role_id == alpha_role_id
    ).first()
    
    if not role:
        print(f"❌ Role {alpha_role_id} not found in Instance DB.")
        sys.exit(1)
        
    print(f"✅ Target Role: {role.name} ({role.role_type})")

    # 2. Get the workflow to retrieve instance_id
    workflow = session.query(Local_Workflows).filter(
        Local_Workflows.local_workflow_id == role.local_workflow_id
    ).first()
    
    if not workflow:
        print(f"❌ Workflow {role.local_workflow_id} not found.")
        sys.exit(1)
    
    print(f"✅ Target Instance: {workflow.instance_id}")

    # 3. Find the OUTBOUND component for this role
    component = session.query(Local_Components).filter(
        Local_Components.role_id == alpha_role_id,
        Local_Components.direction == ComponentDirection.OUTBOUND.value
    ).first()

    if not component:
        print("❌ No OUTBOUND connection found for this Alpha role.")
        sys.exit(1)

    return component.interaction_id, role.local_workflow_id, workflow.instance_id

def inject_loop(alpha_role_id, interval):
    """Main injection loop"""
    db = DatabaseManager(instance_url=INSTANCE_DB_URL)
    
    with db.get_instance_session() as session:
        # One-time setup: find where to put the work
        interaction_id, workflow_id, instance_id = get_entry_interaction(session, alpha_role_id)
        
        print(f"✅ Entry Point Found: Interaction {interaction_id}")
        print(f"🚀 Starting Injection Stream (Interval: {interval}s)")
        print("   Press Ctrl+C to stop\n")

        count = 1
        try:
            while True:
                # Generate unique content
                text_payload = random.choice(SAMPLE_INPUTS)
                timestamp = datetime.utcnow().isoformat()
                
                # 1. Create Unit of Work
                #
                uow_id = uuid.uuid4()
                uow = UnitsOfWork(
                    uow_id=uow_id,
                    instance_id=instance_id,
                    local_workflow_id=workflow_id,
                    current_interaction_id=interaction_id,
                    status=UOWStatus.PENDING.value,
                    child_count=0,
                    finished_child_count=0
                )
                session.add(uow)
                
                # 2. Add Attributes (The Payload)
                #
                attr = UOW_Attributes(
                    attribute_id=uuid.uuid4(),
                    uow_id=uow_id,
                    instance_id=instance_id,
                    key="input_text",
                    value=f"Stream Item #{count}: {text_payload}",
                    version=1,
                    actor_id=uuid.UUID("00000000-0000-0000-0000-000000000001"), # System Actor
                    reasoning="Injected by Continuous Workload Generator"
                )
                session.add(attr)
                
                session.commit()
                
                print(f"   [Batch #{count}] Injected UOW {uow_id}")
                print(f"   └── '{text_payload[:30]}...'")
                
                count += 1
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Injection stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject continuous work into a running instance")
    parser.add_argument("--role-id", required=True, help="The Local UUID of the ALPHA role")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between injections")
    
    args = parser.parse_args()
    
    # Clean UUID string
    try:
        r_id = uuid.UUID(args.role_id)
    except ValueError:
        print("❌ Invalid UUID format for Role ID")
        sys.exit(1)

    inject_loop(r_id, args.interval)