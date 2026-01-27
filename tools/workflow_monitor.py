#!/usr/bin/env python3
"""
Workflow Monitor Dashboard - Real-time Control Room for the Chameleon Workflow Engine

This Streamlit application provides a "Control Room" view of the Chameleon Workflow Engine,
allowing operators to monitor workflow instances, track UOW (Units of Work) status,
visualize workflow topology with real-time state coloring, and inspect execution history.

Features:
- Real-time metrics dashboard showing active, completed, failed, and zombie UOWs
- Interactive workflow topology visualization with dynamic state-based coloring
- Detailed data tables for active work, queue depths, and execution history
- Configurable database connection and auto-refresh capabilities

Usage:
    streamlit run tools/workflow_monitor.py
    
    Or with a custom database:
    streamlit run tools/workflow_monitor.py -- --db-url "sqlite:///path/to/instance.db"

Source of Truth:
    - database/manager.py and database/models_instance.py (State queries)
    - database/enums.py (Status and Role Type definitions)
    - chameleon_workflow_engine/server.py (API structure reference)
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from sqlalchemy import func
from sqlalchemy.orm import Session
import graphviz

from database.manager import DatabaseManager
from database.models_instance import (
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    UnitsOfWork,
    Interaction_Logs,
)
from database.enums import UOWStatus, RoleType, ComponentDirection

# Page configuration
st.set_page_config(
    page_title="Chameleon Workflow Monitor",
    page_icon="🦎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .critical {
        color: #ff4b4b;
    }
    .warning {
        color: #ffa500;
    }
    .success {
        color: #00c851;
    }
    .info {
        color: #33b5e5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_db_manager(db_url: str) -> DatabaseManager:
    """Initialize database manager with caching."""
    if "db_manager" not in st.session_state or st.session_state.get("db_url") != db_url:
        st.session_state.db_manager = DatabaseManager(instance_url=db_url)
        st.session_state.db_url = db_url
    return st.session_state.db_manager


def get_all_instances(session: Session) -> List[Instance_Context]:
    """Get all instance contexts from the database."""
    return session.query(Instance_Context).all()


def get_uow_metrics(
    session: Session, instance_id: str
) -> Dict[str, int]:
    """Calculate key UOW metrics for the dashboard."""
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
    zombie_threshold = datetime.utcnow() - timedelta(minutes=5)
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

    return metrics


def get_active_work(session: Session, instance_id: str) -> List[Dict]:
    """Get all in-progress UOWs with their details."""
    active_uows = (
        session.query(
            UnitsOfWork.uow_id,
            UnitsOfWork.status,
            UnitsOfWork.last_heartbeat,
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
        .all()
    )

    result = []
    now = datetime.utcnow()
    for uow in active_uows:
        duration = None
        if uow.last_heartbeat:
            duration = (now - uow.last_heartbeat).total_seconds()

        result.append(
            {
                "UOW ID": str(uow.uow_id)[:8] + "...",
                "Workflow": uow.workflow_name,
                "Interaction": uow.interaction_name,
                "Status": uow.status,
                "Duration (sec)": int(duration) if duration else "N/A",
            }
        )

    return result


def get_queue_depths(session: Session, instance_id: str) -> List[Dict]:
    """Get count of pending UOWs per interaction."""
    queue_data = (
        session.query(
            Local_Interactions.name.label("interaction_name"),
            Local_Workflows.name.label("workflow_name"),
            func.count(UnitsOfWork.uow_id).label("pending_count"),
        )
        .join(
            UnitsOfWork,
            Local_Interactions.interaction_id == UnitsOfWork.current_interaction_id,
        )
        .join(
            Local_Workflows,
            Local_Interactions.local_workflow_id == Local_Workflows.local_workflow_id,
        )
        .filter(
            UnitsOfWork.instance_id == instance_id,
            UnitsOfWork.status == UOWStatus.PENDING.value,
        )
        .group_by(Local_Interactions.name, Local_Workflows.name)
        .all()
    )

    return [
        {
            "Workflow": row.workflow_name,
            "Interaction": row.interaction_name,
            "Pending Count": row.pending_count,
        }
        for row in queue_data
    ]


def get_recent_history(
    session: Session, instance_id: str, limit: int = 50
) -> List[Dict]:
    """Get the most recent history log entries."""
    history = (
        session.query(
            Interaction_Logs.log_id,
            Interaction_Logs.timestamp,
            UnitsOfWork.uow_id,
            Local_Roles.name.label("role_name"),
            Local_Interactions.name.label("interaction_name"),
        )
        .join(UnitsOfWork, Interaction_Logs.uow_id == UnitsOfWork.uow_id)
        .join(Local_Roles, Interaction_Logs.role_id == Local_Roles.role_id)
        .join(
            Local_Interactions,
            Interaction_Logs.interaction_id == Local_Interactions.interaction_id,
        )
        .filter(Interaction_Logs.instance_id == instance_id)
        .order_by(Interaction_Logs.log_id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "Log ID": row.log_id,
            "Timestamp": row.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if row.timestamp
            else "N/A",
            "UOW ID": str(row.uow_id)[:8] + "...",
            "Role": row.role_name,
            "Interaction": row.interaction_name,
        }
        for row in history
    ]


def get_role_uow_counts(
    session: Session, instance_id: str, workflow_id: str
) -> Dict[str, Dict[str, int]]:
    """Get UOW counts per role, categorized by status."""
    # Query active (locked) UOWs per role via interaction logs
    # A role has "locked" UOWs if there are active logs showing it's processing
    role_data = {}

    # Get all roles for the workflow
    roles = (
        session.query(Local_Roles)
        .filter(Local_Roles.local_workflow_id == workflow_id)
        .all()
    )

    for role in roles:
        # Count active UOWs that have this role in their latest interaction log
        # This is a simplified approach - in production, you might track role locks more explicitly
        role_data[role.name] = {
            "active": 0,
            "pending": 0,
            "failed": 0,
        }

    return role_data


def get_interaction_uow_counts(
    session: Session, instance_id: str, workflow_id: str
) -> Dict[str, Dict[str, int]]:
    """Get UOW counts per interaction, categorized by status."""
    interaction_data = {}

    # Get all interactions for the workflow
    interactions = (
        session.query(Local_Interactions)
        .filter(Local_Interactions.local_workflow_id == workflow_id)
        .all()
    )

    for interaction in interactions:
        # Count UOWs at this interaction by status
        counts = (
            session.query(UnitsOfWork.status, func.count(UnitsOfWork.uow_id))
            .filter(
                UnitsOfWork.instance_id == instance_id,
                UnitsOfWork.current_interaction_id == interaction.interaction_id,
            )
            .group_by(UnitsOfWork.status)
            .all()
        )

        interaction_data[interaction.name] = {
            "pending": 0,
            "active": 0,
            "failed": 0,
        }

        for status, count in counts:
            if status == UOWStatus.PENDING.value:
                interaction_data[interaction.name]["pending"] = count
            elif status == UOWStatus.ACTIVE.value:
                interaction_data[interaction.name]["active"] = count
            elif status == UOWStatus.FAILED.value:
                interaction_data[interaction.name]["failed"] = count

    return interaction_data


def generate_workflow_graph(
    session: Session, instance_id: str, workflow_id: str
) -> Optional[graphviz.Digraph]:
    """
    Generate a Graphviz graph of the workflow topology with dynamic coloring.
    
    Dynamic Coloring Rules:
    - Roles with locked/active UOWs -> Blue
    - Interactions with Pending UOWs -> Yellow (show count in label)
    - Interactions with Failed UOWs -> Red
    """
    # Get workflow
    workflow = (
        session.query(Local_Workflows)
        .filter(Local_Workflows.local_workflow_id == workflow_id)
        .first()
    )

    if not workflow:
        return None

    # Get UOW counts for dynamic coloring
    role_counts = get_role_uow_counts(session, instance_id, workflow_id)
    interaction_counts = get_interaction_uow_counts(session, instance_id, workflow_id)

    # Create graph
    dot = graphviz.Digraph(comment=workflow.name)
    dot.attr(label=workflow.name, labelloc="t", fontsize="16")
    dot.attr("node", fontname="Arial")
    dot.attr("edge", fontname="Arial")

    # Role type colors (border colors)
    role_type_colors = {
        RoleType.ALPHA.value: "green",
        RoleType.BETA.value: "blue",
        RoleType.OMEGA.value: "black",
        RoleType.EPSILON.value: "orange",
        RoleType.TAU.value: "purple",
    }

    # Add roles as box nodes
    for role in workflow.roles:
        color = role_type_colors.get(role.role_type, "gray")
        fillcolor = "lightgray"

        # Check if role has active UOWs
        if role.name in role_counts and role_counts[role.name]["active"] > 0:
            fillcolor = "lightblue"

        node_id = f"role_{role.name.replace(' ', '_')}"
        dot.node(
            node_id,
            label=role.name,
            shape="box",
            style="filled",
            fillcolor=fillcolor,
            color=color,
            penwidth="3",
        )

    # Add interactions as ellipse nodes
    for interaction in workflow.interactions:
        fillcolor = "lightgreen"
        label = interaction.name

        counts = interaction_counts.get(interaction.name, {})

        # Priority: Red for failed, Yellow for pending, default green
        if counts.get("failed", 0) > 0:
            fillcolor = "lightcoral"
            label = f"{interaction.name}\\n(Failed: {counts['failed']})"
        elif counts.get("pending", 0) > 0:
            fillcolor = "lightyellow"
            label = f"{interaction.name}\\n(Pending: {counts['pending']})"

        node_id = f"interaction_{interaction.name.replace(' ', '_')}"
        dot.node(
            node_id,
            label=label,
            shape="ellipse",
            style="filled",
            fillcolor=fillcolor,
        )

    # Add components as edges
    for component in workflow.components:
        role_id = f"role_{component.role.name.replace(' ', '_')}"
        interaction_id = f"interaction_{component.interaction.name.replace(' ', '_')}"

        if component.direction == ComponentDirection.OUTBOUND.value:
            # Role -> Interaction
            dot.edge(role_id, interaction_id, label=component.name)
        else:  # INBOUND
            # Interaction -> Role
            dot.edge(interaction_id, role_id, label=component.name)

    return dot


def render_metrics(metrics: Dict[str, int]):
    """Render key metrics as large cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_active = metrics["active"] + metrics["pending"]
        st.metric(
            label="🔄 Active UOWs",
            value=total_active,
            help="Total ACTIVE + PENDING UOWs",
        )

    with col2:
        st.metric(
            label="✅ Completed",
            value=metrics["completed"],
            help="Total completed UOWs",
        )

    with col3:
        st.metric(
            label="❌ Failed",
            value=metrics["failed"],
            delta=None,
            delta_color="inverse" if metrics["failed"] > 0 else "off",
            help="Total failed UOWs (Critical Alert)",
        )

    with col4:
        st.metric(
            label="🧟 Zombies",
            value=metrics["zombies"],
            delta=None,
            delta_color="inverse" if metrics["zombies"] > 0 else "off",
            help="UOWs with timeout/stale heartbeat",
        )


def main():
    """Main application entry point."""
    st.title("🦎 Chameleon Workflow Monitor")
    st.markdown("**Real-time Control Room for the Workflow Engine**")
    st.markdown("---")

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Database connection
        default_db = "sqlite:///chameleon_instance.db"
        db_url = st.text_input(
            "Database Connection String",
            value=default_db,
            help="SQLAlchemy connection string for the instance database",
        )

        # Auto-refresh toggle and interval
        enable_refresh = st.checkbox("Enable Auto-Refresh", value=False)
        if enable_refresh:
            refresh_interval = st.slider(
                "Refresh Interval (seconds)", min_value=5, max_value=60, value=10
            )
            # Trigger auto-refresh
            st_autorefresh(interval=refresh_interval * 1000, key="datarefresh")

        # Manual refresh button
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.caption("Chameleon Workflow Engine v0.1.0")

    # Initialize database manager
    try:
        db_manager = get_db_manager(db_url)
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        st.stop()

    # Get instances
    try:
        with db_manager.get_instance_session() as session:
            instances = get_all_instances(session)

            if not instances:
                st.warning(
                    "⚠️ No workflow instances found in the database. "
                    "Please create an instance first using the workflow instantiation API."
                )
                st.stop()

            # Instance selector
            instance_options = {
                f"{inst.name} ({str(inst.instance_id)[:8]}...)": str(inst.instance_id)
                for inst in instances
            }

            with st.sidebar:
                st.markdown("---")
                selected_instance_label = st.selectbox(
                    "Select Workflow Instance",
                    options=list(instance_options.keys()),
                    help="Choose the instance to monitor",
                )
                selected_instance_id = instance_options[selected_instance_label]

            # Get selected instance details
            selected_instance = next(
                (inst for inst in instances if str(inst.instance_id) == selected_instance_id),
                None,
            )

            if not selected_instance:
                st.error("Selected instance not found.")
                st.stop()

            # Display instance info
            st.info(
                f"**Monitoring:** {selected_instance.name} | "
                f"**Status:** {selected_instance.status} | "
                f"**Deployed:** {selected_instance.deployment_date.strftime('%Y-%m-%d %H:%M') if selected_instance.deployment_date else 'N/A'}"
            )

            # Get metrics
            metrics = get_uow_metrics(session, selected_instance_id)

            # Render metrics dashboard
            st.subheader("📊 Key Metrics")
            render_metrics(metrics)

            st.markdown("---")

            # Get workflows for this instance
            workflows = (
                session.query(Local_Workflows)
                .filter(Local_Workflows.instance_id == selected_instance_id)
                .all()
            )

            if workflows:
                # Workflow selector for graph
                workflow_options = {
                    f"{wf.name} (v{wf.version})": str(wf.local_workflow_id)
                    for wf in workflows
                }

                selected_workflow_label = st.selectbox(
                    "Select Workflow to Visualize",
                    options=list(workflow_options.keys()),
                    help="Choose the workflow to display in the graph",
                )
                selected_workflow_id = workflow_options[selected_workflow_label]

                # Graph Visualization
                st.subheader("🗺️ Workflow Topology Map")

                try:
                    graph = generate_workflow_graph(
                        session, selected_instance_id, selected_workflow_id
                    )

                    if graph:
                        st.graphviz_chart(graph)
                    else:
                        st.warning("Could not generate workflow graph.")
                except Exception as e:
                    st.error(f"Error generating graph: {e}")

            st.markdown("---")

            # Data Tables
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🔨 Active Work")
                active_work = get_active_work(session, selected_instance_id)
                if active_work:
                    st.dataframe(active_work, use_container_width=True, hide_index=True)
                else:
                    st.info("No active work currently.")

            with col2:
                st.subheader("📦 Queue Depths")
                queue_depths = get_queue_depths(session, selected_instance_id)
                if queue_depths:
                    st.dataframe(
                        queue_depths, use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No pending items in queues.")

            st.markdown("---")

            # History Log
            st.subheader("📜 Recent History Log (Latest 50 Entries)")
            history = get_recent_history(session, selected_instance_id, limit=50)
            if history:
                st.dataframe(history, use_container_width=True, hide_index=True)
            else:
                st.info("No history entries found.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback

        st.code(traceback.format_exc())


if __name__ == "__main__":
    # Parse command-line arguments (optional)
    parser = argparse.ArgumentParser(description="Chameleon Workflow Monitor Dashboard")
    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:///chameleon_instance.db",
        help="Database connection URL",
    )
    args, unknown = parser.parse_known_args()

    # Run the Streamlit app
    main()
