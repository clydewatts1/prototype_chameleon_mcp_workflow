# Phase 3: Frontend Dashboard 🚀

**Status**: Implementation Started  
**Priority**: HIGHEST (Blocks production use)  
**Estimated Completion**: 2-3 days  

---

## Overview

The Chameleon Dashboard frontend is a modern React/TypeScript application that provides pilots with a real-time interface to manage intervention requests. Built with Vite, it connects to the Phase 2 backend via WebSocket for live updates.

## Architecture

### Technology Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite (lightning-fast HMR)
- **Styling**: Tailwind CSS (utility-first)
- **State Management**: React hooks + Zustand (simple)
- **Communication**: WebSocket (real-time) + Fetch (REST)
- **Testing**: Vitest + React Testing Library (ready)

### Project Structure

```
frontend/
├── index.html                    # HTML entry point
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript config
├── vite.config.ts               # Vite configuration
├── src/
│   ├── main.tsx                 # React entry point
│   ├── App.tsx                  # Root component
│   ├── App.css                  # App styles
│   ├── index.css                # Global styles
│   ├── components/
│   │   ├── InterventionCard.tsx       # Single request card
│   │   ├── MetricsDashboard.tsx       # Real-time metrics
│   │   ├── PilotProfile.tsx           # Pilot info display
│   │   ├── StatusBadge.tsx            # Status indicator
│   │   └── index.ts                   # Exports
│   ├── hooks/
│   │   ├── useWebSocket.ts            # WebSocket connection
│   │   ├── useIntervention.ts         # Intervention state
│   │   ├── useAuth.ts                 # JWT token management
│   │   └── index.ts                   # Exports
│   ├── types/
│   │   └── index.ts                   # TypeScript definitions
│   └── utils/
│       └── (utilities - ready for expansion)
└── .env.example                 # Environment template
```

## Quick Start

### Prerequisites

- Node.js 16+ & npm
- Backend running on `localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Opens at `http://localhost:5173`

### Build

```bash
npm run build
npm run preview
```

## Features Implemented (Day 1)

✅ **Project Setup**
- React 18 + TypeScript
- Vite configuration with path aliases
- Tailwind CSS via CDN
- Environment configuration

✅ **WebSocket Integration** (`useWebSocket`)
- Auto-reconnect with exponential backoff
- Message queuing during disconnection
- Type-safe message handling
- Connection state management

✅ **State Management**
- `useIntervention` - Request & metrics state
- `useAuth` - JWT token & pilot info
- Clean, composable hooks

✅ **Core Components**
- `InterventionCard` - Display pending requests with quick actions
- `MetricsDashboard` - Real-time statistics display
- `PilotProfile` - Logged-in pilot info
- `StatusBadge` - Status indicator
- `LoginPage` - Token input (dev mode)

✅ **Main App**
- Full dashboard layout
- WebSocket connection management
- Periodic metrics updates (5s)
- Error handling & display
- Responsive design (mobile-first)

## What's Next (Days 2-3)

### Day 2: Additional Components & Pages

```typescript
// Components to create:
- InterventionList.tsx         // Paginated list with filters
- InterventionDetail.tsx       // Full detail modal/page
- ActionForm.tsx               // Approve/reject with reason
- HistoryPage.tsx              // Past interventions
- SettingsPage.tsx             // Pilot preferences
- Navigation.tsx               // Route-based navigation
```

### Day 3: Pages & Routing

```typescript
// Pages to create:
- pages/Dashboard.tsx          // Main page (current App)
- pages/InterventionDetail.tsx // Single intervention view
- pages/History.tsx            // Past interventions
- pages/Settings.tsx           // Pilot settings
- pages/NotFound.tsx           // 404 page
```

## Testing Backend Connection

### 1. Start Backend

```bash
# In root directory
python -m chameleon_workflow_engine.server
```

Backend runs on `ws://localhost:8000/ws`

### 2. Generate Test Token

```bash
python phase2_jwt_rbac_test.py
```

Copy an ADMIN or OPERATOR token.

### 3. Login to Dashboard

1. Open http://localhost:5173
2. Paste token in "JWT Token" field
3. Click "Login"
4. See dashboard with metrics

### 4. Create Test Request (Backend)

```python
# In Python shell or script
from chameleon_workflow_engine.interactive_dashboard import (
    get_intervention_store,
    InterventionType,
)

store = get_intervention_store()
request = store.create_request(
    request_id="req-test-001",
    uow_id="uow-test-001",
    intervention_type=InterventionType.CLARIFICATION,
    title="Test Intervention",
    description="This is a test",
    priority="high",
)
```

### 5. See Request Appear Live

Request should appear on dashboard within 5 seconds!

## WebSocket Message Protocol

### Frontend → Backend

```typescript
// Subscribe to updates
{ type: "subscribe", payload: { pilot_id: "pilot-001" } }

// Get pending requests
{ type: "get_pending", payload: { pilot_id: "pilot-001", limit: 20 } }

// Get metrics
{ type: "get_metrics", payload: {} }

// Get single request detail
{ type: "request_detail", payload: { request_id: "req-001" } }

// Take action (phase 3.2)
{ type: "action", payload: { request_id: "req-001", action: "approve", reason: "..." } }
```

### Backend → Frontend

```typescript
// Success response
{
  success: true,
  data: {
    requests: [...],           // OR
    total_interventions: 5,    // OR
    request_id: "req-001",     // OR
    ...
  }
}

// Error response
{
  success: false,
  error: {
    code: "NOT_FOUND",
    message: "Request not found"
  }
}
```

## Integration Checklist

- [ ] Backend running on localhost:8000
- [ ] WebSocket endpoint working (`/ws`)
- [ ] JWT token generation working
- [ ] Dashboard loads without errors
- [ ] WebSocket connects automatically
- [ ] Real-time metrics updates working
- [ ] InterventionCard clicks work
- [ ] Mobile responsive on iPhone

## CSS/Styling Notes

Using **Tailwind CSS via CDN** for simplicity:
- No build step needed for Tailwind
- Full utility support
- Responsive breakpoints: `sm:`, `md:`, `lg:`
- Dark mode ready (future)

To switch to local Tailwind:
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

## Performance Targets

- Initial load: < 2 seconds
- WebSocket connection: < 500ms
- Metrics update: < 5 seconds
- Card click response: < 100ms
- Mobile responsiveness: < 60fps

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Environment Variables

See `.env.example`:

```bash
VITE_API_HOST=localhost:8000      # Backend WebSocket host
VITE_API_PROTOCOL=ws              # ws or wss for production
VITE_GITHUB_CLIENT_ID=            # OAuth (Phase 3.3)
VITE_SENTRY_DSN=                  # Error tracking (optional)
```

Copy to `.env` locally:
```bash
cp .env.example .env
```

## Development Mode Features

- Fast Refresh (HMR)
- React DevTools extension support
- TypeScript strict mode
- ESLint setup (ready)

## Production Build

```bash
npm run build
# Creates optimized bundle in dist/

npm run preview
# Test production build locally
```

Output is ready to deploy to:
- Netlify
- Vercel
- AWS S3 + CloudFront
- Any static host

## Troubleshooting

### WebSocket Connection Fails

1. Check backend is running: `curl http://localhost:8000/health`
2. Check CORS: Backend should allow WebSocket origin
3. Check firewall: Port 8000 accessible

### Metrics not updating

1. Dashboard should update every 5 seconds
2. Check browser console for errors
3. Verify WebSocket is connected (green dot in header)
4. Try refreshing page

### Token validation fails

1. Token must be valid JWT
2. Check expiration: `exp` claim should be future timestamp
3. Generate fresh token: `python phase2_jwt_rbac_test.py`

## Next Steps

1. **Today**: Test connection to backend ✓
2. **Tomorrow**: Add InterventionDetail page
3. **Day 3**: Add History page + Routing
4. **Bonus**: Add OAuth login flow

## Questions?

Check the [PHASE_3_ROADMAP.md](../PHASE_3_ROADMAP.md) for full architecture guide and decision tree.
