# **Guard Behavior Specifications**

This document establishes the implementation logic for **Workflow Guardians**, the active components responsible for filtering, aggregating, and dispatching Units of Work (UOW) between Interactions and Roles.

## **1\. General Guard Logic (The Standard Model)**

**Purpose:** To act as the "Supreme Filter" (Article I.3), ensuring that only authorized and valid UOWs enter a Role's isolated sandbox.

**Trigger Condition:**

1. **Push:** An Interaction notifies the Guard that new UOWs have arrived.  
2. **Pull:** An Actor requests work, triggering the Guard to fetch from the Interaction.

**Execution Cycle (The Article IX Protocol):**

1. **Aggregation (The Coalition Rule):**  
   * Guard scans Interaction holding area.  
   * Coalesces related UOWs (Base \+ Children) into a unified **Work Set**.  
   * *Constraint:* A Guard never passes a partial set unless explicitly configured (e.g., Streaming Mode).  
2. **Identity Validation (Article I.3):**  
   * Verify the requesting Actor allows the required role\_type.  
   * Ensure Actor is not currently locked in another sandbox.  
3. **Criteria Filtering (The Gate):**  
   * Evaluate UOW attributes against config.criteria (e.g., amount \> 1000).  
   * **PASS:** UOW remains in the "Approved" set.  
   * **FAIL:** UOW is flagged for the **Ate Path** (Article XI).  
4. **Dispatching:**  
   * **Approved Set:** Routed OUTBOUND to the destination Role.  
   * **Rejected Set:** Routed via ATE\_TRANSIT to the **Epsilon Role** (The Physician).

## **2\. Guard Type: PASS\_THRU (The Fast Lane)**

**Purpose:** Rapid initialization and transit where no data validation is required, only identity verification (Article VII.2).

**Use Case:** Alpha ![][image1] First Beta; or connecting trusted internal steps.

**Logic:**

1. **Identity Check:** Is the Actor assigned to this Role?  
   * *Yes:* Permit entry.  
   * *No:* Block access (Security Violation).  
2. **Data Check:** None (Blind pass).  
3. **Outcome:** Immediate dispatch to Role.

## **3\. Guard Type: CRITERIA\_GATE (The Filter)**

**Purpose:** Enforces business logic thresholds to determine eligibility for a specific Role.

**Use Case:** "High Value Approval" (Amount \> 10k) vs "Standard Approval".

**Config Input:**

* field: The UOW attribute to check (e.g., transaction\_total).  
* operator: GT, LT, EQ, CONTAINS.  
* threshold: The value to compare against.

**Logic:**

1. **Evaluation:** if UOW.attributes\[field\] \[operator\] threshold.  
2. **Branching:**  
   * **True:** Dispatch to **Primary Role**.  
   * **False:** Dispatch to **Alternate Path** (or Ate/Error path if no alternate defined).

## **4\. Guard Type: DIRECTIONAL\_FILTER (The Router)**

**Purpose:** Inspects a processed UOW and routes it to one of multiple downstream Interactions based on a result code (Article IX.2).

**Use Case:** A "Triage" Role that outputs categories like "Urgent", "Standard", "Spam".

**Config Input:**

* routing\_key: The attribute to inspect (e.g., classification).  
* routes: Map of values to destination IDs (e.g., {'Urgent': 'queue\_fast\_track', 'Spam': 'queue\_trash'}).

**Logic:**

1. **Read:** Retrieve value of routing\_key from UOW.  
2. **Lookup:** Find matching destination in routes map.  
3. **Dispatch:** Move UOW to the specific Interaction ID associated with that value.  
4. **Fallback:** If key missing, route to **Epsilon** (Configuration Error).

## **5\. Guard Type: CERBERUS (The Synchronizer)**

**Purpose:** The multi-headed synchronization guard that prevents "Zombie Parents" by enforcing the Three-Headed Check (Article VI).

**Trigger Condition:** Base UOW and Child UOWs approach Omega interaction; guard performs validation before allowing passage.

**Input Data:**

* Base UOW from holding area  
* All associated Child UOWs by parent\_id reference  
* Expected child\_count from Base UOW  
* Status values for all UOWs in set

**Execution Logic:**

### **Head 1: The Base Head**

1. Verify Parent Base UOW is present in the Interaction holding area  
2. Confirm Base UOW has valid identifier and non-null attributes  
3. Check that Base UOW status indicates readiness for completion

### **Head 2: The Child Head**

4. Query all Child UOWs with parent\_id matching Base UOW  
5. Count returned Child UOWs (finished\_child\_count)  
6. Compare against Base UOW child\_count (total children spawned)  
7. Verify: finished\_child\_count \== child\_count  
8. Confirm all expected children have returned from workflow cloud

### **Head 3: The Status Head**

9. Iterate through entire UOW set (Base \+ all Children)  
10. Verify each UOW status is terminal:  
    * Status must be "COMPLETED" or "FINALIZED"  
    * Reject any "IN\_PROGRESS", "FAILED", or intermediate statuses  
11. Confirm no partial work remains unfinished

### **Synchronization Decision:**

12. If all three heads validate successfully:  
    * Allow UOW set to pass through guard  
    * Route complete set to Omega Role for final reconciliation  
    * Log successful synchronization check  
13. If any head fails validation:  
    * Block passage to Omega  
    * Keep UOW set in Interaction holding area  
    * Log specific validation failure reason  
    * Wait for missing children or status updates  
14. Handle timeout scenarios:  
    * If synchronization blocked beyond threshold, escalate to Tau  
    * Tau may force terminal status or route to Epsilon

## **6\. Guard Type: COMPOSITE (The Chain)**

**Purpose:** Stacks multiple logical checks into a single atomic Gate operation, enabling complex validation pipelines without schema changes.

**Use Case:** "Check Amount \> 100" **AND** "Check VIP Status \= True" **AND** "Random Sample 10%".

**Config Input:**

* logic: AND (All must pass) | OR (First pass wins).  
* steps: Array of Guard configurations (each containing type and config).

**Logic:**

1. **Initialization:** Retrieve steps list from config.  
2. **Iteration:** Execute each step in sequence using the logic of its defined Type (CRITERIA\_GATE, etc.).  
3. **Evaluation (AND Logic):**  
   * If **ANY** step fails: Stop immediately. The Composite Guard outcome is **FAIL** (Ate Path).  
   * If **ALL** steps pass: The Composite Guard outcome is **PASS** (Dispatch).  
4. **Evaluation (OR Logic):**  
   * If **ANY** step passes: Stop immediately. The Composite Guard outcome is **PASS** (Dispatch).  
   * If **ALL** steps fail: The Composite Guard outcome is **FAIL** (Ate Path).

**Terminal State:** Complete UOW set (Base \+ all Children) validated and passed to Omega; or incomplete set held in Interaction awaiting resolution.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAt0lEQVR4XmNgGAWjgDpAQUGBQ05OLk1UVJQHXY4cwCgvL98KNNAYXYIsADIIaGAvkMmCLkcOYAR6twBoaByIjSIDlBAA2iRJClZSUgKaJTcfyJ6soqLCBzZIXFycGyhQDcSzSMVAw3YA6a9A3Aw0kB3FhaQAWVlZE6Ahq6WlpWXQ5UgCQAOEgQYtVlRUlEeXIxkADcoChnMEujjJAJRogYZNlZGRkUaXIwcwqqur84JodIlRMMAAAJV7J+RoCL8jAAAAAElFTkSuQmCC>