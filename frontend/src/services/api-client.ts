/**
 * Phase 3 Priority 1.2: REST API Client
 * HTTP client for Phase 2 backend endpoints
 */

import { authService } from './auth-service';
import type { InterventionRequest, DashboardMetrics } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchJSON<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...authService.getAuthHeader(),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        response.status,
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        errorData
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

export const apiClient = {
  /**
   * Get all pending intervention requests
   */
  async getPendingRequests(limit = 50, offset = 0): Promise<InterventionRequest[]> {
    return fetchJSON<InterventionRequest[]>(
      `/api/interventions/pending?limit=${limit}&offset=${offset}`
    );
  },

  /**
   * Get intervention request by ID
   */
  async getRequest(requestId: string): Promise<InterventionRequest> {
    return fetchJSON<InterventionRequest>(`/api/interventions/${requestId}`);
  },

  /**
   * Approve intervention request
   */
  async approveIntervention(requestId: string, reason?: string): Promise<InterventionRequest> {
    return fetchJSON<InterventionRequest>(
      `/api/interventions/${requestId}/approve?action_reason=${encodeURIComponent(reason || '')}`,
      { method: 'POST' }
    );
  },

  /**
   * Reject intervention request
   */
  async rejectIntervention(requestId: string, reason?: string): Promise<InterventionRequest> {
    return fetchJSON<InterventionRequest>(
      `/api/interventions/${requestId}/reject?action_reason=${encodeURIComponent(reason || '')}`,
      { method: 'POST' }
    );
  },

  /**
   * Get intervention metrics
   */
  async getMetrics() {
    return fetchJSON<DashboardMetrics>('/api/interventions/metrics');
  },

  /**
   * Health check
   */
  async health(): Promise<{ status: string }> {
    return fetchJSON<{ status: string }>('/health');
  },
};

export { APIError };

