/**
 * App: Root router configuration for the Chameleon Dashboard
 * 
 * Handles:
 * - Route structure
 * - Layout wrappers
 * - Protected route guards
 * - Page transitions
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthenticatedLayout, GuestLayout } from './layouts'
import { ProtectedRoute } from './utils/navigation'
import { useAuth } from './hooks'

// Pages
import { Login, Dashboard, InterventionDetail, History, Settings, NotFound } from './pages'

export function App() {
  const auth = useAuth()

  // Show loading during auth initialization
  if (auth.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Guest routes (login) */}
        <Route element={<GuestLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={auth.isAuthenticated ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} />
        </Route>

        {/* Protected routes (require authentication) */}
        <Route element={<ProtectedRoute isAuthenticated={auth.isAuthenticated}><AuthenticatedLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/interventions/:interventionId" element={<InterventionDetail />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* 404 handling */}
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
