# **Memory & Learning Specifications**

This document establishes the architecture for the **Memory Hierarchy** and **Adaptive Learning** mechanisms within the Chameleon Workflow Engine, fulfilling the requirements of Article III (Memory Hierarchy) and Article XX (Memory Governance).

## **1\. The Memory Hierarchy (Article III)**

The engine implements a three-tier memory structure to balance isolation with shared learning.

### **1.1 Ephemeral Memory (Transactional)**

* **Scope:** Single Unit of Work (UOW).  
* **Storage:** WorkflowUnitOfWorkAttributes table.  
* **Lifecycle:** Born with UOW, Archived with UOW.  
* **Access:** Only the assigned Actor, during the IN\_PROGRESS state.

### **1.2 The Personal Playbook (Actor-Role Specific)**

* **Scope:** Specific Actor executing a specific Role (e.g., Actor\_123 acting as Approval\_Role).  
* **Storage:** WorkflowRoleAttributes table (where context\_id \= actor\_id and context\_type \= 'ACTOR').  
* **Purpose:** Stores an Actor's personal preferences, shorthand, or learned patterns.  
* **Example:** "When reviewing invoices from Vendor X, I usually check for tax code Y."

### **1.3 The Global Blueprint (Role Wide)**

* **Scope:** All Actors assigned to a specific Role.  
* **Storage:** WorkflowRoleAttributes table (where context\_id \= 'GLOBAL' and context\_type \= 'ROLE').  
* **Purpose:** Institutional knowledge, standard operating procedures, and "Best Practices" distilled from successful executions.  
* **Example:** "Invoices \> $10k require Director approval (Rule learned from past rejections)."

## **2\. The Learning Loop (Adaptive Mechanism)**

Learning is not automatic; it is a deliberate process triggered by the successful completion of work.

### **2.1 Experience Extraction (The Harvest)**

**Trigger:** UOW reaches COMPLETED status.

**Action:** The engine (or the AI Agent Actor) scans the completed UOW for "Novel Patterns."

* **Novelty Detection:** Does this UOW contain a decision path or attribute combination not present in the Playbook?  
* **Consolidation:** If novel, the pattern is summarized and written to the **Personal Playbook**.

### **2.2 Knowledge Promotion (The Graduation)**

**Trigger:** A pattern appears frequently in multiple Personal Playbooks (configurable threshold, e.g., 5 Actors or 100 executions).

**Action:** The System promotes the pattern from **Personal** to **Global**.

* **Promotion Logic:** Copy the attribute/rule to the Global Blueprint context.  
* **Benefit:** New Actors assigned to the role immediately benefit from the experience of veteran Actors.

## **3\. Memory Governance (Article XX)**

To prevent "Adaptive Decay" (learning bad habits), the engine enforces strict governance rules.

### **3.1 The Toxic Knowledge Filter**

**Trigger:** A UOW reaches FAILED status and requires Epsilon remediation, OR an Admin flags a result as incorrect.

**Action:**

1. **Trace:** Identify the Memory Attributes (Playbook/Blueprint) that influenced the failed decision.  
2. **Flag:** Mark those attributes as is\_toxic \= TRUE.  
3. **Quarantine:** Toxic attributes are effectively invisible to Actors during execution.  
4. **Purge:** Toxic attributes are hard-deleted after a retention period (e.g., 30 days).

### **3.2 Relevance Decay (The Janitor)**

**Problem:** Memory bloat slows down inference and decision making.

**Mechanism:**

* Every Memory Attribute has a last\_accessed\_at timestamp.  
* **The Decay Job:** A background process (part of the Tau Role duties) scans for attributes where last\_accessed\_at \< NOW \- MEMORY\_TTL (e.g., 90 days).  
* **Action:** Archive and delete expired memories.

## **4\. Data Schema for Memory**

The WorkflowRoleAttributes table serves as the physical store for both Playbooks and Blueprints.

CREATE TABLE WorkflowRoleAttributes (  
    id UUID PRIMARY KEY,  
    role\_id UUID NOT NULL REFERENCES Template\_Roles(id),  
      
    \-- Context Discriminator  
    context\_type VARCHAR(20) CHECK (context\_type IN ('GLOBAL', 'ACTOR')),  
    context\_id VARCHAR(255) NOT NULL, \-- 'GLOBAL' or Actor\_UUID  
      
    \-- The Knowledge  
    key VARCHAR(255) NOT NULL,  
    value JSONB NOT NULL, \-- The learned rule/pattern  
    confidence\_score FLOAT DEFAULT 0.5, \-- 0.0 to 1.0  
      
    \-- Governance  
    is\_toxic BOOLEAN DEFAULT FALSE,  
    created\_at TIMESTAMP DEFAULT NOW(),  
    last\_accessed\_at TIMESTAMP DEFAULT NOW(),  
      
    UNIQUE(role\_id, context\_type, context\_id, key)  
);

## **5\. Interface for Actors (The Access Pattern)**

Actors (Human or AI) access memory via the standard Context object provided at checkout.

**Read Access:**

When an Actor checks out a UOW, the engine injects a merged view of memory:

Effective\_Memory \= Global\_Blueprint \+ Personal\_Playbook (Override)

**Write Access:**

Actors do not write to memory directly. They output "Insights" or "Decisions" in the UOW result. The **Engine** is responsible for deciding if that result warrants a memory update (see Section 2.1).