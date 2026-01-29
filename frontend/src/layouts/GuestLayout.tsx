/**
 * GuestLayout: Layout for unauthenticated pages (login, etc.)
 * 
 * Provides:
 * - Minimal layout for login page
 */

import { Outlet } from 'react-router-dom'

export function GuestLayout() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Outlet />
    </div>
  )
}
