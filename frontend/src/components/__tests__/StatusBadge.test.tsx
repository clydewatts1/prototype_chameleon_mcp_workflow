/**
 * StatusBadge Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { StatusBadge } from '../StatusBadge';

describe('StatusBadge', () => {
  it('renders PENDING status text', () => {
    render(<StatusBadge status="PENDING" />);
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('renders IN_REVIEW status text', () => {
    render(<StatusBadge status="IN_REVIEW" />);
    expect(screen.getByText('IN_REVIEW')).toBeInTheDocument();
  });

  it('renders APPROVED status text', () => {
    render(<StatusBadge status="APPROVED" />);
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
  });

  it('renders REJECTED status text', () => {
    render(<StatusBadge status="REJECTED" />);
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
  });

  it('renders EXPIRED status text', () => {
    render(<StatusBadge status="EXPIRED" />);
    expect(screen.getByText('EXPIRED')).toBeInTheDocument();
  });

  it('renders CANCELLED status text', () => {
    render(<StatusBadge status="CANCELLED" />);
    expect(screen.getByText('CANCELLED')).toBeInTheDocument();
  });

  it('applies correct CSS class for each status', () => {
    const testCases = [
      { status: 'PENDING', expectedColor: 'yellow' },
      { status: 'IN_REVIEW', expectedColor: 'blue' },
      { status: 'APPROVED', expectedColor: 'green' },
      { status: 'REJECTED', expectedColor: 'red' },
      { status: 'EXPIRED', expectedColor: 'gray' },
      { status: 'CANCELLED', expectedColor: 'gray' },
    ];
    
    testCases.forEach(({ status, expectedColor }) => {
      const { container } = render(<StatusBadge status={status as any} />);
      const badge = container.querySelector('span');
      expect(badge).toBeTruthy();
      const classes = badge?.getAttribute('class') || '';
      expect(classes).toContain(expectedColor);
    });
  });
});
