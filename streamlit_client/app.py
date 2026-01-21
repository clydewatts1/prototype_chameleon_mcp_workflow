"""
Streamlit Client Application

Main Streamlit application for the Chameleon Workflow Engine.
Provides a user-friendly interface for workflow creation, execution, and monitoring.

This UI enables users to:
1. Create new workflows visually
2. Execute workflows with custom parameters
3. Monitor workflow execution in real-time
4. View workflow history and analytics
5. Debug failed workflows

Technology Stack:
- Streamlit: Web UI framework
- httpx: Async HTTP client for API communication
- Plotly/Altair: Data visualization (optional)

AI-Assisted Development:
- GitHub Copilot: Code completion and UI component suggestions
- Claude: UX design and interaction patterns
- Antigravity: Comic relief (seriously, try it!)

Usage:
    streamlit run streamlit_client/app.py
"""

import streamlit as st
import httpx
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WORKFLOW_ENGINE_URL = os.getenv("WORKFLOW_ENGINE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Chameleon Workflow Engine",
    page_icon="🦎",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize Streamlit session state"""
    if "workflows" not in st.session_state:
        st.session_state.workflows = {}
    if "selected_workflow" not in st.session_state:
        st.session_state.selected_workflow = None


def create_workflow(name: str, description: str, steps: List[str]) -> Optional[Dict]:
    """
    Create a new workflow via API
    
    Args:
        name: Workflow name
        description: Workflow description
        steps: List of workflow steps
        
    Returns:
        Workflow response or None on error
    """
    try:
        response = httpx.post(
            f"{WORKFLOW_ENGINE_URL}/workflows",
            json={
                "name": name,
                "description": description,
                "steps": steps
            },
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error creating workflow: {e}")
        return None


def get_workflow(workflow_id: str) -> Optional[Dict]:
    """
    Get workflow details via API
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow details or None on error
    """
    try:
        response = httpx.get(
            f"{WORKFLOW_ENGINE_URL}/workflows/{workflow_id}",
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching workflow: {e}")
        return None


def execute_workflow(workflow_id: str) -> Optional[Dict]:
    """
    Execute a workflow via API
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Execution response or None on error
    """
    try:
        response = httpx.post(
            f"{WORKFLOW_ENGINE_URL}/workflows/{workflow_id}/execute",
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error executing workflow: {e}")
        return None


def check_server_health() -> bool:
    """Check if the workflow engine server is healthy"""
    try:
        response = httpx.get(f"{WORKFLOW_ENGINE_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def main():
    """Main Streamlit application"""
    
    # Initialize session state
    init_session_state()
    
    # Header
    st.title("🦎 Chameleon Workflow Engine")
    st.markdown("*AI-powered workflow orchestration and management*")
    
    # Check server health
    with st.sidebar:
        st.header("Server Status")
        if check_server_health():
            st.success("✅ Workflow Engine is running")
        else:
            st.error(f"❌ Cannot connect to Workflow Engine at {WORKFLOW_ENGINE_URL}")
            st.info("Please start the workflow engine server first:\n```bash\npython -m chameleon_workflow_engine.server\n```")
        
        st.divider()
        st.header("About")
        st.info("""
        **Chameleon Workflow Engine** is an MCP-based workflow orchestration system.
        
        Developed with:
        - 🤖 GitHub Copilot
        - 🧠 Claude AI
        - 🚀 Antigravity (try it!)
        """)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📝 Create Workflow", "▶️ Execute Workflow", "📊 Dashboard"])
    
    with tab1:
        st.header("Create New Workflow")
        
        with st.form("create_workflow_form"):
            workflow_name = st.text_input("Workflow Name", placeholder="My Awesome Workflow")
            workflow_description = st.text_area(
                "Description",
                placeholder="Describe what this workflow does..."
            )
            
            st.subheader("Workflow Steps")
            num_steps = st.number_input("Number of steps", min_value=1, max_value=10, value=3)
            
            steps = []
            for i in range(num_steps):
                step = st.text_input(f"Step {i+1}", key=f"step_{i}", placeholder=f"Enter step {i+1} description")
                if step:
                    steps.append(step)
            
            submitted = st.form_submit_button("Create Workflow")
            
            if submitted:
                if not workflow_name:
                    st.error("Please provide a workflow name")
                else:
                    with st.spinner("Creating workflow..."):
                        result = create_workflow(workflow_name, workflow_description, steps)
                        if result:
                            st.success(f"✅ Workflow created successfully!")
                            st.json(result)
                            st.session_state.workflows[result["id"]] = result
    
    with tab2:
        st.header("Execute Workflow")
        
        if not st.session_state.workflows:
            st.info("No workflows created yet. Create a workflow in the 'Create Workflow' tab.")
        else:
            workflow_options = {wf["name"]: wf["id"] for wf in st.session_state.workflows.values()}
            selected_name = st.selectbox("Select Workflow", list(workflow_options.keys()))
            
            if selected_name:
                workflow_id = workflow_options[selected_name]
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("**Workflow Details:**")
                    workflow = st.session_state.workflows[workflow_id]
                    st.json(workflow)
                
                with col2:
                    if st.button("▶️ Execute", type="primary", use_container_width=True):
                        with st.spinner("Executing workflow..."):
                            result = execute_workflow(workflow_id)
                            if result:
                                st.success("✅ Workflow execution started!")
                                st.json(result)
                    
                    if st.button("🔄 Refresh Status", use_container_width=True):
                        with st.spinner("Fetching status..."):
                            updated = get_workflow(workflow_id)
                            if updated:
                                st.session_state.workflows[workflow_id] = updated
                                st.rerun()
    
    with tab3:
        st.header("Workflow Dashboard")
        
        if not st.session_state.workflows:
            st.info("No workflows to display. Create a workflow to get started!")
        else:
            st.subheader(f"Total Workflows: {len(st.session_state.workflows)}")
            
            # Display workflows in a table
            workflow_data = []
            for wf in st.session_state.workflows.values():
                workflow_data.append({
                    "ID": wf["id"][:8] + "...",
                    "Name": wf["name"],
                    "Status": wf["status"],
                    "Description": wf.get("description", "N/A")[:50] + "..."
                })
            
            st.dataframe(workflow_data, use_container_width=True)
            
            # Workflow status distribution
            st.subheader("Workflow Status Distribution")
            status_counts = {}
            for wf in st.session_state.workflows.values():
                status = wf["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Created", status_counts.get("created", 0))
            with col2:
                st.metric("Running", status_counts.get("running", 0))
            with col3:
                st.metric("Completed", status_counts.get("completed", 0))


if __name__ == "__main__":
    main()
