# Phase 3: Quick Reference Guide

## TL;DR - The Essentials

### What is Phase 3?
Guard-Persistence integration that ensures:
- ✅ Guard authorization on every UOW modification
- ✅ Pilot oversight for high-risk transitions
- ✅ State drift detection via content hashing
- ✅ Actor liveness monitoring via heartbeats
- ✅ Zombie actor cleanup via token reclamation

### Where is it?
```
database/persistence_service.py    <- Main implementation
database/enums.py                  <- Exception classes
tests/test_persistence_service_phase3.py  <- 13 tests
tests/conftest.py                  <- MockGuardContext fixture
```

---

## The Six Core Methods

### 1. `save_uow()` - Basic Save with Authorization
```python
try:
    uow = UOWPersistenceService.save_uow(
        session=db,
        uow=uow_object,
        guard_context=guard,
        new_status="ACTIVE",
        actor_id=actor_uuid,
        reasoning="Actor started processing"
    )
except GuardLayerBypassException:
    # Guard denied - check violations
    print(guard.get_violations())
```

**When to use:** Every UOW state change needs Guard approval
**Constitution:** Article I - Guard authorization requirement

---

### 2. `save_uow_with_pilot_check()` - High-Risk Transitions
```python
result = UOWPersistenceService.save_uow_with_pilot_check(
    session=db,
    uow=uow_object,
    guard_context=guard,
    new_status="COMPLETED",  # This is high-risk!
    actor_id=actor_uuid
)

if result["success"]:
    print(f"Approved: {result['pilot_approved']}")
    print(f"Waiver: {result['waiver_issued']}")
else:
    print(f"Blocked by: {result['blocked_by']}")
    print(f"Error: {result['error']}")
```

**High-risk transitions:**
- PENDING → COMPLETED
- ACTIVE → COMPLETED  
- ACTIVE → FAILED
- PENDING → FAILED

**Constitution:** Article XV - Pilot Management & Oversight

---

### 3. `verify_state_hash()` - Drift Detection
```python
# Simple mode (backward compatible)
is_valid = UOWPersistenceService.verify_state_hash(session=db, uow=uow)

# With violation emission
result = UOWPersistenceService.verify_state_hash(
    session=db, 
    uow=uow,
    emit_violation=True,
    guard_context=guard
)
if not result["is_valid"]:
    violation = result["violation_packet"]
    print(f"Drift detected: {violation.rule_id}")
```

**When to use:** Before critical operations or periodic audits
**Constitution:** Article XVII - Atomic Traceability

---

### 4. `heartbeat_uow()` - Actor Liveness
```python
success = UOWPersistenceService.heartbeat_uow(
    session=db,
    uow_id=uuid.UUID("...")
)

if not success:
    print("UOW not found or not ACTIVE")
```

**When to use:** From actor's heartbeat endpoint (every 1-2 min)
**Constitution:** Article XII - Token Reclamation

---

### 5. `find_zombie_uows()` - Detect Stale Actors
```python
zombies = UOWPersistenceService.find_zombie_uows(
    session=db,
    threshold_minutes=5  # Default
)

print(f"Found {len(zombies)} zombie actors")
```

**When to use:** Background job (every 60 seconds)
**Constitution:** Article XIII - TAU Role

---

### 6. `reclaim_zombie_token()` - Cleanup
```python
for zombie in zombies:
    reclaimed = UOWPersistenceService.reclaim_zombie_token(
        session=db,
        uow=zombie,
        guard_context=guard
    )
    if reclaimed:
        session.commit()
```

**When to use:** After finding zombies
**Constitution:** Article XIII - TAU Role

---

## Exception Handling

### GuardLayerBypassException
Raised when Guard denies authorization.

```python
try:
    UOWPersistenceService.save_uow(...)
except GuardLayerBypassException as e:
    # Get details
    violations = guard.get_violations()
    for v in violations:
        print(v.rule_id)        # e.g., ARTICLE_I_GUARD_AUTHORIZATION
        print(v.severity)       # CRITICAL
        print(v.remedy_suggestion)  # "Request Guard approval"
```

### GuardStateDriftException
Raised when content hash doesn't match (corruption detected).

```python
# Not directly raised in persistence_service
# Instead, use verify_state_hash() with emit_violation=True
```

---

## Testing Your Code

### Using MockGuardContext
```python
from tests.conftest import MockGuardContext

@pytest.fixture
def guard():
    return MockGuardContext()

def test_my_feature(guard):
    # Allow all authorizations
    guard.set_authorized(True)
    
    # Or deny specific actor
    guard.set_authorized(False)
    
    # Check violations
    assert len(guard.get_violations()) > 0
    
    # Simulate pilot decision
    guard.set_pilot_decision(
        uow_id=my_uow.uow_id,
        decision={
            "approved": True,
            "waiver_issued": False,
            "waiver_reason": None,
            "rejection_reason": None
        }
    )
```

### Running Tests
```bash
# All Phase 3 tests
pytest tests/test_persistence_service_phase3.py -v

# Single test
pytest tests/test_persistence_service_phase3.py::TestGuardAuthorization -v

# With output
pytest tests/test_persistence_service_phase3.py -vv
```

---

## Violation Packet Structure

Every violation includes:

```python
violation.rule_id           # "ARTICLE_I_GUARD_AUTHORIZATION"
violation.severity          # "CRITICAL", "HIGH", "MEDIUM", "LOW"
violation.message           # "Guard authorization failed for UOW ..."
violation.remedy_suggestion # "Request Guard approval or ..."
violation.timestamp         # datetime.now(timezone.utc)
violation.metadata          # {"uow_id": "...", "actor_id": "..."}

# Serialize to dict
dict_form = violation.to_dict()
```

---

## Quick Checklist

### Before Using Phase 3:
- [ ] Import `UOWPersistenceService` from `database.persistence_service`
- [ ] Import exceptions from `database.enums`
- [ ] Have a `GuardContext` implementation ready
- [ ] Run tests: `pytest tests/test_persistence_service_phase3.py`

### When Saving UOW:
- [ ] Check if transition is high-risk
- [ ] Use `save_uow()` for low-risk transitions
- [ ] Use `save_uow_with_pilot_check()` for high-risk
- [ ] Handle `GuardLayerBypassException`
- [ ] Check violation details from `guard.get_violations()`

### For Actors:
- [ ] Call heartbeat endpoint every 1-2 minutes
- [ ] Include `uow_id` in heartbeat request
- [ ] Handle 404 (UOW not found)

### For Background Jobs:
- [ ] Find zombies every 60 seconds
- [ ] Reclaim tokens with violation emission
- [ ] Commit changes to database
- [ ] Monitor violation rate

---

## Common Patterns

### Pattern 1: Try-Catch with Violation Logging
```python
try:
    uow = UOWPersistenceService.save_uow(...)
except GuardLayerBypassException:
    violations = guard.get_violations()
    for v in violations:
        logger.warning(f"Guard violation: {v.rule_id}", extra=v.to_dict())
    raise
```

### Pattern 2: Conditional Pilot Check
```python
if is_high_risk_transition(old_status, new_status):
    result = save_uow_with_pilot_check(...)
else:
    result = save_uow(...)
    result = {
        "success": True,
        "uow": result,
        "pilot_approved": False,
        "waiver_issued": False
    }

if not result["success"]:
    raise OperationBlocked(result["error"])
```

### Pattern 3: Zombie Cleanup Loop
```python
while True:
    sleep(60)  # Every 60 seconds
    
    zombies = find_zombie_uows(session, threshold_minutes=5)
    for zombie in zombies:
        reclaim_zombie_token(session, zombie, guard)
    
    if zombies:
        session.commit()
        logger.info(f"Reclaimed {len(zombies)} zombie tokens")
```

---

## Troubleshooting

### Issue: "GuardLayerBypassException: Guard authorization failed"
**Solution:** Check if `guard.is_authorized()` returns True for your actor/UOW

### Issue: "TypeError: can't compare offset-naive and offset-aware datetimes"
**Solution:** Ensure all datetimes use `timezone.utc`: `datetime.now(timezone.utc)`

### Issue: "Tests show 'MetaData object is not iterable'"
**Solution:** Use `transition_metadata` field (not `metadata`) from UnitsOfWorkHistory

### Issue: Violations not appearing in guard.get_violations()
**Solution:** Make sure you're calling `guard.emit_violation()` or the service is

---

## Key Takeaways

1. **Every UOW change needs Guard approval** - Non-negotiable (Article I)
2. **High-risk transitions need Pilot review** - For important decisions (Article XV)
3. **Content hashing detects corruption** - Verify integrity regularly (Article XVII)
4. **Heartbeats keep actors alive** - Regular signals prevent token loss (Article XII)
5. **Zombies get cleaned up** - Stale actors freed after 5 minutes (Article XIII)

---

## Next Steps

- **Phase 4:** Server endpoint integration
- **Phase 5:** Remote Guard implementation
- **Phase 6:** Violation dashboard & monitoring

See [`PHASE_3_DELIVERY_PACKAGE.md`](PHASE_3_DELIVERY_PACKAGE.md) for full details.
