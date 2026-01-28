# **Role Behavior Specifications**

## **1\. The Pilot (Human Role)**

The Pilot is the primary authority within the system, exercising ultimate sovereignty over all automated processes.

### **1.1 Pilot Sovereignty & Authority**

* **Ultimate Override:** The Pilot can pause, terminate, or force-complete any Unit of Work (UOW) at any state.  
* **Constitutional Adjudication:** The Pilot is the final judge for critical safety violations or logic stalemates (Absolute Dead Timeouts).  
* **Goal Redefinition:** The Pilot has the exclusive right to modify the high-level objectives of a running workflow.  
* **Constitutional Constraint:** All actions must be logged to the Shadow Logger to ensure the "Human-Centricity" pillar is measurable.

## **2\. The Agent (Execution Role)**

Agents are autonomous entities responsible for the functional execution of UOWs.

### **2.1 Behaviors**

* **Stateless Operation:** Agents process UOWs based solely on the provided payload and the Workflow Constitution.  
* **Tool-Bound Execution:** Agents interact with the environment exclusively through MCP tools.  
* **Constitutional Constraint:** Agents must halt execution and emit a "Clarification Request" if they encounter ambiguity exceeding their local threshold.

## **3\. The Guard (Governance Role)**

Guards are 100% automated enforcement mechanisms that operate as a "Border Control" layer.

### **3.1 Behaviors**

* **Pre-emptive Validation:** Guards must validate intent and environment *before* an Agent begins a UOW.  
* **Hard Enforcement:** Guards block any action that deviates from the Constitutional safety rails without exception.  
* **Violation Reporting:** Guards generate "Violation Packets" for the Pilot upon any blocked action.  
* **Constitutional Constraint:** Guards are forbidden from modifying UOW data; they are observers and gatekeepers only.

## **4\. The Librarian (Learning Role)**

The Librarian manages the "Continuous Learning" loop, ensuring the system evolves safely.

### **4.1 Behaviors**

* **Refinement Analysis:** Analyzes successful and failed UOWs to propose template optimizations.  
* **Heuristic Management:** Updates the Knowledge Base based on validated Pilot overrides.  
* **Proposal Generation:** Creates "Refinement Proposals" for the Pilot to approve before any logic changes are applied.  
* **Constitutional Constraint:** The Librarian cannot apply changes to the system logic without explicit Pilot sign-off.