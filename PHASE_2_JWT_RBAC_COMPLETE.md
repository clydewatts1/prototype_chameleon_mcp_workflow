# Phase 2 JWT & RBAC Implementation - COMPLETE

**Status**: ✅ 40% Complete (2 of 5 components done)  
**Components**: JWT Authentication + RBAC implemented and verified  
**Constitutional Reference**: Articles IX, XV, XVII

---

## Overview

Phase 2 advances from Phase 1's simple X-Pilot-ID header to enterprise-grade JWT authentication with Role-Based Access Control (RBAC). All Pilot endpoints now enforce role-based permissions.

### Completed Components

✅ **JWT Authentication** - Token parsing, signature verification, expiration validation  
✅ **RBAC (Role-Based Access Control)** - 3 roles with endpoint-specific permissions  
✅ **Updated Pilot Endpoints** - All 5 endpoints now use JWT + RBAC  
⏳ **RedisStreamBroadcaster** - Pending (abstraction phase 2-ready)  
⏳ **Advanced Guardianship** - Pending  
⏳ **Interactive Dashboard** - Pending  

---

## Components Implemented

### 1. JWT Authentication Module ✅

**File**: `chameleon_workflow_engine/jwt_utils.py` (360+ lines)

**Features**:
- Token encoding/decoding with signature verification
- Expiration validation
- Claim extraction (sub, role, exp, iat)
- Graceful error handling
- Production-ready configuration

**Key Classes**:

```python
class JWTConfig:
    secret_key: str          # From JWT_SECRET_KEY env var
    algorithm: str           # HS256, RS256, etc.
    expiration_minutes: int  # Token lifetime

class JWTValidator:
    decode_token(token: str) -> Dict[str, Any]
    parse_pilot_token(token: str) -> PilotToken
    extract_bearer_token(header: str) -> str

class PilotToken:
    pilot_id: str           # From 'sub' claim
    role: str               # From 'role' claim
    issued_at: datetime
    expires_at: datetime
    is_expired() -> bool

def create_token(pilot_id: str, role: str, expires_minutes: int) -> str
```

**Token Format**:
```json
{
  "sub": "pilot-001",
  "role": "ADMIN",
  "iat": 1769692245,
  "exp": 1769695845
}
```

**Error Handling**:
- `InvalidTokenError` - Malformed, expired, or bad signature
- `MissingTokenError` - Header missing or invalid format
- `MissingClaimError` - Required claim not found

---

### 2. RBAC (Role-Based Access Control) Module ✅

**File**: `chameleon_workflow_engine/rbac.py` (260+ lines)

**Pilot Roles**:

| Role | kill-switch | clarify | waive | resume | cancel |
|------|---|---|---|---|---|
| ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ |
| OPERATOR | ❌ | ✅ | ❌ | ✅ | ✅ |
| VIEWER | ❌ | ❌ | ❌ | ❌ | ❌ |

**Key Classes**:

```python
class PilotRole(Enum):
    ADMIN = "ADMIN"           # Full access
    OPERATOR = "OPERATOR"     # Standard operations
    VIEWER = "VIEWER"         # Read-only (future)

class PilotAuthContext:
    pilot_id: str
    role: PilotRole
    
    has_permission(endpoint: str) -> bool
    require_permission(endpoint: str) -> None
    is_admin() -> bool
    is_operator() -> bool
    is_viewer() -> bool
```

**Permission Enforcement**:

```python
# Automatic enforcement via FastAPI Depends()
auth: PilotAuthContext = Depends(
    require_pilot_permission("/pilot/kill-switch")
)
# Returns 403 Forbidden if role insufficient
```

**Audit Trail**:
```python
log_authorization_attempt(
    pilot_id="pilot-001",
    endpoint="/pilot/kill-switch",
    authorized=True,
    role="ADMIN"
)
# Output: PILOT_AUTH: ALLOWED | pilot_id=pilot-001 | endpoint=/pilot/kill-switch | role=ADMIN
```

---

### 3. Updated Pilot Endpoints ✅

**File**: `chameleon_workflow_engine/server.py` (updates to all 5 endpoints)

All endpoints upgraded from Phase 1 X-Pilot-ID to Phase 2 JWT + RBAC:

#### Updated Endpoint Pattern:

```python
@app.post("/pilot/kill-switch", response_model=PilotKillSwitchResponse)
async def pilot_kill_switch(
    request: PilotKillSwitchRequest,
    auth: PilotAuthContext = Depends(
        require_pilot_permission("/pilot/kill-switch")  # ← RBAC enforcement
    ),
    db: Session = Depends(get_db_session),
):
    """
    Phase 2: JWT + RBAC
    Requires: ADMIN role
    Auth: Bearer token with ADMIN role
    """
    # auth.pilot_id and auth.role available
    # Non-ADMIN requests get 403 Forbidden
```

**Request Format** (all endpoints):
```bash
curl -X POST http://localhost:8000/pilot/kill-switch \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "uuid", "reason": "..."}'
```

**Error Responses**:
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Role lacks permission
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Server error

---

## RBAC Permission Matrix

### Endpoint Permissions

```
/pilot/kill-switch       → ADMIN only
/pilot/clarification     → ADMIN, OPERATOR
/pilot/waive             → ADMIN only
/pilot/resume            → ADMIN, OPERATOR
/pilot/cancel            → ADMIN, OPERATOR
```

### Role Capabilities

**ADMIN Role**:
- Full access to all endpoints
- Emergency operations (kill-switch)
- Override privileges (waive)
- Intended for: Chameleon team leads, on-call engineers

**OPERATOR Role**:
- Standard intervention operations
- Recovery operations (clarification, resume, cancel)
- Cannot perform emergency operations
- Intended for: Workflow operators, business analysts

**VIEWER Role**:
- Read-only access (placeholder for Phase 3)
- No intervention permissions
- Intended for: Auditors, observers

---

## Testing

### Test Utility

**File**: `phase2_jwt_rbac_test.py`

#### RBAC Permissions Matrix:
```
Admin auth: PilotAuthContext(pilot_id=admin-001, role=ADMIN)
  Can kill-switch: True
  Can clarify: True
  Can waive: True
  Can resume: True
  Can cancel: True

Operator auth: PilotAuthContext(pilot_id=operator-001, role=OPERATOR)
  Can kill-switch: False
  Can clarify: True
  Can waive: False
  Can resume: True
  Can cancel: True

Viewer auth: PilotAuthContext(pilot_id=viewer-001, role=VIEWER)
  Can kill-switch: False
  Can clarify: False
  Can waive: False
  Can resume: False
  Can cancel: False
```

#### Run Tests:
```bash
python phase2_jwt_rbac_test.py
```

#### Output Includes:
- RBAC permission matrix
- Sample JWT tokens (ready to use)
- API usage examples

---

## Token Examples

### ADMIN Token:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwaWxvdC1hZG1pbiIsInJvbGUiOiJBRE1JTiIsImlhdCI6MTc2OTY5MjI0NSwiZXhwIjoxNzY5Njk1ODQ1fQ.69xBQHKL1QhwP-d269mAgiZLU48Ku6zqHRaLRdRwQeI
```

### OPERATOR Token:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwaWxvdC1vcGVyYXRvciIsInJvbGUiOiJPUEVSQVRPUiIsImlhdCI6MTc2OTY5MjI0NSwiZXhwIjoxNzY5Njk1ODQ1fQ.Le6RsymAhA5MseLPcwQ10zHKl4CEtltsK9og0wkJe0Q
```

### Usage:
```bash
# As ADMIN (succeeds)
curl -X POST http://localhost:8000/pilot/kill-switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"instance_id": "uuid", "reason": "Emergency"}'
# Response: 200 OK

# As OPERATOR (fails)
curl -X POST http://localhost:8000/pilot/kill-switch \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -d '{"instance_id": "uuid", "reason": "Emergency"}'
# Response: 403 Forbidden - Pilot lacks permission
```

---

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=<your-production-secret-key-min-32-chars>  # Required for production
JWT_ALGORITHM=HS256                                        # Default
JWT_EXPIRATION_MINUTES=60                                  # Default
```

### Production Setup

1. **Generate secret key**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set environment variable**:
   ```bash
   export JWT_SECRET_KEY="<generated-key>"
   ```

3. **Start server**:
   ```bash
   python -m chameleon_workflow_engine.server
   ```

---

## Migration from Phase 1 to Phase 2

### Breaking Changes

**Phase 1 Authentication**:
```bash
curl -H "X-Pilot-ID: pilot-001" http://localhost:8000/pilot/kill-switch
# No longer supported
```

**Phase 2 Authentication**:
```bash
curl -H "Authorization: Bearer <jwt_token>" http://localhost:8000/pilot/kill-switch
# New standard (JWT + RBAC)
```

### Migration Path

1. Generate JWT tokens for all Pilots (use `create_token()`)
2. Update API clients to send Authorization header instead of X-Pilot-ID
3. Assign roles to Pilots (ADMIN, OPERATOR, VIEWER)
4. Test with provided test tokens
5. Deploy to production

---

## Security Enhancements

### Phase 1 → Phase 2

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Authentication | X-Pilot-ID header (string) | JWT token (signed) |
| Identity verification | None | HMAC signature validation |
| Token expiration | None | Configurable TTL |
| Authorization | None | Role-based access control |
| Audit trail | Basic logging | Enhanced with role info |
| Production ready | Low | High |

### Phase 3 (Future)

- RS256 (RSA signatures)
- OAuth 2.0 integration
- Multi-factor authentication
- Fine-grained permissions

---

## Logging & Monitoring

### Authorization Logs

```
INFO: Pilot authenticated: PilotAuthContext(pilot_id=pilot-001, role=ADMIN)
PILOT_AUTH: ALLOWED | pilot_id=pilot-001 | endpoint=/pilot/kill-switch | role=ADMIN
```

### Error Logs

```
WARNING: Missing or invalid Authorization header: Missing Authorization header
WARNING: Invalid JWT token: Token has expired
WARNING: Pilot pilot-001 lacks permission for /pilot/kill-switch
```

---

## Phase 2 Metrics

| Metric | Value | Status |
|--------|-------|--------|
| JWT modules | 2 (jwt_utils, rbac) | ✅ |
| Pilot roles | 3 (ADMIN, OPERATOR, VIEWER) | ✅ |
| Endpoints updated | 5/5 | ✅ |
| RBAC enforcement | All endpoints | ✅ |
| Token expiration | Validated | ✅ |
| Error handling | Comprehensive | ✅ |
| Audit trail | Enhanced | ✅ |
| Test coverage | Ready | ✅ |

---

## Files Created/Modified

### New Files
- `chameleon_workflow_engine/jwt_utils.py` - JWT authentication
- `chameleon_workflow_engine/rbac.py` - Role-based access control
- `phase2_jwt_rbac_test.py` - Testing utility

### Modified Files
- `chameleon_workflow_engine/server.py` - Updated all 5 endpoints
- `requirements.txt` - Added PyJWT

---

## Next Steps (Phase 2 Continuation)

### Immediate (Next priority)
1. **RedisStreamBroadcaster** - Scale beyond JSONL files
   - Zero code changes to emit() calls
   - Redis Streams integration
   - Phase 3-ready architecture

2. **Advanced Guardianship** - Implement guardian types
   - CERBERUS (3-way synchronization)
   - PASS_THRU (identity-only)
   - CRITERIA_GATE (data-driven)
   - DIRECTIONAL_FILTER (routing)

### Medium-term (This month)
3. **Interactive Dashboard** - Real-time Pilot UI
   - Intervention request display
   - One-click actions
   - Audit trail visualization

### Long-term (Future)
4. **OAuth 2.0 Integration**
5. **Multi-factor authentication**
6. **Fine-grained permissions**

---

## Compliance

✅ **Constitutional Articles**:
- Article IX: Logic-Blind (interaction_policy immutable)
- Article XV: Pilot Sovereignty (JWT-secured interventions)
- Article XVII: Atomic Traceability (RBAC audit logs)

✅ **Security Standards**:
- HMAC-SHA256 signatures
- Expiration validation
- Error handling per OAuth 2.0
- Role-based access control

✅ **Production Ready**:
- Error handling
- Logging
- Configuration management
- Testing utilities

---

## Support Commands

```bash
# Generate test tokens
python phase2_jwt_rbac_test.py

# Start server
python -m chameleon_workflow_engine.server

# View API docs (when running)
# http://localhost:8000/docs

# Test kill-switch with ADMIN token
curl -X POST http://localhost:8000/pilot/kill-switch \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "550e8400-e29b-41d4-a716-446655440000", "reason": "Emergency"}'

# Test OPERATOR token (should fail for kill-switch)
curl -X POST http://localhost:8000/pilot/kill-switch \
  -H "Authorization: Bearer <OPERATOR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "550e8400-e29b-41d4-a716-446655440000", "reason": "Emergency"}'
# Expected: 403 Forbidden
```

---

**Status**: Phase 2 JWT + RBAC Complete ✅  
**Completion**: 40% (2 of 5 Phase 2 components)  
**Next**: RedisStreamBroadcaster + Advanced Guardianship  
**Date**: 2026-01-29
