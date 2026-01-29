# Phase 2 Complete → Phase 3 Planning

## Status Overview

✅ **Phase 1**: 100% Complete (Pilot Sovereignty Foundation)  
✅ **Phase 2**: 100% Complete (Security, Guardianship, Real-time Monitoring)  
⏳ **Phase 3**: Ready for Planning  

---

## What Phase 2 Delivered

### Security Layer ✅
- JWT Authentication (signed tokens, expiration)
- RBAC (3-tier role hierarchy, endpoint permissions)
- Audit logging (pilot ID + role in every action)

### Intelligent Routing ✅
- 6 Guardian types (CERBERUS, PASS_THRU, CRITERIA_GATE, DIRECTIONAL_FILTER, TTL_CHECK, COMPOSITE)
- Guardian registry for batch evaluation
- Immutable policy-respecting design

### Event Streaming ✅
- RedisStreamBroadcaster (XADD, consumer groups)
- Metrics tracking (events, bytes, errors)
- Zero code changes to emit() calls

### Real-time Monitoring ✅
- InterventionStore (request management)
- WebSocketMessageHandler (message processing)
- DashboardMetrics (analytics aggregation)

---

## Phase 3 Priorities

### 🏆 **Priority 1: Interactive Dashboard UI** (Frontend)
**Why**: Pilots can't use the system without UI  
**Estimated Effort**: 2-3 days  
**Impact**: HIGH (blocks production use)

**Components Needed**:
1. Frontend Framework
   - React (recommended for real-time)
   - Vue as alternative
   - TypeScript for type safety

2. Real-time Connection
   - WebSocket client library
   - Auto-reconnect handling
   - Message queueing

3. UI Components
   - Intervention request cards
   - Priority badges (critical, high, normal, low)
   - Status indicators (pending, approved, etc.)
   - One-click action buttons

4. Pages
   - Dashboard (pending requests)
   - Request detail
   - History/audit trail
   - Metrics (analytics)
   - Pilot profile

### 🏆 **Priority 2: Database Persistence** (Backend)
**Why**: In-memory store is temporary MVP  
**Estimated Effort**: 1-2 days  
**Impact**: MEDIUM (reliability)

**Components Needed**:
1. Database Tables
   - Intervention_Requests
   - Intervention_History
   - Pilot_Metrics (cache)

2. Data Migration
   - Move InterventionStore to SQLAlchemy
   - Preserve same API interface
   - Add pagination support

3. Indexes
   - Request ID (fast lookup)
   - UOW ID (reverse lookup)
   - Pilot ID (user-scoped)
   - Status + Priority (sorting)

### 🏆 **Priority 3: OAuth 2.0 Integration** (Security)
**Why**: Production systems need SSO  
**Estimated Effort**: 2 days  
**Impact**: MEDIUM (security)

**Components Needed**:
1. OAuth Provider Integration
   - GitHub login
   - Azure/Entra ID
   - Google (optional)

2. Token Refresh
   - Access token + refresh token
   - Auto-refresh on expiration
   - Revocation support

3. User Mapping
   - External ID → Pilot ID
   - Role mapping from OAuth scopes
   - Profile sync (name, email)

### ⭐ **Priority 4: Advanced Features** (Optimization)
**Estimated Effort**: 3-5 days  
**Impact**: LOW-MEDIUM (nice to have)

#### 4A: Machine Learning Guardian Routing
- Analyze historical decisions
- Predict optimal routing
- A/B test guardian configs

#### 4B: Anomaly Detection
- Statistical models for UOW patterns
- Alert on unusual behavior
- Suggest interventions proactively

#### 4C: Performance Analytics
- Pilot efficiency (avg resolution time)
- Bottleneck detection
- SLA tracking

#### 4D: Multi-Tenant Support
- Instance-scoped permissions
- Tenant-specific dashboards
- Audit separation

---

## Recommended Phase 3 Roadmap

### Week 1: Frontend Dashboard
**Day 1-2**: React setup + WebSocket integration
- Scaffold React app
- Connect to WebSocket endpoint
- Handle connection lifecycle

**Day 3**: UI Components
- Intervention cards
- Action buttons
- Status/priority badges

**Day 4-5**: Pages
- Dashboard (pending)
- Request detail
- History
- Basic styling

### Week 2: Persistence + OAuth
**Day 1-2**: Database migration
- Create Intervention_Requests table
- Migrate InterventionStore
- Add pagination

**Day 3-4**: OAuth 2.0
- GitHub integration
- Token refresh
- User mapping

**Day 5**: Testing + Deployment
- E2E tests
- Load testing
- Staging deployment

### Week 3: Polish + Documentation
**Day 1-2**: Advanced features (choose 1-2)
- ML routing, anomaly detection, analytics, or multi-tenant

**Day 3-4**: Performance optimization
- Caching strategy
- Database indexes
- Query optimization

**Day 5**: Documentation + training
- User guide
- API documentation
- Deployment guide

---

## Technical Decisions for Phase 3

### Frontend Framework
**Options**:
- ✅ **React** (recommended)
  - Pros: Largest ecosystem, WebSocket libraries, real-time patterns well-established
  - Cons: Steeper learning curve
  - **Recommendation**: Use if team experienced with React

- ✅ **Vue** (alternative)
  - Pros: Simpler syntax, easier to learn
  - Cons: Smaller ecosystem
  - **Recommendation**: Use if team prefers simplicity

- ❌ **Angular** (not recommended for MVP)
  - Overkill for this project

### Real-time Library
- **Socket.IO** (recommended for Phase 3+)
  - Better fallbacks than raw WebSocket
  - Automatic reconnection
  - Room/namespace support
  - Future: broadcast to multiple pilots

- **ws.js** (simpler, works with existing WebSocket endpoint)
  - Lightweight
  - Works with existing endpoint
  - Manual reconnection needed

**Recommendation**: Use Socket.IO for production readiness

### Database Storage
- **SQLAlchemy** (native to project)
  - Leverage existing models
  - Use for InterventionRequest persistence
  - Same ORM pattern as Phase 1 & 2

**Tables to Create**:
```python
class Intervention_Requests(InstanceBase):
    """Persistent intervention requests."""
    request_id = Column(UUID, primary_key=True)
    instance_id = Column(UUID, ForeignKey(...))
    uow_id = Column(UUID, nullable=False)
    intervention_type = Column(String(50))  # Enum value
    status = Column(String(50))
    priority = Column(String(50))
    title, description, context = ...
    created_at, updated_at, expires_at = ...
    # etc.
```

---

## Architecture Recommendations

### Frontend → Backend Communication

```
User Browser
    ↓
WebSocket (Socket.IO)
    ↓
FastAPI WebSocket Endpoint
    ↓
WebSocketMessageHandler
    ↓
InterventionStore (future: InterventionDB)
    ↓
UnitsOfWork (existing)
```

### Request Flow

```
System detects ambiguity
    ↓
Creates intervention via store.create_request()
    ↓
Store publishes event (if backend supports)
    ↓
Dashboard WebSocket receives update
    ↓
UI shows new pending request to assigned pilot
    ↓
Pilot clicks approve/reject
    ↓
WebSocket sends action → Handler
    ↓
store.update_request() → UnitsOfWork
    ↓
System resumes workflow
```

### Pilot Session Flow

```
Browser
    ↓
OAuth login (GitHub)
    ↓
Get JWT token
    ↓
Connect WebSocket (with JWT auth)
    ↓
Receive pending requests
    ↓
Perform actions (approve, reject, etc.)
    ↓
See updated metrics in real-time
```

---

## Open Questions for Phase 3

1. **Frontend Framework**: React or Vue?
2. **Realtime Library**: Socket.IO or raw WebSocket?
3. **Styling**: Tailwind, Material-UI, or custom?
4. **Mobile**: Support mobile pilots? (Progressive Web App)
5. **Internationalization**: Multi-language support?
6. **Accessibility**: WCAG compliance level?
7. **Performance**: Expected concurrent pilots?
8. **Analytics**: Google Analytics, custom, or none?

---

## Success Criteria for Phase 3

### MVP (Minimum Viable Product)
- [x] Dashboard displays pending interventions
- [x] One-click approve/reject/waive/resume actions
- [x] Real-time updates via WebSocket
- [x] Request history view
- [x] Basic metrics display

### Production Ready
- [x] Persistent storage (database)
- [x] OAuth 2.0 authentication
- [x] Role-based UI (show appropriate actions)
- [x] Audit trail view
- [x] Error handling + offline support
- [x] Performance optimized (<100ms response time)
- [x] Mobile-responsive design
- [x] Full test coverage (unit + e2e)
- [x] Documentation complete

---

## Files to Create in Phase 3

### Frontend
```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── InterventionCard.tsx
│   │   ├── ActionButtons.tsx
│   │   ├── MetricsBadges.tsx
│   │   └── PriorityBadge.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── RequestDetail.tsx
│   │   ├── History.tsx
│   │   ├── Metrics.tsx
│   │   └── Profile.tsx
│   ├── services/
│   │   ├── websocket.ts
│   │   ├── auth.ts
│   │   └── api.ts
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── usePendingRequests.ts
│   │   └── useAuth.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

### Backend (Extensions)
```
chameleon_workflow_engine/
├── oauth_provider.py (new)
├── persistence_layer.py (new - DB migration)
└── websocket_auth.py (new - JWT validation for WS)

database/
├── models_intervention.py (new - persistent storage)
└── migrations/ (new - DB schema updates)
```

### Tests (Phase 3)
```
tests/
├── test_dashboard_frontend.py (Selenium/Playwright)
├── test_oauth_flow.py
├── test_websocket_auth.py
└── e2e/
    ├── test_intervention_workflow.py
    └── test_pilot_actions.py
```

---

## Development Velocity Estimate

| Phase | Components | LOC | Duration | Status |
|-------|-----------|-----|----------|--------|
| Phase 1 | 5 systems | 1500 | ~2 days | ✅ DONE |
| Phase 2 | 5 systems | 1980 | ~1 day | ✅ DONE |
| Phase 3 | Frontend + Persist + OAuth | 3000+ | ~5-7 days | ⏳ Next |

---

## Phase 2 → Phase 3 Transition Checklist

Before starting Phase 3:

- [x] Phase 2 all tests passing (21/21)
- [x] Phase 2 documentation complete
- [x] Phase 2 code reviewed and approved
- [ ] Decide on frontend framework (React/Vue)
- [ ] Set up frontend build environment (Vite/Webpack)
- [ ] Choose OAuth provider (GitHub/Azure)
- [ ] Define database schema for persistence
- [ ] Plan UI mockups (low-fidelity OK for MVP)
- [ ] Schedule Phase 3 kickoff meeting

---

## Quick Start Template (Phase 3 Frontend)

```bash
# Create React app with Vite
npm create vite@latest chameleon-dashboard -- --template react-ts

# Install dependencies
cd chameleon-dashboard
npm install

# WebSocket + state management
npm install socket.io-client zustand axios

# UI components
npm install @headlessui/react @tailwindcss/ui tailwindcss

# Start dev server
npm run dev
```

**Sample WebSocket Hook** (for Phase 3):

```typescript
// hooks/useWebSocket.ts
import { useEffect, useState } from 'react';
import io from 'socket.io-client';

export function useWebSocket(url: string, token: string) {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const newSocket = io(url, {
      auth: { token }
    });

    newSocket.on('connect', () => setConnected(true));
    newSocket.on('disconnect', () => setConnected(false));

    setSocket(newSocket);
    return () => newSocket.close();
  }, [url, token]);

  return { socket, connected };
}
```

---

## Final Thoughts

**Phase 2 has provided a rock-solid foundation** for Phase 3:

✅ Security (JWT + RBAC)  
✅ Intelligent routing (Guardian types)  
✅ Real-time infrastructure (WebSocket-ready)  
✅ Data structures (InterventionStore, DashboardMetrics)  
✅ Test patterns (mocking, integration tests)  
✅ Documentation (examples, docstrings)  

**Phase 3 is ready to begin immediately** with frontend implementation being the highest priority.

**Estimated time from Phase 3 start to production**: 1-2 weeks (accelerated due to solid Phase 2 foundation)

---

## Questions?

Refer back to:
- `PHASE_2_COMPLETE.md` - Detailed spec
- `chameleon_workflow_engine/interactive_dashboard.py` - API reference
- `phase2_dashboard_test.py` - Integration examples

---

**Phase 2 Complete** ✨  
**Phase 3: Ready to Begin** 🚀  
**Production Deployment**: 2-3 weeks estimated  

Good luck with Phase 3! 🎉
