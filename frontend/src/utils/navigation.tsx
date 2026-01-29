/**
 * Navigation utilities and route guards
 * 
 * Provides:
 * - ProtectedRoute component
 * - Navigation helpers
 * - Route path constants
 */

import { ReactNode, ReactElement } from 'react'
import { Navigate } from 'react-router-dom'

// Route path constants
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  INTERVENTION_DETAIL: (id: string) => `/interventions/${id}`,
  HISTORY: '/history',
  SETTINGS: '/settings',
  NOT_FOUND: '*',
} as const

// Protected route guard component
interface ProtectedRouteProps {
  isAuthenticated: boolean
  children: ReactNode
}

export function ProtectedRoute({
  isAuthenticated,
  children,
}: ProtectedRouteProps): ReactElement | ReactNode {
  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  return children
}

// Navigation helper functions
export const navigateTo = {
  dashboard: () => ROUTES.DASHBOARD,
  interventionDetail: (id: string) => ROUTES.INTERVENTION_DETAIL(id),
  history: () => ROUTES.HISTORY,
  settings: () => ROUTES.SETTINGS,
  login: () => ROUTES.LOGIN,
} as const
