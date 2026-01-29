/**
 * Login: Authentication page
 * 
 * Handles:
 * - JWT token input
 * - Token validation
 * - Redirect to dashboard on success
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks'

export function Login() {
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { setToken: setAuthToken } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!token) {
      setError('Token is required')
      return
    }

    try {
      setAuthToken(token)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError('Invalid token format')
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white rounded-lg shadow-md p-8 max-w-md w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">🦎 Chameleon</h1>
        <p className="text-gray-600 mb-6">Pilot Intervention Dashboard</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              JWT Token
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste your JWT token"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-2">
              Get a token from the backend: POST /auth/token
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full px-4 py-2 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 transition"
          >
            Login
          </button>
        </form>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-xs text-blue-800">
            <strong>For development:</strong> Use the test token generator
          </p>
          <code className="text-xs text-blue-600 mt-2 block break-words">
            python phase2_jwt_rbac_test.py
          </code>
        </div>
      </div>
    </div>
  )
}
