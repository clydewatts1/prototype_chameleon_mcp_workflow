# **Guard Behavior Specifications**

## **1\. Automated Enforcement Mandate**

Guards serve as the automated "Police" of the system. They are non-bypassable and operate at the protocol level.

### **1.1 The Violation Packet**

When a Guard blocks an action, it must emit a standardized **Violation Packet**:

* rule\_id: The specific Constitutional article or Guard rule triggered.  
* severity: \[LOW, MEDIUM, HIGH, CRITICAL\].  
* raw\_data: The snippet of data or intent that caused the block.  
* remedy\_suggestion: Machine-generated advice for the Pilot to resolve the block.

## **2\. Three-Layer Defense**

### **2.1 Pre-Flight Guards (Intent Check)**

* **Validation:** Checks if the Agent has the necessary permissions to call a specific tool for the current UOW.  
* **Environmental Integrity:** Ensures the required MCP resources are available and in a safe state.

### **2.2 Semantic Guards (Logic Check)**

* **Output Analysis:** Verifies that the Agent's output satisfies the "Definition of Done."  
* **Loop Prevention:** Detects repetitive "spinning" behavior (Ambiguity Lock).

### **2.3 Structural Guards (Protocol Check)**

* **Hash Verification:** Re-calculates the state\_hash of the UOW to ensure no unauthorized data modification occurred during execution.

## **3\. Heuristic Evolution & Learning**

* **Override Tracking:** If a Pilot issues a "Constitutional Waiver" for a specific block, the Guard logs this as a "Heuristic Signal."  
* **Librarian Integration:** Repeated signals are sent to the **Librarian** to evaluate if the underlying Guard rule needs refinement to reduce friction.