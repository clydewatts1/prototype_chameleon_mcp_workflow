/**
 * Settings: Pilot preferences and configuration page
 * 
 * Handles:
 * - User preferences
 * - Notification settings
 * - Account information
 */

import { useState } from 'react'
import { useAuth } from '../hooks'

export function Settings() {
  const auth = useAuth()
  const [notificationPreferences, setNotificationPreferences] = useState({
    emailOnApproval: true,
    emailOnCritical: true,
    emailDailyDigest: false,
  })
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // TODO: Call backend API to save preferences
      console.log('Saving preferences:', notificationPreferences)
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">Manage your pilot preferences and account</p>
      </div>

      {/* Account Information */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Information</h2>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Pilot ID</label>
          <p className="px-4 py-2 bg-gray-50 rounded-lg text-gray-900 font-mono text-sm">
            {auth.auth?.pilot_id || 'Unknown'}
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <p className="px-4 py-2 bg-gray-50 rounded-lg text-gray-900 font-medium">
            {auth.auth?.role || 'VIEWER'}
          </p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Token Expires</label>
          <p className="px-4 py-2 bg-gray-50 rounded-lg text-gray-900">
            {auth.auth?.expires_at
              ? new Date(auth.auth.expires_at).toLocaleString()
              : 'Unknown'}
          </p>
        </div>
      </div>

      {/* Notification Preferences */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Notification Preferences</h2>
        </div>
        
        <label className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={notificationPreferences.emailOnApproval}
            onChange={(e) =>
              setNotificationPreferences({
                ...notificationPreferences,
                emailOnApproval: e.target.checked,
              })
            }
            className="w-4 h-4 rounded"
          />
          <div>
            <p className="font-medium text-gray-900">Email on Approval</p>
            <p className="text-sm text-gray-600">Notify me when interventions are approved</p>
          </div>
        </label>

        <label className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={notificationPreferences.emailOnCritical}
            onChange={(e) =>
              setNotificationPreferences({
                ...notificationPreferences,
                emailOnCritical: e.target.checked,
              })
            }
            className="w-4 h-4 rounded"
          />
          <div>
            <p className="font-medium text-gray-900">Critical Alerts</p>
            <p className="text-sm text-gray-600">Always notify me of critical interventions</p>
          </div>
        </label>

        <label className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg cursor-pointer">
          <input
            type="checkbox"
            checked={notificationPreferences.emailDailyDigest}
            onChange={(e) =>
              setNotificationPreferences({
                ...notificationPreferences,
                emailDailyDigest: e.target.checked,
              })
            }
            className="w-4 h-4 rounded"
          />
          <div>
            <p className="font-medium text-gray-900">Daily Digest</p>
            <p className="text-sm text-gray-600">Send me a daily summary of all interventions</p>
          </div>
        </label>

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="mt-4 px-4 py-2 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition"
        >
          {isSaving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  )
}
