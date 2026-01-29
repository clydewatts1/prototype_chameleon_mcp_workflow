/**
 * useIntervention: State management for intervention requests
 *
 * Manages:
 * - Pending interventions list
 * - Current selected intervention
 * - Metrics data
 * - Actions (approve, reject, etc.)
 */

import { useCallback, useState } from 'react'
import { InterventionRequest, DashboardMetrics, InterventionStatus } from '../types'

interface UseInterventionState {
  pendingRequests: InterventionRequest[]
  currentRequest: InterventionRequest | null
  metrics: DashboardMetrics | null
  isLoading: boolean
  error: string | null
}

export function useIntervention() {
  const [state, setState] = useState<UseInterventionState>({
    pendingRequests: [],
    currentRequest: null,
    metrics: null,
    isLoading: false,
    error: null,
  })

  // Update pending requests
  const setPendingRequests = useCallback((requests: InterventionRequest[]) => {
    setState((prev) => ({
      ...prev,
      pendingRequests: requests,
      error: null,
    }))
  }, [])

  // Select current request
  const selectRequest = useCallback((request: InterventionRequest) => {
    setState((prev) => ({
      ...prev,
      currentRequest: request,
    }))
  }, [])

  // Update metrics
  const setMetrics = useCallback((metrics: DashboardMetrics) => {
    setState((prev) => ({
      ...prev,
      metrics,
    }))
  }, [])

  // Update request status
  const updateRequestStatus = useCallback(
    (requestId: string, newStatus: InterventionStatus, reason?: string) => {
      setState((prev) => {
        const updated = {
          ...prev,
          pendingRequests: prev.pendingRequests.filter(
            (r) => r.request_id !== requestId
          ),
        }

        // Update current request if it matches
        if (prev.currentRequest?.request_id === requestId) {
          updated.currentRequest = {
            ...prev.currentRequest,
            status: newStatus,
            action_reason: reason,
            action_timestamp: new Date().toISOString(),
          }
        }

        return updated
      })
    },
    []
  )

  // Add new intervention request (real-time update from server)
  const addRequest = useCallback((request: InterventionRequest) => {
    setState((prev) => {
      // Don't add duplicates
      const exists = prev.pendingRequests.some(
        (r) => r.request_id === request.request_id
      )
      if (exists) return prev

      return {
        ...prev,
        pendingRequests: [request, ...prev.pendingRequests],
      }
    })
  }, [])

  // Clear current request
  const clearCurrentRequest = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentRequest: null,
    }))
  }, [])

  // Set loading state
  const setLoading = useCallback((loading: boolean) => {
    setState((prev) => ({
      ...prev,
      isLoading: loading,
    }))
  }, [])

  // Set error
  const setError = useCallback((error: string | null) => {
    setState((prev) => ({
      ...prev,
      error,
    }))
  }, [])

  // Get request by ID
  const getRequest = useCallback(
    (requestId: string): InterventionRequest | undefined => {
      return state.pendingRequests.find((r) => r.request_id === requestId)
    },
    [state.pendingRequests]
  )

  // Get sorted pending requests by priority
  const getSortedPending = useCallback((): InterventionRequest[] => {
    const priorityOrder: Record<string, number> = {
      critical: 0,
      high: 1,
      normal: 2,
      low: 3,
    }

    return [...state.pendingRequests].sort((a, b) => {
      const aPriority = priorityOrder[a.priority] ?? 999
      const bPriority = priorityOrder[b.priority] ?? 999
      if (aPriority !== bPriority) return aPriority - bPriority

      // Sort by created_at descending (newest first)
      return (
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    })
  }, [state.pendingRequests])

  return {
    // State
    ...state,

    // Actions
    setPendingRequests,
    selectRequest,
    setMetrics,
    updateRequestStatus,
    addRequest,
    clearCurrentRequest,
    setLoading,
    setError,

    // Selectors
    getRequest,
    getSortedPending,
  }
}
