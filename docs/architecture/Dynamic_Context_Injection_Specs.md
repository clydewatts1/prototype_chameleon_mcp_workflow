# **Technical Specification: Dynamic Context Injection (DCI) & Model Orchestration**

## **1\. Executive Summary**

This specification defines the runtime mutation of the execution environment within the **Chameleon** ecosystem. It empowers the **Semantic Guard** to transition from a passive validator to an **Execution Orchestrator**.

The engine will dynamically adjust both the **semantic context** and the **underlying intelligence model** of a **Unit of Work (UOW)** based on real-time project state. This ensures optimal resource allocation, security posture, and accuracy without violating the core architectural principle: **Worker Roles must remain logic-blind.**

## **2\. Constitutional Alignment**

* **Role Purity:** Worker roles remain unaware of the business logic governing the choice of context or model. They receive a final prompt and a model endpoint; the "why" is abstracted.  
* **Engine Supremacy:** The engine remains the sole authority for branching and state mutation.  
* **Auditability:** Every mutation (context injection or model swap) must be recorded in the **Experience Ledger** to allow the **Teacher** process to evaluate the efficacy of the orchestration.

## **3\. Orchestration Schema**

DCI and Model overrides are defined within the guards section of the workflow YAML using the conditional\_injector type.

### **3.1 YAML Configuration**

guards:  
  \- id: global\_risk\_orchestrator  
    type: "conditional\_injector"  
    scope: "pre\_execution"  
    rules:  
      \- condition: "state.transaction\_value \> 50000"  
        action: "mutate"  
        payload:  
          model\_override: "gpt-4o" \# High-reasoning required for large sums  
          instructions: "POLICY: This is a high-value transaction. Verify against anti-money-laundering (AML) checklists."  
          knowledge\_fragments: \["aml\_compliance\_v4"\]  
            
      \- condition: "state.user\_reputation \< 0.2"  
        action: "mutate"  
        payload:  
          model\_override: "grok-1-pro" \# Switch provider to verify across diverse logic  
          instructions: "ALERT: Low reputation user. Scrutinize metadata for bot signatures."

## **4\. Implementation Logic**

### **A. Mutation Pipeline (UOW Preparation)**

The Engine executes this pipeline during the transition from PENDING to IN\_PROGRESS:

1. **Variable Resolution:** The DSL\_Evaluator fetches relevant fields from the global project state.  
2. **Rule Evaluation:** Guards are evaluated in the defined order.  
3. **Model Selection:** \* If a model\_override is matched, the UOW model\_id is updated.  
   * If multiple rules match, the **Last Match Wins** principle applies to the model\_id.  
4. **Context Merging:** \* instructions are prepended to the system prompt.  
   * knowledge\_fragments are injected into the Role's local Universe for RAG retrieval.

### **B. The Provider Router**

The engine maintains a mapping of model\_id to specific API providers (Gemini, Grok, OpenAI). The router is responsible for:

* **Credential Management:** Selecting the correct API key for the chosen model.  
* **Format Normalization:** Translating the UOW state into the provider-specific payload (e.g., system vs. user message roles).

## **5\. Resilience & Error Handling**

### **5.1 Provider Failover Protocol**

As a high-authority directive, the system must not stall if an overridden model is unavailable.

1. **Primary Attempt:** Engine attempts to dispatch to the model\_override.  
2. **Fallback:** If the provider returns a 5xx or rate-limit error, the engine reverts to the Role's **Template Default Model**.  
3. **Logging:** A FailoverViolation packet is emitted to the **ShadowLogger** so the **Teacher** can investigate provider reliability.

### **5.2 DSL Validation**

To prevent "jailbreaking" of the orchestration layer:

* model\_override values must match a strict whitelist in the **Meta-Store**.  
* Conditions cannot execute arbitrary code; they are limited to boolean operations on known state variables via dsl\_evaluator.py.

## **6\. Ledger Integration for Upskilling**

The **Teacher** analyzes the orchestration data to:

1. **Model Benchmark:** Compare if "High Risk" tasks succeed more often on grok vs gemini.  
2. **Prompt Refinement:** Determine if the injected\_instructions are sufficient for Tier 1 models to perform without needing an upgrade.  
3. **Cost Optimization:** Suggest downgrading models for specific states where cheap models consistently perform as well as expensive ones.

## **7\. Known Drawbacks & Mitigation Strategies**

### **A. Prompt Portability (The Polyglot Problem)**

* **Risk:** A Role's system prompt optimized for Gemini may perform poorly when dynamically swapped to Grok or Llama due to differing instruction-following capabilities.  
* **Mitigation:**  
  1. **Polyglot Templates:** Role templates must use standard Markdown/XML formatting that is generally understood by all Tier 1 and Tier 2 models.  
  2. **Teacher Alerting:** The Learning Loop must explicitly flag when a Role has a high failure rate *only* on specific swapped models.

### **B. Reproducibility (The Chaos Factor)**

* **Risk:** Troubleshooting becomes difficult because small changes in State trigger different execution paths (different models/instructions).  
* **Mitigation:**  
  1. **Snapshot Logging:** The ShadowLogger must capture the *exact* resolved context and model ID for every UOW.  
  2. **Dry-Run Mode:** The Dashboard must support a "Dry Run" that simulates Guard evaluation against a given state without executing the LLM, to verify routing logic.

### **C. Configuration Complexity**

* **Risk:** The YAML file becomes bloated with complex business logic.  
* **Mitigation:**  
  1. **Logic Caps:** Limit DSL conditions to simple comparisons (\<, \>, \==). Complex logic should be calculated upstream by a specialized "Analyst" role and stored as a simple boolean flag in the state (e.g., state.is\_high\_risk) rather than calculating it in the YAML.