/**
 * ActionButtons Component Tests
 * Simplified tests focusing on rendering logic
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { ActionButtons } from '../ActionButtons';

describe('ActionButtons', () => {
  const mockOnApprove = vi.fn();
  const mockOnReject = vi.fn();
  const mockOnReview = vi.fn();

  it('renders approve and reject buttons for PENDING status', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('renders approve button for IN_REVIEW status', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="IN_REVIEW"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
  });

  it('does not render buttons for APPROVED status', () => {
    const { container } = render(
      <ActionButtons
        requestId="req-001"
        status="APPROVED"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(container.innerHTML).toBe('');
  });

  it('does not render buttons for REJECTED status', () => {
    const { container } = render(
      <ActionButtons
        requestId="req-001"
        status="REJECTED"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(container.innerHTML).toBe('');
  });

  it('renders review button when onReview is provided', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        onReview={mockOnReview}
      />
    );

    expect(screen.getByRole('button', { name: /review/i })).toBeInTheDocument();
  });

  it('does not render review button when onReview is not provided', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.queryByRole('button', { name: /review/i })).not.toBeInTheDocument();
  });

  it('disables buttons when disabled prop is true', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        disabled={true}
      />
    );

    const approveBtn = screen.getByRole('button', { name: /approve/i });
    const rejectBtn = screen.getByRole('button', { name: /reject/i });

    expect(approveBtn).toBeDisabled();
    expect(rejectBtn).toBeDisabled();
  });

  it('buttons are enabled when disabled prop is false', () => {
    render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        disabled={false}
      />
    );

    const approveBtn = screen.getByRole('button', { name: /approve/i });
    const rejectBtn = screen.getByRole('button', { name: /reject/i });

    expect(approveBtn).not.toBeDisabled();
    expect(rejectBtn).not.toBeDisabled();
  });

  it('renders correct number of buttons based on status and handlers', () => {
    const { rerender } = render(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    let buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(2); // Approve and Reject

    rerender(
      <ActionButtons
        requestId="req-001"
        status="PENDING"
        onApprove={mockOnApprove}
        onReject={mockOnReject}
        onReview={mockOnReview}
      />
    );

    buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(3); // Approve, Review, and Reject
  });
});
