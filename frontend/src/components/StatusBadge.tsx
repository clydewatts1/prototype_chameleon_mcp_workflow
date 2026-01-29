/**
 * StatusBadge: Reusable status indicator badge
 */

import React from 'react'
import { InterventionStatus } from '../types'

interface StatusBadgeProps {
  status: InterventionStatus
  className?: string
}

const STATUS_STYLES: Record<InterventionStatus, string> = {
  [InterventionStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
  [InterventionStatus.APPROVED]: 'bg-green-100 text-green-800',
  [InterventionStatus.REJECTED]: 'bg-red-100 text-red-800',
  [InterventionStatus.EXPIRED]: 'bg-gray-100 text-gray-800',
  [InterventionStatus.IN_PROGRESS]: 'bg-blue-100 text-blue-800',
  [InterventionStatus.COMPLETED]: 'bg-green-100 text-green-800',
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  return (
    <span
      className={`
        inline-block px-2 py-1 text-xs font-semibold rounded-full
        ${STATUS_STYLES[status]}
        ${className}
      `}
    >
      {status}
    </span>
  )
}
