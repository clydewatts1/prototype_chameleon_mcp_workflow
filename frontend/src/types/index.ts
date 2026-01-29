/**
 * Core types for the Chameleon Dashboard
 * These mirror the backend InterventionStore data structures
 */

export enum InterventionType {
  KILL_SWITCH = 'kill_switch',
  CLARIFICATION = 'clarification',
  WAIVE_VIOLATION = 'waive_violation',
  RESUME = 'resume',
  CANCEL = 'cancel',
}

export enum InterventionStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  EXPIRED = 'EXPIRED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
}

export enum PilotRole {
  ADMIN = 'ADMIN',
  OPERATOR = 'OPERATOR',
  VIEWER = 'VIEWER',
}

export interface InterventionRequest {
  request_id: string
  uow_id: string
  intervention_type: InterventionType
  status: InterventionStatus
  priority: 'critical' | 'high' | 'normal' | 'low'

  // Content
  title: string
  description: string
  context: Record<string, any>

  // Timing
  created_at: string
  expires_at?: string
  updated_at?: string

  // Pilot info
  required_role: string
  assigned_to?: string

  // Action info
  action_reason?: string
  action_timestamp?: string
}

export interface DashboardMetrics {
  total_interventions: number
  pending_interventions: number
  approved_interventions: number
  rejected_interventions: number
  avg_resolution_time_seconds: number

  by_type: Record<string, number>
  by_priority: Record<string, number>
  top_pilots: Array<{
    pilot_id: string
    interventions: number
  }>
}

export interface PilotAuth {
  pilot_id: string
  role: PilotRole
  issued_at: string
  expires_at: string
}

export interface WebSocketMessage {
  type:
    | 'subscribe'
    | 'get_pending'
    | 'get_metrics'
    | 'get_history'
    | 'request_detail'
    | 'action'
  payload: Record<string, any>
}

export interface WebSocketResponse {
  success: boolean
  data?: any
  error?: {
    code: string
    message: string
  }
}
