/**
 * Phase 3 Priority 1.2: WebSocket Client
 * Real-time communication with Phase 2 backend
 */

import type { WSMessage, InterventionRequest, InterventionMetrics } from '@/types/intervention';
import { authService } from './auth-service';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export type WSEventType = 'open' | 'close' | 'error' | 'message';
export type WSEventCallback = (data?: any) => void;

interface WSConfig {
  url?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private shouldReconnect = true;
  private eventListeners: Map<WSEventType, Set<WSEventCallback>> = new Map();

  constructor(config: WSConfig = {}) {
    this.url = config.url || WS_URL;
    this.reconnectInterval = config.reconnectInterval || 3000;
    this.maxReconnectAttempts = config.maxReconnectAttempts || 10;
  }

  connect(pilotId?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    try {
      // Build URL with token if available
      const token = authService.getToken();
      const urlWithAuth = token 
        ? `${this.url}?token=${encodeURIComponent(token)}`
        : this.url;

      this.ws = new WebSocket(urlWithAuth);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.emit('open');

        // Subscribe to updates if pilot ID provided
        if (pilotId) {
          this.subscribe(pilotId);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.emit('close', { code: event.code, reason: event.reason });
        
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  disconnect(): void {
    this.shouldReconnect = false;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: WSMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }

    this.ws.send(JSON.stringify(message));
  }

  // Convenience methods
  subscribe(pilotId: string): void {
    this.send({
      type: 'subscribe',
      pilot_id: pilotId,
    });
  }

  unsubscribe(pilotId: string): void {
    this.send({
      type: 'unsubscribe',
      pilot_id: pilotId,
    });
  }

  getPending(pilotId: string, limit = 20): void {
    this.send({
      type: 'get_pending',
      data: { pilot_id: pilotId, limit },
    });
  }

  getMetrics(): void {
    this.send({
      type: 'get_metrics',
    });
  }

  getRequestDetail(requestId: string): void {
    this.send({
      type: 'request_detail',
      data: { request_id: requestId },
    });
  }

  // Event handling
  on(event: WSEventType, callback: WSEventCallback): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off(event: WSEventType, callback: WSEventCallback): void {
    this.eventListeners.get(event)?.delete(callback);
  }

  private emit(event: WSEventType, data?: any): void {
    this.eventListeners.get(event)?.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${event} callback:`, error);
      }
    });
  }

  private handleMessage(message: WSMessage): void {
    this.emit('message', message);

    // Also emit typed events for specific message types
    switch (message.type) {
      case 'new_request':
        this.emit('new_request' as WSEventType, message.data);
        break;
      case 'status_changed':
        this.emit('status_changed' as WSEventType, message.data);
        break;
      case 'metrics_update':
        this.emit('metrics_update' as WSEventType, message.data);
        break;
      case 'error':
        console.error('Server error:', message.error);
        break;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();
