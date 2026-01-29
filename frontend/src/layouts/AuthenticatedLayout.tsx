/**
 * AuthenticatedLayout: Shared layout for authenticated pages
 * 
 * Provides:
 * - Header with navigation
 * - Sidebar with links
 * - Connection status indicator
 * - Pilot profile menu
 */

import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth, useWebSocket } from '../hooks'
import { PilotProfile } from '../components'

const navigationItems = [
  { label: 'Dashboard', path: '/dashboard', icon: '📊' },
  { label: 'History', path: '/history', icon: '📋' },
  { label: 'Settings', path: '/settings', icon: '⚙️' },
]

export function AuthenticatedLayout() {
  const auth = useAuth()
  const ws = useWebSocket({
    url: `ws://${import.meta.env.VITE_API_HOST || 'localhost:8000'}/ws`,
  })
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white shadow hidden md:block">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-900">🦎 Chameleon</h1>
          <p className="text-sm text-gray-600 mt-1">Intervention Dashboard</p>
        </div>

        <nav className="mt-8 space-y-2 px-4">
          {navigationItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`block px-4 py-2 rounded-lg transition ${
                location.pathname === item.path
                  ? 'bg-blue-50 text-blue-600 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span className="mr-2">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow">
          <div className="px-6 py-4 flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {navigationItems.find((item) => item.path === location.pathname)?.label || 'Dashboard'}
              </h2>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection status */}
              <div className="flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    ws.isConnected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                ></div>
                <span className="text-xs text-gray-600">
                  {ws.isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* Pilot profile */}
              <PilotProfile auth={auth.auth} onLogout={auth.logout} />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 px-6 py-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
