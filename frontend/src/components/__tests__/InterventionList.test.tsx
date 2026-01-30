/**
 * InterventionList Component Tests
 * Simplified tests without async operations
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { InterventionList } from '../InterventionList';
import { mockInterventionRequests } from '@/test/mocks/data';

describe('InterventionList', () => {
  it('renders empty state when no requests provided', () => {
    render(<InterventionList requests={[]} />);
    expect(screen.getByText(/no pending requests/i)).toBeInTheDocument();
  });

  it('shows loading spinner when isLoading is true', () => {
    render(<InterventionList requests={[]} isLoading={true} />);
    expect(screen.getByText(/loading requests/i)).toBeInTheDocument();
  });

  it('renders intervention cards for each request', () => {
    render(<InterventionList requests={mockInterventionRequests} />);

    mockInterventionRequests.forEach((request) => {
      expect(screen.getByText(request.title)).toBeInTheDocument();
    });
  });

  it('renders request priority badges', () => {
    render(<InterventionList requests={mockInterventionRequests} />);

    mockInterventionRequests.forEach((request) => {
      expect(screen.getByText(request.priority)).toBeInTheDocument();
    });
  });

  it('renders request status badges', () => {
    render(<InterventionList requests={mockInterventionRequests} />);

    mockInterventionRequests.forEach((request) => {
      expect(screen.getByText(request.status)).toBeInTheDocument();
    });
  });

  it('renders action buttons for cards', () => {
    render(<InterventionList requests={mockInterventionRequests} />);

    const approveButtons = screen.getAllByRole('button', { name: /approve/i });
    expect(approveButtons.length).toBeGreaterThan(0);
  });

  it('calls onAction when provided', () => {
    const mockOnAction = vi.fn();
    render(
      <InterventionList
        requests={mockInterventionRequests}
        onAction={mockOnAction}
      />
    );

    expect(screen.getAllByRole('button').length).toBeGreaterThan(0);
  });

  it('handles single request correctly', () => {
    const singleRequest = [mockInterventionRequests[0]];
    render(<InterventionList requests={singleRequest} />);

    expect(screen.getByText(singleRequest[0].title)).toBeInTheDocument();
    expect(screen.getByText(singleRequest[0].description)).toBeInTheDocument();
  });

  it('renders loading state over empty state', () => {
    const { rerender } = render(<InterventionList requests={[]} />);
    expect(screen.getByText(/no pending requests/i)).toBeInTheDocument();

    rerender(<InterventionList requests={[]} isLoading={true} />);
    expect(screen.getByText(/loading requests/i)).toBeInTheDocument();
    expect(screen.queryByText(/no pending requests/i)).not.toBeInTheDocument();
  });
});
