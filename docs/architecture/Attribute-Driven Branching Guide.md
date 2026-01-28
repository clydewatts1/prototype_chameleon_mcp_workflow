# **Implementation Guide: Attribute-Driven Branching**

This guide illustrates how to implement attribute-based UOW routing using the interaction\_policy, featuring advanced arithmetic, functional transformations, and robust error handling.

## **1\. The Policy Configuration (YAML)**

The interaction\_policy supports complex expressions. Variables in the condition string are automatically mapped to UOW attributes provided by the interaction outbound.

interaction\_policy:  
  type: "branching"  
  evaluator: "attribute\_check"  
  target\_attribute: "risk\_score"  
  branches:  
    \# 1\. Complex Math & Logic: uses arithmetic (+, \-, \*, /) and grouping  
    \- condition: "((normalize\_score(score) \* 10\) \+ abs(offset\_value)) / 2 \> 8"  
      action: "proceed"  
      next\_state: "auto\_process\_critical"

    \# 2\. Universal Functions: min, max, abs are supported natively  
    \- condition: "max(score, previous\_batch\_score) \< 0.3 and not is\_flagged"  
      action: "proceed"  
      next\_interaction: "low\_risk\_handler"

    \# 3\. Specific Error Handling: You can define an explicit error branch  
    \- on\_error: true   
      action: "escalate"  
      next\_state: "PENDING\_PILOT\_ADJUDICATION"

    \# 4\. Fallback (Else)  
    \- default: true  
      action: "proceed"  
      next\_interaction: "standard\_processor"

## **2\. The Outbound Contract**

To maintain decoupling, the relationship between a Role and a Guard is managed via the **Outbound Contract**.

* **Interaction Outbound:** The state of the UOW immediately after a Role/Agent completes its task.  
* **Attribute Mapping:** The component is required to "emit" specific attributes into the UOW payload upon completion. It is unaware of the routing logic; it simply fulfills its contract to provide the data.  
* **The Hand-off:** The moment the interaction moves "outbound," the Semantic Guard intercepts the payload. The Guard uses the interaction\_policy to determine the relationship between the emitted attributes and the next destination.

## **3\. Expression Capabilities**

The **Semantic Guard** utilizes a high-performance expression engine with the following capabilities:

* **Arithmetic Operations:** Full support for \+, \-, \*, /, and modulo %.  
* **Boolean Logic:** Use of and, or, not, and parentheses (...) for complex nesting.  
* **Universal Functions:** Native support for abs(), min(), max(), round(), and floor().  
* **Custom Functions:** Ability to call registered system-specific functions like normalize\_score().  
* **Context Injection:** The target\_attribute is mapped to score. All other top-level UOW attributes (e.g., offset\_value, is\_flagged) are injected as local variables.

## **4\. Evaluation & Error Handling Protocol**

To satisfy the **Safety First** pillar of the Constitution, the Guard follows a strict evaluation sequence:

1. **Sequential Attempt:** The Guard attempts to evaluate branches from top to bottom.  
2. **Silent Failure (Next-on-Error):** If an expression causes an error (e.g., AttributeError, ZeroDivisionError), the Guard **silently logs the error** to the Shadow Logger and moves immediately to the next branch in the list.  
3. **Explicit Error Branch:** If a branch contains on\_error: true, it acts as a "Catch" block. If any *previous* branch failed due to an execution error, this branch is triggered.  
4. **Default/Else:** If no conditions match or if all previous conditions errored out, the default: true branch is executed.

## **5\. Architectural Decoupling: Component vs. Guard**

To maintain modularity and compliance with the **Workflow Constitution**, the relationship between components and routing logic must be decoupled:

* **The Component (Data Provider):** Responsible solely for **execution**. It must be "logic-blind"—meaning it should not know where the UOW goes next. It simply updates the UOW attributes (e.g., setting risk\_score: 0.85) as its outbound contribution.  
* **The Guard (Navigator):** Holds the **Routing Contract**. It intercepts the UOW post-execution, reads the interaction\_policy (the relationship definition), and executes the branching logic based on the component's outbound data.

## **6\. Visual Representation (Flow Diagramming)**

When documenting or visualizing the interaction\_policy, the "Outbound Flow" must be represented using decision diamonds.

### **Mermaid Visualization Standard**

graph TD  
    Start((Interaction End/Outbound)) \--\> Eval{Semantic Guard: Evaluate Outbound Attributes}  
      
    Eval \-- "normalize\_score(score) \> 8" \--\> StateCrit\[\[State: auto\_process\_critical\]\]  
    Eval \-- "max(score, prev) \< 0.3" \--\> ToolLow\[Tool: low\_risk\_handler\]  
    Eval \-- "Evaluation Error" \--\> PilotWait\[\[State: PENDING\_PILOT\_ADJUDICATION\]\]  
    Eval \-- "Default/Else" \--\> ToolStd\[Tool: standard\_processor\]

    style PilotWait fill:\#f96,stroke:\#333  
    style StateCrit fill:\#f66,stroke:\#333

## **7\. Atomic Verification Trace**

| Sequence | Event Type | Details | Status |
| :---- | :---- | :---- | :---- |
| 4 | INTERACTION\_OUTBOUND | Role 'Scorer' emitted risk\_score: 0.75 | **SUCCESS** |
| 5 | EVALUATE\_BRANCH | Expression: (normalize\_score(0.75) \> 0.8) \-\> Result: False | **LOGGED** |
| 6 | BRANCH\_TRIGGERED | Policy: 'branching' \-\> Result: 'default' | **SUCCESS** |

## **8\. Key Takeaways**

* **The "Fork in the Road":** The Role Interaction provides the raw material (attributes), and the Guard interprets the roadmap (policy) to choose the path. The interaction defines the relationship, but the Guard executes the choice.  
* **Outbound Contract:** The Role provides the "What"; the Guard provides the "Where."  
* **Decoupling:** Keep components focused on *what* they do; keep Guards focused on *where* work goes.  
* **Robustness:** Expressions are treated as "suggestions." If they break, the system falls back to the next safest path.