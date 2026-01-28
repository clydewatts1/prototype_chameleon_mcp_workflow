# **Chameleon Workflow Engine \- Bare Minimum (Zero-Agent) Flow**

This directory documents the "Constitutional Zero-Agent" workflow configuration. Unlike the standard examples, this flow requires **no external Python agents** (no Human, AI, or Auto scripts).

Instead, it demonstrates the structural physics of the Chameleon Engine—specifically **Timeouts**, **Guard Logic**, and **Lifecycle Management**—by relying entirely on the internal Structural Roles (Alpha, Omega, Tau).

## **Overview**

The workflow defined in constitutional\_zero\_agent.yaml demonstrates a "Stale Token" lifecycle:

1. **Alpha Role** instantiates a transaction.  
2. The transaction enters a **Stasis Chamber** (Interaction).  
3. Because no Beta roles exist to pick it up, the token effectively "stalls."  
4. The **Tau Role (System Background Service)** detects the timeout.  
5. The token is forced into a terminal state and reconciled by **Omega**.

## **Prerequisites**

* Python 3.9+  
* Chameleon Workflow Engine server running  
* **No** external LLMs (Ollama) or API keys are required.

## **Workflow Definition**

Save the following content as tools/constitutional\_zero\_agent.yaml:

workflow:  
  name: "Constitutional\_Zero\_Agent\_Flow"  
  description: "A bare minimum workflow satisfying the Constitution without Beta agents. Relies on system timeouts for progression."  
  version: 1.0  
  ai\_context:  
    goal: "Validate structural integrity and timeout protocols."  
    risk\_level: "Low"

  \# Structural Roles Only (No BETA, HUMAN, AI\_AGENT, AUTO)  
  roles:  
    \- name: "Prime\_Mover"  
      type: "ALPHA"  
      description: "Instantiates the Base Unit of Work."  
      ai\_context: {"persona": "System Origin"}

    \- name: "The\_End"  
      type: "OMEGA"  
      description: "Reconciles and archives the workflow."  
      ai\_context: {"persona": "System Terminal"}

    \- name: "Entropy\_Guard"  
      type: "TAU"  
      description: "Background service to claim stalled tokens."  
      ai\_context: {"persona": "Timekeeper"}

  interactions:  
    \- name: "Stasis\_Chamber"  
      description: "A holding area where UOWs wait for non-existent agents."

  components:  
    \# 1\. Instantiation: Alpha creates the UOW and places it in Stasis  
    \- role: "Prime\_Mover"  
      interaction: "Stasis\_Chamber"  
      direction: "OUTBOUND"  
      name: "Genesis\_Outbound"

    \# 2\. Timeout Path: Tau watches Stasis for stalled items (Simulating progression)  
    \- role: "Entropy\_Guard"  
      interaction: "Stasis\_Chamber"  
      direction: "INBOUND"  
      name: "Timeout\_Sweep"  
      guardian:  
        type: "STANDARD"  
        config:   
          timeout\_seconds: 5  \# Short timeout for demo purposes

    \# 3\. Finalization: Omega attempts to pull completed work  
    \- role: "The\_End"  
      interaction: "Stasis\_Chamber"  
      direction: "INBOUND"  
      name: "Terminal\_Inbound"  
      guardian:  
        type: "CERBERUS"  
        config:   
          synchronization: "strict\_all\_children"

## **Quick Start**

### **1\. Import the Workflow**

Load the Constitutional Zero-Agent YAML definition into the database:

python tools/workflow\_manager.py \-i \-f examples/minimum/constitutional\_zero\_agent.yaml

### **2\. Start the Server**

Start the main engine server. This server includes the background "Tau" (Zombie/Timeout) protocols.

python \-m chameleon\_workflow\_engine.server

### **3\. Instantiate the Workflow**

Since there are no external agents to start, you simply trigger the workflow. The system handles the rest.

\# Instantiate the workflow  
curl \-X POST http://localhost:8000/workflow/instantiate \\  
  \-H "Content-Type: application/json" \\  
  \-d '{  
    "template\_name": "Constitutional\_Zero\_Agent\_Flow",  
    "initial\_context": {  
      "test\_type": "structural\_integrity\_check"  
    },  
    "instance\_name": "Zero Agent Test 01"  
  }'

### **4\. Trigger the Timeout (The "Agent")**

In a production environment, the Tau role runs automatically in the background. For this demo, you can manually trigger the "Zombie Protocol" to simulate the Tau Role sweeping for stalled work:

\# Wait 5 seconds (the timeout configured in the YAML), then run:  
curl \-X POST http://localhost:8000/admin/run-zombie-protocol \\  
  \-H "Content-Type: application/json" \\  
  \-d '{"timeout\_seconds": 1}'

## **Constitutional Compliance**

This workflow is designed to strictly adhere to the **Workflow Constitution** while using the minimum number of moving parts.

### **Article V: Structural Role Purity**

* **Satisfaction:** The workflow uses *only* Structural Roles (ALPHA, OMEGA, TAU). It explicitly excludes the "Beta" family (Processing Roles), proving that the engine can maintain lifecycle integrity without worker agents.

### **Article I: The Principle of Isolation**

* **Satisfaction:** The Unit of Work (UOW) is confined to the Stasis\_Chamber interaction. It cannot "teleport" to the end; it must sit in the holding area until a valid constitutional trigger (Timeout) acts upon it.

### **Article VI: Cerberus Synchronization**

* **Satisfaction:** The The\_End (Omega) role is guarded by Cerberus.  
* **Mechanism:** Cerberus normally blocks any UOW that isn't "COMPLETED." By allowing the Tau role to modify the status to TIMEOUT or FAILED, the workflow demonstrates how the system handles non-happy-path termination without violating the synchronization check (which rejects "IN\_PROGRESS" or "PENDING" states).

### **Article XI: The Stale Token Protocol**

* **Satisfaction:** This entire workflow is a demonstration of **Article XI.2 (The Chronos Path)**. It validates that the engine can reclaim work that has exceeded its STALE\_TOKEN\_LIMIT without human intervention.

## **Execution Behavior**

When you run this workflow, the following lifecycle occurs:

| Stage | Actor/Role | Action | State Transition |
| :---- | :---- | :---- | :---- |
| **1\. Genesis** | Prime\_Mover (Alpha) | Instantiates the workflow. | NULL → INITIALIZED |
| **2\. Transit** | System Guard | Routes UOW to Stasis. | INITIALIZED → PENDING |
| **3\. Stasis** | *None* | The UOW sits in Stasis\_Chamber. No agent exists to pick it up. | PENDING (Stalls) |
| **4\. Sweep** | Entropy\_Guard (Tau) | Background service detects UOW age \> 5 seconds. | PENDING → TIMEOUT |
| **5\. Terminate** | The\_End (Omega) | Receives the timed-out token, reconciles, and archives it. | TIMEOUT → FINALIZED |

## **Workflow Diagram**

┌──────────────┐  
│  Prime\_Mover │ (Alpha Role)  
│   (System)   │  
└──────┬───────┘  
       │  
       ▼  
┌──────────────┐    Timeout Sweep      ┌───────────────┐  
│Stasis\_Chamber│  (\> 5 Seconds)      │ Entropy\_Guard │  
│ (Interaction)├────────────────────►│     (Tau)     │  
└──────┬───────┘    (Article XI)       └───────┬───────┘  
       │                                       │  
       │           Forced Transition           │  
       │          (TIMEOUT / FAILED)           │  
       │◄──────────────────────────────────────┘  
       ▼  
┌──────────────┐  
│    The\_End   │ (Omega Role)  
│   (System)   │ Archives the dead token  
└──────────────┘  
