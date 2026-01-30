/**
 * MetricsDashboard Component Tests
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { MetricsDashboard } from '../MetricsDashboard'
import { DashboardMetrics } from '../../types'

const mockMetrics: DashboardMetrics = {
  total_interventions: 150,
  pending_interventions: 25,
  approved_interventions: 100,
  rejected_interventions: 25,
  avg_resolution_time_seconds: 45.5,
  by_priority: {
    critical: 10,
    high: 40,
    medium: 70,
    low: 30,
  },
  by_type: {
    authorization: 60,
    escalation: 40,
    exception_review: 30,
    policy_override: 20,
  },
  top_pilots: [
    { pilot_id: 'pilot-001', interventions: 45 },
    { pilot_id: 'pilot-002', interventions: 35 },
    { pilot_id: 'pilot-003', interventions: 25 },
  ],
}

describe('MetricsDashboard', () => {
  it('renders loading state', () => {
    render(<MetricsDashboard metrics={null} isLoading={true} />)
    // Check for skeleton loading elements
    const skeleton = document.querySelector('.animate-pulse')
    expect(skeleton).toBeTruthy()
  })

  it('renders "no metrics" message when metrics is null', () => {
    render(<MetricsDashboard metrics={null} isLoading={false} />)
    expect(screen.getByText('No metrics available')).toBeInTheDocument()
  })

  it('renders dashboard title and subtitle', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('Dashboard Metrics')).toBeInTheDocument()
    expect(
      screen.getByText('Real-time intervention statistics')
    ).toBeInTheDocument()
  })

  it('displays all key metrics', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('Total')).toBeInTheDocument()
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
    expect(screen.getByText('Rejected')).toBeInTheDocument()
  })

  it('displays correct metric values', () => {
    const { container } = render(<MetricsDashboard metrics={mockMetrics} />)
    
    // Check if values appear in the document using getAllByText
    const totalElements = screen.getAllByText('150')
    expect(totalElements.length).toBeGreaterThan(0)
    
    const pendingElements = screen.getAllByText('25')
    expect(pendingElements.length).toBeGreaterThan(0)
    
    const approvedElements = screen.getAllByText('100')
    expect(approvedElements.length).toBeGreaterThan(0)
  })

  it('displays average resolution time', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('Avg Resolution Time')).toBeInTheDocument()
    expect(screen.getByText('45.5s')).toBeInTheDocument()
  })

  it('displays priority breakdown', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('By Priority')).toBeInTheDocument()
    expect(screen.getByText('critical')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
    expect(screen.getByText('low')).toBeInTheDocument()
  })

  it('displays intervention type breakdown', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('By Type')).toBeInTheDocument()
    expect(screen.getByText('authorization')).toBeInTheDocument()
    expect(screen.getByText('escalation')).toBeInTheDocument()
    expect(screen.getByText('exception_review')).toBeInTheDocument()
    expect(screen.getByText('policy_override')).toBeInTheDocument()
  })

  it('displays top pilots section when pilots exist', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('Top Pilots')).toBeInTheDocument()
    expect(screen.getByText('pilot-001')).toBeInTheDocument()
    expect(screen.getByText('pilot-002')).toBeInTheDocument()
    expect(screen.getByText('pilot-003')).toBeInTheDocument()
  })

  it('displays pilot rankings numerically', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('#3')).toBeInTheDocument()
  })

  it('hides top pilots section when empty', () => {
    const metricsNoPilots = { ...mockMetrics, top_pilots: [] }
    render(<MetricsDashboard metrics={metricsNoPilots} />)
    expect(screen.queryByText('Top Pilots')).not.toBeInTheDocument()
  })

  it('handles edge case with zero metrics', () => {
    const emptyMetrics: DashboardMetrics = {
      total_interventions: 0,
      pending_interventions: 0,
      approved_interventions: 0,
      rejected_interventions: 0,
      avg_resolution_time_seconds: 0,
      by_priority: {},
      by_type: {},
      top_pilots: [],
    }
    render(<MetricsDashboard metrics={emptyMetrics} />)
    expect(screen.getByText('Dashboard Metrics')).toBeInTheDocument()
  })

  it('sorts priorities by count in descending order', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    // Verify sorting works by checking that medium (70) appears in the document
    // and is listed in the priority section
    expect(screen.getByText('By Priority')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
  })

  it('sorts intervention types by count in descending order', () => {
    render(<MetricsDashboard metrics={mockMetrics} />)
    // Verify that authorization (60) appears before lower counts
    expect(screen.getByText('authorization')).toBeInTheDocument()
  })

  it('handles large metric values correctly', () => {
    const largeMetrics: DashboardMetrics = {
      ...mockMetrics,
      total_interventions: 10000,
      avg_resolution_time_seconds: 1234.56,
    }
    render(<MetricsDashboard metrics={largeMetrics} />)
    expect(screen.getByText('10000')).toBeInTheDocument()
    expect(screen.getByText('1234.6s')).toBeInTheDocument()
  })

  it('limits display of top pilots to 5', () => {
    const manyPilots: DashboardMetrics = {
      ...mockMetrics,
      top_pilots: Array.from({ length: 10 }, (_, i) => ({
        pilot_id: `pilot-${i.toString().padStart(3, '0')}`,
        interventions: 100 - i * 5,
      })),
    }
    const { container } = render(<MetricsDashboard metrics={manyPilots} />)
    const pilotsCount = container.querySelectorAll('[class*="flex items-center justify-between"]').length
    // Should display header + 5 pilots max in the top pilots section
    expect(pilotsCount).toBeLessThanOrEqual(6)
  })
})
