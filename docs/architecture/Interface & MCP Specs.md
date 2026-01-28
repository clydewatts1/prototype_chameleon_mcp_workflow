# **Interface & MCP Specs**

## **1\. Constitutional Protocol Extensions**

### **1.1 First-Class Human Tools**

Intervention is not a fallback; it is a core tool in the MCP manifest.

* **wait\_for\_pilot**: Suspends execution and notifies the dashboard.  
* **request\_pilot\_intervention**: Explicitly used for high-risk decisions or ambiguity resolution.

### **1.2 The Telemetry Header**

Every message sent via the MCP protocol must include an **X-Constitutional-Context** header containing:

* uow\_id: The unique identifier for the current work unit.  
* interaction\_depth: Current step count in the lifecycle.  
* state\_hash: The cryptographic signature of the current UOW payload.

## **2\. Protocol Security & Validation**

* **Atomic State Verification:** MCP Servers *must* validate the state\_hash before executing a tool call to prevent "State Drift."  
* **Intent Validation:** Before executing a tool, the server must query the **Pre-Flight Guard** to confirm the Agent's authorization.

## **3\. Telemetry Hooks**

All MCP servers must implement standardized notification types for the **Observation Stream**, allowing for real-time monitoring of resource usage and tool performance.