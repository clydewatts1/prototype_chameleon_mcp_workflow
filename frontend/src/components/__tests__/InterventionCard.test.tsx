/**
 * InterventionCard Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/test/test-utils'
import { InterventionCard } from '../InterventionCard'
import { InterventionRequest } from '../../types'

const mockRequest: InterventionRequest = {
  request_id: '123',
  uow_id: 'uow-123',
  intervention_type: 'AUTHORIZATION',
  status: 'PENDING',
  priority: 'HIGH',
  title: 'Expense Approval Required',
  description: 'User attempting to approve $5,000 expense',
  actor_id: 'actor-123',
  actor_name: 'John Doe',
  reason: 'Amount exceeds policy limit',
  created_at: new Date().toISOString(),
  action_reason: undefined,
}

describe('InterventionCard', () => {
  it('renders intervention title and description', () => {
    render(<InterventionCard request={mockRequest} />)
    expect(screen.getByText('Expense Approval Required')).toBeInTheDocument()
    expect(
      screen.getByText('User attempting to approve $5,000 expense')
    ).toBeInTheDocument()
  })

  it('displays priority badge with correct text', () => {
    render(<InterventionCard request={mockRequest} />)
    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('displays status text', () => {
    render(<InterventionCard request={mockRequest} />)
    expect(screen.getByText('PENDING')).toBeInTheDocument()
  })

  it('displays UOW ID', () => {
    render(<InterventionCard request={mockRequest} />)
    expect(screen.getByText(/UOW: uow-123/)).toBeInTheDocument()
  })

  it('shows intervention type', () => {
    render(<InterventionCard request={mockRequest} />)
    expect(screen.getByText('AUTHORIZATION')).toBeInTheDocument()
  })

  it('displays action buttons when pending and user is operator', () => {
    render(
      <InterventionCard
        request={mockRequest}
        pilotRole={'OPERATOR'}
      />
    )
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /details/i })).toBeInTheDocument()
  })

  it('hides action buttons when status is not pending', () => {
    const approvedRequest = { ...mockRequest, status: 'APPROVED' as const }
    render(<InterventionCard request={approvedRequest} />)
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
  })

  it('calls onSelect when card is clicked', () => {
    const onSelect = vi.fn()
    render(<InterventionCard request={mockRequest} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('Expense Approval Required'))
    expect(onSelect).toHaveBeenCalledWith(mockRequest)
  })

  it('calls onApprove with correct ID when approve button clicked', () => {
    const onApprove = vi.fn()
    render(
      <InterventionCard
        request={mockRequest}
        onApprove={onApprove}
        pilotRole={'OPERATOR'}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /approve/i }))
    expect(onApprove).toHaveBeenCalledWith(
      '123',
      'Quick approved from dashboard'
    )
  })

  it('calls onReject with correct ID when reject button clicked', () => {
    const onReject = vi.fn()
    render(
      <InterventionCard
        request={mockRequest}
        onReject={onReject}
        pilotRole={'OPERATOR'}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /reject/i }))
    expect(onReject).toHaveBeenCalledWith('123', 'Quick rejected from dashboard')
  })

  it('applies selected styling when isSelected is true', () => {
    const { container } = render(
      <InterventionCard request={mockRequest} isSelected={true} />
    )
    const card = container.querySelector('div[class*="border-blue-500"]')
    expect(card).toBeTruthy()
  })

  it('disables action buttons for non-operator users', () => {
    // SENIOR_OPERATOR cannot take action - only ADMIN or OPERATOR can
    render(
      <InterventionCard
        request={mockRequest}
        pilotRole={'SENIOR_OPERATOR'}
      />
    )
    // Action buttons should not be visible for SENIOR_OPERATOR
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
  })

  it('formats time correctly', () => {
    const now = new Date()
    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60000)
    const request = { ...mockRequest, created_at: fiveMinutesAgo.toISOString() }
    
    render(<InterventionCard request={request} />)
    expect(screen.getByText(/5 minutes ago/)).toBeInTheDocument()
  })

  it('shows "Just now" for very recent requests', () => {
    const now = new Date()
    const request = { ...mockRequest, created_at: now.toISOString() }
    
    render(<InterventionCard request={request} />)
    expect(screen.getByText(/Just now/)).toBeInTheDocument()
  })

  it('handles different priority levels', () => {
    const priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const
    
    priorities.forEach((priority) => {
      const { unmount } = render(
        <InterventionCard request={{ ...mockRequest, priority }} />
      )
      expect(screen.getByText(priority)).toBeInTheDocument()
      unmount()
    })
  })
})
