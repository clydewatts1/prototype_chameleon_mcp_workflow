/**
 * Phase 3 Priority 1.3: InterventionList Component
 * Displays paginated list of intervention requests
 */

import React from 'react';
import { InterventionCard } from './InterventionCard';
import type { InterventionRequest } from '@/types/intervention';

export interface InterventionListProps {
  requests: InterventionRequest[];
  isLoading?: boolean;
  onRequestClick?: (request: InterventionRequest) => void;
  onAction?: (requestId: string, action: 'APPROVE' | 'REJECT' | 'REVIEW') => void;
}

export function InterventionList({
  requests,
  isLoading = false,
  onRequestClick,
  onAction,
}: InterventionListProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">
          Loading requests...
        </span>
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
          No pending requests
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          All intervention requests have been processed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {requests.map((request) => (
        <InterventionCard
          key={request.request_id}
          request={request}
          onClick={onRequestClick}
          onAction={onAction}
        />
      ))}
    </div>
  );
}
