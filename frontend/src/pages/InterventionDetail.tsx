/**
 * InterventionDetail: Single intervention detail page
 * 
 * Handles:
 * - Display full intervention details
 * - Approval/rejection actions
 * - Navigation back to dashboard
 */

import { useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useIntervention } from '../hooks'
import { InterventionStatus } from '../types'

export function InterventionDetail() {
  const { interventionId } = useParams<{ interventionId: string }>()
  const navigate = useNavigate()
  const intervention = useIntervention()
  const [actionReason, setActionReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const request = intervention.currentRequest

  // Handle if request not loaded
  if (!request || request.request_id !== interventionId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Intervention Not Found</h2>
          <p className="text-gray-600 mb-4">The intervention you're looking for doesn't exist or has expired.</p>
          <Link
            to="/dashboard"
            className="inline-block px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const handleApprove = async () => {
    if (!interventionId) return
    setIsSubmitting(true)
    try {
      await intervention.updateRequestStatus(
        interventionId,
        InterventionStatus.APPROVED,
        actionReason
      )
      // Navigate back after success
      navigate('/dashboard', { replace: true })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!interventionId) return
    setIsSubmitting(true)
    try {
      await intervention.updateRequestStatus(
        interventionId,
        InterventionStatus.REJECTED,
        actionReason
      )
      // Navigate back after success
      navigate('/dashboard', { replace: true })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="text-blue-500 hover:text-blue-600 flex items-center gap-1 mb-4"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">{request.title}</h1>
      </div>

      {/* Main card */}
      <div className="bg-white rounded-lg shadow-lg p-8 space-y-6">
        {/* Status badge */}
        <div>
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
            request.status === InterventionStatus.PENDING
              ? 'bg-yellow-100 text-yellow-800'
              : request.status === InterventionStatus.APPROVED
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}>
            {request.status}
          </span>
        </div>

        {/* Description */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Description</h2>
          <p className="text-gray-700">{request.description}</p>
        </div>

        {/* Context */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Context</h2>
          <pre className="bg-gray-50 p-4 rounded-lg text-xs overflow-auto max-h-64">
            {JSON.stringify(request.context, null, 2)}
          </pre>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Created:</span>
            <p className="font-medium text-gray-900">
              {new Date(request.created_at).toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-gray-600">Priority:</span>
            <p className={`font-medium ${
              request.priority === 'critical' ? 'text-red-600' :
              request.priority === 'high' ? 'text-orange-600' :
              request.priority === 'normal' ? 'text-blue-600' :
              'text-gray-600'
            }`}>
              {request.priority?.toUpperCase()}
            </p>
          </div>
        </div>

        {/* Action section (only for pending) */}
        {request.status === InterventionStatus.PENDING && (
          <div className="border-t pt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Action Reason (optional)
              </label>
              <textarea
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder="Explain your decision..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 disabled:bg-gray-400 transition"
              >
                {isSubmitting ? 'Processing...' : 'Approve'}
              </button>
              <button
                onClick={handleReject}
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 bg-red-500 text-white font-medium rounded-lg hover:bg-red-600 disabled:bg-gray-400 transition"
              >
                {isSubmitting ? 'Processing...' : 'Reject'}
              </button>
              <Link
                to="/dashboard"
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-900 font-medium rounded-lg hover:bg-gray-400 transition text-center"
              >
                Cancel
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
