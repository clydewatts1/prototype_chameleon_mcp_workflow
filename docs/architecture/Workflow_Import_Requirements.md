# Workflow Import Requirements Specification

## Overview
This document formalizes the validation rules that must be enforced during workflow YAML import operations. These rules are derived from the **Chameleon Workflow Constitution** and ensure structural integrity, fault tolerance, and proper topology of all workflow templates.

## Source of Truth
- **Primary Reference**: `docs/architecture/Workflow_Constitution.md`
- **Implementation**: `tools/workflow_manager.py` (YAML import validation)
- **Infrastructure**: `database/manager.py` (Transactional rollback on validation failure)

## Validation Rules

### R1: Workflow Must Have Exactly One ALPHA Role (The Origin)
**Constitutional Reference**: Article V.1 - Structural Roles

**Description**: Every workflow must have exactly one role with `role_type='ALPHA'`. The ALPHA role is responsible for instantiating the Base UOW (Root Token) and serves as the entry point for all workflow executions.

**Validation Logic**:
```sql
COUNT(roles WHERE role_type = 'ALPHA') == 1
```

**Error Message**: 
```
"Violation of Article V: Workflow must have exactly one ALPHA role (The Origin). Found: {count}"
```

---

### R2: Workflow Must Have Exactly One OMEGA Role (The Terminal)
**Constitutional Reference**: Article V.1 - Structural Roles

**Description**: Every workflow must have exactly one role with `role_type='OMEGA'`. The OMEGA role reconciles and finalizes the complete UOW set, serving as the terminal point for all workflow executions.

**Validation Logic**:
```sql
COUNT(roles WHERE role_type = 'OMEGA') == 1
```

**Error Message**: 
```
"Violation of Article V: Workflow must have exactly one OMEGA role (The Terminal). Found: {count}"
```

---

### R3: Workflow Must Have Exactly One EPSILON Role (The Physician)
**Constitutional Reference**: Article V.1 - Structural Roles, Article XI.1 - The Ate Path

**Description**: Every workflow must have exactly one role with `role_type='EPSILON'`. The EPSILON role is the error handling role responsible for remediating explicit data failures through the Ate Path.

**Validation Logic**:
```sql
COUNT(roles WHERE role_type = 'EPSILON') == 1
```

**Error Message**: 
```
"Violation of Article V & XI.1: Workflow must have exactly one EPSILON role (The Physician) for error remediation. Found: {count}"
```

---

### R4: Workflow Must Have Exactly One TAU Role (The Chronometer)
**Constitutional Reference**: Article V.1 - Structural Roles, Article XI.2-3 - Stale Token & Zombie Actor Protocols

**Description**: Every workflow must have exactly one role with `role_type='TAU'`. The TAU role manages stale or expired tokens and serves as the ultimate failsafe for timeout scenarios and zombie actors.

**Validation Logic**:
```sql
COUNT(roles WHERE role_type = 'TAU') == 1
```

**Error Message**: 
```
"Violation of Article V & XI.2: Workflow must have exactly one TAU role (The Chronometer) for timeout management. Found: {count}"
```

---

### R5: All BETA Roles Must Have Valid Strategy Defined
**Constitutional Reference**: Article V.2 - Processing Roles (The "Beta" Family)

**Description**: Any role with `role_type='BETA'` must have a valid decomposition strategy defined. The strategy cannot be null and must be either 'HOMOGENEOUS' or 'HETEROGENEOUS'. This configures how the Beta role decomposes Base UOWs into Child UOWs.

**Validation Logic**:
```sql
FOR EACH role WHERE role_type = 'BETA':
    ASSERT role.strategy IS NOT NULL
    ASSERT role.strategy IN ('HOMOGENEOUS', 'HETEROGENEOUS')
```

**Error Message**: 
```
"Violation of Article V.2: BETA role '{role_name}' must have a valid strategy (HOMOGENEOUS or HETEROGENEOUS). Found: {strategy}"
```

---

### R6: All Components Must Have Valid Directionality
**Constitutional Reference**: Article IV - Interaction Dynamics

**Description**: Every component must have a valid direction defined, indicating the flow relative to the Role. Valid directions are 'INBOUND' (flow into the role) or 'OUTBOUND' (flow out of the role).

**Validation Logic**:
```sql
FOR EACH component:
    ASSERT component.direction IN ('INBOUND', 'OUTBOUND')
```

**Error Message**: 
```
"Violation of Article IV: Component '{component_name}' must have valid direction (INBOUND or OUTBOUND). Found: {direction}"
```

---

### R7: Interaction Flow Integrity - Producers and Consumers
**Constitutional Reference**: Article IV - Interaction Dynamics

**Description**: Every Interaction must serve as a valid holding area with at least one producer (Role → Interaction via OUTBOUND component) and at least one consumer (Interaction → Role via INBOUND component). This ensures UOWs can enter and exit each interaction point.

**Validation Logic**:
```sql
FOR EACH interaction:
    producer_count = COUNT(components WHERE interaction_id = interaction.id AND direction = 'OUTBOUND')
    consumer_count = COUNT(components WHERE interaction_id = interaction.id AND direction = 'INBOUND')
    ASSERT producer_count >= 1
    ASSERT consumer_count >= 1
```

**Error Message**: 
```
"Violation of Article IV: Interaction '{interaction_name}' must have at least one producer (OUTBOUND) and one consumer (INBOUND). Found: {producer_count} producer(s), {consumer_count} consumer(s)"
```

---

### R8: The Ate Guard - EPSILON INBOUND Components Must Have Guardians
**Constitutional Reference**: Article XI.1 - The Ate Path (Explicit Data Error)

**Description**: Any component connecting TO the EPSILON role (direction='INBOUND' to Epsilon) must have an associated Guardian. This enforces the constitutional requirement that data failures are properly filtered before reaching the error remediation role.

**Validation Logic**:
```sql
epsilon_role = GET role WHERE role_type = 'EPSILON'
FOR EACH component WHERE role_id = epsilon_role.id AND direction = 'INBOUND':
    guardian_count = COUNT(guardians WHERE component_id = component.id)
    ASSERT guardian_count >= 1
```

**Error Message**: 
```
"Violation of Article XI.1 (The Ate Guard): Component '{component_name}' connects to EPSILON role (INBOUND) and must have an associated Guardian. Found: {guardian_count} guardian(s)"
```

---

### R9: The Cerberus Mandate - OMEGA INBOUND Component Must Have CERBERUS Guardian
**Constitutional Reference**: Article VI - The Cerberus Synchronization

**Description**: The component connecting TO the OMEGA role (direction='INBOUND' to Omega) must have an associated Guardian of type 'CERBERUS'. This enforces the Three-Headed Check that prevents "Zombie Parents" by verifying the Base UOW is present, all Child UOWs have returned, and all UOWs in the set are complete.

**Validation Logic**:
```sql
omega_role = GET role WHERE role_type = 'OMEGA'
FOR EACH component WHERE role_id = omega_role.id AND direction = 'INBOUND':
    guardian = GET guardian WHERE component_id = component.id
    ASSERT guardian EXISTS
    ASSERT guardian.type == 'CERBERUS'
```

**Error Message**: 
```
"Violation of Article VI (The Cerberus Mandate): Component '{component_name}' connects to OMEGA role (INBOUND) and must have a CERBERUS guardian. Found: {guardian_type}"
```

---

### R10: Topology Flow - ALPHA Outbound and OMEGA Inbound
**Constitutional Reference**: Article V.1 - Structural Roles, Article VII - Transit Path and Guard Logic

**Description**: The ALPHA role must have at least one OUTBOUND component to initiate workflow execution by sending UOWs to an Interaction. The OMEGA role must have at least one INBOUND component to receive UOWs for final reconciliation. This ensures the basic flow from origin to terminal.

**Validation Logic**:
```sql
alpha_role = GET role WHERE role_type = 'ALPHA'
omega_role = GET role WHERE role_type = 'OMEGA'

alpha_outbound_count = COUNT(components WHERE role_id = alpha_role.id AND direction = 'OUTBOUND')
omega_inbound_count = COUNT(components WHERE role_id = omega_role.id AND direction = 'INBOUND')

ASSERT alpha_outbound_count >= 1
ASSERT omega_inbound_count >= 1
```

**Error Message**: 
```
"Violation of Article V & VII: ALPHA role must have at least one OUTBOUND component. Found: {count}"
"Violation of Article V & VII: OMEGA role must have at least one INBOUND component. Found: {count}"
```

---

### R11: BETA Roles With Interaction Policy Must Have Valid DSL Syntax
**Constitutional Reference**: Article V.2 - Processing Roles, Article IX.1 - Interaction Policy Evaluation

**Description**: Any BETA role with an `interaction_policy` field defined in its associated Guardian(s) must have valid Domain Specific Language (DSL) syntax. The policy conditions must use only permitted Python comparison operators (`<`, `>`, `<=`, `>=`, `==`, `!=`) and logical operators (`and`, `or`, `not`). All referenced attributes must be either UOW_Attributes keys or reserved metadata (`uow_id`, `child_count`, `finished_child_count`, `status`, `parent_id`).

**Validation Logic**:
```python
FOR EACH role WHERE role_type = 'BETA':
    FOR EACH guardian WHERE role_id = role.id AND guardian.attributes.interaction_policy IS NOT NULL:
        policy_conditions = guardian.attributes.interaction_policy
        FOR EACH condition IN policy_conditions:
            # Validate syntax
            ASSERT condition.syntax_is_valid()  # Parentheses balanced, operators recognized
            # Validate attribute references
            FOR EACH attribute_reference IN condition.get_referenced_attributes():
                ASSERT attribute_reference IN (uow_attributes_keys ∪ reserved_metadata)
```

**Error Message**: 
```
"Violation of Article V.2 & IX.1: BETA role '{role_name}' Guardian '{guardian_name}' has invalid interaction_policy: {error_detail}. Syntax must use Python operators (<, >, <=, >=, ==, !=) and logical operators (and, or, not). Referenced attributes must be UOW_Attributes or reserved metadata (uow_id, child_count, finished_child_count, status, parent_id)."
```

**Example Valid Policies**:
- `"risk_score > 8"`
- `"amount >= 1000 and not is_flagged"`
- `"child_count <= 5 and status == 'CREATED'"`

**Example Invalid Policies**:
- `"invalid_attribute > 10"` — attribute not in permitted set
- `"call_function(x)"` — function calls not permitted
- `"actor_id == 'user@example.com'"` — actor_id not exposed for isolation
- `"amount >> 100"` — invalid operator

---

### R12: BETA Roles With Multiple OUTBOUND Components Must Have Interaction Policy
**Constitutional Reference**: Article V.2 - Processing Roles, Article IX - Guard as Aggregator and Dispatcher

**Description**: If a BETA role has more than one OUTBOUND component (enabling multi-outcome routing), it must define an `interaction_policy` in at least one associated Guardian on those OUTBOUND components. This ensures that routing decisions are explicit and documented, preventing silent or ambiguous routing behavior. A BETA role with exactly one OUTBOUND component may omit `interaction_policy` (single path is implicit).

**Validation Logic**:
```python
FOR EACH role WHERE role_type = 'BETA':
    outbound_components = GET components WHERE role_id = role.id AND direction = 'OUTBOUND'
    IF COUNT(outbound_components) > 1:
        # Multiple outcomes require explicit policy
        has_policy = FALSE
        FOR EACH component IN outbound_components:
            FOR EACH guardian WHERE component_id = component.id:
                IF guardian.attributes.interaction_policy IS NOT NULL:
                    has_policy = TRUE
                    BREAK
            IF has_policy:
                BREAK
        ASSERT has_policy == TRUE
```

**Error Message**: 
```
"Violation of Article V.2: BETA role '{role_name}' has {outbound_count} OUTBOUND components and must define an interaction_policy in a Guardian to specify routing logic. Use interaction_policy field with conditions like 'risk_score > 8' to route to different Interaction queues."
```

**Example Scenario**:
- BETA role `Invoice_Analyzer` has 2 OUTBOUND components:
  - Component A → `High_Risk_Queue` (for risky invoices)
  - Component B → `Standard_Queue` (for normal invoices)
- Must define `interaction_policy` with condition: `"risk_score > 8"` in Component A's Guardian and default fallback in Component B's Guardian
- Without policy: validation fails at import time

**Backward Compatibility**:
- Single OUTBOUND component: no policy required (auto-routes to that component)
- Multiple OUTBOUND components: policy required (explicit design)
- Existing workflows with 1 OUTBOUND: no changes needed

---

## Implementation Guidelines

### Validation Sequence
The validation method `_validate_workflow_topology(session, workflow_id)` should be called:
1. **After** all workflow entities have been created and flushed to the session
2. **Before** the session commits (i.e., before the `return workflow_name` statement)
3. **Inside** the `with self.manager.get_template_session() as session:` context

This placement ensures that:
- All entities are available for validation queries
- Any `ValueError` raised triggers automatic `session.rollback()` via the context manager
- No invalid workflow data is persisted to the template database

### Query Strategy
For efficient validation:
1. Query roles by workflow_id and build a type-to-role mapping
2. Query components by workflow_id and group by interaction and role
3. Query guardians by workflow_id and index by component_id
4. Perform in-memory checks to minimize database round-trips

### Error Handling
- All validation errors should raise `ValueError` with descriptive messages
- Error messages must cite the specific Constitutional Article violated
- Include contextual information (counts, names, values) in error messages
- Rollback is handled automatically by the DatabaseManager session context

---

## Test Coverage Requirements

Tests must verify:
1. **Valid Complete Workflow**: A workflow meeting all requirements imports successfully
2. **Each Rule Violation**: Individual test for each rule (R1-R10) demonstrating validation failure
3. **Rollback Behavior**: Failed validation must not persist any workflow data
4. **Error Messages**: Validation errors include correct Constitutional references
5. **Edge Cases**: Workflows with multiple violations, empty workflows, etc.

---

## Appendix: Reference Example

The file `tools/complete_workflow_example.yaml` demonstrates a valid workflow that satisfies all ten requirements:
- 1 ALPHA role: `Invoice_Creator`
- 1 OMEGA role: `Invoice_Reconciler`
- 1 EPSILON role: `Error_Handler`
- 1 TAU role: `Timeout_Manager`
- 2 BETA roles with strategies: `Invoice_Validator` (HOMOGENEOUS), `Senior_Approver` (HETEROGENEOUS)
- All components have valid direction (INBOUND/OUTBOUND)
- All interactions have producers and consumers
- EPSILON INBOUND component `Error_From_Queue` is unguarded in example (needs guardian to pass R8)
- OMEGA INBOUND component `Reconciler_From_Queue` has `Cerberus_Reconciliation_Guard` (CERBERUS)
- ALPHA has OUTBOUND: `Create_To_Validation`
- OMEGA has INBOUND: `Reconciler_From_Queue`

**Note**: The example YAML may need to be updated to add a guardian to the `Error_From_Queue` component to fully comply with R8.
