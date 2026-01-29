/**
 * useAuth: JWT authentication management
 *
 * Handles:
 * - JWT token storage
 * - Token validation & expiration
 * - Logout
 * - Authorization header generation
 */

import { useCallback, useEffect, useState } from 'react'
import { PilotAuth, PilotRole } from '../types'

const TOKEN_KEY = 'chameleon_jwt_token'
const PILOT_ID_KEY = 'chameleon_pilot_id'
const TOKEN_CHECK_INTERVAL = 60000 // Check every minute

export function useAuth() {
  const [auth, setAuth] = useState<PilotAuth | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load token from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      try {
        // Decode JWT to get pilot info
        const decoded = decodeJWT(token)
        if (decoded && !isTokenExpired(decoded.exp)) {
          setAuth({
            pilot_id: decoded.sub,
            role: (decoded.role || 'VIEWER') as PilotRole,
            issued_at: new Date(decoded.iat * 1000).toISOString(),
            expires_at: new Date(decoded.exp * 1000).toISOString(),
          })
        } else {
          // Token expired
          logout()
        }
      } catch (err) {
        console.error('Failed to decode token:', err)
        logout()
      }
    }
    setIsLoading(false)
  }, [])

  // Periodically check token expiration
  useEffect(() => {
    const interval = setInterval(() => {
      if (auth) {
        const expiresAt = new Date(auth.expires_at)
        const now = new Date()
        const minutesUntilExpiry = (expiresAt.getTime() - now.getTime()) / 60000

        if (minutesUntilExpiry < 5) {
          // Token expires in less than 5 minutes, should refresh
          console.warn('Token expires soon, should refresh')
          // In production, would trigger refresh flow here
        } else if (minutesUntilExpiry < 0) {
          // Token expired
          logout()
        }
      }
    }, TOKEN_CHECK_INTERVAL)

    return () => clearInterval(interval)
  }, [auth])

  // Store token
  const setToken = useCallback((token: string) => {
    try {
      const decoded = decodeJWT(token)
      if (!decoded) {
        throw new Error('Invalid token format')
      }

      if (isTokenExpired(decoded.exp)) {
        throw new Error('Token is expired')
      }

      localStorage.setItem(TOKEN_KEY, token)
      setAuth({
        pilot_id: decoded.sub,
        role: (decoded.role || 'VIEWER') as PilotRole,
        issued_at: new Date(decoded.iat * 1000).toISOString(),
        expires_at: new Date(decoded.exp * 1000).toISOString(),
      })
      setError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(message)
      throw err
    }
  }, [])

  // Get current token
  const getToken = useCallback(() => {
    return localStorage.getItem(TOKEN_KEY)
  }, [])

  // Get authorization header
  const getAuthHeader = useCallback(() => {
    const token = getToken()
    if (!token) return {}
    return {
      Authorization: `Bearer ${token}`,
    }
  }, [])

  // Logout
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(PILOT_ID_KEY)
    setAuth(null)
    setError(null)
  }, [])

  // Check if authenticated
  const isAuthenticated = useCallback(() => {
    return auth !== null && !isTokenExpired(new Date(auth.expires_at).getTime() / 1000)
  }, [auth])

  return {
    auth,
    isLoading,
    error,
    setToken,
    getToken,
    getAuthHeader,
    logout,
    isAuthenticated: isAuthenticated(),
  }
}

/**
 * Helper: Decode JWT token
 */
function decodeJWT(token: string) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      throw new Error('Invalid token format')
    }

    const payload = JSON.parse(atob(parts[1]))
    return payload as {
      sub: string
      role: string
      iat: number
      exp: number
    }
  } catch (err) {
    console.error('Failed to decode JWT:', err)
    return null
  }
}

/**
 * Helper: Check if token is expired
 */
function isTokenExpired(exp: number): boolean {
  const now = Math.floor(Date.now() / 1000)
  return now > exp
}
