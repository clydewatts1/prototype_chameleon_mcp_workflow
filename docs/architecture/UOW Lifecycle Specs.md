# **Unit of Work (UOW) Lifecycle Specifications**

This document establishes the physics and lifecycle rules for the **Unit of Work (UOW)**, the atomic container of state within the Chameleon Workflow Engine. It defines the State Machine, Data Versioning protocols, and Cloning mechanics required to satisfy the Constitution.

## **1\. The UOW Definition**

**Core Concept:** A UOW is a self-contained envelope comprising:

1. **Identity:** Unique uow\_id, parent\_id (if child), and workflow\_id.  
2. **State:** Current status (The Lifecycle Stage).  
3. **Payload:** The attributes JSON blob (The Business Data).  
4. **Lineage:** The history log (The Audit Trail).

## **2\. The State Machine (Valid Transitions)**

To ensure process integrity, UOWs may only transition between states along specific, pre-defined vectors. "Teleportation" between unconnected states is forbidden (except via Admin Intervention).

### **2.1 The States**

| Status | Definition | owner |
| :---- | :---- | :---- |
| **INITIALIZED** | Born in Alpha role. Attributes populated. Not yet in queue. | System |
| **CREATED** | Born in Beta role (Child UOW). Linked to Parent. | System |
| **PENDING** | Sitting in an Interaction (Queue). Available for pickup. | Interaction |
| **IN\_PROGRESS** | Locked by an Actor. Invisible to others. | Actor |
| **COMPLETED** | Work finished successfully by Actor. Ready for next step. | System |
| **FAILED** | Work failed (Error/Crash) or Rejected by Guard. | System |
| **REMEDIATED** | Fixed by Epsilon role. Ready for re-verification. | Epsilon |
| **TIMEOUT** | Expired in queue (Chronos Path). | Tau |
| **FINALIZED** | Reconciled by Omega. Terminal state. | Omega |
| **ARCHIVED** | Moved to cold storage. Removed from active set. | System |

### **2.2 Valid Transition Matrix**

| From State | To State | Trigger | Context |
| :---- | :---- | :---- | :---- |
| INITIALIZED | PENDING | Alpha Handoff | Entry to first Interaction |
| CREATED | PENDING | Beta Handoff | Entry to Interaction |
| PENDING | IN\_PROGRESS | **Guard Pull** | Actor locks token (Checkout) |
| IN\_PROGRESS | COMPLETED | **Actor Success** | Work finished |
| IN\_PROGRESS | FAILED | **Actor Error** | Exception or Criteria Rejection |
| IN\_PROGRESS | PENDING | **Lock Timeout** | Actor crash / Lease expiry |
| FAILED | IN\_PROGRESS | **Guard Pull** | Epsilon picks up for fix |
| FAILED | FINALIZED | **Omega Pull** | Terminal failure (Abort) |
| REMEDIATED | PENDING | **Epsilon Success** | Return to main flow |
| PENDING | TIMEOUT | **Tau Sweep** | Stale Token Limit exceeded |
| TIMEOUT | FAILED | **Tau Escalation** | Mark as dead |
| COMPLETED | FINALIZED | **Omega Sync** | Cerberus Validated |

**Forbidden Transitions (Examples):**

* FAILED ![][image1] COMPLETED (Must go through REMEDIATED or be reset).  
* PENDING ![][image1] FINALIZED (Must be processed first).

## **3\. Atomic Versioning (The Data Physics)**

**Article XVII Mandate:** "Attribute updates must not overwrite previous states; they must append to a versioned lineage."

### **3.1 The Attribute Protocol**

* **Current State:** The attributes column holds the *latest* valid JSON state.  
* **Lineage:** The history table (or JSON array) holds the delta of every change.

### **3.2 The Write Operation**

When an Actor (or Admin) updates a UOW:

1. **Calculate Diff:** Compare new\_attributes vs current\_attributes.  
2. **Generate Event:** Create a history record:  
   {  
     "event\_id": "uuid",  
     "timestamp": "ISO8601",  
     "actor\_id": "actor\_123",  
     "action": "UPDATE\_ATTRIBUTES",  
     "reason": "Enriched customer data",  
     "changes": {  
       "email": { "old": "null", "new": "bob@example.com" }  
     }  
   }

3. **Atomic Commit:** Write current\_attributes AND history\_record in the same transaction.

## **4\. Recursive Cloning (The Sigma Protocol)**

When a UOW enters a **Sigma Role** (Recursive Gateway), it undergoes **Deep Copy Replication**.

### **4.1 The Cloning Logic**

1. **Source:** The active UOW in the Sigma Role.  
2. **Action:** The **Hermes Interaction** triggers the Cloner.  
3. **Transformation:**  
   * Generate NEW uow\_id (The Instance Token).  
   * Set origin\_uow\_id \= Source UOW ID (Linkage).  
   * Copy attributes (Payload).  
   * **Reset Lineage:** The new token starts with a clean history (Privacy).  
   * Set workflow\_id \= Child Workflow ID.  
4. **Injection:** The new token is placed in INITIALIZED state at the Child **Alpha Role**.

### **4.2 The Return Logic (Iris)**

1. **Source:** The Finalized UOW at Child **Omega Role**.  
2. **Action:** The **Iris Interaction** triggers the Merger.  
3. **Transformation:**  
   * Retrieve Parent UOW via origin\_uow\_id.  
   * Update Parent attributes with Child results (configurable merge strategy).  
   * Log "Recursion Completed" event in Parent history.  
4. **Resume:** Parent UOW moves to COMPLETED state in the Sigma Role.

## **5\. Cleanup & Archival**

To maintain engine performance, UOWs cannot remain in the active database forever.

**The Omega Protocol:**

1. **Trigger:** UOW reaches FINALIZED state.  
2. **Archival:** Move full record (Header \+ Attributes \+ History) to Cold\_Store (Data Warehouse / S3).  
3. **Purge:** Hard delete from Active\_Transactions table.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAAt0lEQVR4XmNgGAWjgDpAQUGBQ05OLk1UVJQHXY4cwCgvL98KNNAYXYIsADIIaGAvkMmCLkcOYAR6twBoaByIjSIDlBAA2iRJClZSUgKaJTcfyJ6soqLCBzZIXFycGyhQDcSzSMVAw3YA6a9A3Aw0kB3FhaQAWVlZE6Ahq6WlpWXQ5UgCQAOEgQYtVlRUlEeXIxkADcoChnMEujjJAJRogYZNlZGRkUaXIwcwqqur84JodIlRMMAAAJV7J+RoCL8jAAAAAElFTkSuQmCC>