# **Role Behavior Specifications**

This document provides detailed implementation specifications for each role in the Chameleon Workflow Engine, derived from the Workflow Constitution. Each role specification includes purpose, trigger conditions, input requirements, execution logic, and terminal states.

---

## **1. Alpha Role (The Origin)**

**Purpose:** Instantiates the Base UOW (Root Token) that serves as the container for all workflow execution.

**Trigger Condition:** External initiation event or API call to start a new workflow instance.

**Input Data:**
- Workflow template identifier (workflow_id)
- Initial context attributes (JSON object)
- Instance context reference (instance_id)
- Actor identity (actor_id)

**Execution Logic:**
1. Receive workflow initiation request from external source
2. Create a new Base UOW with status "INITIALIZED"
3. Assign unique UOW identifier (uow_id)
4. Populate initial UOW attributes from input context
5. Set parent_id to NULL (marking this as Base UOW)
6. Log creation event with Actor ID and timestamp
7. Place Base UOW into the first Interaction holding area
8. Pass token through Pass-Thru Guard for identity validation
9. Route to first processing Role (typically Beta)

**Terminal State:** Base UOW placed in first Interaction; Actor assignment complete; workflow execution chain initiated.

---

## **2. Omega Role (The Terminal)**

**Purpose:** Reconciles and finalizes the complete UOW set, serving as the terminal point for workflow execution.

**Trigger Condition:** Base UOW and all associated Child UOWs pass through Cerberus Guard validation (Three-Headed Check complete).

**Input Data:**
- Base UOW with all child references
- Complete set of Child UOWs (all with terminal status)
- Historical attribute lineage
- Reconciliation configuration (Archive/Prune/Selective mode)

**Execution Logic:**
1. Receive validated UOW set from Cerberus Guard
2. Verify all Child UOWs have terminal status (completed/finalized)
3. Aggregate results from all Child UOWs into Base UOW
4. Perform final business logic and validation
5. Execute data lifecycle policy:
   - **Archive Mode**: Retain all Base and Child UOWs with full lineage
   - **Prune Mode**: Delete all Child UOWs after Base archival
   - **Selective Mode**: Archive flagged children, delete remainder
6. Mark Base UOW status as "FINALIZED"
7. Execute Toxic Knowledge Filter (scrub flagged decision paths from Global Blueprint)
8. Log final reconciliation event with Actor ID and timestamp
9. Optionally route to Eternal Loop (back to Alpha) if configured
10. Purge active work set from transactional database for performance

**Terminal State:** Base UOW finalized and archived; Child UOW disposition complete; workflow execution concluded or recycled to Alpha.

---

## **3. Epsilon Role (The Physician)**

**Purpose:** The Error Handling Role responsible for remediating explicit data failures detected during workflow execution.

**Trigger Condition:** A Guard detects UOW set failing explicit user-defined criteria (e.g., AMOUNT < 10) and routes token to "Ate" interaction.

**Input Data:**
- Failed UOW set with error context
- Failure reason and validation criteria that failed
- Error log attributes
- Remediation rules from Global Blueprint

**Execution Logic:**
1. Receive failed UOW set from "Ate" interaction holding area
2. Read error log and identify failure root cause
3. Load remediation strategies from Role's Global Blueprint
4. Attempt automated remediation:
   - Apply data correction rules
   - Recalculate derived attributes
   - Request additional data from external sources if configured
5. Re-validate UOW set against original criteria
6. If remediation successful:
   - Update UOW status to "REMEDIATED"
   - Log remediation action with reasoning
   - Send UOW set to Cerberus Guard for re-synchronization
7. If remediation fails after max retry attempts:
   - Update UOW status to "FAILED"
   - Log failure reasoning
   - Send to Omega for terminal disposition
8. Update Personal Playbook with remediation experience (if successful)

**Terminal State:** UOW set either remediated and sent to Cerberus, or marked as failed and sent to Omega for cleanup.

---

## **4. Tau Role (The Chronometer)**

**Purpose:** The Timeout Role responsible for managing stale or expired tokens that exceed time limits, and for detecting and reclaiming work from failed or unresponsive Actors (Zombie Actors).

**Trigger Conditions:**
1. **Stale Token Monitor**: A UOW remains in an Interaction beyond the STALE_TOKEN_LIMIT threshold (Queue Timeout).
2. **Zombie Actor Monitor**: A UOW with status `ACTIVE` has `last_heartbeat` timestamp exceeding the EXECUTION_TIMEOUT threshold (Execution Timeout).

**Input Data:**
- Stale UOW set from "Chronos" interaction (for Queue Timeout)
- Active UOW records with ACTIVE status (for Zombie detection)
- Original timestamp and timeout thresholds
- Escalation policy configuration
- Current workflow state
- Actor heartbeat thresholds

**Execution Logic:**

### **Duty 1: Stale Token Monitor (Queue Timeout)**
1. Receive stale UOW set from "Chronos" interaction holding area
2. Evaluate staleness severity (how long past threshold)
3. Load timeout handling policy from Role configuration
4. Execute timeout management strategy:
   - Log timeout event with UOW context
   - Attempt "forced-end" status transition
   - Preserve partial work and attribute state
5. Apply escalation logic:
   - For recoverable timeouts: route to Epsilon for remediation
   - For unrecoverable timeouts: mark as "TIMEOUT_FAILED"
6. Send processed UOW set to appropriate next destination:
   - Typically to Epsilon Role first for attempted recovery
   - Then to Cerberus Guard for final synchronization
7. Update Global Blueprint with timeout patterns for future prevention
8. Serve as Safety Valve for infinite loops (enforce termination conditions)

### **Duty 2: Zombie Actor Monitor (Execution Timeout)**
1. Periodically sweep UnitsOfWork table for records with:
   - Status = `ACTIVE`
   - `last_heartbeat` NULL or exceeds EXECUTION_TIMEOUT threshold (e.g., 5 minutes)
2. Identify Zombie Actor scenarios:
   - Actor crashed or terminated unexpectedly
   - Network disruption preventing heartbeat updates
   - System-level failures
3. Execute reclamation strategy:
   - Log Zombie Actor detection event with Actor ID and UOW context
   - Force UOW status transition based on policy:
     * **FAILED**: For immediate escalation to Epsilon Role for remediation
     * **PENDING**: For automatic re-queuing if failure is transient
4. Release Actor assignment (if applicable) to free resource
5. Route reclaimed UOW to appropriate next destination:
   - FAILED → Epsilon Role for remediation
   - PENDING → Return to original Interaction queue
6. Update monitoring metrics for Actor reliability tracking

**Terminal State:**
- **Stale Token Path**: Stale UOW set processed with forced-end status; routed to Epsilon or Cerberus depending on recoverability.
- **Zombie Actor Path**: Zombie UOW reclaimed and transitioned to FAILED or PENDING; Actor assignment released.

---

## **5. Sigma Role (The Gateway)**

**Purpose:** A specialized Beta role which executes another nested WORKFLOW, enabling recursive workflow composition.

**Trigger Condition:** Base or Child UOW arrives at Role configured as Recursive Gateway with linked_local_workflow_id set.

**Input Data:**
- Source UOW set to be passed to child workflow
- Linked child workflow identifier (linked_local_workflow_id)
- Replication policy and boundary guard configuration
- Context isolation rules

**Execution Logic:**
1. Receive UOW set designated for recursive processing
2. Execute Deep Copy of UOW set (Principle of Protected Replication)
3. Route copied UOW set through "Hermes" interaction (Outbound Gateway):
   - Apply boundary guard validation
   - Inject copied UOW into child workflow's Alpha role
4. Child workflow executes independently with isolated context
5. Monitor child workflow progress (passive observation)
6. Await child workflow completion (Omega reached)
7. Receive results through "Iris" interaction (Inbound Gateway):
   - Apply boundary guard validation
   - Perform state synchronization from child to parent
8. Merge child workflow results back into original UOW set
9. Update parent UOW attributes with child execution summary
10. Route updated UOW set to next Interaction in parent workflow

**Terminal State:** Child workflow executed and results merged; parent UOW set updated and routed to next stage in parent workflow.

---

## **6. Beta Role (The Processor)**

**Purpose:** The generic processor role that decomposes Base UOW into actionable Child UOWs for parallel or sequential processing.

**Trigger Condition:** Base UOW arrives from previous Interaction with status ready for decomposition.

**Input Data:**
- Base UOW with decomposition instructions
- Decomposition strategy (HOMOGENEOUS or HETEROGENEOUS)
- Child UOW template specifications
- Processing rules from Global Blueprint

**Execution Logic:**
1. Receive Base UOW from Interaction holding area
2. Load decomposition strategy configuration
3. Analyze Base UOW attributes to determine child requirements
4. Generate Child UOWs according to strategy:
   - **HOMOGENEOUS**: All children of same type/structure
   - **HETEROGENEOUS**: Children of different types as needed
5. For each Child UOW:
   - Assign unique child_uow_id
   - Set parent_id to Base UOW identifier
   - Copy relevant attributes from Base to Child
   - Set child status to "CREATED"
6. Update Base UOW with child_count (total children created)
7. Log decomposition event with Actor ID
8. Place all Child UOWs into appropriate next Interaction(s)
9. Place Base UOW into holding area (awaits child completion)
10. Child UOWs proceed through their own processing paths

**Terminal State:** Base UOW decomposed into Child UOWs; Base UOW in waiting state; Child UOWs routed to next processing stages.

---

### **6.1 Beta Subtype: Human (The Approver)**

**Purpose:** A specialized Beta role requiring manual human intervention and approval.

**Trigger Condition:** UOW arrives at role designated for HUMAN actor type.

**Input Data:**
- UOW set requiring human review
- Approval criteria and business rules
- Human Actor assignment (actor_id with type HUMAN)
- UI context for human interface

**Execution Logic:**
1. Receive UOW set from Interaction
2. Explicitly pause workflow execution engine
3. Present UOW data to assigned Human Actor via UI
4. Provide approval/rejection interface with comment field
5. Wait for human input (may exceed standard processing time)
6. Once human provides input:
   - Capture approval decision (approved/rejected/modified)
   - Record human reasoning/comments
   - Update UOW attributes with decision
7. If approved: route UOW to next Interaction for continued processing
8. If rejected: route UOW to Ate interaction for error handling
9. Log human decision with Actor ID and timestamp
10. Update Personal Playbook for this Human Actor with decision pattern

**Terminal State:** UOW processed with human approval decision; workflow execution resumed; routed based on approval outcome.

---

### **6.2 Beta Subtype: AI Agent (The Intelligence)**

**Purpose:** A specialized Beta role driven by an autonomous AI agent for reasoning and intelligent decision-making.

**Trigger Condition:** UOW arrives at role designated for AI_AGENT actor type.

**Input Data:**
- UOW set requiring intelligent processing
- AI context (ai_context field with instructions and constraints)
- Access to Global Blueprint and Personal Playbook
- AI Agent identity and model configuration

**Execution Logic:**
1. Receive UOW set from Interaction
2. Load AI context configuration and reasoning instructions
3. Retrieve relevant memory from Global Blueprint and Personal Playbook
4. Invoke AI Agent with:
   - UOW attributes as input data
   - AI context as system instructions
   - Historical patterns from memory
5. AI Agent performs reasoning task:
   - Analysis, classification, generation, or transformation
   - Apply learned patterns from previous successful UOWs
6. Receive AI Agent output and validation
7. Update UOW attributes with AI-generated results
8. Log AI reasoning and decision path for traceability
9. Update Personal Playbook with successful decision pattern
10. Route processed UOW to next Interaction
11. Support iterative refinement via internal loops with mandatory exit conditions

**Terminal State:** UOW processed by AI intelligence; results captured in attributes; memory updated with successful patterns; routed to next stage.

---

### **6.3 Beta Subtype: Auto (The Script)**

**Purpose:** A specialized Beta role for deterministic, automated system tasks requiring no intelligence or human delay.

**Trigger Condition:** UOW arrives at role designated for AUTO (SYSTEM) actor type.

**Input Data:**
- UOW set with attributes for automated processing
- System script or API endpoint configuration
- Deterministic transformation rules
- Error handling configuration

**Execution Logic:**
1. Receive UOW set from Interaction
2. Load deterministic processing script/configuration
3. Execute automated task:
   - Call external API with UOW data
   - Perform calculation or data transformation
   - Execute database query or update
   - Generate report or file
4. Receive system response synchronously
5. Update UOW attributes with system results
6. If system call successful:
   - Mark operation as completed
   - Route UOW to next Interaction
7. If system call fails:
   - Log error details
   - Route UOW to Ate interaction for error handling
8. Log system operation with execution time
9. No memory update needed (deterministic, no learning)

**Terminal State:** UOW processed by automated system task; results captured; routed based on success/failure outcome.

---

## **7. Cerberus Guard (Three-Headed Synchronization Check)**

**Purpose:** The multi-headed synchronization guard that ensures integrity before final completion, preventing "Zombie Parents" from reaching Omega prematurely.

**Trigger Condition:** Base UOW and Child UOWs approach Omega interaction; guard performs validation before allowing passage.

**Input Data:**
- Base UOW from holding area
- All associated Child UOWs by parent_id reference
- Expected child_count from Base UOW
- Status values for all UOWs in set

**Execution Logic:**

### **Head 1: The Base Head**
1. Verify Parent Base UOW is present in the Interaction holding area
2. Confirm Base UOW has valid identifier and non-null attributes
3. Check that Base UOW status indicates readiness for completion

### **Head 2: The Child Head**
4. Query all Child UOWs with parent_id matching Base UOW
5. Count returned Child UOWs (finished_child_count)
6. Compare against Base UOW child_count (total children spawned)
7. Verify: finished_child_count == child_count
8. Confirm all expected children have returned from workflow cloud

### **Head 3: The Status Head**
9. Iterate through entire UOW set (Base + all Children)
10. Verify each UOW status is terminal:
    - Status must be "COMPLETED" or "FINALIZED"
    - Reject any "IN_PROGRESS", "FAILED", or intermediate statuses
11. Confirm no partial work remains unfinished

### **Synchronization Decision:**
12. If all three heads validate successfully:
    - Allow UOW set to pass through guard
    - Route complete set to Omega Role for final reconciliation
    - Log successful synchronization check
13. If any head fails validation:
    - Block passage to Omega
    - Keep UOW set in Interaction holding area
    - Log specific validation failure reason
    - Wait for missing children or status updates
14. Handle timeout scenarios:
    - If synchronization blocked beyond threshold, escalate to Tau
    - Tau may force terminal status or route to Epsilon

**Terminal State:** Complete UOW set (Base + all Children) validated and passed to Omega; or incomplete set held in Interaction awaiting resolution.

---

## **Cross-Reference: Transit Paths**

The roles interact through standardized transit paths:

1. **Standard Flow**: Alpha → Beta → Omega (via Cerberus)
2. **Error Path**: Any Role → Ate Interaction → Epsilon → Cerberus → Omega
3. **Timeout Path**: Any Interaction → Chronos Interaction → Tau → Epsilon → Cerberus → Omega
4. **Recursive Path**: Sigma → Hermes (outbound) → Child Workflow → Iris (inbound) → Parent Workflow
5. **Eternal Loop**: Omega → Alpha (optional, for continuous processing)

## **Notes on Implementation**

- All role executions must be wrapped in strict sandbox isolation (Article I)
- Every role transition must be logged for audit trail (Article XVII)
- Memory updates (Personal Playbook and Global Blueprint) must occur only for successful UOW completions (Article XX)
- Failed experiences are subject to immediate purge to prevent toxic knowledge propagation
- All roles must respect the air-gapped two-tier architecture (Templates vs Instances)
