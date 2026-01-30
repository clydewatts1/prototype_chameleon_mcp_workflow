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
  'PENDING': 'bg-yellow-100 text-yellow-800',
  'IN_REVIEW': 'bg-blue-100 text-blue-800',
  'APPROVED': 'bg-green-100 text-green-800',
  'REJECTED': 'bg-red-100 text-red-800',
  'EXPIRED': 'bg-gray-100 text-gray-800',
  'CANCELLED': 'bg-gray-100 text-gray-800',
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
