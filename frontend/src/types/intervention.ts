/**
 * Phase 3 Priority 1: TypeScript Types
 * Mirrors Phase 2 backend models for intervention requests
 */

export type InterventionType = 
  | 'AUTHORIZATION'
  | 'ESCALATION'
  | 'EXCEPTION_REVIEW'
  | 'POLICY_OVERRIDE'
  | 'CUSTOM';

export type InterventionStatus =
  | 'PENDING'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED';

export type PriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type PilotRole = 'OPERATOR' | 'SENIOR_OPERATOR' | 'ADMIN';

export interface InterventionRequest {
  request_id: string;
  uow_id: string;
  intervention_type: InterventionType;
  status: InterventionStatus;
  priority: PriorityLevel;
  title: string;
  description: string;
  context: Record<string, any>;
  
  created_at: string; // ISO 8601
  updated_at: string;
  assigned_to: string | null;
  action_reason: string | null;
  expires_at: string | null;
  
  // Metadata
  workflow_name?: string;
  role_name?: string;
  actor_name?: string;
}

export interface Pilot {
  pilot_id: string;
  name: string;
  email: string;
  role: PilotRole;
  last_login: string;
  oauth_provider?: string;
  oauth_id?: string;
}

export interface InterventionMetrics {
  total: number;
  pending: number;
  in_review: number;
  approved: number;
  rejected: number;
  expired: number;
  
  // Performance metrics
  avg_response_time_seconds?: number;
  approval_rate?: number;
}

export interface InterventionAction {
  request_id: string;
  action: 'APPROVE' | 'REJECT' | 'REVIEW';
  reason?: string;
  pilot_id: string;
}

// WebSocket message types
export type WSMessageType =
  | 'subscribe'
  | 'unsubscribe'
  | 'get_pending'
  | 'get_metrics'
  | 'request_detail'
  | 'new_request'
  | 'status_changed'
  | 'metrics_update'
  | 'error';

export interface WSMessage {
  type: WSMessageType;
  data?: any;
  error?: string;
  timestamp?: string;
}

export interface WSSubscribeMessage extends WSMessage {
  type: 'subscribe';
  pilot_id: string;
}

export interface WSNewRequestMessage extends WSMessage {
  type: 'new_request';
  data: InterventionRequest;
}

export interface WSStatusChangedMessage extends WSMessage {
  type: 'status_changed';
  data: {
    request_id: string;
    old_status: InterventionStatus;
    new_status: InterventionStatus;
    updated_by: string;
  };
}

export interface WSMetricsUpdateMessage extends WSMessage {
  type: 'metrics_update';
  data: InterventionMetrics;
}
