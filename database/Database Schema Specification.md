# **📊 CHAMELEON ENGINE: DATABASE SCHEMA SPECIFICATION**

**Architecture:** Air-Gapped Instantiation (Physical & Logical Isolation)

**Version:** 3.7 (Namespace Uniqueness & Agnosticism)

This specification defines a strict **Two-Database Architecture** designed for absolute independence.

1. **The Meta-Store (Templates):** Holds the inactive blueprints. Used *only* during the instantiation phase.  
2. **The Instance-Store (Runtime):** A self-contained database containing the **Engine**, the **Cloned Metadata**, and the **Local Resources (Actors)**. Once instantiated, the engine runs exclusively against this store.

# **🛑 TIER 1: THE META-STORE (Templates)**

*Access:* Read-Only during Instantiation.

*Purpose:* Source of truth for structural definitions.

### **Template\_Workflows**

*Description:* Defines the high-level container for a workflow blueprint.

* workflow\_id: UUID (Primary Key) \- Unique identifier for the blueprint.  
* name: String (Short Identifier) \- Human-readable system name. **Must be unique per version.**  
* description: Text (Human Readable) \- Detailed documentation of what this workflow achieves.  
* ai\_context: JSONB \- Model-specific prompts/descriptions used to prime AI agents about the overall workflow goal.  
* version: Integer \- Incremental version number; updated whenever the structure (roles, edges) changes.  
* schema\_json: JSONB \- A serialized, cached representation of the full graph (Nodes+Edges) to speed up the cloning process.  
* created\_at: Timestamp \- UTC timestamp of creation.

### **Template\_Roles**

*Description:* Defines the functional agents or steps within a blueprint.

* role\_id: UUID (PK) \- Unique identifier for the role definition.  
* workflow\_id: UUID (FK \-\> Template\_Workflows) \- The blueprint this role belongs to.  
* name: String \- Display name of the role. **Must be unique within the workflow\_id namespace.**  
* description: Text \- Human-readable description of responsibilities.  
* ai\_context: JSONB \- Specific instructions for AI agents assigned to this role.  
* role\_type: Enum \- Functional classification (![][image1], ![][image2], ![][image3], ![][image4], ![][image5]).  
* strategy: Enum \- Decomposition strategy (HOMOGENEOUS/HETEROGENEOUS) for Beta roles.  
* child\_workflow\_id: UUID (Nullable, FK \-\> Template\_Workflows) \- If set, this Role acts as a Recursive Gateway triggering this referenced blueprint.

### **Template\_Interactions**

*Description:* Defines the passive holding areas (waiting rooms) between roles.

* interaction\_id: UUID (PK) \- Unique identifier.  
* workflow\_id: UUID (FK \-\> Template\_Workflows) \- Parent blueprint.  
* name: String \- System name. **Must be unique within the workflow\_id namespace.**  
* description: Text \- Documentation of what UOW state resides here.  
* ai\_context: JSONB \- Context for agents observing this interaction.

### **Template\_Components**

*Description:* Defines the topology (directional pipes) linking Roles and Interactions.

* component\_id: UUID (PK) \- Unique identifier.  
* workflow\_id: UUID (FK \-\> Template\_Workflows) \- **Added for Namespace Scope.**  
* interaction\_id: UUID (FK) \- The interaction endpoint.  
* role\_id: UUID (FK) \- The role endpoint.  
* direction: Enum \- Flow direction relative to the Role (INBOUND/OUTBOUND).  
* name: String \- Descriptive name. **Must be unique within the workflow\_id namespace.**  
* description: Text \- Documentation of the data flow.  
* ai\_context: JSONB \- Semantic description of this specific data pipe.

### **Template\_Guardians**

*Description:* Defines the active logic gates attached to components.

* guardian\_id: UUID (PK) \- Unique identifier.  
* workflow\_id: UUID (FK \-\> Template\_Workflows) \- **Added for Namespace Scope.**  
* component\_id: UUID (FK) \- The specific pipe this guard protects.  
* name: String \- Name of the guard logic. **Must be unique within the workflow\_id namespace.**  
* description: Text \- Explanation of the gating criteria.  
* ai\_context: JSONB \- Instructions for AI agents acting as the guard.  
* type: Enum \- Logic type (CERBERUS, PASS\_THRU, CRITERIA\_GATE, etc.).  
* config: JSONB \- Configuration payload (e.g., {"criteria": "amount \> 1000"}).

# **🚀 TIER 2: THE INSTANCE-STORE (Runtime Engine)**

*Access:* Read/Write by the Engine.

*Purpose:* The complete, self-contained universe for a running workflow.

**Crucial:** All tables below reside in the Local Instance Database.

## **1\. The Root Context (The Container)**

### **Instance\_Context**

*Description:* Represents the "World" or "Tenant" for this deployment. It is the root of the isolation boundary.

* instance\_id: UUID (Primary Key) \- The Global ID for this specific deployment.  
* name: String \- Display name. **Must be unique globally.**  
* description: Text \- Operational notes.  
* status: Enum \- Deployment health (ACTIVE, PAUSED, ARCHIVED).  
* deployment\_date: Timestamp \- When this instance was cloned from the meta-store.

## **2\. Cloned Metadata (The "Frozen" Physics)**

These tables are populated by deep-copying from Tier 1\. A single Instance can hold **multiple** distinct workflows linked by roles.

### **Local\_Workflows**

*Description:* A specific workflow definition active within this instance. Can be a Master or a Child dependency.

* local\_workflow\_id: UUID (PK) \- Unique ID for this workflow within this instance.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The parent container.  
* original\_workflow\_id: UUID (Reference to Tier 1\) \- Traceability link to the source blueprint.  
* name: String \- Local name of the workflow. **Must be unique within the instance\_id namespace.**  
* description: Text \- Local description.  
* ai\_context: JSONB \- Localized AI prompts.  
* version: Integer \- The version of the blueprint used for this snapshot.  
* is\_active: Boolean \- Controls execution eligibility.  
* is\_master: Boolean (Default: False) \- Only one workflow in the instance can be True. This is the entry point.

### **Local\_Roles**

*Description:* The execution logic nodes. Cloned from Template\_Roles.

* role\_id: UUID (PK) \- Local unique identifier.  
* local\_workflow\_id: UUID (FK \-\> Local\_Workflows) \- Parent local workflow.  
* name: String \- Role Name. **Must be unique within the local\_workflow\_id namespace.**  
* description: Text \- Description.  
* ai\_context: JSONB \- AI Instructions.  
* role\_type: Enum \- (![][image6]).  
* decomposition\_strategy: Enum \- How this role breaks down tasks.  
* is\_recursive\_gateway: Boolean \- Flag if this role spawns a sub-workflow.  
* linked\_local\_workflow\_id: UUID (Nullable, FK \-\> Local\_Workflows) \- *Crucial:* Points to the **Child Workflow** hosted in this same instance if recursive.

### **Local\_Interactions**

*Description:* The execution holding areas. Cloned from Template\_Interactions.

* interaction\_id: UUID (PK) \- Local unique identifier.  
* local\_workflow\_id: UUID (FK \-\> Local\_Workflows) \- Parent local workflow.  
* name: String \- Interaction Name. **Must be unique within the local\_workflow\_id namespace.**  
* description: Text \- Description.  
* ai\_context: JSONB \- AI Context.  
* stale\_token\_limit\_seconds: Integer \- Runtime configuration for Timeout (Chronos) logic.

### **Local\_Components (Topology)**

*Description:* The execution connections. Cloned from Template\_Components.

* component\_id: UUID (PK) \- Local unique identifier.  
* local\_workflow\_id: UUID (FK \-\> Local\_Workflows) \- Parent local workflow.  
* interaction\_id: UUID (FK \-\> Local\_Interactions) \- Connection Endpoint A.  
* role\_id: UUID (FK \-\> Local\_Roles) \- Connection Endpoint B.  
* direction: Enum \- Flow direction.  
* name: String \- Component Name. **Must be unique within the local\_workflow\_id namespace.**  
* description: Text \- Description.  
* ai\_context: JSONB \- AI Context.

### **Local\_Guardians (Logic)**

*Description:* The active security gates. Cloned from Template\_Guardians.

* guardian\_id: UUID (PK) \- Local unique identifier.  
* local\_workflow\_id: UUID (FK \-\> Local\_Workflows) \- Parent local workflow.  
* component\_id: UUID (FK \-\> Local\_Components) \- The pipe being guarded.  
* name: String \- Guard Name. **Must be unique within the local\_workflow\_id namespace.**  
* description: Text \- Description.  
* ai\_context: JSONB \- AI Context.  
* type: Enum \- Logic Class (CERBERUS, PASS\_THRU, etc.).  
* attributes: JSONB \- The runtime configuration logic (e.g., criteria rules).

## **3\. Local Resources (Shared Identity & Long-Term Memory)**

**Feature:** Actors and their Experiences are global to the *Instance*.

### **Local\_Actors**

*Description:* Identities authorized to operate within this specific Instance Context.

* actor\_id: UUID (PK) \- Unique ID for the actor in this instance.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The container.  
* identity\_key: String \- External reference ID.  
* name: String \- Display name. **Must be unique within the instance\_id namespace.**  
* description: Text \- Description of capabilities.  
* ai\_context: JSONB \- System prompts or Persona definitions specific to this instance.  
* type: Enum \- (HUMAN, AI\_AGENT, SYSTEM).  
* capabilities: JSONB \- Dictionary of tools/skills the actor possesses.

### **Local\_Actor\_Role\_Assignments**

*Description:* Mapping table defining which Actors can perform which Roles.

* assignment\_id: UUID (PK) \- Unique identifier.  
* actor\_id: UUID (FK \-\> Local\_Actors) \- The Actor.  
* role\_id: UUID (FK \-\> Local\_Roles) \- The Role they are allowed to assume.  
* status: Enum \- (ACTIVE, REVOKED).

### **Local\_Role\_Attributes (The Memory Store)**

*Description:* The persistent knowledge base (Article III). Stores both shared Blueprints and private Playbooks.

* memory\_id: UUID (PK) \- Unique identifier.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The container.  
* role\_id: UUID (FK \-\> Local\_Roles) \- The Role context this memory applies to.  
* actor\_id: UUID (Nullable, FK \-\> Local\_Actors)  
  * *If NULL*: This is a **Global Blueprint** (Shared knowledge for all actors in this role).  
  * *If SET*: This is a **Personal Playbook** (Private knowledge for this specific actor).  
* key: String \- Retrieval key.  
* value: JSONB \- The stored knowledge/configuration.  
* is\_toxic: Boolean (Default: False) \- Flagged by Omega/Epsilon if this memory led to failure (Article XX).  
* last\_accessed\_at: Timestamp \- Used for pruning decay.

## **4\. Execution State (The Flow)**

### **UnitsOfWork**

*Description:* The atomic token representing a task or data packet moving through the graph.

* uow\_id: UUID (PK) \- Unique identifier.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The container.  
* local\_workflow\_id: UUID (FK \-\> Local\_Workflows) \- Identifies which specific process this token is traversing.  
* parent\_id: UUID (Nullable, Self-Reference) \- Link to the Base UOW if this is a Child.  
* current\_interaction\_id: UUID (FK \-\> Local\_Interactions) \- Physical location of the token.  
* status: Enum \- Current state (PENDING, ACTIVE, COMPLETED, FAILED).  
* child\_count: Integer \- Total children generated (Optimization for Cerberus).  
* finished\_child\_count: Integer \- Total children completed (Optimization for Cerberus).

### **UOW\_Attributes (Ephemeral Transactional Data)**

*Description:* The specific data payload of a Unit of Work. Immutable/Versioned.

* attribute\_id: UUID (PK) \- Unique identifier.  
* uow\_id: UUID (FK \-\> UnitsOfWork) \- The parent token.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The container.  
* key: String \- Data label.  
* value: JSONB \- Data payload.  
* version: Integer \- Version number (increments on updates).  
* actor\_id: UUID (FK \-\> Local\_Actors) \- Who made this change.  
* reasoning: Text \- The "Why" or "Intent" behind this data change (traceability).

### **Interaction\_Logs (Audit)**

*Description:* The immutable ledger of every movement in the system.

* log\_id: BigInt (PK) \- Sequence number.  
* instance\_id: UUID (FK \-\> Instance\_Context) \- The container.  
* uow\_id: UUID (FK \-\> UnitsOfWork) \- The token moved.  
* actor\_id: UUID (FK \-\> Local\_Actors) \- The actor responsible.  
* role\_id: UUID (FK \-\> Local\_Roles) \- The active role context.  
* interaction\_id: UUID (FK \-\> Local\_Interactions) \- The location involved.  
* timestamp: Timestamp \- When the event occurred.

## **6\. AI Introspection & Schema Metadata**

To ensure AI Coding Agents can autonomously understand and navigate the schema, the following implementation standards are **mandatory**.

### **6.1. The "Code as Comments" Mandate**

Every SQLAlchemy model must include the comment= attribute for both the Table and every Column. The content of these comments **must** match the *Descriptions* provided in this specification.

* *Rationale:* This persists the "Why" directly into the database catalog (information\_schema or pg\_description), making it accessible to any agent with SQL access.

### **6.2. The v\_ai\_schema\_guide View**

The database must include a predefined View acting as a "Cheat Sheet" for AI agents. This view joins system catalog tables to present a flattened, human-readable map of the database.

**View Schema Requirement:**

* table\_name: String  
* column\_name: String  
* data\_type: String  
* is\_primary\_key: Boolean  
* foreign\_key\_target: String (Table.Column)  
* description: Text (The SQL Comment/Context)

*Usage:* An AI Agent executing SELECT \* FROM v\_ai\_schema\_guide WHERE table\_name \= 'Local\_Roles' will immediately understand the schema, relationships, and business purpose of the table without hallucinating columns.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAZCAYAAAAFbs/PAAABCElEQVR4XmNgGAWDEigqKorLycn5KigoOAAxB7o8HAAlJeTl5dcA8XogOwJIVwPxE1lZWROQvIyMjDQQq4IVA00FyslfAeJZxsbGrFAzWID85UDbdgAVcgLZNUC2DUxiDsg0IFaEKgYDoIJyoNgnoI0eQPZ8JSUlftI1AAU0gfgtEK8BaUbWABSLBuKvIMVATeEwU3yBgv+BAunIipHlgHgzyB9gQSDHEyQIkkRTD9PwB2iYPVxQWVlZFih4G4hzkNQyAvlOQHwDZpi0tLSMlJSUCFgWKnkfiFcD8VwgPgHExSoqKqJAehvQhlOg4AUFP5KhDMxA28SAJgmDbEAWB5mMFD+jgCAAAIbsQ2IsKGhEAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAABWUlEQVR4XtWSvS4EcRTF/xskPkPCmOx8f0imUCgmCBGFTrHNqmnEIyBEp5YIjYJCQ7IvQKHYVyBReQCFTvT87piR/3+yHmBPcnJnzzn37p27q1T/IM/zoTiO14MgaLmuO133Dfi+vxiGYQfu0rBDfYbteq4AgXnMuyRJJjXtEO3Jtu0xPas8zxvBvKLO6TrhY9i1LGtc18VYoeFA18ohj1EUnfOxoXvScIK5hjnMc5M6Rd2Sd+AAoRGW/TAu4Sp8h98lvwgvGWEBkxPMMx4b5eSm4zij1FN4jz5oNCBu0rRniKoY1JJvlIGGwdQjub8hqmJQG36y1sKfWO3PCjNatgD6BXw1vHL/TpZlE1pWpWnqo7/Jeyj9pLI//GCt5UqT+6Ndwwf9Vy8Q/t5/m9ql6ZZ6Q32h7kujEa7tP8Aas+W/0/xVK+j3r3s9Ifv3uv+/oGGD+6d1vY/wA532SAKpo509AAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAYCAYAAAAh8HdUAAABEElEQVR4XmNgGAVDCTAqAIGxsTErugQIiIuLc8vJyTmDaLggUMAViHeKioryIKmFA3l5+Wog/g80Nx0sICMjwwnkrARiczS1cKCoqKgP1PQKiIvAAkCGJVDDRCCTBaqGESgWLSsr6wfXxQB2zXyguCeYA2TkAAVcYJJAU8WBYneBuBWuA2ggkD8ZqE4JzINyjGGyIDZQ7BnIBTAxoBdUgPxZQBdxwBTNR3YKUCIcqOC0ioqKKIgPClGgmhlA8QiYGpBNk4D4OciTQDwbiH8A8T8g3gfE2UB8HqhhF0rIAv1gBpR4D8T/gfgjEHsDcTGUD8LHpKWlZeAaYADkVlAAIEcuUEwAqFgYyGREUjoKKAYAOCU5sbHkI8kAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAYCAYAAADH2bwQAAAAqUlEQVR4XmNgGAVYgbGxMauioqI4CIPYcAkVFRU+eXn5SUD8Wk5ObgOQnqKkpKQGlgSqlldQULgFFJwjIyPDCdcFAiBjgBKrgPgJECuiSIIAUFATiN8C8S+g0Y9gGGhiJFgBkGMMlPwKpMvR9EIA0H59oIJPOBWAHAVUsBnkDiRvMYqLi3PDFQHtkwAq2A405SCQngXEh4G4GijFAlcEAqKiojwYATQsAAClYyU1cc8o2gAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAXCAYAAADduLXGAAAAm0lEQVR4XmNgGAV0BcbGxqyKiori8vLykuhYVFSUB64QKGAJxK+B+D8OvFVBQYGDQUZGRgXIOQDkeABpSSAdAKQng9gwDFYIAkBGhKysrDKSLa1AsXS4tbiAnJycMVDhJWlpaRl0OQwAVFwONPmwuro6L7ocCgC6nROoeAfQ5IXochhASUlJDWjqa6LcCwTMQLcKg2h0iVGADQAA3ZQiPk9XdcEAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFoAAAAYCAYAAAB6OOplAAAEhUlEQVR4Xu2YXYhVVRTHz3An0krScprm654zHzX01MP0gZEUYqHIQGCooeBTKOhDGSVaD0FERT0E8xDpVESEZpLBpAj6YPSiBoGSIplEYQ8h9SAVRDb2+3v2ntl3ec659zgNCJ0//Nn7rrX3Omuvs9be+9woqlChQoXrG52dnTf39/c/Lqpv9RVmjrY4jlfU6/XdtGvhJni6r6/vPjuwwgxAgB8jsGMjIyM3eFmSJB8iGw/HVZgBBgcH7yCg7/f09NweiJXhHyvYgazCTEAwV4uhjD26k0CfQr4xlP+voCBQ6qME4VE4x+pLol1bBvYGOjo6bqHfNTw8PI/fL9A/NDAwcKudUIBab2/vEG2bVQjd3d0L5XO4PZWB1ir/VIH8rFl9HvQ8lzhdllqzHa8H3YlyL9xHfw3ti/C8P7BYZA+8y84rgnNgTLcM2r/hZcdzLKjPji+Csp95O+i2Wx2oofsITvISl1plEdjSepm3B/7MMz6hfdMFuykYuwheCNZlub8hWQkEsvhbuCPICGXjLhw/SIDn0n+J/sNTk1qAxjNvC9027dEKvK51yPbgwMt2fB7cC5tgTmJ1HuhXwD/hcqvLA3YfYPxvmN0WlchiQdXF3CPMXUbbRfsE7Zj6ng1BjtKAjsPzsD9UEKityC7KGP0PSpa6Fr85K8Oc3a9pF1hdFlyFPe9/KxmQPUu13e9lbmvaR/Du9bIi6MVj4zhzjpZdlyCfeP6g/42dV5FtCMc0gAH3wF/h3siUZZzeef9QkBNzoLWAdua8rdK0Cmxuh+eUqVaXBey8Lj/9bwVTCSD/vEwvjXHvtvrylADMn4S/0/9JpH8WPmTHNoOeCb8srHiUoxi/nPU2vA5OaPuw+iL4/dmWj34j3y9aXRaUqUl65+7yMudXQwWSXYuRv+Z/N4Nfm1qrKwtsjODjyaykmgIPW573QOfMJYw8YnXI5otW7qG3y9ydkbklyCnkF2nXhXIF1N21G8ZLztjPNc+J2njuNr38oaGhGyVQ6WsMskXTM4t9LFq3R55PFvV0K/xKNyqrm4JO/zgtmc2BWB8US+AZ74zelq5QUpKtw8h/iTP2dQ8W+Az8DiZeRlXcxvjD2HsnvIZpMchPwL8yguUrQIe1Pt0/g5fitOx3wS3wR9mMgq2vmY/uQ0o2X4mmA1ljjTepU+RTCFU6zz6YtPLxFadB/QF+Ct+DR+FzZEwH7QGMHJcxnI813l2J5MRkTkZcuT8zbw36Y7IpR2hP0z4VmRPeHWQHZC8ODj0PZCvhP3G6jX2PjQcVWPdbibDbHmgt+OjPp2/gF7FbN7bXS9fMJw+eezf6C0nG1puHmt5yRqnoLS/M+hBgAU/HGdepcH/2F/okp4RD1NMDKqysKWjh5mPiypWxmd08H0PIRt6HSpFPDjUXs6vm/ldQ1r4VZ5Rlffr+XAr19Isxt0yvAbk+topZ8KkcyIJl8I0o46BQBigTrLwI7so2XvZ2U4QiH1vBbPhUFu0EcpXdFz3QPWn+rWsK7aOF16PyKPSxFcyCTxUqVKhQBv8CWz48IEdGjSoAAAAASUVORK5CYII=>