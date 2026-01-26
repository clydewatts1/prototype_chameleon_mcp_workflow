# **📜 THE CHAMELEON WORKFLOW CONSTITUTION**

This document establishes the fundamental laws governing the interaction between **Actors**, **Roles**, **Interactions**, and **Units of Work (UOW)** to ensure absolute isolation, structural integrity, and adaptive learning within the Chameleon Workflow Engine.

## **ARTICLE I: The Principle of Total Isolation**

1. **The Sandbox Rule**: Every execution cycle for a Unit of Work (UOW) or a set of UOWs must occur within a strictly isolated sandbox.  
2. **No Cross-Contamination**: An Actor is forbidden from accessing data, context, or attributes from any UOW or Role outside of their current active assignment.  
3. **The Guard’s Mandate**: The WorkflowGuardian acts as the supreme filter. It ensures only authorized UOWs pass to a Role and verifies that the Actor is locked into the correct context before processing begins.

## **ARTICLE II: The Actor (Responsible Resource)**

1. **Definition**: An **Actor** is a responsible resource and a unique identity within the engine.  
2. **Actor Types**: The engine recognizes **HUMAN**, **AI\_AGENT**, and **SYSTEM (Auto Role)** types.  
3. **Identity vs. Capability**: The Actor provides identity; the **Role** provides the functional specification.  
4. **Multi-Role Capability**: Actors may hold multiple roles but execute only within the sandbox granted by the Guard.

## **ARTICLE III: The Memory Hierarchy**

1. **Ephemeral Memory**: WorkflowUnitOfWorkAttribute (Transactional, non-persistent).  
2. **The Personal Playbook**: WorkflowRoleAttribute (Actor-Role specific long-term memory).  
3. **The Global Blueprint**: WorkflowRoleAttribute (Role-wide shared memory, context=GLOBAL).

## **ARTICLE IV: Interaction Dynamics**

1. **Holding Areas**: The **Interaction** is the primary holding area for UOWs.  
2. **Components**: WorkflowInteractionComponents define Inbound/Outbound flow.  
3. **Transformation**: UOWs are "Complete" only when terminal status and attributes are finalized.

## **ARTICLE V: The Functional Role Types & Decomposition**

Workflows are composed of standardized functional roles. To balance integrity with flexibility, the engine supports configurable decomposition strategies.

### **1\. Structural Roles**

These roles define the lifecycle and topology of the workflow.

* **Alpha (![][image1]) (The Origin)**: Instantiates the Base UOW (Root Token).  
* **Omega (![][image2]) (The Terminal)**: Reconciles and finalizes the complete UOW set.  
* **Epsilon (![][image3]) (The Physician)**: The Error Handling Role responsible for remediating explicit data failures.  
* **Tau (![][image4]) (The Chronometer)**: The Timeout Role responsible for managing stale or expired tokens.  
* **Sigma (![][image5]) (The Gateway)**: A specialized Beta role which executes another nested WORKFLOW.

### **2\. Processing Roles (The "Beta" Family)**

These roles perform the actual work. While functionally acting as **Beta (![][image6])** nodes (decomposing and processing), they are classified by their execution requirements.

* **Beta (![][image6]) (The Processor)**: The generic processor role. Decomposes Base UOW into Child UOWs.  
  * **Configurable Decomposition Strategy**: Every ![][image6] role must be configured with a specific strategy (HOMOGENEOUS or HETEROGENEOUS).  
* **Human (**HUMAN**) (The Approver)**: A specialized Beta role requiring manual intervention. It explicitly pauses execution until a Human Actor provides input.  
* **AI Agent (**AI\_AGENT**) (The Intelligence)**: A specialized Beta role driven by an autonomous agent. It utilizes the ai\_context to perform reasoning tasks.  
* **Auto (**AUTO**) (The Script)**: A specialized Beta role for deterministic system tasks (e.g., API calls, calculations) requiring no intelligence or human delay.

## **ARTICLE VI: The Cerberus Synchronization**

The **Cerberus Guard** prevents "Zombie Parents" from reaching Omega by enforcing a Three-Headed Check:

1. **The Base Head**: The Parent Base UOW is present in the Interaction holding area.  
2. **The Child Head**: Every Child UOW associated with the parent (via parent\_id) has returned from the workflow cloud.  
3. **The Status Head**: Every UOW in the set has achieved a status of completed or finalized.

## **ARTICLE VII: Transit Path and Guard Logic**

1. **Standard Transit**: ![][image7].  
2. **Pass-Thru Guards**: Identity-only validation for rapid initialization and remediation transit.  
3. **The Eternal Loop**: Optional re-routing from ![][image2] back to ![][image1].  
4. **Cycle Safety Protocol**:  
   * **Allowed Cycles**: Internal loops (e.g., "Critique and Refine") are permitted to facilitate iterative improvement by AI Agents.  
   * **Mandatory Exit Condition**: Every cycle must be protected by a **Guardian** that enforces a termination condition (e.g., "Max Retries" or "Quality Threshold Met").  
   * **Safety Valve**: The **Tau (![][image4]) Role** serves as the ultimate failsafe for any cycle, forcefully terminating loops that exceed the global timeout.

## **ARTICLE IX: The Guard as Aggregator and Dispatcher**

1. **Inbound Aggregation (Gathering)**:  
   * **Coalition Rule**: The Guard fetches UOWs and coalates them into a unified **Work Set**.  
   * **Attribute Filtering (Criteria Gate)**: Enforces data-driven thresholds (e.g., TRANSACTION\_AMOUNT \> 1000).  
2. **Outbound Dispatching (Direction)**:  
   * **Post-Processing Wait**: The Guard waits until a complete set has finished processing before dispatching.  
   * **Directional Filtering**: Routes UOW sets to next interactions based on specific attribute results.

## **ARTICLE XI: Fault Tolerance and Resilience Paths**

### **1\. The Ate Path (Explicit Data Error)**

* **Trigger**: A Guard detects a UOW set failing explicit user criteria (e.g., AMOUNT \< 10).  
* **Transit**: ![][image8].  
* **Resolution**: The ![][image3] Role remediates the data and dispatches the set back to the **Interaction (Cerberus)** for final synchronization.

### **2\. The Stale Token Protocol (The Chronos Path)**

* **Trigger**: A UOW remains in an Interaction beyond the STALE\_TOKEN\_LIMIT.  
* **Transit**: ![][image9].  
* **Resolution**: The ![][image4] Role manages "forced-end" transitions, typically escalating to the ![][image3] **Role** before routing the set to the **Interaction (Cerberus)**.

### **3\. The Zombie Actor Protocol**

The Zombie Actor Protocol ensures that Units of Work do not remain indefinitely in an ACTIVE state due to Actor failure, system crashes, or network disruptions. The ![][image4] (Tau) Role monitors execution health and reclaims stalled work.

* **Passive Heartbeat**: Actors processing a UOW must periodically update the `last_heartbeat` timestamp in the UnitsOfWork table. This signals active execution.
* **Active Sweep**: The ![][image4] Role continuously monitors for UOWs with status `ACTIVE` where `last_heartbeat` exceeds a configurable threshold (e.g., 5 minutes).
* **Reclamation**: When a Zombie Actor is detected, ![][image4] forces the affected UOW to either:
  * **FAILED** status: For immediate escalation to the ![][image3] (Epsilon) Role for remediation.
  * **PENDING** status: For automatic re-queuing if the failure is transient (e.g., network timeout).

This protocol protects the workflow from "silent" Actor failures and ensures all work is either completed, remediated, or explicitly terminated.

## **ARTICLE XIII: Recursive Workflows (Nesting)**

A Role may be defined as a **Recursive Gateway**, where a Parent Workflow Role delegates execution to an independent Child Workflow.

1. **The Principle of Protected Replication**: To protect the integrity of the Parent Workflow, the entry point operates on a **Deep Copy** of the UOW set.  
2. **The Hermes Entry Point (Outbound)**: The **Hermes Interaction** serves as the gateway for replication and injection into the Child Workflow.  
3. **Double-Guarded Boundary**: The recursive boundary is guarded on both sides at the Hermes and Iris interfaces.  
4. **The Iris Exit Point (Inbound)**: Upon reaching the Child's ![][image2] role, results pass through the **Iris Interaction** to manage state-sync back to the Parent Workflow Role.  
5. **Recursive Instantiation (The Dependency Walker)**:  
   * **Pre-Flight Resolution**: When an Instance is created, the engine must resolve all recursive references. The engine must clone not only the Master Blueprint but also every Child Workflow referenced by any Role within the hierarchy.  
   * **Runtime Independence**: Lazy loading is forbidden. The Instance must contain a complete, local copy of the entire dependency tree at the moment of creation, ensuring the engine never needs to contact the Meta-Store during execution.

## **ARTICLE XV: Role Ownership and Master-Child Federation**

To maintain structural integrity and prevent context leakage, the engine enforces strict ownership rules within an Instance Context.

1. **Master-Child Federation**: A single Instance Context may contain multiple cloned workflows. One workflow is designated as the **Master (Entry Point)**, while all others are designated as **Dependencies (Children)**.  
2. **Internal Linking**: Connections between workflows within an instance are only permitted via the linked\_local\_workflow\_id property of a Recursive Gateway Role. Arbitrary cross-linking is forbidden.  
3. **Reusability via Cloning**: Functional requirements are replicated by cloning role definitions into the new context.

## **ARTICLE XVII: Observability and Traceability**

To ensure accountability and system health, the engine enforces a strict audit trail for every action.

1. **The Law of the Immutable Audit**: All interactions between a Role and an Interaction must be logged. Every transition (Inbound or Outbound) must record the Actor ID, Role ID, Interaction ID, and a Timestamp.  
2. **UOW Travel Traceability**: The travel of every UOW (Base or Child) must be traceable from its point of origin (![][image1] or ![][image6]) to its terminal reconciliation (![][image2]).  
3. **Historical Lineage**: Any modification to a UOW's attributes must be recorded as a historical event.  
   * **Atomic Versioning**: Attribute updates must not overwrite previous states; they must append to a versioned lineage.  
   * **Attribution and Intent**: For every modification, the system must capture the "Reasoning" or "Contextual Intent" provided by the Actor.

## **ARTICLE XIX: Data Lifecycle and Terminal Disposition**

The **Omega (![][image2]) Role** is the designated steward of the workflow's terminal state and data lifecycle.

1. **Mandatory Archiving of the Base**: Upon final reconciliation, the ![][image2] role must archive the **Base UOW**, including its terminal status, core metadata, and the historical lineage of its primary attributes.  
2. **Configurable Child Disposition**: The disposition of Child UOWs is a configurable policy within the ![][image2] role:  
   * **Archive Mode**: Full historical retention of all child tokens and their attributes.  
   * **Prune Mode**: Deletion of all child UOWs and attributes once the Base UOW has been successfully finalized and archived.  
   * **Selective Mode**: Archiving of specific child UOW types or those flagged with "High Priority" attributes, while deleting the remainder.  
3. **Terminal Cleanup**: Following successful archiving, the ![][image2] role is responsible for purging the active "Work Set" from the transactional database to maintain optimal engine performance.

## **ARTICLE XX: Memory Governance Policy**

To prevent "adaptive decay" and ensure the long-term health of the **Personal Playbook** and **Global Blueprint**, the engine enforces strict governance over stored experiences.

1. **Experience Validation**: Every memory entry in a Role's attribute set must be associated with a successfully completed **Base UOW**. Experiences gained from UOW sets that terminated in failure without successful remediation (Epsilon) are subject to immediate purge.  
2. **The Toxic Knowledge Filter**: The **Omega (![][image2]) Role** has the authority to flag specific attributes or decision paths as "Toxic." Flagged logic is automatically scrubbed from the Global Blueprint to prevent systemic recursion of errors.  
3. **Pruning and Decay**:  
   * **Active Pruning**: Actors or Developers may manually trigger a "Reset" of a Personal Playbook if an AI\_AGENT exhibits drifted behavior.  
   * **Relevance Decay**: Attributes in the Memory Hierarchy that have not been accessed by an Actor for a duration exceeding the MEMORY\_THRESHOLD shall be archived and removed from active role context.  
4. **Audit of Influence**: The engine must be able to report which "Global Blueprint" entries influenced a specific UOW decision, ensuring that adaptive learning is as traceable as transactional work.

## **ARTICLE XXI: Infrastructure Independence**

To ensure deployment flexibility across diverse environments, the engine mandates strict decoupling from specific infrastructure technologies.

1. **Database Agnosticism**: The Core Engine must remain agnostic to the underlying database vendor. All persistence logic must be implemented using a standard abstraction layer (ORM) compatible with major SQL engines (e.g., PostgreSQL, SQLite, MySQL).  
2. **Schema Portability**: Database schemas must be defined in a portable format. The reliance on vendor-specific features (e.g., proprietary stored procedures) is forbidden within the core logic to preserve the ability to migrate instances between different infrastructure providers.

## **ARTICLE XXII: Amendments**

This Constitution may be amended as the Chameleon Engine evolves, but the **Principle of Total Isolation** (Article I) shall remain the foundational pillar of the system.

## **APPENDIX: Glossary of Terms**

| Term | Definition |
| :---- | :---- |
| **Actor** | The "Who" of the system; a responsible resource (Human, AI, or System) with a unique identity. |
| **AI Agent** | A specialized Beta role driven by an autonomous agent. |
| **Alpha (![][image1])** | The starting role responsible for birthing the Base UOW container. |
| **Ate** | The interaction holding area for UOWs that fail explicit validation. |
| **Auto** | A specialized Beta role for deterministic system tasks. |
| **Base UOW** | The root container/token that holds the high-level task and all associated child work. |
| **Beta (![][image6])** | The processor role that breaks down a Base UOW into actionable Child UOWs. |
| **Cerberus** | The multi-headed synchronization guard that ensures integrity before final completion. |
| **Child UOW** | A granular task generated by a Beta role, linked to a Base UOW via parent\_id. |
| **Chronos** | The interaction holding area for UOWs that have exceeded their allowed time limit. |
| **Cloning** | The process of copying a role's specification into a new workflow. |
| **Dependency Walker** | The instantiation logic that resolves and clones all child workflow dependencies before execution. |
| **Epsilon (![][image3])** | The error-handling role (The Physician) that remediates data failures from the Ate path. |
| **Global Blueprint** | Shared role memory accessible to all actors assigned to a specific role. |
| **Guardian** | The active filter and orchestrator between Interactions and Roles. |
| **Hermes** | The gateway interaction responsible for replicating UOW sets for recursive workflows (Outbound). |
| **Heterogeneous Decomposition** | A strategy allowing a Beta role to generate different UOW types within a single set. |
| **Homogeneous Decomposition** | A strategy requiring all child UOWs in a set to be of the same UOW type. |
| **Human** | A specialized Beta role requiring manual intervention. |
| **Instance Context** | The container holding a specific deployment of a Master Workflow and all its dependencies. |
| **Interaction** | A passive holding area (waiting room) where UOWs reside between processing steps. |
| **Iris** | The gateway interaction responsible for synchronizing child results back to the parent (Inbound). |
| **Master Workflow** | The primary entry point workflow within an Instance Context. |
| **Omega (![][image2])** | The terminal role where the final results of a Base UOW and its children are reconciled. |
| **Pass-Thru** | A simplified Guard logic that validates identity but permits immediate transit of tokens. |
| **Personal Playbook** | Private role memory unique to an Actor-Role pair. |
| **Recursive Gateway** | A configuration where a Role’s execution is delegated to an entirely separate workflow. |
| **Sigma (![][image5])** | A specialized Beta role which executes another nested WORKFLOW. |
| **Tau (![][image4])** | The timeout-handling role (The Chronometer) that manages stale tokens from the Chronos path. |
| **Toxic Knowledge** | Decision logic or data flagged as erroneous or harmful, preventing its reuse in memory. |
| **Traceability** | The ability to reconstruct the complete travel path and attribute history of any Unit of Work. |
| **UOW** | Unit of Work; the fundamental atomic element of data and task tracking in the engine. |

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAVCAYAAACQcBTNAAAA9ElEQVR4XmNgGAUDAhQVFcXl5OR8FRQUHICYA10eDIASEvLy8muAeD2QHQGkq4H4iaysrAlIXkZGRhqsEGgaUFz+ChDPMjY2ZoXqZwHylwNt2QFUyAlk18AE54BMAWJFqEIwACosB4p9AtrkAWTPZwByNIH4LcgJII3IioFi0UD8FaQQqCEcpNsXKPAfyElHVggCMDkg3gxyCki3J0gAJIFD8R+gQfZgAWVlZVmgwG0gzkFSxwjkOwHxDZhB0tLSMmAZqMR9IF4NxHOB+AQQF6uoqIgC6W1Ak0+BQgXJMAZmoC1iQBOEQSYji0tJSYkgBelAAwCXNjoINhOi9AAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAVCAYAAACQcBTNAAAA9klEQVR4XmNgGAX0BIwKQGBsbMyKLgEC4uLi3HJycs5gDpDhCsQ7RUVFedDUgYG8vHw1EP9nkJGR4QQauhKIzdEVwYCioqI+UPErkC5LoMKJQDEWqBwjUCxaVlbWD1kD0Ob5IMU5QIYLTBBoijhQ7C4QtyKpZQHyJ4MUTwYqNoaJgthAsWcgG2FiQKeqAPmzwMYjWwl0UjhQ4rSKioooiA8KIaCaGUDxCJDJk4D4ORAXAfFsIP4BxP+AeB8QZwPxeaDCXeCQArrRDCjwHoj/A/FHIPYG4mIoH4SPSUtLy8BsBlnNAfIYcqQAxQSAioSBTEa4wsEBAHRfNkG0BhCNAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAVCAYAAACKTPRDAAAAn0lEQVR4XmNgGKHA2NiYVVFRURyE4YIqKip88vLyk4D4tZyc3AYgPQUsAVQlr6CgcAsoMEdGRoYTrgNkDFBwFRA/AWJFuAQIAAU0gfgtEP8CGvcIhoEmRTIAGcZAia9AuhxFFwgA7dMHSn7CKglyAFByM8hekP1QYUZxcXFuMAtovgRQcjtQ90EgPQuIDwNxNcIIIBAVFeUBeR7JBFoAALYVJAeyJKqqAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAWCAYAAAASEbZeAAAAnElEQVR4XmNgGAUkAWNjY1ZFRUVxeXl5SXQMVgBkWALxayD+jw0zyMjIqAAZBxQUFDxAuoB0AJCeDGLDMHGKgIIRsrKyyjC3AQVbgWLpcMeiAzk5OUEgPgjENuhycACUNAaacklaWloGXQ4OgIrKgdYdVldX50WXAwOgBziBinYATVqILgcHSkpKakBTXuN1NBAwA90iDKLRJegMANxEJ+IzoEMaAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAUCAYAAAC58NwRAAAA+0lEQVR4XmNgGAZAWVlZTEFB4Za8vPx/IP4lJyf3CISB7CdA/BcqDsNfwZqACmJAAiCNioqK8mhmMoiLi3MD5SqBan6DBYyNjVmBnFlQUzbLyMhwoukBAUag3BQ4D2QyzGlAG8tAChBqIQAo54kiAFToKg9x91egZnMUSSAAiimgizGCTIf655S0tLQwugIMoKSkxA/UsAeqqRJdHisAKowA2rQTpBldDgMAFboATV8P1CSBLgcMPV0UAWBImQEVH8EWFyAgKyvrB+eAFEEVmyGpgQNoXK0Cc6Ae3QrEweiKgAaIA52iKg+J2H/gaAcytoNChQgMSUuDCwAASuxLpVOPF2cAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAWCAYAAAD5Jg1dAAABNElEQVR4XmNgGHzA2NiYVVFR0U5OTs5XWlpaGF0eDGRlZU3l5eVXAXEyUGEckL6IroYBKKENlFimpKTEjyRWjqyGQUZGhhMoOANIqyCLAzVWIfNBApZAhWXIYlDNO5DFQAprgII2CgoKHEC2JJAWANLBKG4UFxfnBgpMBmIrIH4OxP+h+AvQ92ZwhUCTlICCvUAmI9QkSSkpKS4g3QzEy0lXCOR4AhWnwgWgABTgIKfABYCmVIICGkkNGAAVBQHxJzAH5hGgVSJo6kAKJwHxVTAH6r5V6urqvMiKlJWVZYHit0HuhOnyBOLXQOvNYYpAAQ0UmwPE2+HRKQ8J6FggfQCoeCGQngukLwHpUpAGsCI09zEDrRODJitGmOlggBx+KBLoAOQ+bOGHAYAKnYDhp4wujg4AqchGIy8gSLMAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,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>