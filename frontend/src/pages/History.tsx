/**
 * History: Past interventions and audit log page
 * 
 * Handles:
 * - Display completed/rejected interventions
 * - Filtering and sorting
 * - Detailed view of past decisions
 */

import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useIntervention, useWebSocket } from '../hooks'
import { InterventionStatus } from '../types'

export function History() {
  const intervention = useIntervention()

  // WebSocket for history updates
  const ws = useWebSocket({
    url: `ws://${import.meta.env.VITE_API_HOST || 'localhost:8000'}/ws`,
    onConnected: () => {
      ws.send({
        type: 'get_history',
        payload: { limit: 50 },
      })
    },
  })

  // Fetch history on mount
  useEffect(() => {
    if (ws.isConnected) {
      ws.send({
        type: 'get_history',
        payload: { limit: 50 },
      })
    }
  }, [ws.isConnected])

  const completedRequests = intervention.pendingRequests.filter(
    (r) => r.status === InterventionStatus.APPROVED || r.status === InterventionStatus.REJECTED
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Intervention History</h1>
        <p className="text-gray-600 mt-2">View past decisions and audit trail</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 flex gap-3">
        <button className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg font-medium">
          All
        </button>
        <button className="px-4 py-2 text-gray-600 rounded-lg hover:bg-gray-50">
          Approved
        </button>
        <button className="px-4 py-2 text-gray-600 rounded-lg hover:bg-gray-50">
          Rejected
        </button>
        <button className="px-4 py-2 text-gray-600 rounded-lg hover:bg-gray-50">
          Expired
        </button>
      </div>

      {/* History list */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {completedRequests.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500">No intervention history available</p>
            <Link
              to="/dashboard"
              className="text-blue-500 hover:text-blue-600 mt-2 inline-block"
            >
              Go to Dashboard
            </Link>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Priority
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {completedRequests.map((request) => (
                <tr key={request.request_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/interventions/${request.request_id}`}
                      className="text-blue-500 hover:text-blue-600 font-medium"
                    >
                      {request.title}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                      request.status === InterventionStatus.APPROVED
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {request.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(request.updated_at || request.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`font-medium ${
                      request.priority === 'critical' ? 'text-red-600' :
                      request.priority === 'high' ? 'text-orange-600' :
                      request.priority === 'normal' ? 'text-blue-600' :
                      'text-gray-600'
                    }`}>
                      {request.priority?.toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
