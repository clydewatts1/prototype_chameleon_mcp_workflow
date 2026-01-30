# **Branching Logic Guide**

## **1\. Philosophy**

Chameleon relies on **Engine-Driven Branching**. Roles do not decide which path to take; the Engine evaluates the state and directs the flow.

## **2\. Mechanisms**

### **A. Attribute-Driven (Deterministic)**

The most common branching. The flow moves based on specific values in the global state.

* **Example:** if state.payment\_status \== 'PAID' then goto ship\_item  
* **Best Practice:** Keep logic simple. Avoid complex calculations in YAML.

### **B. LLM-Driven (Semantic)**

An LLM (Guard or Router) analyzes text and determines the next step.

* **Example:** "Is the user angry?" \-\> True \-\> goto escalation\_team

### **C. Dynamic Context Injection (DCI) & Model Orchestration**

The Engine modifies the *properties* of the current step based on state, rather than changing the path.

* **Use Case:** High-stakes scenarios (Fraud, VIPs) requiring better models or stricter instructions.  
* **Reference:** [Dynamic Context Injection Specs](https://www.google.com/search?q=Dynamic_Context_Injection_Specs.md)

## **3\. The "Computed State" Rule (Preventing Complexity)**

**Do not** put complex business logic or math inside the Workflow YAML conditions.

* ❌ **Bad:** condition: "state.orders.length \> 5 && (state.age \> 21 || state.location \== 'US')"  
* ✅ **Good:** condition: "state.is\_eligible\_for\_promo"

**Implementation:**

Calculate derived values (like is\_eligible\_for\_promo) in your application code (e.g., inside a specialized "Analyst" role or a pre-processor) and store the simple boolean result in the state. The Workflow YAML should only react to these simple flags.