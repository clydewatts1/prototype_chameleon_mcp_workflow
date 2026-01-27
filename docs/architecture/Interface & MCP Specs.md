# **Interface & MCP Specifications**

This document establishes the **External Interface** of the Chameleon Workflow Engine. It defines the API contract for the Control Plane and the **Model Context Protocol (MCP)** tool definitions for Actor interaction, ensuring compliance with Article XXI (Infrastructure Independence).

## **1\. The Actor Interface (MCP Protocol)**

Actors (Human or AI) do not query the database directly. They interact via a strict set of **Tools** that enforce the "Total Isolation" principle (Article I).

### **1.1 Tool: checkout\_work**

**Purpose:** Acquires a Unit of Work (UOW) from a specific Role's queue and locks it for processing.

**Input:**

* role\_id: The Role the Actor is assuming (e.g., "Approver").  
* actor\_id: The Actor's unique identity.  
  **Output (Success):**  
* uow\_id: The unique token ID.  
* attributes: The payload data.  
* context: Merged Memory (Global Blueprint \+ Personal Playbook).  
  **Output (Empty):** null (No work available).  
  **Logic:**  
1. Scan Inbound Interactions for PENDING items.  
2. Run **Guard Logic** to find eligible items.  
3. Execute **Transactional Lock** (State ![][image1] IN\_PROGRESS).

### **1.2 Tool: submit\_work**

**Purpose:** Submits the results of a completed task, unlocking the UOW and moving it to the next stage.

**Input:**

* uow\_id: The token being processed.  
* actor\_id: The Actor's identity (Must match lock holder).  
* result\_attributes: JSON blob of *new* or *modified* data.  
* reasoning: (Optional) Text explanation for the decision (for Traceability).  
  **Output:** success: true or error.  
  **Logic:**  
1. Verify Lock ownership.  
2. Compute **Attribute Diff** and write to History (Atomic Versioning).  
3. Update UOW Status ![][image1] COMPLETED.  
4. Trigger **Learning Loop** (Novelty Detection).  
5. Release Lock.

### **1.3 Tool: report\_failure**

**Purpose:** Explicitly flags a UOW as failed/invalid, triggering the **Ate Path** (Epsilon).

**Input:**

* uow\_id: The token ID.  
* error\_code: Standardized error string.  
* details: Descriptive text.  
  **Output:** success: true.  
  **Logic:**  
1. Update UOW Status ![][image1] FAILED.  
2. Route to **Ate Interaction**.  
3. Release Lock.

### **1.4 Tool: get\_memory**

**Purpose:** Allows an Actor to explicitly query the Global Blueprint for similar past cases (RAG).

**Input:**

* role\_id: The current role context.  
* query: Natural language search string (e.g., "How do we handle vendor X?").  
  **Output:** List of relevant WorkflowRoleAttributes (filtered for Toxicity).

## **2\. The Control Plane (Management API)**

This interface is used by external systems (Orchestrators, Webhooks) to manage the lifecycle of Workflow Instances.

### **2.1 Endpoint: POST /workflow/instantiate**

**Purpose:** Spins up a new Instance from a Template.

**Payload:**

{  
  "template\_id": "uuid",  
  "initial\_context": { "customer\_id": "123", "amount": 5000 }  
}

**Behavior:**

1. Clone Template Roles ![][image1] Instance Roles.  
2. Clone Interactions/Guards.  
3. Create **Alpha UOW** with initial\_context.  
4. Inject into Alpha Interaction.

### **2.2 Endpoint: GET /workflow/{id}/status**

**Purpose:** Observability dashboard.

**Response:**

* status: "ACTIVE" | "COMPLETED" | "STALLED".  
* metrics: { "pending\_count": 5, "error\_count": 0 }.  
* active\_actors: List of currently locked UOWs.

### **2.3 Endpoint: POST /admin/intervene**

**Purpose:** "Break-Glass" operations for System Admins (See *Operational Intervention Specs*).

**Payload:**

{  
  "action": "FORCE\_UNLOCK",  
  "target\_uow": "uuid",  
  "reason": "Actor crash recovery"  
}

**Security:** Requires SYSTEM\_ADMIN scope.

## **3\. Transport Layer Abstraction**

To satisfy Article XXI (Infrastructure Independence), these interfaces must be decoupled from the transport protocol.

### **3.1 The Adapter Pattern**

The Core Engine exposes a Python Class ChameleonEngine with methods matching the tools above.

* **REST Adapter:** Wraps ChameleonEngine in FastAPI/Flask routes.  
* **MCP Adapter:** Wraps ChameleonEngine in an MCP Server (stdio/SSE) for AI Agent connection.  
* **CLI Adapter:** Wraps ChameleonEngine in argparse commands for local testing.

### **3.2 Event Bus Integration (Optional)**

For asynchronous architectures, the engine can emit events on status changes:

* TOPIC: workflow.uow.completed  
* TOPIC: workflow.alert.ate\_path  
  External systems can subscribe to these topics instead of polling the API.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAt0lEQVR4XmNgGAWjgDpAQUGBQ05OLk1UVJQHXY4cwCgvL98KNNAYXYIsADIIaGAvkMmCLkcOYAR6twBoaByIjSIDlBAA2iRJClZSUgKaJTcfyJ6soqLCBzZIXFycGyhQDcSzSMVAw3YA6a9A3Aw0kB3FhaQAWVlZE6Ahq6WlpWXQ5UgCQAOEgQYtVlRUlEeXIxkADcoChnMEujjJAJRogYZNlZGRkUaXIwcwqqur84JodIlRMMAAAJV7J+RoCL8jAAAAAElFTkSuQmCC>