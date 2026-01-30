/**
 * Phase 3 Priority 1.3: ActionButtons Component
 * Action buttons for intervention requests (Approve/Reject/Review)
 */

import React, { useState } from 'react';
import type { InterventionStatus } from '@/types/intervention';

export interface ActionButtonsProps {
  requestId: string;
  status: InterventionStatus;
  onApprove?: (requestId: string, reason?: string) => void;
  onReject?: (requestId: string, reason?: string) => void;
  onReview?: (requestId: string) => void;
  disabled?: boolean;
}

export function ActionButtons({
  requestId,
  status,
  onApprove,
  onReject,
  onReview,
  disabled = false,
}: ActionButtonsProps) {
  const [showReasonInput, setShowReasonInput] = useState(false);
  const [reason, setReason] = useState('');
  const [actionType, setActionType] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Only show actions for PENDING or IN_REVIEW status
  if (status !== 'PENDING' && status !== 'IN_REVIEW') {
    return null;
  }

  const handleActionClick = (type: 'APPROVE' | 'REJECT' | 'REVIEW') => {
    if (type === 'REVIEW' && onReview) {
      onReview(requestId);
      return;
    }

    setActionType(type);
    setShowReasonInput(true);
  };

  const handleSubmit = async () => {
    if (!actionType) return;

    setIsSubmitting(true);
    try {
      if (actionType === 'APPROVE' && onApprove) {
        await onApprove(requestId, reason || undefined);
      } else if (actionType === 'REJECT' && onReject) {
        await onReject(requestId, reason || undefined);
      }

      // Reset state
      setShowReasonInput(false);
      setReason('');
      setActionType(null);
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowReasonInput(false);
    setReason('');
    setActionType(null);
  };

  if (showReasonInput) {
    return (
      <div className="space-y-3">
        <div>
          <label
            htmlFor={`reason-${requestId}`}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Reason (optional)
          </label>
          <textarea
            id={`reason-${requestId}`}
            rows={2}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white sm:text-sm"
            placeholder={`Why are you ${actionType?.toLowerCase()}ing this request?`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={isSubmitting}
          />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={`flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white ${
              actionType === 'APPROVE'
                ? 'bg-success-600 hover:bg-success-700 focus:ring-success-500'
                : 'bg-danger-600 hover:bg-danger-700 focus:ring-danger-500'
            } focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isSubmitting ? (
              <>
                <div className="spinner mr-2" />
                Processing...
              </>
            ) : (
              `Confirm ${actionType}`
            )}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSubmitting}
            className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => handleActionClick('APPROVE')}
        disabled={disabled}
        className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-success-600 hover:bg-success-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success-500 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Approve request"
      >
        <svg
          className="-ml-1 mr-2 h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
        Approve
      </button>

      {status === 'PENDING' && onReview && (
        <button
          type="button"
          onClick={() => handleActionClick('REVIEW')}
          disabled={disabled}
          className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Review request"
        >
          <svg
            className="-ml-1 mr-2 h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
            <path
              fillRule="evenodd"
              d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
              clipRule="evenodd"
            />
          </svg>
          Review
        </button>
      )}

      <button
        type="button"
        onClick={() => handleActionClick('REJECT')}
        disabled={disabled}
        className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-danger-600 hover:bg-danger-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-danger-500 disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Reject request"
      >
        <svg
          className="-ml-1 mr-2 h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
        Reject
      </button>
    </div>
  );
}
