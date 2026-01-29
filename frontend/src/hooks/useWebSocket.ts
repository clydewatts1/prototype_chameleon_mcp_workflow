/**
 * useWebSocket: WebSocket connection management for real-time dashboard
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Message queue during disconnection
 * - Type-safe message handling
 * - React hook integration
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { WebSocketMessage, WebSocketResponse } from '../types'

interface UseWebSocketOptions {
  url: string
  onMessage?: (response: WebSocketResponse) => void
  onError?: (error: Event) => void
  onConnected?: () => void
  onDisconnected?: () => void
  reconnectAttempts?: number
  reconnectDelay?: number
}

interface PendingMessage {
  id: string
  message: WebSocketMessage
  timestamp: number
}

export function useWebSocket({
  url,
  onMessage,
  onError,
  onConnected,
  onDisconnected,
  reconnectAttempts = 5,
  reconnectDelay = 1000,
}: UseWebSocketOptions) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectCount = useRef(0)
  const messageQueue = useRef<PendingMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (isConnecting || isConnected) return

    setIsConnecting(true)

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        console.log('[WebSocket] Connected')
        setIsConnected(true)
        setIsConnecting(false)
        reconnectCount.current = 0

        // Flush message queue
        while (messageQueue.current.length > 0) {
          const pending = messageQueue.current.shift()
          if (pending && ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(pending.message))
          }
        }

        onConnected?.()
      }

      ws.current.onmessage = (event) => {
        try {
          const response: WebSocketResponse = JSON.parse(event.data)
          onMessage?.(response)
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err)
        }
      }

      ws.current.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        onError?.(error)
      }

      ws.current.onclose = () => {
        console.log('[WebSocket] Disconnected')
        setIsConnected(false)
        setIsConnecting(false)
        onDisconnected?.()

        // Attempt reconnect
        if (reconnectCount.current < reconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectCount.current)
          console.log(`[WebSocket] Reconnecting in ${delay}ms...`)
          reconnectCount.current += 1

          setTimeout(() => {
            connect()
          }, delay)
        } else {
          console.error('[WebSocket] Max reconnection attempts reached')
        }
      }
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err)
      setIsConnecting(false)
      onError?.(new Event('connection_error'))
    }
  }, [url, onMessage, onError, onConnected, onDisconnected, reconnectAttempts, reconnectDelay, isConnecting, isConnected])

  // Send message
  const send = useCallback((message: WebSocketMessage) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      // Queue message if not connected
      messageQueue.current.push({
        id: `${Date.now()}-${Math.random()}`,
        message,
        timestamp: Date.now(),
      })

      // Try to connect if not already attempting
      if (!isConnected && !isConnecting) {
        connect()
      }

      return
    }

    ws.current.send(JSON.stringify(message))
  }, [isConnected, isConnecting, connect])

  // Disconnect
  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    setIsConnected(false)
    setIsConnecting(false)
    messageQueue.current = []
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [])

  return {
    isConnected,
    isConnecting,
    send,
    disconnect,
    reconnect: connect,
    messageQueueLength: messageQueue.current.length,
  }
}
