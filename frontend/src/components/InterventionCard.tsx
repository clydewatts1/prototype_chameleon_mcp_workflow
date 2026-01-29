/**
 * InterventionCard: Display a single intervention request
 *
 * Shows:
 * - Title & description
 * - Priority badge (critical/high/normal/low)
 * - Status indicator
 * - Quick action buttons
 * - Time since created
 */

import React from 'react'
import { InterventionRequest, InterventionStatus, PilotRole } from '../types'

interface InterventionCardProps {
  request: InterventionRequest
  onSelect?: (request: InterventionRequest) => void
  onApprove?: (requestId: string, reason: string) => void
  onReject?: (requestId: string, reason: string) => void
  pilotRole?: PilotRole
  isSelected?: boolean
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  normal: 'bg-blue-100 text-blue-800 border-blue-300',
  low: 'bg-gray-100 text-gray-800 border-gray-300',
}

const STATUS_COLORS: Record<InterventionStatus, string> = {
  [InterventionStatus.PENDING]: 'text-yellow-600',
  [InterventionStatus.APPROVED]: 'text-green-600',
  [InterventionStatus.REJECTED]: 'text-red-600',
  [InterventionStatus.EXPIRED]: 'text-gray-600',
  [InterventionStatus.IN_PROGRESS]: 'text-blue-600',
  [InterventionStatus.COMPLETED]: 'text-green-600',
}

export const InterventionCard: React.FC<InterventionCardProps> = ({
  request,
  onSelect,
  onApprove,
  onReject,
  pilotRole = PilotRole.OPERATOR,
  isSelected = false,
}) => {
  const createdAt = new Date(request.created_at)
  const now = new Date()
  const minutesAgo = Math.floor((now.getTime() - createdAt.getTime()) / 60000)

  const timeDisplay =
    minutesAgo === 0
      ? 'Just now'
      : minutesAgo === 1
        ? '1 minute ago'
        : `${minutesAgo} minutes ago`

  const handleQuickApprove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onApprove?.(request.request_id, 'Quick approved from dashboard')
  }

  const handleQuickReject = (e: React.MouseEvent) => {
    e.stopPropagation()
    onReject?.(request.request_id, 'Quick rejected from dashboard')
  }

  const canTakeAction =
    request.status === InterventionStatus.PENDING &&
    (pilotRole === PilotRole.ADMIN || pilotRole === PilotRole.OPERATOR)

  return (
    <div
      onClick={() => onSelect?.(request)}
      className={`
        p-4 border rounded-lg cursor-pointer transition-all
        ${isSelected ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-gray-200 bg-white hover:shadow-md'}
      `}
    >
      {/* Header with title and priority badge */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900">{request.title}</h3>
          <p className="text-sm text-gray-600 mt-1">{request.description}</p>
        </div>

        <div className="ml-4 flex gap-2">
          {/* Priority Badge */}
          <span
            className={`
              px-2 py-1 text-xs font-medium rounded-full border whitespace-nowrap
              ${PRIORITY_COLORS[request.priority] || PRIORITY_COLORS.normal}
            `}
          >
            {request.priority.toUpperCase()}
          </span>

          {/* Status Indicator */}
          <span className={`text-xs font-semibold ${STATUS_COLORS[request.status]}`}>
            {request.status}
          </span>
        </div>
      </div>

      {/* UOW ID and Time */}
      <div className="text-xs text-gray-500 mb-3">
        <div>UOW: {request.uow_id}</div>
        <div>Created: {timeDisplay}</div>
      </div>

      {/* Type indicator */}
      <div className="mb-3 text-xs">
        <span className="inline-block bg-gray-100 px-2 py-1 rounded">
          {request.intervention_type}
        </span>
      </div>

      {/* Quick action buttons (if PENDING and user has permission) */}
      {canTakeAction && (
        <div className="flex gap-2 pt-3 border-t border-gray-200 mt-3">
          <button
            onClick={handleQuickApprove}
            className="flex-1 px-3 py-2 bg-green-500 text-white text-xs font-medium rounded hover:bg-green-600 transition"
          >
            Approve
          </button>
          <button
            onClick={handleQuickReject}
            className="flex-1 px-3 py-2 bg-red-500 text-white text-xs font-medium rounded hover:bg-red-600 transition"
          >
            Reject
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onSelect?.(request)
            }}
            className="flex-1 px-3 py-2 bg-blue-500 text-white text-xs font-medium rounded hover:bg-blue-600 transition"
          >
            Details
          </button>
        </div>
      )}

      {/* Show as read-only if not pending or user doesn't have permission */}
      {!canTakeAction && request.status !== InterventionStatus.PENDING && (
        <div className="pt-3 border-t border-gray-200 mt-3">
          <p className="text-xs text-gray-600">
            {request.action_reason && <strong>Reason:</strong>}
            {' '}
            {request.action_reason || 'No reason provided'}
          </p>
        </div>
      )}
    </div>
  )
}
