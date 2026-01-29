/**
 * PilotProfile: Display current pilot information
 */

import React from 'react'
import { PilotAuth, PilotRole } from '../types'

interface PilotProfileProps {
  auth: PilotAuth | null
  onLogout?: () => void
}

const ROLE_COLORS: Record<PilotRole, string> = {
  [PilotRole.ADMIN]: 'bg-red-100 text-red-800',
  [PilotRole.OPERATOR]: 'bg-blue-100 text-blue-800',
  [PilotRole.VIEWER]: 'bg-gray-100 text-gray-800',
}

export const PilotProfile: React.FC<PilotProfileProps> = ({ auth, onLogout }) => {
  if (!auth) {
    return <div>Not authenticated</div>
  }

  return (
    <div className="flex items-center gap-4">
      <div className="text-right">
        <p className="text-sm font-semibold text-gray-900">{auth.pilot_id}</p>
        <span className={`text-xs font-medium px-2 py-1 rounded ${ROLE_COLORS[auth.role]}`}>
          {auth.role}
        </span>
      </div>

      {onLogout && (
        <button
          onClick={onLogout}
          className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded transition"
        >
          Logout
        </button>
      )}
    </div>
  )
}
