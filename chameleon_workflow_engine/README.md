# Chameleon Engine - Core Controller

## Overview

The `ChameleonEngine` class is the core controller that implements the Transport Layer Abstraction for the Chameleon Workflow Engine. It provides the business logic that powers both the REST API and the MCP Server.

## Architecture

This implementation follows the specifications defined in:
- `docs/architecture/Interface & MCP Specs.md` - API Contract and Tools
- `docs/architecture/UOW Lifecycle Specs.md` - UOW State Transitions
- `docs/architecture/Workflow_Constitution.md` - Core Laws (Articles I, XVII, XI, XXI)

## Core Methods

### 1. `instantiate_workflow(template_id, initial_context)`

Creates a new workflow instance from a template.

**Process:**
1. Clones all entities from Template tier to Instance tier
2. Creates Alpha UOW with initial context
3. Injects UOW into Alpha Role's outbound interaction
4. Returns instance_id

**Example:**
```python
from chameleon_workflow_engine.engine import ChameleonEngine
from database.manager import DatabaseManager

manager = DatabaseManager(
    template_url="sqlite:///templates.db",
    instance_url="sqlite:///instance.db"
)

engine = ChameleonEngine(manager)

instance_id = engine.instantiate_workflow(
    template_id=template_uuid,
    initial_context={
        "customer_id": "CUST-001",
        "amount": 5000,
        "description": "Purchase order"
    },
    instance_name="PO Processing - Jan 2026",
    instance_description="Monthly purchase order batch"
)
```

### 2. `checkout_work(actor_id, role_id)`

Acquires a pending UOW from a role's queue with transactional locking.

**Process:**
1. Finds PENDING UOWs in interactions feeding the role
2. Verifies path exists via Component topology
3. Locks UOW (PENDING → ACTIVE)
4. Returns (uow_id, attributes) or None

**Example:**
```python
# Actor checks out work from their assigned role
result = engine.checkout_work(
    actor_id=actor_uuid,
    role_id=role_uuid
)

if result:
    uow_id, attributes = result
    print(f"Processing UOW {uow_id}")
    print(f"Data: {attributes}")
    # ... do work ...
else:
    print("No work available")
```

### 3. `submit_work(uow_id, actor_id, result_attributes, reasoning)`

Submits completed work with atomic versioning.

**Process:**
1. Verifies lock ownership (status check)
2. Calculates attribute diff
3. Creates versioned UOW_Attributes records
4. Updates status to COMPLETED
5. Releases lock

**Example:**
```python
# After completing work, submit results
success = engine.submit_work(
    uow_id=uow_id,
    actor_id=actor_uuid,
    result_attributes={
        "approval_status": "APPROVED",
        "approver_comments": "Looks good",
        "approval_timestamp": "2026-01-26T10:00:00Z"
    },
    reasoning="All criteria met, vendor verified"
)
```

### 4. `report_failure(uow_id, actor_id, error_code, details)`

Reports work failure and routes to Ate Path (Epsilon).

**Process:**
1. Verifies lock ownership
2. Updates status to FAILED
3. Logs error in UOW_Attributes
4. Routes to Epsilon Role's inbound interaction
5. Releases lock

**Example:**
```python
# If work cannot be completed, report failure
success = engine.report_failure(
    uow_id=uow_id,
    actor_id=actor_uuid,
    error_code="VALIDATION_ERROR",
    details="Customer account not found in system"
)
```

## Status Mapping

The engine maps specification statuses to available enum values:

| Spec Status | Enum Value | Meaning |
|-------------|------------|---------|
| INITIALIZED | PENDING | Initial state after creation |
| IN_PROGRESS | ACTIVE | Locked by an actor |
| COMPLETED | COMPLETED | Work finished successfully |
| FAILED | FAILED | Work failed or rejected |

## Known Limitations

### 1. Interaction Logging (Temporarily Disabled)
- **Issue**: SQLite BigInteger autoincrement incompatibility
- **Impact**: Audit trail temporarily incomplete
- **Status**: Commented out with TODO markers
- **Resolution**: Fix schema or migrate to PostgreSQL

### 2. Lock Fields
- **Issue**: Schema lacks dedicated `locked_by`/`locked_at` fields
- **Current**: Using `status` + `last_heartbeat` as lock mechanism
- **Impact**: Less explicit lock ownership tracking
- **Resolution**: Add fields to UnitsOfWork table

### 3. Recursive Workflows
- **Issue**: Child workflow instantiation not implemented
- **Impact**: Templates with `child_workflow_id` won't fully instantiate
- **Status**: Documented with TODO and implementation approach
- **Resolution**: Implement Hermes/Iris recursive instantiation

### 4. Guardian Evaluation
- **Issue**: Guards are cloned but evaluation logic not implemented
- **Impact**: All guards currently behave as PASS_THRU
- **Resolution**: Implement CERBERUS, CRITERIA_GATE, DIRECTIONAL_FILTER logic

### 5. Zombie Actor Detection
- **Issue**: Heartbeat monitoring not implemented
- **Impact**: Hung work items won't automatically be reclaimed
- **Resolution**: Implement Tau role sweep for stale heartbeat

## Testing

Run the comprehensive test suite:

```bash
cd /home/runner/work/prototype_chameleon_mcp_workflow/prototype_chameleon_mcp_workflow
python tests/test_engine.py
```

All tests currently passing:
- ✅ Workflow instantiation from template
- ✅ Work checkout with transactional locking
- ✅ Work submission with atomic versioning
- ✅ Failure reporting with Ate Path routing

## Security

CodeQL scan results: **0 alerts found**

The engine:
- Uses proper transaction handling with rollback
- Employs SQLAlchemy ORM (no SQL injection)
- Has no hardcoded credentials
- Implements proper error handling

## Constants

### SYSTEM_ACTOR_ID
```python
SYSTEM_ACTOR_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')
```

Well-known UUID used for all system-initiated operations to ensure consistent identity across the workflow engine.

## Production Readiness

### Ready Now ✅
- Core workflow instantiation
- Work checkout/submit flow
- Failure handling and routing
- Atomic attribute versioning
- Transaction safety

### Recommended Before Production 🔄
1. Add `locked_by`/`locked_at` fields to UnitsOfWork
2. Fix Interaction_Logs for SQLite or migrate to PostgreSQL  
3. Implement recursive workflows if needed
4. Implement Guardian evaluation logic
5. Add Zombie actor detection (Tau role)

## References

- [Interface & MCP Specs](../docs/architecture/Interface%20&%20MCP%20Specs.md)
- [UOW Lifecycle Specs](../docs/architecture/UOW%20Lifecycle%20Specs.md)
- [Workflow Constitution](../docs/architecture/Workflow_Constitution.md)
- [Database Schema](../database/README.md)
