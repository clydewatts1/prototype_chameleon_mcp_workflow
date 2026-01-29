# **Implementation Guide: Attribute-Driven Branching**

This document defines the standards for implementing attribute-based Unit of Work (UOW) routing using the interaction\_policy. It ensures that routing is dynamic, robust, and decoupled from the execution roles.

## **1\. The Policy Configuration (YAML)**

The interaction\_policy is stored in the database as JSONB. It defines a set of branches that the Semantic Guard evaluates immediately following an interaction outbound.

interaction\_policy:  
  type: "branching"  
  evaluator: "attribute\_check"  
  target\_attribute: "risk\_score"  
  branches:  
    \# 1\. Complex Math & Logic: Arithmetic and Boolean grouping  
    \- condition: "((normalize\_score(score) \* 10\) \+ abs(offset\_value)) / 2 \> 8"  
      action: "proceed"  
      next\_state: "auto\_process\_critical"

    \# 2\. Universal Functions: min, max, abs supported natively  
    \- condition: "max(score, previous\_batch\_score) \< 0.3 and not is\_flagged"  
      action: "proceed"  
      next\_interaction: "low\_risk\_handler"

    \# 3\. Specific Error Handling: Explicit 'Catch' block for evaluation errors  
    \- on\_error: true   
      action: "escalate"  
      next\_state: "PENDING\_PILOT\_ADJUDICATION"

    \# 4\. Fallback (Else): The mandatory safety exit  
    \- default: true  
      action: "proceed"  
      next\_interaction: "standard\_processor"

## **2\. Expression Capabilities**

The Semantic Guard utilizes a secure expression engine capable of processing:

* **Arithmetic:** \+, \-, \*, /, % (modulo).  
* **Boolean Logic:** and, or, not, and parentheses (...) for precedence.  
* **Comparison:** \<, \<=, \>, \>=, \==, \!=.  
* **Universal Functions:** abs(), min(), max(), round(), floor().  
* **Custom Functions:** Registered system-specific calls like normalize\_score(value).  
* **Context:** The target\_attribute is mapped to score. All other UOW attributes are injected as local variables.

## **3\. Evaluation & Error Handling Protocol**

To satisfy the **Safety First** pillar, the Guard follows this strict execution sequence:

1. **Sequential Attempt:** Evaluations proceed top-to-bottom. The first condition that returns True is executed.  
2. **Silent Failure (Next-on-Error):** If an expression causes an error (e.g., divide-by-zero, missing variable), the Guard logs the error to the **Shadow Logger** and moves to the next branch.  
3. **The "Catch" Block:** If a branch contains on\_error: true, it triggers ONLY if a *previous* branch failed due to an execution error.  
4. **The "Else" Block:** The default: true branch is the final fallback, triggered if no conditions match or all previous branches errored out.

## **4\. Architectural Decoupling (The Outbound Contract)**

To maintain modularity, the relationship between Roles and Guards is strictly decoupled:

* **The Component (Data Provider):** Roles/Agents are "logic-blind." They fulfill their **Outbound Contract** by emitting specific attributes (e.g., risk\_score: 0.85) into the UOW payload. They do not know where the UOW goes next.  
* **The Guard (Navigator):** Holds the **Routing Contract**. It intercepts the UOW post-execution, reads the interaction\_policy, and executes the "Fork in the Road" choice based on the component's data.

## **5\. Visual Representation (Mermaid)**

When visualizing these policies in the Pilot Dashboard, the following decision diamond standard must be used:

graph TD  
    Start((Interaction Outbound)) \--\> Eval{Semantic Guard: Evaluate Attributes}  
      
    Eval \-- "normalize\_score(score) \> 8" \--\> StateCrit\[\[State: auto\_process\_critical\]\]  
    Eval \-- "max(score, prev) \< 0.3" \--\> ToolLow\[Tool: low\_risk\_handler\]  
    Eval \-- "Evaluation Error" \--\> PilotWait\[\[State: PENDING\_PILOT\_ADJUDICATION\]\]  
    Eval \-- "Default/Else" \--\> ToolStd\[Tool: standard\_processor\]

    style PilotWait fill:\#f96,stroke:\#333  
    style StateCrit fill:\#f66,stroke:\#333

## **6\. Atomic Verification & Traceability**

Every branching decision is recorded in the uow\_history table:

* **Input Hash:** The hash of the UOW before evaluation.  
* **Context:** The specific values of the variables used during evaluation.  
* **Result:** The Boolean outcome of the expression and the resulting destination.  
* **Execution Log:** Any silent errors captured during the evaluation process.