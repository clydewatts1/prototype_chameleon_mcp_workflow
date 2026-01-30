/**
 * Mock API responses for testing
 */

import type { InterventionRequest, InterventionMetrics } from '@/types/intervention';

export const mockInterventionRequest: InterventionRequest = {
  request_id: 'req-001',
  uow_id: 'uow-001',
  intervention_type: 'AUTHORIZATION',
  status: 'PENDING',
  priority: 'HIGH',
  title: 'UOW Authorization Required',
  description: 'Unit of Work 001 requires manual authorization before proceeding',
  context: {
    workflow_name: 'Invoice_Approval',
    role_name: 'Approver',
    amount: 50000,
  },
  created_at: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
  updated_at: new Date().toISOString(),
  assigned_to: null,
  action_reason: null,
  expires_at: new Date(Date.now() + 3600000).toISOString(), // 1 hour from now
};

export const mockInterventionRequest2: InterventionRequest = {
  request_id: 'req-002',
  uow_id: 'uow-002',
  intervention_type: 'ESCALATION',
  status: 'IN_REVIEW',
  priority: 'CRITICAL',
  title: 'Critical Error Escalation',
  description: 'System encountered critical error requiring immediate attention',
  context: {
    workflow_name: 'Error_Handler',
    role_name: 'ErrorHandler',
    error_code: 'ERR_DB_TIMEOUT',
  },
  created_at: new Date(Date.now() - 600000).toISOString(), // 10 minutes ago
  updated_at: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
  assigned_to: 'pilot-001',
  action_reason: null,
  expires_at: null,
};

export const mockInterventionRequests: InterventionRequest[] = [
  mockInterventionRequest,
  mockInterventionRequest2,
];

export const mockMetrics: InterventionMetrics = {
  total: 25,
  pending: 3,
  in_review: 2,
  approved: 15,
  rejected: 5,
  expired: 0,
  avg_response_time_seconds: 120,
  approval_rate: 0.75,
};

export const mockApprovedRequest: InterventionRequest = {
  ...mockInterventionRequest,
  status: 'APPROVED',
  updated_at: new Date().toISOString(),
  assigned_to: 'pilot-001',
  action_reason: 'Amount within approval limit',
};

export const mockRejectedRequest: InterventionRequest = {
  ...mockInterventionRequest,
  status: 'REJECTED',
  updated_at: new Date().toISOString(),
  assigned_to: 'pilot-001',
  action_reason: 'Requires additional documentation',
};

export const mockPilot = {
  pilot_id: 'pilot-001',
  name: 'John Doe',
  email: 'john@example.com',
  role: 'OPERATOR' as const,
  last_login: new Date().toISOString(),
};

export const mockToken = {
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwaWxvdF9pZCI6InBpbG90LTAwMSIsIm5hbWUiOiJKb2huIERvZSIsImV4cCI6OTk5OTk5OTk5OX0.mock',
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  pilot_id: 'pilot-001',
};
