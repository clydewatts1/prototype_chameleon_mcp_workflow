/**
 * Dashboard: Main intervention management page
 * 
 * Handles:
 * - Display pending interventions
 * - Show metrics sidebar
 * - WebSocket real-time updates
 * - Intervention selection and navigation
 */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, useWebSocket, useIntervention } from '../hooks'
import { InterventionCard, MetricsDashboard } from '../components'
import { InterventionStatus, WebSocketResponse } from '../types'

export function Dashboard() {
  const auth = useAuth()
  const intervention = useIntervention()
  const navigate = useNavigate()

  // WebSocket connection (will auto-connect)
  const ws = useWebSocket({
    url: `ws://${import.meta.env.VITE_API_HOST || 'localhost:8000'}/ws`,
    onMessage: handleWebSocketMessage,
    onConnected: () => {
      console.log('[Dashboard] WebSocket connected')
      if (auth.auth) {
        // Subscribe to updates
        ws.send({
          type: 'subscribe',
          payload: { pilot_id: auth.auth.pilot_id },
        })
        // Get pending requests
        ws.send({
          type: 'get_pending',
          payload: { pilot_id: auth.auth.pilot_id, limit: 20 },
        })
        // Get metrics
        ws.send({
          type: 'get_metrics',
          payload: {},
        })
      }
    },
    onDisconnected: () => {
      console.log('[Dashboard] WebSocket disconnected')
      intervention.setError('Connection lost. Reconnecting...')
    },
    onError: (error) => {
      console.error('[Dashboard] WebSocket error:', error)
      intervention.setError('WebSocket error occurred')
    },
  })

  // Handle WebSocket messages
  function handleWebSocketMessage(response: WebSocketResponse) {
    if (!response.success) {
      intervention.setError(response.error?.message || 'Unknown error')
      return
    }

    // Route based on message type
    if (response.data?.requests) {
      // Pending requests update
      intervention.setPendingRequests(response.data.requests)
    } else if (response.data?.total_interventions !== undefined) {
      // Metrics update
      intervention.setMetrics(response.data)
    } else if (response.data?.request_id) {
      // Single request detail
      intervention.selectRequest(response.data)
    }
  }

  // Periodically fetch updates
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws.isConnected && auth.auth) {
        ws.send({
          type: 'get_pending',
          payload: { pilot_id: auth.auth.pilot_id, limit: 20 },
        })
        ws.send({
          type: 'get_metrics',
          payload: {},
        })
      }
    }, 5000) // Update every 5 seconds

    return () => clearInterval(interval)
  }, [ws.isConnected, auth.auth])

  const handleSelectRequest = (requestId: string) => {
    // Navigate to detail page instead of modal
    navigate(`/interventions/${requestId}`)
  }

  return (
    <main className="space-y-6">
      {/* Error message */}
      {intervention.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {intervention.error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Pending interventions list */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Pending Interventions ({intervention.pendingRequests.length})
            </h2>

            {intervention.isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-24 bg-gray-100 rounded animate-pulse"
                  ></div>
                ))}
              </div>
            ) : intervention.pendingRequests.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No pending interventions</p>
              </div>
            ) : (
              <div className="space-y-3">
                {intervention.getSortedPending().map((request) => (
                  <InterventionCard
                    key={request.request_id}
                    request={request}
                    onSelect={() => handleSelectRequest(request.request_id)}
                    isSelected={false}
                    pilotRole={auth.auth?.role}
                    onApprove={(requestId, reason) => {
                      intervention.updateRequestStatus(
                        requestId,
                        InterventionStatus.APPROVED,
                        reason
                      )
                    }}
                    onReject={(requestId, reason) => {
                      intervention.updateRequestStatus(
                        requestId,
                        InterventionStatus.REJECTED,
                        reason
                      )
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar with metrics */}
        <div className="lg:col-span-1">
          <MetricsDashboard
            metrics={intervention.metrics}
            isLoading={intervention.isLoading}
          />
        </div>
      </div>
    </main>
  )
}
