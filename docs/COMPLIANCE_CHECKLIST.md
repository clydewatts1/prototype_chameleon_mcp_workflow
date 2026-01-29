# Constitutional Compliance Checklist

## Purpose
This checklist ensures all code complies with the Chameleon Workflow Constitution. Use it during code reviews, PR approvals, and automated compliance scanning.

---

## Article I: The Guard's Mandate (Authorization)

### ✅ Required Checks

- [ ] **No Direct Database Writes**
  - All UOW modifications go through `UOWPersistenceService.save_uow()`
  - No direct `session.add(uow)` or `session.commit()` for UnitsOfWork
  - **Violation Example:**
    ```python
    # ❌ WRONG: Direct write bypasses Guard
    uow.status = "COMPLETED"
    session.commit()
    
    # ✅ CORRECT: Goes through Guard authorization
    UOWPersistenceService.save_uow(session, uow, guard_context, new_status="COMPLETED")
    ```

- [ ] **Guard Context Injection**
  - All endpoints that modify UOWs inject `GuardContext` via dependency injection
  - Guard authorization checked before state transitions
  - **Files to check:** `chameleon_workflow_engine/server.py`, endpoint handlers

- [ ] **Exception Handling**
  - `GuardLayerBypassException` caught and handled appropriately
  - Violations logged with remedy suggestions
  - Users receive actionable error messages
  - **Pattern:**
    ```python
    try:
        UOWPersistenceService.save_uow(...)
    except GuardLayerBypassException as e:
        violations = guard.get_violations()
        logger.error(f"Guard denied: {violations[0].remedy_suggestion}")
        return {"error": "Authorization denied", "remedy": violations[0].remedy_suggestion}
    ```

---

## Article XV: Pilot Management & Oversight

### ✅ Required Checks

- [ ] **High-Risk Transition Detection**
  - Code identifies high-risk transitions:
    - PENDING → COMPLETED
    - ACTIVE → COMPLETED
    - ACTIVE → FAILED
    - PENDING → FAILED
  - Uses `save_uow_with_pilot_check()` instead of `save_uow()`
  - **Example:**
    ```python
    # For high-risk transitions
    if (current_status, new_status) in HIGH_RISK_TRANSITIONS:
        result = UOWPersistenceService.save_uow_with_pilot_check(
            session, uow, guard_context, new_status, actor_id=actor_id
        )
    ```

- [ ] **Pilot Decision Handling**
  - Code checks `result["success"]` and `result["blocked_by"]`
  - Rejection reasons displayed to user
  - Approval/waiver status logged
  - **Pattern:**
    ```python
    if not result["success"]:
        if result["blocked_by"] == "PILOT_APPROVAL_REQUIRED":
            # Handle pilot rejection
            return {"error": result["error"], "requires_pilot": True}
    ```

- [ ] **Constitutional Waiver Tracking**
  - Waivers logged in `UnitsOfWorkHistory.transition_metadata`
  - Waiver reason and authority captured
  - Audit trail includes waiver timestamp
  - **Verification:**
    ```sql
    SELECT transition_metadata->'constitutional_waiver' 
    FROM uow_history 
    WHERE uow_id = ?
    ```

---

## Article XVII: Atomic Traceability (State Drift)

### ✅ Required Checks

- [ ] **Content Hash Computation**
  - Every `save_uow()` call computes `content_hash` automatically
  - Hash includes all UOW attributes (sorted by ID)
  - SHA256 algorithm used for cryptographic strength
  - **Implementation:** `UOWPersistenceService._compute_content_hash()`

- [ ] **State Drift Detection**
  - Critical operations call `verify_state_hash()` before execution
  - Drift detection enabled with `emit_violation=True` for monitoring
  - **Pattern:**
    ```python
    # Before critical operation
    result = UOWPersistenceService.verify_state_hash(
        session, uow, emit_violation=True, guard_context=guard
    )
    if not result["is_valid"]:
        logger.critical(f"State drift detected: {result['drift_detected']}")
        # Handle drift (rollback, alert, etc.)
    ```

- [ ] **History Append-Only**
  - No DELETE or UPDATE statements on `uow_history` table
  - All state transitions recorded with `previous_state_hash` and `new_state_hash`
  - Reasoning field populated for audit trail
  - **Database constraint:** Check for triggers/policies preventing modifications

---

## Article IX: Attribute-Driven Branching (Routing Logic)

### ✅ Required Checks

- [ ] **Logic-Blind Components**
  - No routing logic (if/else for next interaction) in component/role code
  - Components only emit attributes, never decide destinations
  - **Anti-Pattern:**
    ```python
    # ❌ WRONG: Component decides routing
    if risk_score > 0.8:
        return "HighRiskProcessing"
    else:
        return "LowRiskProcessing"
    
    # ✅ CORRECT: Component emits attributes only
    return {"risk_score": risk_score}
    ```

- [ ] **Guardian Policy Completeness**
  - Every Guardian has `interaction_policy` with branches
  - All policies include `default: true` fallback branch
  - Error-prone branches include `on_error: true` recovery
  - **YAML Validation:**
    ```yaml
    guardians:
      - name: RiskRouter
        attributes:
          interaction_policy:
            branches:
              - condition: "risk_score > 0.8"
                next_interaction: "HighRisk"
              - default: true  # ✅ REQUIRED
                next_interaction: "LowRisk"
    ```

- [ ] **No Hard-Coded Routing**
  - No string literals for interaction names in component code
  - All routing decisions via Guardian evaluation
  - **Pattern:** Components return `Dict[str, Any]`, never `str` (interaction name)

---

## Article XII & XIII: Token Reclamation & TAU Role

### ✅ Required Checks

- [ ] **Heartbeat Implementation**
  - Actors call `heartbeat_uow()` every 1-2 minutes during processing
  - Heartbeat endpoint rejects non-ACTIVE UOWs
  - **Actor Pattern:**
    ```python
    while processing:
        # Send heartbeat every 60 seconds
        UOWPersistenceService.heartbeat_uow(session, uow_id)
        time.sleep(60)
    ```

- [ ] **Zombie Detection Background Job**
  - TAU role runs `find_zombie_uows()` every 60 seconds
  - Threshold set to 5 minutes (configurable)
  - **Background Service:**
    ```python
    async def zombie_sweeper():
        while True:
            zombies = UOWPersistenceService.find_zombie_uows(session, threshold_minutes=5)
            for zombie in zombies:
                UOWPersistenceService.reclaim_zombie_token(session, zombie, guard)
            await asyncio.sleep(60)
    ```

- [ ] **Token Reclamation Logging**
  - Reclamation events logged with `ARTICLE_XIII_ZOMBIE_RECLAIM` violation
  - Old status captured in metadata
  - History entry includes "zombie_reclaim: true" flag

---

## Code Review Checklist (Pull Request Template)

### 🔍 **Pre-Merge Review**

1. **Guard Bypass Detection**
   - [ ] No direct UOW database writes
   - [ ] All modifications go through `UOWPersistenceService`
   - [ ] Guard Context properly injected

2. **State Hash Verification**
   - [ ] Critical operations verify content hash
   - [ ] Drift violations emitted to monitoring
   - [ ] History includes state hashes

3. **Branching Logic**
   - [ ] No routing decisions in component code
   - [ ] All policies have default branches
   - [ ] Error branches defined for unsafe operations

4. **Pilot Intervention**
   - [ ] High-risk transitions use `save_uow_with_pilot_check()`
   - [ ] Rejection handling implemented
   - [ ] Waivers logged in metadata

5. **Zombie Protocol**
   - [ ] Actors send heartbeats during processing
   - [ ] Background sweeper runs periodically
   - [ ] Reclamation logged with violations

---

## Automated Compliance Tool

### Usage
```bash
# Scan single file
python tools/compliance_checker.py --file chameleon_workflow_engine/engine.py

# Scan entire project
python tools/compliance_checker.py --all

# Generate compliance report
python tools/compliance_checker.py --report compliance_report.json
```

### Tool Checks
1. **Guard Bypass Detection** (regex patterns for direct DB writes)
2. **Missing verify_state_hash** (AST analysis of critical paths)
3. **Routing Logic in Components** (detect if/else with interaction names)
4. **Missing Default Branches** (YAML policy validation)
5. **Missing Pilot Checks** (detect high-risk transitions without `save_uow_with_pilot_check`)

---

## Constitutional References

| Check | Article | Section | Implementation |
|-------|---------|---------|----------------|
| Guard Authorization | I | 3 | `save_uow()` with Guard Context |
| State Drift Detection | XVII | 1 | `verify_state_hash()` with content hash |
| Pilot Oversight | XV | 1-3 | `save_uow_with_pilot_check()` |
| Token Reclamation | XII | 1-2 | `heartbeat_uow()` + `find_zombie_uows()` |
| TAU Role | XIII | 1 | `reclaim_zombie_token()` |
| Branching Logic | IX | 1 | Guardian `interaction_policy` evaluation |

---

## Violation Severity Guide

| Severity | Impact | Example | Action |
|----------|--------|---------|--------|
| **CRITICAL** | System integrity compromised | Guard bypass, state drift | Block deployment |
| **HIGH** | Constitutional violation | Missing pilot check, no default branch | Require fix before merge |
| **MEDIUM** | Best practice violation | Missing heartbeat, poor logging | Fix in sprint |
| **LOW** | Documentation issue | Missing comments, unclear naming | Technical debt item |

---

## Example Violations & Remedies

### ❌ Violation: Direct Database Write
```python
# Code that violates Article I
uow.status = "COMPLETED"
session.commit()
```

**Remedy:**
```python
# Compliant code
from database.persistence_service import UOWPersistenceService
UOWPersistenceService.save_uow(
    session=session,
    uow=uow,
    guard_context=guard,
    new_status="COMPLETED",
    actor_id=actor_id,
    reasoning="Workflow completed successfully"
)
```

---

### ❌ Violation: Routing Logic in Component
```python
# Code that violates Article IX
class RiskAnalyzer:
    def execute(self, uow):
        score = self.calculate_risk(uow)
        if score > 0.8:
            return "HighRiskProcessing"  # ❌ Component decides routing
```

**Remedy:**
```python
# Compliant code
class RiskAnalyzer:
    def execute(self, uow):
        score = self.calculate_risk(uow)
        return {"risk_score": score}  # ✅ Only emit attributes
        
# Routing handled by Guardian:
# guardians:
#   - name: RiskRouter
#     attributes:
#       interaction_policy:
#         branches:
#           - condition: "risk_score > 0.8"
#             next_interaction: "HighRiskProcessing"
```

---

### ❌ Violation: Missing State Hash Verification
```python
# Code that violates Article XVII
def critical_operation(session, uow):
    # Modify UOW without verifying state
    uow.attributes["critical_data"] = new_value
    session.commit()
```

**Remedy:**
```python
# Compliant code
def critical_operation(session, uow, guard):
    # Verify state before modification
    result = UOWPersistenceService.verify_state_hash(
        session=session,
        uow=uow,
        emit_violation=True,
        guard_context=guard
    )
    if not result["is_valid"]:
        raise GuardStateDriftException("State drift detected")
    
    # Proceed with modification through proper service
    UOWPersistenceService.save_uow(session, uow, guard, ...)
```

---

## Quick Reference Links

- **Constitution:** [docs/architecture/Workflow_Constitution.md](../architecture/Workflow_Constitution.md)
- **Guard Implementation:** [chameleon_workflow_engine/semantic_guard.py](../../chameleon_workflow_engine/semantic_guard.py)
- **Persistence Service:** [database/persistence_service.py](../../database/persistence_service.py)
- **Branching Guide:** [docs/architecture/Branching Logic Guide.md](../architecture/Branching%20Logic%20Guide.md)
- **Phase 3 Tests:** [tests/test_persistence_service_phase3.py](../../tests/test_persistence_service_phase3.py)

---

**Last Updated:** January 29, 2026  
**Compliance Version:** 1.0.0  
**Status:** Active
