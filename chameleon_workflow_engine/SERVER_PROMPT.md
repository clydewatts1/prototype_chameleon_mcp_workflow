# Server.py Developer Prompt & Instructions 🚀

## Purpose
This document provides specific guidance for working with `chameleon_workflow_engine/server.py` - the FastAPI-based workflow engine server that orchestrates AI agent workflows.

## What is server.py?

`server.py` is the **main entry point** for the Chameleon Workflow Engine. It's a FastAPI REST API server that:
- Manages workflow lifecycle (create, execute, delete, query)
- Handles Units of Work (UOW) heartbeats to prevent zombie actors
- Runs background tasks like the TAU zombie sweeper
- Provides database session management for instance data

## Architecture at a Glance 🏗️

```
server.py (FastAPI App)
    │
    ├── REST API Endpoints
    │   ├── POST /workflows - Create workflow
    │   ├── GET /workflows/{id} - Get workflow status
    │   ├── POST /workflows/{id}/execute - Execute workflow
    │   ├── DELETE /workflows/{id} - Delete workflow
    │   └── POST /workflow/uow/{uow_id}/heartbeat - UOW heartbeat
    │
    ├── Database Layer (via DatabaseManager)
    │   └── Instance database for runtime state
    │
    └── Background Tasks
        └── Zombie Actor Sweeper (TAU role)
```

## Key Components & Their Purpose 🔑

### 1. Database Manager (`db_manager`)
- **Global instance** initialized on startup
- Manages **Tier 2 (Instance)** database only
- Provides session factory via `get_db_session()` dependency
- Uses `INSTANCE_DB_URL` environment variable (defaults to `sqlite:///instance.db`)

**When to use:**
- Any endpoint that needs to read/write runtime workflow data
- Querying UnitsOfWork, Local_Workflows, etc.

**Important:** The server ONLY uses Tier 2 (Instance) database. Tier 1 (Templates) are managed via `tools/workflow_manager.py`.

### 2. Zombie Actor Sweeper (`run_tau_zombie_sweeper`)
- **Background asyncio task** that runs every 60 seconds
- Implements the **TAU role** (zombie detection and cleanup)
- Finds UOWs with:
  - status == 'ACTIVE'
  - last_heartbeat older than 5 minutes
- Actions taken:
  - Updates zombie UOWs to status='FAILED'
  - Logs warning "Zombie Actor Detected - Reclaiming Token"
  - Commits changes to free up resources

**Purpose:** Prevents stale actors from holding tokens indefinitely when they crash or disconnect.

### 3. Heartbeat Endpoint (`POST /workflow/uow/{uow_id}/heartbeat`)
- **Critical for actor liveness**
- Actors MUST call this endpoint at least every 5 minutes to signal they're still processing
- Updates `UnitsOfWork.last_heartbeat` timestamp
- Prevents the zombie sweeper from reclaiming the token

**Usage pattern:**
```python
# Actor code should do this periodically
import httpx
response = httpx.post(
    f"http://localhost:8000/workflow/uow/{uow_id}/heartbeat",
    json={"actor_id": "my-actor-123"}
)
```

### 4. Workflow Management Endpoints
- **Simple in-memory workflow storage** for now (`workflows` dict)
- TODO: Integrate with Tier 2 database (Local_Workflows, UnitsOfWork)
- These endpoints are placeholders for future full workflow execution engine

## Project Conventions for server.py ⚙️

### 1. Async/Await Pattern
- FastAPI endpoints can be `async def` but don't have to be
- Background tasks (like zombie sweeper) MUST be `async` and use `asyncio`
- Database sessions are synchronous (SQLAlchemy ORM), not async

### 2. Dependency Injection
```python
@app.post("/workflow/uow/{uow_id}/heartbeat")
async def heartbeat(
    uow_id: str,
    request: HeartbeatRequest,
    db: Session = Depends(get_db_session)  # ← Injected session
):
    # Use db to query/update
```

**Always use `Depends(get_db_session)`** for database access. Never create sessions directly.

### 3. Error Handling
- Use `HTTPException` for client errors (400, 404, etc.)
- Always rollback on errors: `db.rollback()`
- Log errors with `logger.error()`
- Return meaningful error messages

### 4. UUID Handling
- UUIDs are strings in URLs (`/workflow/uow/{uow_id}`)
- Must parse to `uuid.UUID` for database queries:
  ```python
  import uuid
  uow_uuid = uuid.UUID(uow_id)
  ```
- Catch `ValueError` if invalid format

### 5. Timezone Awareness
- **ALWAYS use UTC** for timestamps:
  ```python
  from datetime import datetime, timezone
  timestamp = datetime.now(timezone.utc)
  ```
- The zombie sweeper uses UTC for threshold calculations

### 6. Logging
- Use `loguru` logger (already imported)
- Log levels: `logger.info()`, `logger.warning()`, `logger.error()`, `logger.debug()`
- Include relevant IDs in log messages:
  ```python
  logger.info(f"Heartbeat received for UOW {uow_id} from actor {request.actor_id}")
  ```

## Common Development Tasks 🛠️

### Adding a New Endpoint
1. Define Pydantic models for request/response (if needed)
2. Add endpoint with proper type hints and docstring
3. Use `Depends(get_db_session)` if accessing database
4. Handle errors with `HTTPException`
5. Add logging for important events
6. Update this file if endpoint has special semantics

### Modifying the Zombie Sweeper
1. Update the sweep interval (currently 60 seconds) if needed
2. Update zombie threshold (currently 5 minutes) if needed
3. Ensure UTC timezone usage
4. Test with stale UOWs in database
5. Add tests in `tests/test_workflow_engine.py`

### Adding a New Background Task
1. Define async function similar to `run_tau_zombie_sweeper()`
2. Use `while True` with `await asyncio.sleep(interval)`
3. Catch `asyncio.CancelledError` for graceful shutdown
4. Start in `startup_event()` with `asyncio.create_task()`
5. Cancel in `shutdown_event()`
6. Store task handle in global variable

### Integrating with Tier 2 Database
**Current state:** Workflows stored in-memory dict (temporary)

**To integrate:**
1. Replace `workflows` dict with `Local_Workflows` queries
2. Create `UnitsOfWork` records when executing workflows
3. Query `Local_Roles`, `Local_Interactions`, etc. to orchestrate execution
4. Use transactions for multi-step operations
5. See `tests/example_usage.py` for Tier 2 usage patterns

## Testing server.py 🧪

### Manual Testing
```bash
# Start the server
python -m chameleon_workflow_engine.server

# Or with uvicorn
uvicorn chameleon_workflow_engine.server:app --reload --port 8000

# Test health check
curl http://localhost:8000/health

# Create a workflow
curl -X POST http://localhost:8000/workflows \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Workflow", "description": "Test", "steps": ["step1"]}'

# Test heartbeat (need valid UOW ID from database)
curl -X POST http://localhost:8000/workflow/uow/{uow-id}/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"actor_id": "test-actor"}'
```

### Automated Testing
- Add tests to `tests/test_workflow_engine.py`
- Use `TestClient` from `fastapi.testclient`
- Mock database with in-memory SQLite
- Test zombie sweeper with manually created stale UOWs

### Testing the Zombie Sweeper
```python
# In test, create a UOW with old heartbeat
from datetime import datetime, timezone, timedelta
old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
uow = UnitsOfWork(
    uow_id=uuid.uuid4(),
    status='ACTIVE',
    last_heartbeat=old_time,
    # ... other fields
)
session.add(uow)
session.commit()

# Wait for sweeper to run (or trigger manually)
# Verify status changed to 'FAILED'
```

## Environment Variables 📝

```bash
# Database
INSTANCE_DB_URL=sqlite:///instance.db  # Instance database URL

# Server
WORKFLOW_ENGINE_HOST=0.0.0.0           # Server host
WORKFLOW_ENGINE_PORT=8000              # Server port

# AI Services (future use)
ANTHROPIC_API_KEY=...                  # For Claude integration
OPENAI_API_KEY=...                     # For OpenAI integration
```

## Common Pitfalls ⚠️

### 1. Forgetting UTC timezone
❌ **Wrong:**
```python
timestamp = datetime.now()  # Local timezone, inconsistent
```

✅ **Correct:**
```python
timestamp = datetime.now(timezone.utc)
```

### 2. Not handling UUID parsing errors
❌ **Wrong:**
```python
uow_uuid = uuid.UUID(uow_id)  # Can raise ValueError
```

✅ **Correct:**
```python
try:
    uow_uuid = uuid.UUID(uow_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid UOW ID format")
```

### 3. Forgetting to rollback on error
❌ **Wrong:**
```python
try:
    # ... database operations
except Exception as e:
    raise HTTPException(...)  # Session left in bad state
```

✅ **Correct:**
```python
try:
    # ... database operations
except Exception as e:
    db.rollback()
    raise HTTPException(...)
```

### 4. Mixing Tier 1 and Tier 2 databases
- server.py ONLY uses Tier 2 (Instance) database
- Templates are managed separately via `tools/workflow_manager.py`
- Never query Template_* tables from server.py

### 5. Blocking the event loop
- Don't use `time.sleep()` in async functions, use `await asyncio.sleep()`
- Don't run CPU-intensive tasks in endpoint handlers
- Database queries are blocking (SQLAlchemy ORM) - this is acceptable for short queries

## Integration Points 🔌

### With tools/workflow_manager.py
- workflow_manager creates **Templates** (Tier 1)
- server.py uses **Instances** (Tier 2)
- Templates must be instantiated before execution (future feature)

### With database module
- Import: `from database import DatabaseManager, UnitsOfWork`
- Use instance database only
- Query runtime state: Local_Workflows, UnitsOfWork, Local_Actors, etc.

### With AI agent clients
- Clients call heartbeat endpoint to stay alive
- Clients query UOW status via future endpoints
- Clients submit results via future endpoints

## Future Enhancements 🚀

Current TODOs in server.py:
1. **Implement actual workflow execution logic**
   - Currently workflows just change status to "running"
   - Need to orchestrate roles, interactions, components
   - Create and manage UnitsOfWork
   - Handle actor assignments

2. **Integrate with Tier 2 database for workflows**
   - Replace in-memory `workflows` dict
   - Store in Local_Workflows table
   - Link to Instance_Context

3. **Add workflow query endpoints**
   - GET /workflows/{workflow_id}/status - Detailed execution status
   - GET /workflows/{workflow_id}/uows - List Units of Work
   - GET /uows/{uow_id} - UOW details
   - POST /uows/{uow_id}/complete - Mark UOW complete

4. **Add workflow template instantiation endpoint**
   - POST /workflows/from-template/{template_name}
   - Creates instance from Tier 1 template
   - Sets up Local_Workflows, Local_Roles, etc.

5. **Add guardian evaluation**
   - Evaluate Local_Guardians when routing UOWs
   - Implement CERBERUS, PASS_THRU, etc. logic

6. **Add authentication and authorization**
   - API key authentication
   - Role-based access control
   - Audit logging

## Quick Reference Commands 📋

```bash
# Start server (development)
python -m chameleon_workflow_engine.server

# Start with custom host/port
WORKFLOW_ENGINE_HOST=127.0.0.1 WORKFLOW_ENGINE_PORT=9000 \
  python -m chameleon_workflow_engine.server

# Start with uvicorn (more control)
uvicorn chameleon_workflow_engine.server:app --reload --port 8000

# Run with different database
INSTANCE_DB_URL=postgresql://user:pass@localhost/chameleon \
  python -m chameleon_workflow_engine.server

# Check if server is running
curl http://localhost:8000/health

# View API docs
# Open browser: http://localhost:8000/docs
```

## Questions to Ask When Modifying server.py ❓

1. **Does this change affect the zombie sweeper?**
   - If modifying UOW status or heartbeat logic, ensure sweeper still works correctly

2. **Does this need database access?**
   - If yes, use `Depends(get_db_session)` and handle transactions properly

3. **Is this creating a long-running operation?**
   - If yes, consider background tasks or async execution
   - Don't block the API response

4. **Does this need to be backward compatible?**
   - Changing endpoint signatures breaks clients
   - Consider versioning: `/v1/workflows`, `/v2/workflows`

5. **Should this be logged?**
   - Important events: YES (info level)
   - Errors: ALWAYS (error level)
   - Debug info: Use debug level

6. **Is there a security implication?**
   - Input validation (UUID format, request body schema)
   - SQL injection (use ORM, not raw SQL)
   - Rate limiting (future consideration)

---

## Summary for AI Assistants 🤖

When working on `server.py`:
1. **Understand the two-tier architecture** - server.py uses Instance (Tier 2) database only
2. **Respect the zombie sweeper** - It's critical for token reclamation
3. **Use proper async patterns** - Background tasks are async, endpoints can be
4. **Always use UTC timestamps** - No local time
5. **Handle UUIDs correctly** - Parse and validate
6. **Log important events** - Use structured logging
7. **Follow FastAPI patterns** - Dependency injection, Pydantic models
8. **Test your changes** - Manual testing with curl, automated with TestClient

**When asked to:**
- **"Add an endpoint"** → Follow the pattern in existing endpoints, use Pydantic models
- **"Fix the zombie sweeper"** → Check UTC usage, threshold logic, and logging
- **"Integrate database"** → Use Tier 2 models, session dependency, transactions
- **"Add a background task"** → Follow the zombie sweeper pattern
- **"Debug a server issue"** → Check logs, database state, environment variables

This file should be kept in sync with `server.py` as the codebase evolves. When making significant changes to server.py, update this prompt accordingly.
