# **UOW Lifecycle Specifications**

## **1\. State Machine Transitions**

### **1.1 Atomic Progression**

A UOW moves through a strictly gated sequence. Every transition requires a **State Hash Verification**.

## **2\. Interaction Routing & Policy**

To prevent aimless "wandering" or unauthorized tool usage, every UOW is governed by an **Interaction Policy**.

### **2.1 Routing Mechanics**

1. **Sequential Locking:** Enforces a strict order of tool calls (e.g., Read\_Context \-\> Generate\_Draft \-\> Validate\_Syntax). Any attempt to call tools out of order results in an automated Guard block.  
2. **Branching Logic:** Defines conditional paths based on interaction outcomes. For example, if a validation tool returns a "Low Confidence" score, the policy forces the flow to a PENDING\_PILOT\_APPROVAL state rather than proceeding.  
3. **Pilot Pulse:** A mandatory check-in mechanism. After a set number of interactions (e.g., every 5 steps), the policy requires a Pilot "Heartbeat" (approval or acknowledgment) before further processing is permitted.

## **3\. The Zombie Protocol**

### **3.1 Ambiguity Lock Detection**

* **Interaction Counter:** Every UOW maintains a MAX\_INTERACTIONS limit.  
* If an Agent makes too many calls without reaching a state transition, the UOW is "Zombied" as an Ambiguity Lock.

### **3.2 Timeout Classification**

1. **Soft Timeout (Recoverable):** Transient failures. The system attempts a RETRY based on the UOW's retry\_policy.  
2. **Absolute Dead Timeout (Terminal):** A fatal logic flaw. The UOW is moved to DEAD\_LETTER for Pilot adjudication.

## **4\. Refinement State**

Before a UOW is moved to ARCHIVED, it passes through a **REFINEMENT\_ANALYSIS** phase where the **Librarian** evaluates efficiency.