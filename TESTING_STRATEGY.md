# Phase 3 Testing Strategy 🧪

**Priority 1.5**: Testing & Integration  
**Estimated Time**: 1-2 days  
**Goal**: Validate frontend components and Phase 2 backend integration

---

## Testing Levels

### 1. Unit Tests (Component Testing)
Test individual React components in isolation

**Stack**: Vitest + React Testing Library

**Components to Test**:
- `InterventionCard.tsx`
- `InterventionList.tsx`
- `ActionButtons.tsx`
- `MetricsDashboard.tsx`
- `StatusBadge.tsx`
- `PilotProfile.tsx`

**Test Coverage Goal**: 80%+

### 2. Integration Tests
Test how components work together with hooks and services

**Stack**: Vitest + Mock WebSocket Server

**Tests**:
- WebSocket connection and reconnection
- API client error handling
- Authentication token management
- Real-time updates flow

### 3. E2E Tests (Optional)
Full application flow testing

**Stack**: Cypress or Playwright

**Scenarios**:
- User login flow
- Approval workflow
- WebSocket disconnect/reconnect
- Real-time metrics updates

---

## Quick Start: Running Tests

```bash
# From frontend directory
cd frontend

# Run all tests (watch mode)
npm test

# Run tests with UI
npm test:ui

# Run specific test file
npm test components/InterventionCard.test.tsx

# Run with coverage
npm test -- --coverage
```

---

## Test File Structure

```
src/
├── components/
│   ├── InterventionCard.tsx
│   └── InterventionCard.test.tsx          ← Create these
├── hooks/
│   ├── useWebSocket.ts
│   └── useWebSocket.test.ts               ← Create these
├── services/
│   ├── ws-client.ts
│   └── ws-client.test.ts                  ← Create these
└── test/
    ├── setup.ts
    ├── mocks/
    │   ├── handlers.ts                    ← Mock API responses
    │   └── server.ts                      ← Mock server setup
    └── utils/
        └── test-utils.tsx                 ← Custom render functions
```

---

## Phase 2 Backend Integration Testing

### Prerequisites

Before running integration tests, ensure Phase 2 backend is running:

```bash
# Terminal 1: Start Phase 2 backend
cd examples/example_agents
python setup_demo.py

# Check backend is running
curl http://localhost:8000/health
```

### Integration Test Scenarios

| Scenario | Test | Expected Result |
|----------|------|-----------------|
| **WebSocket Connection** | Client connects | Connected state = true |
| **Auto-Reconnect** | Close connection | Reconnects within 3s |
| **Request Fetching** | Fetch pending requests | Returns list of InterventionRequest[] |
| **Action Submission** | Submit approval | Status changes to APPROVED |
| **Metrics Update** | Stream metrics | Updates dashboard real-time |
| **Token Refresh** | Token expires | Auto-refreshes JWT |
| **Error Handling** | Network failure | Displays error, retries |

---

## Test Implementation Plan

### Step 1: Set Up Test Infrastructure ✅
- [x] Vitest configured in vite.config.ts
- [x] Test setup file created (setup.ts)
- [ ] Create mock utilities

### Step 2: Write Component Tests
- [ ] Create `__tests__` directory
- [ ] Write tests for each component
- [ ] Mock API responses
- [ ] Test user interactions

### Step 3: Integration Tests
- [ ] Test WebSocket flow
- [ ] Test API client methods
- [ ] Test auth token management
- [ ] Test error scenarios

### Step 4: E2E Tests (Optional)
- [ ] Create Cypress tests
- [ ] Test full user workflows
- [ ] Test real backend integration

### Step 5: Validate Against Phase 2
- [ ] Connect to running Phase 2 backend
- [ ] Create test interventions
- [ ] Verify approval workflow
- [ ] Monitor WebSocket streams

---

## Testing Commands

```bash
# Development
npm test                    # Watch mode
npm test:ui                 # UI dashboard

# CI/CD
npm test -- --run          # Run once, exit
npm test -- --coverage     # Generate coverage report

# Specific tests
npm test components/        # Test all components
npm test hooks/             # Test all hooks
npm test services/          # Test all services
```

---

## Success Criteria for Testing Phase

✅ **Unit Test Coverage**:
- [ ] 80%+ code coverage
- [ ] All components tested
- [ ] All hooks tested
- [ ] All services tested

✅ **Integration Testing**:
- [ ] WebSocket client works
- [ ] API client handles errors
- [ ] Auth flow works
- [ ] Real-time updates work

✅ **Backend Integration**:
- [ ] Connects to Phase 2
- [ ] Fetches interventions
- [ ] Submits actions
- [ ] Receives broadcasts

✅ **User Workflows**:
- [ ] Login works
- [ ] Dashboard loads
- [ ] Approval flow works
- [ ] Rejection flow works
- [ ] History loads
- [ ] Settings work

---

## Running Tests Now

```bash
# 1. Install test dependencies (if needed)
cd frontend
npm install --save-dev @testing-library/react @testing-library/jest-dom jsdom

# 2. Run tests
npm test

# 3. View coverage
npm test -- --coverage
```

---

## Next: Implement First Test

Start with a simple component test:

```typescript
// src/components/__tests__/StatusBadge.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';

describe('StatusBadge', () => {
  it('renders pending status', () => {
    render(<StatusBadge status="PENDING" />);
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('applies correct CSS class for approved status', () => {
    const { container } = render(<StatusBadge status="APPROVED" />);
    expect(container.querySelector('.status-approved')).toBeInTheDocument();
  });
});
```

---

## Phase 2 Backend Integration Checklist

Before testing integration:

- [ ] Backend running on `http://localhost:8000`
- [ ] WebSocket endpoint available on `ws://localhost:8000/ws`
- [ ] Demo data created (interventions)
- [ ] CORS configured for frontend
- [ ] JWT tokens working

Test commands:

```bash
# Check backend health
curl http://localhost:8000/health

# Fetch pending interventions
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/interventions/pending

# Test WebSocket connection
wscat -c ws://localhost:8000/ws
```

---

## Troubleshooting

### Tests Not Running

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm test
```

### WebSocket Connection Fails

- Check backend is running: `curl http://localhost:8000/health`
- Check CORS is configured
- Check token is valid
- Try with `check_same_thread=False` in SQLite URL

### Component Tests Fail

- Ensure @testing-library/react is installed
- Check jsdom environment in vite.config.ts
- Mock external APIs/WebSocket

---

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Mock Service Worker](https://mswjs.io/) (optional, for API mocking)

---

## Estimated Timeline

| Task | Time | Status |
|------|------|--------|
| Set up test infrastructure | 30 min | 🟢 Ready |
| Write component tests | 2-3 hours | 🔴 Todo |
| Write integration tests | 2-3 hours | 🔴 Todo |
| Test Phase 2 integration | 1-2 hours | 🔴 Todo |
| Fix bugs & improve coverage | 2-3 hours | 🔴 Todo |
| **Total** | **1-2 days** | 🟡 In Progress |

---

## Let's Get Started! 🚀

Run these commands to begin testing:

```bash
cd frontend
npm test
```

See the next section for the first test to implement.
