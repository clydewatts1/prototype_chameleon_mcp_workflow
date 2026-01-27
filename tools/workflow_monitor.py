#!/usr/bin/env python3
"""
Workflow Monitor CLI - Interactive Command-Line Control Room for the Chameleon Workflow Engine

This script provides an interactive text-based menu system for monitoring workflow instances,
tracking UOW (Units of Work) status, and inspecting roles and interactions.

Features:
- Interactive menu loop with multiple monitoring options
- Monitor Global Status: Real-time metrics dashboard
- Inspect Roles: View all roles with their work counts
- Inspect Interactions: View all interactions with their work counts
- Configurable database connection

Usage:
    python tools/workflow_monitor.py [--db-url <url>]

    Examples:
    python tools/workflow_monitor.py
    python tools/workflow_monitor.py --db-url "sqlite:///path/to/instance.db"

Source of Truth:
    - database/manager.py and database/models_instance.py (State queries)
    - database/enums.py (Status and Role Type definitions)
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.manager import DatabaseManager
from database.models_instance import (
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    UnitsOfWork,
)
from database.enums import UOWStatus, ComponentDirection

# Try to import tabulate for nice table formatting
try:
    from tabulate import tabulate

    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_table(headers: List[str], rows: List[List], tablefmt: str = "grid"):
    """Print a formatted table using tabulate or fallback to manual formatting."""
    if TABULATE_AVAILABLE:
        print(tabulate(rows, headers=headers, tablefmt=tablefmt))
    else:
        # Fallback to simple formatting
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print header
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        print(header_line)
        print("-" * len(header_line))

        # Print rows
        for row in rows:
            row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            print(row_line)


def get_all_instances(session: Session) -> List[Instance_Context]:
    """Get all instance contexts from the database."""
    return session.query(Instance_Context).all()


def select_instance(session: Session) -> Optional[str]:
    """Prompt user to select an instance and return the instance_id."""
    instances = get_all_instances(session)

    if not instances:
        print("\n⚠️  No workflow instances found in the database.")
        print("Please create an instance first using the workflow instantiation API.")
        return None

    print("\nAvailable Workflow Instances:")
    print("-" * 80)
    for i, inst in enumerate(instances, 1):
        deployed = (
            inst.deployment_date.strftime("%Y-%m-%d %H:%M") if inst.deployment_date else "N/A"
        )
        print(f"{i}. {inst.name} (Status: {inst.status}, Deployed: {deployed})")
        print(f"   ID: {str(inst.instance_id)[:8]}...")

    while True:
        try:
            choice = input("\nSelect instance number (or 'q' to quit): ").strip()
            if choice.lower() == "q":
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(instances):
                return str(instances[idx].instance_id)
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return None


def monitor_global_status(session: Session, instance_id: str):
    """Display global status metrics for the instance."""
    clear_screen()
    print_header("🦎 Monitor Global Status")

    # Get instance details
    instance = (
        session.query(Instance_Context).filter(Instance_Context.instance_id == instance_id).first()
    )

    if not instance:
        print("❌ Instance not found.")
        return

    print(f"Instance: {instance.name}")
    print(f"Status: {instance.status}")
    print(
        f"Deployed: {instance.deployment_date.strftime('%Y-%m-%d %H:%M:%S') if instance.deployment_date else 'N/A'}"
    )
    print(f"ID: {instance_id}\n")

    # Calculate metrics
    metrics = {
        "active": 0,
        "pending": 0,
        "completed": 0,
        "failed": 0,
        "zombies": 0,
    }

    # Count UOWs by status
    status_counts = (
        session.query(UnitsOfWork.status, func.count(UnitsOfWork.uow_id))
        .filter(UnitsOfWork.instance_id == instance_id)
        .group_by(UnitsOfWork.status)
        .all()
    )

    for status, count in status_counts:
        if status == UOWStatus.ACTIVE.value:
            metrics["active"] = count
        elif status == UOWStatus.PENDING.value:
            metrics["pending"] = count
        elif status == UOWStatus.COMPLETED.value:
            metrics["completed"] = count
        elif status == UOWStatus.FAILED.value:
            metrics["failed"] = count

    # Detect zombies: ACTIVE UOWs with stale heartbeat (>5 minutes)
    zombie_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    zombies = (
        session.query(func.count(UnitsOfWork.uow_id))
        .filter(
            UnitsOfWork.instance_id == instance_id,
            UnitsOfWork.status == UOWStatus.ACTIVE.value,
            UnitsOfWork.last_heartbeat.isnot(None),
            UnitsOfWork.last_heartbeat < zombie_threshold,
        )
        .scalar()
    )
    metrics["zombies"] = zombies or 0

    # Display metrics
    print("📊 Key Metrics:")
    print("-" * 80)
    print(f"  🔄 Active UOWs:      {metrics['active']}")
    print(f"  ⏳ Pending UOWs:     {metrics['pending']}")
    print(f"  ✅ Completed UOWs:   {metrics['completed']}")
    print(f"  ❌ Failed UOWs:      {metrics['failed']}")
    print(f"  🧟 Zombie UOWs:      {metrics['zombies']} (stale heartbeat)")
    print("-" * 80)

    # Additional details: Active work
    active_work = (
        session.query(
            UnitsOfWork.uow_id,
            Local_Interactions.name.label("interaction_name"),
            Local_Workflows.name.label("workflow_name"),
        )
        .join(
            Local_Interactions,
            UnitsOfWork.current_interaction_id == Local_Interactions.interaction_id,
        )
        .join(
            Local_Workflows,
            UnitsOfWork.local_workflow_id == Local_Workflows.local_workflow_id,
        )
        .filter(
            UnitsOfWork.instance_id == instance_id,
            UnitsOfWork.status == UOWStatus.ACTIVE.value,
        )
        .limit(10)
        .all()
    )

    if active_work:
        print("\n🔨 Active Work (Top 10):")
        headers = ["UOW ID", "Workflow", "Interaction"]
        rows = [
            [str(uow.uow_id)[:8] + "...", uow.workflow_name, uow.interaction_name]
            for uow in active_work
        ]
        print_table(headers, rows)


def inspect_roles(session: Session, instance_id: str):
    """Display all roles with their work counts."""
    clear_screen()
    print_header("👥 Inspect Roles")

    # Query: Get all Local_Roles and count their inbound work using a single query
    # Join path: Local_Roles -> Local_Components (INBOUND) -> Local_Interactions -> UnitsOfWork
    # Using LEFT OUTER JOIN and GROUP BY to handle roles with zero work count

    roles_with_counts = (
        session.query(
            Local_Roles.name,
            Local_Roles.role_type,
            Local_Roles.role_id,
            func.count(UnitsOfWork.uow_id).label("work_count"),
        )
        .join(Local_Workflows, Local_Roles.local_workflow_id == Local_Workflows.local_workflow_id)
        .outerjoin(
            Local_Components,
            (Local_Components.role_id == Local_Roles.role_id)
            & (Local_Components.direction == ComponentDirection.INBOUND.value),
        )
        .outerjoin(
            Local_Interactions,
            Local_Components.interaction_id == Local_Interactions.interaction_id,
        )
        .outerjoin(
            UnitsOfWork,
            (UnitsOfWork.current_interaction_id == Local_Interactions.interaction_id)
            & (UnitsOfWork.instance_id == instance_id)
            & (UnitsOfWork.status == UOWStatus.PENDING.value),
        )
        .filter(Local_Workflows.instance_id == instance_id)
        .group_by(Local_Roles.role_id, Local_Roles.name, Local_Roles.role_type)
        .all()
    )

    if not roles_with_counts:
        print("No roles found for this instance.")
        return

    # Prepare data for display
    role_data = [
        [role.name, role.role_type, str(role.role_id)[:8] + "...", role.work_count]
        for role in roles_with_counts
    ]

    # Sort by work count descending
    role_data.sort(key=lambda x: x[3], reverse=True)

    print(f"\nTotal Roles: {len(role_data)}\n")

    headers = ["Role Name", "Role Type", "Role ID", "Work Count"]
    print_table(headers, role_data)


def inspect_interactions(session: Session, instance_id: str):
    """Display all interactions with their work counts."""
    clear_screen()
    print_header("🔗 Inspect Interactions")

    # Query: Get all Local_Interactions and count their UOWs
    interactions_query = (
        session.query(
            Local_Interactions.name,
            Local_Interactions.interaction_id,
            func.count(UnitsOfWork.uow_id).label("work_count"),
        )
        .join(
            Local_Workflows,
            Local_Interactions.local_workflow_id == Local_Workflows.local_workflow_id,
        )
        .outerjoin(
            UnitsOfWork, Local_Interactions.interaction_id == UnitsOfWork.current_interaction_id
        )
        .filter(Local_Workflows.instance_id == instance_id)
        .group_by(Local_Interactions.name, Local_Interactions.interaction_id)
        .all()
    )

    if not interactions_query:
        print("No interactions found for this instance.")
        return

    # Prepare data for display
    interaction_data = [
        [interaction.name, str(interaction.interaction_id)[:8] + "...", interaction.work_count]
        for interaction in interactions_query
    ]

    # Sort by work count descending
    interaction_data.sort(key=lambda x: x[2], reverse=True)

    print(f"\nTotal Interactions: {len(interaction_data)}\n")

    headers = ["Interaction Name", "Interaction ID", "Work Count"]
    print_table(headers, interaction_data)


def show_menu():
    """Display the main menu and return user choice."""
    print("\n" + "=" * 80)
    print("  🦎 Chameleon Workflow Monitor - Main Menu")
    print("=" * 80)
    print("\n1. Monitor Global Status")
    print("2. Inspect Roles")
    print("3. Inspect Interactions")
    print("4. Exit")
    print("\n" + "-" * 80)

    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            if choice in ["1", "2", "3", "4"]:
                return choice
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return "4"


def main():
    """Main application entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Chameleon Workflow Monitor - Interactive CLI")
    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:///chameleon_instance.db",
        help="Database connection URL (default: sqlite:///chameleon_instance.db)",
    )
    args = parser.parse_args()

    # Initialize database manager
    try:
        db_manager = DatabaseManager(instance_url=args.db_url)
        # Ensure the schema exists
        try:
            db_manager.create_instance_schema()
        except Exception as schema_error:
            # Schema likely already exists, log and continue
            # In production, you might want to check for specific exceptions like
            # sqlalchemy.exc.OperationalError for table already exists
            import logging

            logging.debug(f"Schema creation skipped: {schema_error}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print(f"Connection string: {args.db_url}")
        sys.exit(1)

    # Welcome message
    clear_screen()
    print_header("🦎 Chameleon Workflow Monitor")
    print(f"Database: {args.db_url}")

    if not TABULATE_AVAILABLE:
        print("\n⚠️  Note: 'tabulate' package not found. Using basic table formatting.")
        print("    Install with: pip install tabulate")

    # Select instance
    with db_manager.get_instance_session() as session:
        instance_id = select_instance(session)

        if not instance_id:
            print("\nExiting...")
            sys.exit(0)

    # Main menu loop
    while True:
        choice = show_menu()

        if choice == "1":
            with db_manager.get_instance_session() as session:
                monitor_global_status(session, instance_id)
            input("\nPress Enter to continue...")

        elif choice == "2":
            with db_manager.get_instance_session() as session:
                inspect_roles(session, instance_id)
            input("\nPress Enter to continue...")

        elif choice == "3":
            with db_manager.get_instance_session() as session:
                inspect_interactions(session, instance_id)
            input("\nPress Enter to continue...")

        elif choice == "4":
            clear_screen()
            print("\n👋 Thank you for using Chameleon Workflow Monitor!")
            print("Goodbye!\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
        sys.exit(0)
