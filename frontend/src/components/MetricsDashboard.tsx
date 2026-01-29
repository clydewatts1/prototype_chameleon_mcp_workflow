/**
 * MetricsDashboard: Display real-time metrics
 *
 * Shows:
 * - Total interventions
 * - By status (pending, approved, rejected)
 * - By priority
 * - By type
 * - Top pilots
 * - Average resolution time
 */

import React from 'react'
import { DashboardMetrics } from '../types'

interface MetricsDashboardProps {
  metrics: DashboardMetrics | null
  isLoading?: boolean
}

export const MetricsDashboard: React.FC<MetricsDashboardProps> = ({
  metrics,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg p-6 shadow">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-12 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="bg-white rounded-lg p-6 shadow">
        <p className="text-gray-500 text-center">No metrics available</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg p-6 shadow space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard Metrics</h2>
        <p className="text-sm text-gray-600">Real-time intervention statistics</p>
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total"
          value={metrics.total_interventions}
          color="bg-blue-50 text-blue-700"
        />
        <MetricCard
          label="Pending"
          value={metrics.pending_interventions}
          color="bg-yellow-50 text-yellow-700"
        />
        <MetricCard
          label="Approved"
          value={metrics.approved_interventions}
          color="bg-green-50 text-green-700"
        />
        <MetricCard
          label="Rejected"
          value={metrics.rejected_interventions}
          color="bg-red-50 text-red-700"
        />
      </div>

      {/* Resolution time */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-4">
        <p className="text-sm text-gray-700 font-medium">Avg Resolution Time</p>
        <p className="text-3xl font-bold text-purple-600">
          {metrics.avg_resolution_time_seconds.toFixed(1)}s
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* By Priority */}
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">By Priority</h3>
          <div className="space-y-2">
            {Object.entries(metrics.by_priority)
              .sort(([, a], [, b]) => b - a)
              .map(([priority, count]) => (
                <div key={priority} className="flex justify-between items-center">
                  <span className="text-sm text-gray-700 capitalize">{priority}</span>
                  <span className="text-sm font-semibold text-gray-900">{count}</span>
                </div>
              ))}
          </div>
        </div>

        {/* By Type */}
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">By Type</h3>
          <div className="space-y-2">
            {Object.entries(metrics.by_type)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => (
                <div key={type} className="flex justify-between items-center">
                  <span className="text-sm text-gray-700 capitalize">{type}</span>
                  <span className="text-sm font-semibold text-gray-900">{count}</span>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Top Pilots */}
      {metrics.top_pilots.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">Top Pilots</h3>
          <div className="space-y-2">
            {metrics.top_pilots.slice(0, 5).map((pilot, index) => (
              <div key={pilot.pilot_id} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">
                  <span className="font-semibold mr-2">#{index + 1}</span>
                  {pilot.pilot_id}
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {pilot.interventions}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: number
  color: string
}

function MetricCard({ label, value, color }: MetricCardProps) {
  return (
    <div className={`${color} rounded-lg p-4`}>
      <p className="text-xs font-medium opacity-75">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}
