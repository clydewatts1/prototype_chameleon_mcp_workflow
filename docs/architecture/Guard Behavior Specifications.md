# **Guard Behavior Specifications**

## **1\. Core Philosophy**

Guards in Chameleon are the enforcement layer of the architecture. They act as the "immune system," protecting the workflow from invalid states, policy violations, and low-quality outputs. Guards are **distinct from Roles**; they do not generate content, they evaluate it.

## **2\. Guard Types**

### **A. Semantic Guards (Policy & Safety)**

* **Function**: Analyze the *content* of a message or artifact.  
* **Mechanism**: LLM-based evaluation against natural language policy sets (e.g., "Ensure tone is professional", "Check for PII").  
* **Trigger**: Can run Pre-Execution (on inputs) or Post-Execution (on outputs).

### **B. Structural Guards (Schema & Format)**

* **Function**: Validate the *structure* of data.  
* **Mechanism**: Code-based validation (JSON Schema, Regex, Type Checking).  
* **Trigger**: Primarily Post-Execution to ensure an agent's output matches the required format for the next step.

### **C. Conditional Injectors (Context & Routing)**

* **Function**: Mutate the execution environment based on state.  
* **Mechanism**: Evaluates DSL conditions against Project State to inject specific instructions, knowledge, or swap the underlying LLM model.  
* **Trigger**: Pre-Execution (during UOW preparation).  
* **Reference**: See [Dynamic Context Injection Specs](https://www.google.com/search?q=Dynamic_Context_Injection_Specs.md) for detailed routing logic.

## **3\. The Guard Lifecycle**

1. **Interception**: The Engine pauses the UOW workflow at a designated Guard Point.  
2. **Evaluation**:  
   * The Guard receives the payload (Input or Output).  
   * It retrieves the specific Rule Set defined in the YAML.  
   * It performs the check (LLM call or Code execution).  
3. **Verdict**:  
   * **PASS**: The UOW continues to the next step.  
   * **FAIL**:  
     * **Blocking**: The UOW is halted. A Violation event is logged.  
     * **Correction**: (Optional) The Guard returns feedback to the Agent for a retry.  
   * **MUTATE** (Injectors only): The UOW metadata (model, prompt) is updated, and the UOW continues.

## **4\. Configuration Schema**

Guards are defined in the Workflow YAML:

guards:  
  \- id: output\_safety\_check  
    type: semantic  
    rules:  
      \- "No profanity allowed"  
      \- "Must mention the company name"  
    retry\_limit: 3

## **5\. Logging & Audit**

All Guard evaluations are logged to the **ShadowLogger**.

* **Success**: Logged as GUARD\_PASS.  
* **Failure**: Logged as GUARD\_FAIL with the specific rule violated and the raw input.  
* **Mutation**: Logged as CONTEXT\_INJECTION with the applied overrides.