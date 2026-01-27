# 🦎 Chameleon Workflow Engine - User Guide

## Table of Contents
1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Defining a Workflow](#3-defining-a-workflow-the-yaml)
4. [Using the Engine](#4-using-the-engine-the-api)
5. [Governance & Admin](#5-governance--admin)
6. [Writing an Agent](#6-writing-an-agent-client-example)

---

## 1. Introduction

### What is Chameleon?

The **Chameleon Workflow Engine** is a **Constitutional, Adaptive Workflow Engine** designed for orchestrating AI agents and human actors in complex, multi-stage workflows. Unlike traditional workflow engines that rely on rigid state machines, Chameleon provides:

- **Total Isolation**: Every execution occurs in a strictly isolated sandbox, preventing cross-contamination between tasks
- **Constitutional Governance**: All workflow behavior is governed by a formal "constitution" (see `docs/architecture/Workflow_Constitution.md`)
- **Adaptive Learning**: The engine learns from past executions, building a "Global Blueprint" and "Personal Playbooks" for continuous improvement
- **Fault Resilience**: Built-in error handling through specialized roles (Epsilon, Tau) that manage failures and timeouts

### Why is Chameleon Different?

**1. Role-Based Architecture**

Chameleon uses five specialized role types to define workflow topology:

- **Alpha (α)**: The Origin - creates the initial Unit of Work (UOW)
- **Beta (β)**: The Processor - decomposes work and performs tasks
- **Omega (Ω)**: The Terminal - reconciles and finalizes completed work
- **Epsilon (ε)**: The Physician - handles data errors and remediation
- **Tau (τ)**: The Chronometer - manages timeouts and stale tokens

**2. Atomic Versioning**

Every modification to a Unit of Work is tracked through atomic versioning. Changes are never overwritten - they're appended to a versioned lineage, ensuring complete traceability and the ability to understand "why" decisions were made.

**3. Zombie Protection**

The **Zombie Actor Protocol** ensures that work never gets permanently stuck. If an actor fails or crashes, the Tau role automatically reclaims stalled work and routes it for remediation.

**4. Memory Hierarchy**

Chameleon maintains three levels of memory:
- **Ephemeral Memory**: Transaction-scoped attributes (non-persistent)
- **Personal Playbook**: Actor-specific learnings and preferences
- **Global Blueprint**: Role-wide shared knowledge and best practices

---

## 2. Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.9 or higher** installed
- **pip** (Python package installer)
- **SQLite** (included with Python) or **PostgreSQL** for production
- A virtual environment tool (`venv`, `conda`, etc.)

### Installation

**1. Clone the Repository**

```bash
git clone https://github.com/clydewatts1/prototype_chameleon_mcp_workflow.git
cd prototype_chameleon_mcp_workflow
```

**2. Create and Activate a Virtual Environment**

```bash
# Using venv
python -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

**3. Install Dependencies**

```bash
# Install all required packages
pip install -r requirements.txt

# Or install in development mode with optional dev tools
pip install -e ".[dev]"
```

**4. Configure Environment Variables**

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

Key environment variables:
- `TEMPLATE_DB_URL`: Database URL for workflow templates (default: `sqlite:///template.db`)
- `INSTANCE_DB_URL`: Database URL for runtime instances (default: `sqlite:///instance.db`)
- `WORKFLOW_ENGINE_HOST`: Server host (default: `0.0.0.0`)
- `WORKFLOW_ENGINE_PORT`: Server port (default: `8000`)

**5. Verify Your Setup**

```bash
python verify_setup.py
```

This checks that all dependencies are installed correctly and the project structure is valid.

### Running the Server

Start the Chameleon Workflow Engine server:

```bash
# Using Python module syntax
python -m chameleon_workflow_engine.server

# Or with uvicorn directly
uvicorn chameleon_workflow_engine.server:app --reload --port 8000
```

The API will be available at:
- Base URL: `http://localhost:8000`
- Interactive API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## 3. Defining a Workflow (The YAML)

Workflows in Chameleon are defined using YAML files. This section explains the structure and provides examples.

### Workflow Structure

A Chameleon workflow YAML file has five main sections:

```yaml
workflow:           # Workflow metadata
roles:              # Functional agents (Alpha, Beta, Omega, Epsilon, Tau)
interactions:       # Queues/holding areas between roles
components:         # Directional connections (INBOUND/OUTBOUND)
guardians:          # Logic gates that control flow
```

### Minimal "Hello World" Example

Here's a minimal workflow that creates a task, processes it, and completes it:

```yaml
workflow:
  name: "Hello_World_Workflow"
  description: "A simple workflow demonstrating the basic flow"
  version: 1
  ai_context:
    purpose: "Process a simple greeting task"
  schema_json:
    topology: "linear"

roles:
  - name: "Task_Creator"
    role_type: "ALPHA"
    description: "Creates the initial greeting task"
    ai_context:
      persona: "You are a task initiator"
      instructions: "Create a greeting task with a message"

  - name: "Greeter"
    role_type: "BETA"
    strategy: "HOMOGENEOUS"
    description: "Processes the greeting"
    ai_context:
      persona: "You are a friendly greeter"
      instructions: "Add a personalized greeting to the message"

  - name: "Task_Finalizer"
    role_type: "OMEGA"
    description: "Finalizes the greeting task"
    ai_context:
      persona: "You are a task finalizer"
      instructions: "Mark the greeting task as complete"

interactions:
  - name: "Greeting_Queue"
    description: "Queue for pending greetings"
    ai_context:
      purpose: "Holds greetings awaiting processing"

  - name: "Completed_Queue"
    description: "Queue for completed greetings"
    ai_context:
      purpose: "Holds finished greeting tasks"

components:
  - name: "Creator_To_Queue"
    role_name: "Task_Creator"
    interaction_name: "Greeting_Queue"
    direction: "OUTBOUND"
    description: "Route new tasks to greeting queue"

  - name: "Greeter_From_Queue"
    role_name: "Greeter"
    interaction_name: "Greeting_Queue"
    direction: "INBOUND"
    description: "Greeter pulls tasks from queue"

  - name: "Greeter_To_Complete"
    role_name: "Greeter"
    interaction_name: "Completed_Queue"
    direction: "OUTBOUND"
    description: "Route processed greetings to completion"

  - name: "Finalizer_From_Complete"
    role_name: "Task_Finalizer"
    interaction_name: "Completed_Queue"
    direction: "INBOUND"
    description: "Finalizer pulls from completed queue"

guardians:
  - name: "Simple_Pass_Guard"
    component_name: "Greeter_From_Queue"
    type: "PASS_THRU"
    description: "Allow all greetings through"
    config:
      validation: "basic"
```

### Understanding Guard Types

Guards control the flow of Units of Work between roles. Chameleon supports several guard types:

#### 1. PASS_THRU (The Fast Lane)

The simplest guard - performs only identity validation, no data checks.

```yaml
guardians:
  - name: "Quick_Entry_Guard"
    component_name: "Alpha_To_First_Queue"
    type: "PASS_THRU"
    description: "Rapid initialization with no validation"
    config:
      validation: "identity_only"
```

**Use Case**: Connecting Alpha to the first Beta, or trusted internal steps.

#### 2. CRITERIA_GATE (The Filter)

Enforces business logic thresholds to determine eligibility.

```yaml
guardians:
  - name: "High_Value_Guard"
    component_name: "Validator_To_Senior"
    type: "CRITERIA_GATE"
    description: "Route high-value items to senior review"
    config:
      criteria: "amount > 10000"
      field: "transaction_total"
      threshold: 10000
      operator: "GT"
```

**Use Case**: Routing based on monetary amounts, priority levels, or other thresholds.

#### 3. DIRECTIONAL_FILTER (The Router)

Routes UOWs to different interactions based on an attribute value.

```yaml
guardians:
  - name: "Priority_Router"
    component_name: "Triage_Output"
    type: "DIRECTIONAL_FILTER"
    description: "Route based on priority classification"
    config:
      routing_key: "priority"
      routes:
        urgent: "queue_fast_track"
        standard: "queue_normal"
        low: "queue_batch"
```

**Use Case**: Triaging tasks into different processing lanes.

#### 4. TTL_CHECK (Time-To-Live)

Validates UOW age and routes expired items to timeout handling.

```yaml
guardians:
  - name: "Staleness_Check"
    component_name: "Processing_Queue_Exit"
    type: "TTL_CHECK"
    description: "Check for stale tasks"
    config:
      max_age_seconds: 3600
      field: "created_at"
```

**Use Case**: Ensuring tasks don't linger too long in a queue.

#### 5. CERBERUS (The Synchronizer)

The three-headed guard that ensures all child UOWs are complete before allowing parent reconciliation.

```yaml
guardians:
  - name: "Reconciliation_Gate"
    component_name: "Omega_Inbound"
    type: "CERBERUS"
    description: "Ensure all child tasks complete"
    config:
      wait_for_children: true
      min_children: 1
      sync_strategy: "all_complete"
```

**Use Case**: Preventing "zombie parents" from reaching Omega before their children finish.

For a complete example workflow with all role types and guard configurations, see `tools/complete_workflow_example.yaml`.

### Loading and Exporting Workflows

**Import a workflow from YAML:**

```bash
python tools/workflow_manager.py -l -f my_workflow.yml
```

**Export a workflow to YAML:**

```bash
python tools/workflow_manager.py -w "My_Workflow_Name" -e
```

**Export a visual graph (requires Graphviz):**

```bash
python tools/workflow_manager.py -w "My_Workflow_Name" --graph
dot -Tpng workflow_My_Workflow_Name.dot -o workflow.png
```

---

## 4. Using the Engine (The API)

The Chameleon Workflow Engine exposes a REST API for managing workflow instances and processing work.

### Core Workflow Lifecycle

#### 4.1 Instantiate a Workflow

**Endpoint**: `POST /workflow/instantiate`

Creates a new workflow instance from a template.

**Request Body**:
```json
{
  "template_id": "550e8400-e29b-41d4-a716-446655440000",
  "initial_context": {
    "customer_id": "CUST-123",
    "amount": 5000,
    "priority": "high"
  },
  "instance_name": "Customer Order 123",
  "instance_description": "Order processing for customer 123"
}
```

**Response**:
```json
{
  "workflow_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Workflow instantiated successfully"
}
```

**What Happens**:
1. The template is cloned into a new workflow instance
2. All roles, interactions, components, and guardians are copied
3. An Alpha UOW is created with the `initial_context`
4. The Alpha UOW is injected into the first interaction
5. The workflow is ready for actors to begin processing

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/workflow/instantiate",
    json={
        "template_id": "550e8400-e29b-41d4-a716-446655440000",
        "initial_context": {
            "customer_id": "CUST-123",
            "order_total": 1500
        }
    }
)
workflow = response.json()
print(f"Created workflow: {workflow['workflow_id']}")
```

---

#### 4.2 Checkout Work

**Endpoint**: `POST /workflow/checkout`

Acquires a Unit of Work from a role's queue and locks it for processing.

**Request Body**:
```json
{
  "actor_id": "770e8400-e29b-41d4-a716-446655440002",
  "role_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

**Response (Work Available)**:
```json
{
  "uow_id": "990e8400-e29b-41d4-a716-446655440004",
  "attributes": {
    "customer_id": "CUST-123",
    "order_total": 1500,
    "priority": "high"
  },
  "context": {
    "global_blueprint": {
      "similar_orders": ["CUST-100", "CUST-105"]
    },
    "personal_playbook": {
      "preferred_method": "auto_approve"
    }
  }
}
```

**Response (No Work Available)**: `204 No Content`

**The "Locking" Concept**:

When an actor checks out work:
1. The system scans inbound interactions for PENDING UOWs
2. Guard logic is executed to find eligible items
3. A **transactional lock** is applied (status → `ACTIVE`)
4. The UOW ID, attributes, and merged memory context are returned
5. The actor is now the exclusive owner of this work

The lock prevents other actors from processing the same work simultaneously. If the actor fails to complete the work, the **Zombie Protocol** (see section 5) will eventually reclaim it.

**Python Example**:
```python
response = requests.post(
    "http://localhost:8000/workflow/checkout",
    json={
        "actor_id": "770e8400-e29b-41d4-a716-446655440002",
        "role_id": "880e8400-e29b-41d4-a716-446655440003"
    }
)

if response.status_code == 204:
    print("No work available")
else:
    work = response.json()
    print(f"Got work: {work['uow_id']}")
    print(f"Attributes: {work['attributes']}")
```

---

#### 4.3 Submit Work

**Endpoint**: `POST /workflow/submit`

Submits completed work, releasing the lock and moving the UOW to the next stage.

**Request Body**:
```json
{
  "uow_id": "990e8400-e29b-41d4-a716-446655440004",
  "actor_id": "770e8400-e29b-41d4-a716-446655440002",
  "result_attributes": {
    "approval_status": "approved",
    "reviewer_notes": "Order verified and approved",
    "processed_at": "2024-01-15T10:30:00Z"
  },
  "reasoning": "Standard approval - all criteria met"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Work submitted successfully"
}
```

**"Atomic Versioning" Explained**:

When work is submitted:
1. Lock ownership is verified (actor_id must match)
2. An **attribute diff** is computed (new/modified fields only)
3. The diff is written to the historical lineage (immutable audit trail)
4. UOW status is updated to `COMPLETED`
5. The **Learning Loop** is triggered (Novelty Detection)
6. The lock is released
7. The UOW moves to the next interaction based on guard logic

This ensures complete traceability - you can always see what changed, who changed it, and why.

**Python Example**:
```python
response = requests.post(
    "http://localhost:8000/workflow/submit",
    json={
        "uow_id": "990e8400-e29b-41d4-a716-446655440004",
        "actor_id": "770e8400-e29b-41d4-a716-446655440002",
        "result_attributes": {
            "approval_status": "approved",
            "reviewer_notes": "Looks good!"
        },
        "reasoning": "All validation checks passed"
    }
)
result = response.json()
print(f"Submission: {result['message']}")
```

---

#### 4.4 Report Failure

**Endpoint**: `POST /workflow/failure`

Explicitly flags a UOW as failed, triggering the **Ate Path** (Epsilon role).

**Request Body**:
```json
{
  "uow_id": "990e8400-e29b-41d4-a716-446655440004",
  "actor_id": "770e8400-e29b-41d4-a716-446655440002",
  "error_code": "VALIDATION_FAILED",
  "details": "Missing required field: customer_address"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Failure reported successfully"
}
```

**The "Ate Path" (Epsilon) Explained**:

When a failure is reported:
1. UOW status is updated to `FAILED`
2. The error code and details are logged
3. The UOW is routed to the **Ate Interaction** (error queue)
4. The **Epsilon role** picks it up for remediation
5. The lock is released

Epsilon can:
- Apply automated data correction rules
- Request additional information from external sources
- Log the issue for manual review
- Re-route the corrected UOW back to the workflow

For more on Epsilon role behavior, see `docs/architecture/Role_Behavior_Specs.md`.

**Python Example**:
```python
response = requests.post(
    "http://localhost:8000/workflow/failure",
    json={
        "uow_id": "990e8400-e29b-41d4-a716-446655440004",
        "actor_id": "770e8400-e29b-41d4-a716-446655440002",
        "error_code": "INVALID_DATA",
        "details": "Amount exceeds allowed limit"
    }
)
result = response.json()
print(f"Failure reported: {result['message']}")
```

---

#### 4.5 Heartbeat (Zombie Prevention)

**Endpoint**: `POST /workflow/uow/{uow_id}/heartbeat`

Updates the heartbeat timestamp to signal active processing.

**Request Body**:
```json
{
  "actor_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Heartbeat recorded successfully",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

**Why Heartbeats Matter**:

Long-running tasks should send periodic heartbeats (e.g., every 60 seconds) to prevent the Zombie Actor Protocol from reclaiming the work. If the `last_heartbeat` timestamp becomes too old (default: 5 minutes), the Tau role will mark the UOW as `FAILED` and release it for remediation.

**Python Example**:
```python
import time

# Long-running processing
while processing:
    # Do work...
    time.sleep(60)
    
    # Send heartbeat
    requests.post(
        f"http://localhost:8000/workflow/uow/{uow_id}/heartbeat",
        json={"actor_id": actor_id}
    )
```

---

## 5. Governance & Admin

### The Zombie Protocol

The **Zombie Actor Protocol** (Article XI.3 of the Constitution) ensures that Units of Work don't remain stuck in an `ACTIVE` state indefinitely due to actor crashes or network failures.

**How It Works**:

1. **Passive Heartbeat**: Actors processing a UOW must periodically update the `last_heartbeat` timestamp (see section 4.5)
2. **Active Sweep**: The Tau role continuously monitors for zombie UOWs (default: every 60 seconds)
3. **Detection**: A UOW is considered a zombie if:
   - Status is `ACTIVE`
   - `last_heartbeat` is older than the threshold (default: 5 minutes)
4. **Reclamation**: Zombie UOWs are marked as `FAILED` and routed to Epsilon for remediation

**Background Service**:

The zombie sweeper runs automatically as a background task when the server starts. You can see logs like:

```
INFO: Zombie Actor Sweeper (TAU) starting...
WARNING: Zombie Actor Detected - Found 2 stale UOW(s)
WARNING: Zombie Actor Detected - Reclaiming Token: UOW xyz, last heartbeat: 2024-01-15T10:20:00Z
INFO: Reclaimed 2 zombie tokens
```

**Manual Trigger** (for testing or on-demand cleanup):

```bash
curl -X POST http://localhost:8000/admin/run-zombie-protocol \
  -H "Content-Type: application/json" \
  -d '{"timeout_seconds": 300}'
```

**Response**:
```json
{
  "success": true,
  "zombies_reclaimed": 2,
  "message": "Zombie protocol completed. Reclaimed 2 zombie token(s)."
}
```

---

### Memory Decay (The Janitor)

The **Memory Decay** process (Article XX.3 of the Constitution) prevents "adaptive decay" by cleaning up stale memory entries from the Personal Playbook and Global Blueprint.

**How It Works**:

1. The system tracks when each memory entry was last accessed
2. Memories older than the retention period (default: 90 days) are deleted
3. This prevents the knowledge base from becoming polluted with outdated patterns

**Manual Trigger**:

```bash
curl -X POST http://localhost:8000/admin/run-memory-decay \
  -H "Content-Type: application/json" \
  -d '{"retention_days": 90}'
```

**Response**:
```json
{
  "success": true,
  "memories_deleted": 47,
  "message": "Memory decay completed. Deleted 47 stale memory entries."
}
```

**Best Practices**:
- Run memory decay periodically (e.g., weekly) via cron job
- Adjust `retention_days` based on your workflow's learning cycle
- Monitor deletion counts to detect anomalies

---

### Toxic Memory Filter

The **Toxic Knowledge Filter** (Article XX.1) allows you to flag specific memories that led to incorrect decisions.

**Manual Flagging**:

```bash
curl -X POST http://localhost:8000/admin/mark-toxic \
  -H "Content-Type: application/json" \
  -d '{
    "memory_id": "aa0e8400-e29b-41d4-a716-446655440005",
    "reason": "Led to incorrect approval of fraudulent transaction"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Memory aa0e8400-e29b-41d4-a716-446655440005 successfully marked as toxic."
}
```

**Automatic Behavior**:

Toxic memories are automatically excluded from the context during work checkout. The engine filters them out when building the Global Blueprint and Personal Playbook, preventing the same mistake from being repeated.

---

### Admin Endpoints Summary

| Endpoint | Purpose | When to Use |
|----------|---------|-------------|
| `POST /admin/run-zombie-protocol` | Manually trigger zombie detection | Testing, on-demand cleanup |
| `POST /admin/run-memory-decay` | Clean up stale memory entries | Periodic maintenance (weekly/monthly) |
| `POST /admin/mark-toxic` | Flag problematic memory | Post-mortem analysis after failures |

**Security Note**: In production, these endpoints should require `SYSTEM_ADMIN` authentication scope.

---

## 6. Writing an Agent (Client Example)

This section provides a practical example of how to write an AI agent that processes work from the Chameleon Workflow Engine.

### Basic Agent Loop

```python
import requests
import time
from typing import Optional, Dict, Any

class ChameleonAgent:
    """A simple agent that processes work from the Chameleon Workflow Engine."""
    
    def __init__(self, base_url: str, actor_id: str, role_id: str):
        self.base_url = base_url
        self.actor_id = actor_id
        self.role_id = role_id
        self.current_uow_id: Optional[str] = None
        
    def checkout_work(self) -> Optional[Dict[str, Any]]:
        """Attempt to checkout work from the engine."""
        response = requests.post(
            f"{self.base_url}/workflow/checkout",
            json={
                "actor_id": self.actor_id,
                "role_id": self.role_id
            }
        )
        
        if response.status_code == 204:
            # No work available
            return None
        
        response.raise_for_status()
        return response.json()
    
    def submit_work(self, uow_id: str, result_attributes: Dict[str, Any], 
                   reasoning: str) -> bool:
        """Submit completed work."""
        response = requests.post(
            f"{self.base_url}/workflow/submit",
            json={
                "uow_id": uow_id,
                "actor_id": self.actor_id,
                "result_attributes": result_attributes,
                "reasoning": reasoning
            }
        )
        response.raise_for_status()
        return response.json()["success"]
    
    def report_failure(self, uow_id: str, error_code: str, 
                      details: str) -> bool:
        """Report work failure."""
        response = requests.post(
            f"{self.base_url}/workflow/failure",
            json={
                "uow_id": uow_id,
                "actor_id": self.actor_id,
                "error_code": error_code,
                "details": details
            }
        )
        response.raise_for_status()
        return response.json()["success"]
    
    def send_heartbeat(self, uow_id: str) -> bool:
        """Send heartbeat for long-running work."""
        response = requests.post(
            f"{self.base_url}/workflow/uow/{uow_id}/heartbeat",
            json={"actor_id": self.actor_id}
        )
        response.raise_for_status()
        return response.json()["success"]
    
    def process_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the work - OVERRIDE THIS METHOD in your agent.
        
        Args:
            work: Dict containing uow_id, attributes, and context
            
        Returns:
            Dict with result attributes
        """
        # Example: Simple approval logic
        attributes = work["attributes"]
        
        # Access context for learning
        context = work.get("context", {})
        global_blueprint = context.get("global_blueprint", {})
        
        # Your processing logic here...
        result = {
            "processed": True,
            "approval_status": "approved",
            "processed_by": self.actor_id
        }
        
        return result
    
    def run(self, poll_interval: int = 5):
        """
        Main agent loop.
        
        Args:
            poll_interval: Seconds to wait between checkout attempts
        """
        print(f"Agent starting (actor_id={self.actor_id}, role_id={self.role_id})")
        
        while True:
            try:
                # Checkout work
                work = self.checkout_work()
                
                if not work:
                    print(f"No work available, sleeping {poll_interval}s...")
                    time.sleep(poll_interval)
                    continue
                
                uow_id = work["uow_id"]
                self.current_uow_id = uow_id
                print(f"Checked out UOW: {uow_id}")
                
                try:
                    # Process the work
                    result_attributes = self.process_work(work)
                    
                    # Submit results
                    self.submit_work(
                        uow_id=uow_id,
                        result_attributes=result_attributes,
                        reasoning="Work processed successfully"
                    )
                    print(f"Submitted UOW: {uow_id}")
                    
                except Exception as e:
                    # Report failure
                    print(f"Error processing UOW {uow_id}: {e}")
                    self.report_failure(
                        uow_id=uow_id,
                        error_code="PROCESSING_ERROR",
                        details=str(e)
                    )
                
                finally:
                    self.current_uow_id = None
                    
            except KeyboardInterrupt:
                print("Agent shutting down...")
                break
            except Exception as e:
                print(f"Unexpected error in agent loop: {e}")
                time.sleep(poll_interval)


# Example usage
if __name__ == "__main__":
    agent = ChameleonAgent(
        base_url="http://localhost:8000",
        actor_id="770e8400-e29b-41d4-a716-446655440002",
        role_id="880e8400-e29b-41d4-a716-446655440003"
    )
    
    agent.run(poll_interval=5)
```

---

### Long-Running Agent with Heartbeat

For tasks that take more than 5 minutes, implement heartbeat sending:

```python
import threading
import time

class LongRunningAgent(ChameleonAgent):
    """Agent that sends heartbeats during long processing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_thread = None
        self.heartbeat_active = False
    
    def start_heartbeat(self, uow_id: str, interval: int = 60):
        """Start heartbeat thread for long-running work."""
        self.heartbeat_active = True
        
        def heartbeat_loop():
            while self.heartbeat_active:
                try:
                    self.send_heartbeat(uow_id)
                    print(f"Heartbeat sent for UOW: {uow_id}")
                except Exception as e:
                    print(f"Heartbeat error: {e}")
                time.sleep(interval)
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def stop_heartbeat(self):
        """Stop heartbeat thread."""
        self.heartbeat_active = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
    
    def process_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """Process work with heartbeat support."""
        uow_id = work["uow_id"]
        
        # Start heartbeat for long processing
        self.start_heartbeat(uow_id, interval=60)
        
        try:
            # Your long-running processing logic here
            time.sleep(300)  # Simulate 5 minutes of work
            
            result = {
                "processed": True,
                "duration_seconds": 300
            }
            return result
            
        finally:
            # Always stop heartbeat when done
            self.stop_heartbeat()
```

---

### AI-Powered Agent Example

Here's an example using an AI model (pseudocode - adapt for your AI provider):

```python
from anthropic import Anthropic  # Example: Claude API

class AIAgent(ChameleonAgent):
    """Agent powered by an AI model."""
    
    def __init__(self, *args, ai_api_key: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.ai_client = Anthropic(api_key=ai_api_key)
    
    def process_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to process the work."""
        attributes = work["attributes"]
        context = work.get("context", {})
        
        # Build prompt from attributes and context
        prompt = f"""
        You are processing a workflow task.
        
        Task Attributes:
        {attributes}
        
        Context from previous executions:
        {context.get('global_blueprint', {})}
        
        Please analyze this task and provide your decision.
        """
        
        # Call AI model
        response = self.ai_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        ai_decision = response.content[0].text
        
        # Structure the result
        result = {
            "ai_analysis": ai_decision,
            "decision": "approved",  # Parse from AI response
            "confidence": 0.95
        }
        
        return result
```

---

### Best Practices for Agent Development

1. **Graceful Degradation**: Always handle cases where work is unavailable (204 response)
2. **Error Handling**: Use try/except blocks and report failures properly
3. **Heartbeats**: Send heartbeats for any work taking >2 minutes
4. **Idempotency**: Design your processing logic to be idempotent in case of retries
5. **Logging**: Log all checkout/submit/failure operations for debugging
6. **Memory Usage**: Use the context (Global Blueprint, Personal Playbook) to improve decisions
7. **Reasoning**: Always provide clear reasoning in submit calls for traceability

---

## Next Steps

Now that you understand the basics:

1. **Explore Architecture**: Read `docs/architecture/Workflow_Constitution.md` for deep constitutional concepts
2. **Study Examples**: Review `tools/complete_workflow_example.yaml` for a comprehensive workflow
3. **Understand Roles**: See `docs/architecture/Role_Behavior_Specs.md` for detailed role specifications
4. **Learn Guards**: Read `docs/architecture/Guard Behavior Specifications.md` for guard logic details
5. **API Deep Dive**: Check `docs/architecture/Interface & MCP Specs.md` for complete API reference

---

## Troubleshooting

### Server won't start
- Check that both database URLs are accessible
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check for port conflicts: `lsof -i :8000`

### No work available (constant 204 responses)
- Verify workflow is instantiated: Check template_id
- Ensure UOWs are in PENDING status
- Check guard logic isn't blocking all work
- Verify role_id matches an existing role in the workflow

### Zombie UOWs accumulating
- Ensure agents are sending heartbeats for long tasks
- Check zombie protocol is running (check server logs)
- Verify timeout threshold is appropriate for your workload

### Memory growing indefinitely
- Run memory decay periodically
- Check for memory leaks in agent code
- Adjust retention_days based on workflow patterns

---

## Support & Resources

- **GitHub Repository**: [clydewatts1/prototype_chameleon_mcp_workflow](https://github.com/clydewatts1/prototype_chameleon_mcp_workflow)
- **API Documentation**: `http://localhost:8000/docs` (when server is running)
- **Architecture Docs**: `docs/architecture/` directory
- **Example Workflows**: `tools/*.yaml` files

For questions or issues, open an issue on GitHub.

---

**Happy Orchestrating! 🦎✨**
