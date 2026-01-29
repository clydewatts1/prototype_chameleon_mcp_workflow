# Phase 3: Production Features & User Experience 🚀

**Status**: Starting NOW (Phase 2 ✅ 100% Complete)  
**Target Completion**: 7-10 days  
**Team Size**: 1-2 developers

---

## Executive Summary

Phase 3 focuses on **user-facing features** that turn the Chameleon backend into a production-ready system. With Phase 2's solid foundation (JWT, RBAC, Guardianship, Stream Broadcasting), Phase 3 enables pilots to actually interact with the system via a modern dashboard.

**Key Principle**: All backend APIs are ready. Frontend is the focus.

---

## Priority 1: Interactive Dashboard UI ✨ (HIGHEST PRIORITY)

**Effort**: 2-3 days  
**Impact**: HIGH - Blocks production use  
**Status**: Starting now  

### Architecture

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── InterventionCard.tsx        # Render single intervention request
│   │   ├── InterventionList.tsx        # List of pending requests
│   │   ├── MetricsDashboard.tsx        # Real-time metrics display
│   │   ├── PilotProfile.tsx            # Pilot info & role
│   │   └── ActionButtons.tsx           # Approve/Reject/Review buttons
│   ├── hooks/
│   │   ├── useWebSocket.ts             # WebSocket connection management
│   │   ├── useIntervention.ts          # Intervention request state
│   │   └── useAuth.ts                  # JWT token management
│   ├── pages/
│   │   ├── Dashboard.tsx               # Main dashboard page
│   │   ├── InterventionDetail.tsx      # Detailed intervention view
│   │   ├── History.tsx                 # Past interventions
│   │   └── Settings.tsx                # Pilot settings
│   ├── services/
│   │   ├── ws-client.ts                # WebSocket API client
│   │   ├── api-client.ts               # REST API client
│   │   └── auth-service.ts             # JWT token handling
│   ├── styles/
│   │   ├── global.css
│   │   └── components.css
│   ├── App.tsx
│   └── index.tsx
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Recommended Stack

- **Framework**: React 18 (or Vue 3 alternative)
- **TypeScript**: Full type safety
- **Build**: Vite (lightning fast)
- **WebSocket**: `ws` or `socket.io` client
- **State**: React Query or Zustand
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui or Headless UI

### Implementation Steps

1. **Day 1**: Project setup & WebSocket client
   - Create React/Vite project
   - Build `useWebSocket` hook
   - Establish connection to backend
   - Handle reconnection logic

2. **Day 2**: Core UI components
   - `InterventionCard` - Display request with priority badge
   - `InterventionList` - Paginated list of pending requests
   - `ActionButtons` - Approve/Reject/Review actions
   - `MetricsDashboard` - Real-time stats (pending, approved, rejected)

3. **Day 3**: Pages & routing
   - Dashboard page (main view)
   - Detail page (single intervention)
   - History page (past interventions)
   - Responsive design

### WebSocket Message Flow

```
FRONTEND → BACKEND:
1. { "type": "subscribe", "pilot_id": "pilot-001" }
2. { "type": "get_pending", "pilot_id": "pilot-001", "limit": 20 }
3. { "type": "get_metrics", ... }
4. { "type": "request_detail", "request_id": "req-001" }

BACKEND → FRONTEND (broadcast):
1. New intervention request created
2. Metrics updated every 30 seconds
3. Request status changed (approved/rejected)
4. Pilot action completed notification
```

### Testing Approach

- Unit tests for React components (Vitest)
- E2E tests with mock backend (Cypress)
- WebSocket testing with mock server
- Manual testing against real Phase 2 backend

---

## Priority 2: Database Persistence 💾 (MEDIUM PRIORITY)

**Effort**: 1-2 days  
**Impact**: MEDIUM - Required for production  
**Status**: Ready when Priority 1 complete  
**Prerequisite**: InterventionStore API locked (no changes)

### Current State

`InterventionStore` is in-memory. Works great for:
- Development & testing
- Small deployments
- Single-instance setups

### Changes Required

1. **Create SQLAlchemy models** (`models_phase3.py`)
   ```python
   class Intervention(Base):
       __tablename__ = "interventions"
       
       request_id: str = Column(String, primary_key=True)
       uow_id: str = Column(String)
       intervention_type: str = Column(String)
       status: str = Column(String)
       priority: str = Column(String)
       title: str = Column(String)
       description: str = Column(String)
       context: dict = Column(JSON)
       
       created_at: datetime = Column(DateTime)
       updated_at: datetime = Column(DateTime)
       assigned_to: str = Column(String, nullable=True)
       action_reason: str = Column(String, nullable=True)
       expires_at: datetime = Column(DateTime, nullable=True)
       
       # Indexes for performance
       __table_args__ = (
           Index('idx_status_priority', 'status', 'priority'),
           Index('idx_assigned_to', 'assigned_to'),
           Index('idx_uow_id', 'uow_id'),
       )
   ```

2. **Implement SQLAlchemy adapter**
   ```python
   class InterventionStoreSQLAlchemy(InterventionStore):
       """Drop-in replacement for in-memory store."""
       
       def __init__(self, db_url: str):
           self.engine = create_engine(db_url)
           self.SessionLocal = sessionmaker(bind=self.engine)
           # Create tables
           Base.metadata.create_all(self.engine)
       
       # Implement all InterventionStore methods using SQL
   ```

3. **Zero-downtime migration**
   - Deploy adapter alongside in-memory store
   - Log all operations to both (temporary dual-write)
   - Validate consistency
   - Switch to database-only
   - Monitor for 24 hours

### Performance Targets

- Create request: < 50ms
- Get pending requests (paginated): < 100ms
- Update status: < 50ms
- Get metrics: < 200ms (with aggregation)

### Migration Checklist

- [ ] SQLAlchemy models created & tested
- [ ] DB adapter passes all InterventionStore tests
- [ ] Pagination implemented
- [ ] Indexes optimized
- [ ] Connection pooling configured
- [ ] Backup & restore procedures documented

---

## Priority 3: OAuth 2.0 Integration 🔐 (MEDIUM-LOW PRIORITY)

**Effort**: 2 days  
**Impact**: MEDIUM - Blocks production  
**Status**: Ready when Priority 1 UI can display user  
**Options**: GitHub, Azure Entra ID, Google

### Architecture

```
Frontend:                          Backend:
┌──────────────────┐              ┌──────────────────┐
│  Login Page      │ ──oauth──→   │  OAuth Handler   │
│  (GitHub/Azure)  │              │  ↓               │
└──────────────────┘              │ Create/Update    │
        ↑                          │ Pilot profile    │
        │                          │ ↓               │
        └─── token (JWT) ─────────│  Return JWT      │
                                   └──────────────────┘
```

### Implementation Path

**Option A: GitHub OAuth** (Simplest, 1 day)
```python
# backend: oauth_handler.py
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='github',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    authorize_url='https://github.com/login/oauth/authorize',
    token_url='https://github.com/login/oauth/access_token',
    userinfo_endpoint='https://api.github.com/user',
)

@app.post("/auth/github-callback")
async def github_callback(code: str):
    # Exchange code for token
    # Fetch user info
    # Create/update pilot
    # Return JWT
    pass
```

**Option B: Azure Entra ID** (Enterprise, 1.5 days)
```python
# More complex setup but integrates with corporate directories
# Requires tenant ID, client ID, secret
# Token refresh support built-in
```

**Option C: Google OAuth** (Popular, 1 day)
```python
# Similar to GitHub, Google OAuth flow
# Scope: email, profile
```

### Token Refresh Strategy

```
Frontend:
- Store access token in memory (not localStorage)
- Store refresh token in httpOnly cookie
- Auto-refresh 5 minutes before expiration
- Show login modal if refresh fails
```

### Pilot Profile Creation

```python
# Upon first login, create/update Pilot:
{
    "pilot_id": "github:clydewatts1",
    "name": "Clyde Watts",
    "email": "clyde@example.com",
    "role": "OPERATOR",  # Default, upgradeable by ADMIN
    "last_login": "2026-01-29T10:00:00Z",
    "oauth_provider": "github",
    "oauth_id": "12345",
}
```

### Testing

```python
# Mock OAuth provider for testing
class MockOAuthProvider:
    def authorize_url(self): pass
    def token(self, code): 
        return {"access_token": "mock_token"}
    def userinfo(self, token):
        return {"login": "test_user", "name": "Test User"}
```

---

## Priority 4: Advanced Features 🧠 (LOW PRIORITY - Phase 3.5)

**Effort**: 3-5 days  
**Impact**: LOW-MEDIUM - Nice-to-have  
**Status**: After Priorities 1-3 complete  

### 4a: ML-Based Routing
Route interventions to best-qualified pilot based on:
- Historical approval rate
- Expertise tags
- Workload
- Time zone

### 4b: Anomaly Detection
- Unusual request patterns
- Rapid re-requests (same UOW, multiple pilots)
- Timeout patterns (requests expiring without action)

### 4c: Performance Analytics
- Dashboard load time
- API latency percentiles
- WebSocket connection stability
- Pilot response time distribution

### 4d: Multi-Tenant Support
- Isolated stores per organization
- Scoped API keys
- Cross-tenant reporting (admin only)

---

## Deployment Strategy

### Pre-Production Checklist

**Frontend**:
- [ ] Build optimized (Vite build)
- [ ] Environment variables configured
- [ ] Error tracking enabled (Sentry)
- [ ] Analytics installed (optional)
- [ ] PWA support (offline mode)
- [ ] CDN configured (CloudFlare, etc.)

**Backend**:
- [ ] Database backups automated
- [ ] Connection pooling tuned
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Error logging to external service
- [ ] Performance monitoring (New Relic, DataDog)

**Infrastructure**:
- [ ] Frontend: Netlify, Vercel, or AWS CloudFront
- [ ] Backend: Docker container ready
- [ ] Database: PostgreSQL or managed (AWS RDS)
- [ ] Redis: For streaming (ElastiCache)
- [ ] Load balancer: Handle multiple instances

### Release Plan

1. **Beta Release** (Week 1)
   - Deploy to staging environment
   - Internal testing with team
   - Performance benchmarking
   - Security audit

2. **Production Release** (Week 2)
   - Blue-green deployment
   - Monitor error rates
   - Performance metrics
   - User feedback collection

3. **Post-Release** (Ongoing)
   - Bug fixes (weekly)
   - Performance optimization
   - Feature requests
   - Security patches

---

## Success Criteria

### Phase 3 Complete When:

✅ **Frontend UI**
- Dashboard loads in < 2 seconds
- WebSocket connection automatic
- Real-time updates every 5 seconds
- Mobile responsive (tested on iPhone/Android)
- Keyboard accessible (WCAG 2.1 AA)

✅ **Database Persistence**
- All InterventionStore tests passing
- Performance benchmarks met (< 200ms p95)
- 24-hour production validation passed

✅ **OAuth 2.0**
- User can login via GitHub/Azure/Google
- JWT token generated correctly
- Token refresh works automatically
- Logout clears session

✅ **Production Ready**
- All 3 priorities tested
- Deployment docs written
- Runbook for on-call team
- SLA defined (99.9% uptime)

---

## Timeline & Milestones

| Week | Focus | Deliverable |
|------|-------|-------------|
| **Week 1** | Frontend UI | Dashboard + WebSocket integration |
| **Week 1** | DB Persistence | SQLAlchemy adapter ready |
| **Week 1-2** | OAuth | GitHub OAuth working |
| **Week 2** | Integration | Full system E2E tests |
| **Week 2** | Deploy | Production release |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| WebSocket connection drops | Medium | High | Auto-reconnect with exponential backoff |
| Database query slow | Low | High | Add indexes, optimize queries, monitor |
| OAuth token expiration | Low | Medium | Implement refresh token rotation |
| Frontend build fails | Low | High | Test in CI/CD before deploy |
| Production outage | Very Low | Critical | Blue-green deployment, health checks |

---

## Team Handoff Notes

- **For Frontend Dev**: Start with `useWebSocket` hook and `InterventionCard` component
- **For Backend Dev**: DB adapter can start in parallel after Priority 1 UI is complete
- **For DevOps**: Begin infrastructure planning (Docker, K8s, monitoring)
- **For QA**: Prepare test scenarios for OAuth, WebSocket reliability, performance

---

## Questions & Decisions

1. **React vs Vue?**
   - Recommendation: React (larger community)
   - Alternative: Vue (easier learning curve)

2. **Database: PostgreSQL vs Managed (AWS RDS)?**
   - Recommendation: Managed (reduces ops burden)
   - Dev: Local PostgreSQL in Docker

3. **Frontend Hosting: Netlify vs Vercel vs S3?**
   - Recommendation: Netlify (easiest, built-in functions for serverless)
   - Alternative: Vercel (if using Next.js)

4. **OAuth Provider: GitHub vs Azure vs Google?**
   - Recommendation: GitHub (simplest to implement)
   - Enterprise: Azure Entra ID (if corporate)

---

## Next Steps

1. **Right Now**: ✅ You are here
2. **Next**: Initialize React project & build WebSocket client
3. **Then**: Connect to Phase 2 backend & test live
4. **Then**: Build UI components
5. **Finally**: Complete Priorities 2 & 3

Ready to start? Let's build this! 🚀
