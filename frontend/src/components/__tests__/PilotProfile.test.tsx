/**
 * PilotProfile Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@/test/test-utils'
import { PilotProfile } from '../PilotProfile'
import { PilotAuth, PilotRole } from '../../types'

const mockAuthAdmin: PilotAuth = {
  pilot_id: 'admin-001',
  role: PilotRole.ADMIN,
  token: 'jwt-token-123',
  token_expires_at: '2026-02-01T00:00:00Z',
}

const mockAuthOperator: PilotAuth = {
  pilot_id: 'operator-001',
  role: PilotRole.OPERATOR,
  token: 'jwt-token-456',
  token_expires_at: '2026-02-01T00:00:00Z',
}

const mockAuthViewer: PilotAuth = {
  pilot_id: 'viewer-001',
  role: PilotRole.VIEWER,
  token: 'jwt-token-789',
  token_expires_at: '2026-02-01T00:00:00Z',
}

describe('PilotProfile', () => {
  it('renders not authenticated message when auth is null', () => {
    render(<PilotProfile auth={null} />)
    expect(screen.getByText('Not authenticated')).toBeInTheDocument()
  })

  it('displays pilot ID', () => {
    render(<PilotProfile auth={mockAuthAdmin} />)
    expect(screen.getByText('admin-001')).toBeInTheDocument()
  })

  it('displays ADMIN role with correct styling', () => {
    render(<PilotProfile auth={mockAuthAdmin} />)
    const roleTag = screen.getByText('ADMIN')
    expect(roleTag).toBeInTheDocument()
    expect(roleTag).toHaveClass('bg-red-100')
    expect(roleTag).toHaveClass('text-red-800')
  })

  it('displays OPERATOR role with correct styling', () => {
    render(<PilotProfile auth={mockAuthOperator} />)
    const roleTag = screen.getByText('OPERATOR')
    expect(roleTag).toBeInTheDocument()
    expect(roleTag).toHaveClass('bg-blue-100')
    expect(roleTag).toHaveClass('text-blue-800')
  })

  it('displays VIEWER role with correct styling', () => {
    render(<PilotProfile auth={mockAuthViewer} />)
    const roleTag = screen.getByText('VIEWER')
    expect(roleTag).toBeInTheDocument()
    expect(roleTag).toHaveClass('bg-gray-100')
    expect(roleTag).toHaveClass('text-gray-800')
  })

  it('renders logout button when onLogout callback provided', () => {
    render(<PilotProfile auth={mockAuthAdmin} onLogout={() => {}} />)
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('does not render logout button when onLogout not provided', () => {
    render(<PilotProfile auth={mockAuthAdmin} />)
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
  })

  it('calls onLogout when logout button clicked', () => {
    const onLogout = vi.fn()
    render(<PilotProfile auth={mockAuthAdmin} onLogout={onLogout} />)
    fireEvent.click(screen.getByRole('button', { name: /logout/i }))
    expect(onLogout).toHaveBeenCalled()
  })

  it('displays all role colors correctly', () => {
    const roles = [
      { auth: mockAuthAdmin, expectedColor: 'bg-red-100' },
      { auth: mockAuthOperator, expectedColor: 'bg-blue-100' },
      { auth: mockAuthViewer, expectedColor: 'bg-gray-100' },
    ]

    roles.forEach(({ auth, expectedColor }) => {
      const { unmount } = render(<PilotProfile auth={auth} />)
      const roleTag = screen.getByText(auth.role)
      expect(roleTag).toHaveClass(expectedColor)
      unmount()
    })
  })

  it('renders profile information in correct layout', () => {
    const { container } = render(<PilotProfile auth={mockAuthAdmin} />)
    const profileContainer = container.querySelector('div[class*="flex items-center gap-4"]')
    expect(profileContainer).toBeTruthy()
    
    // Verify pilot info is on the right
    const infoDiv = container.querySelector('div[class*="text-right"]')
    expect(infoDiv).toBeTruthy()
  })

  it('handles rapid logout clicks', () => {
    const onLogout = vi.fn()
    render(<PilotProfile auth={mockAuthAdmin} onLogout={onLogout} />)
    const logoutBtn = screen.getByRole('button', { name: /logout/i })
    
    fireEvent.click(logoutBtn)
    fireEvent.click(logoutBtn)
    fireEvent.click(logoutBtn)
    
    expect(onLogout).toHaveBeenCalledTimes(3)
  })

  it('displays pilot ID and role together', () => {
    render(<PilotProfile auth={mockAuthOperator} />)
    expect(screen.getByText('operator-001')).toBeInTheDocument()
    expect(screen.getByText('OPERATOR')).toBeInTheDocument()
  })

  it('renders with different role types', () => {
    const allRoles: PilotRole[] = ['ADMIN', 'OPERATOR', 'VIEWER']
    
    allRoles.forEach((role) => {
      const auth: PilotAuth = {
        pilot_id: `test-${role}`,
        role,
        token: 'token',
        token_expires_at: '2026-02-01T00:00:00Z',
      }
      
      const { unmount } = render(<PilotProfile auth={auth} />)
      expect(screen.getByText(role)).toBeInTheDocument()
      unmount()
    })
  })

  it('has logout button with correct styling', () => {
    render(<PilotProfile auth={mockAuthAdmin} onLogout={() => {}} />)
    const logoutBtn = screen.getByRole('button', { name: /logout/i })
    expect(logoutBtn).toHaveClass('text-red-600')
    expect(logoutBtn).toHaveClass('hover:bg-red-50')
  })
})
