/**
 * Phase 3 Priority 1.2: Authentication Service
 * JWT token management for pilot authentication
 */

const TOKEN_KEY = 'chameleon_auth_token';
const PILOT_KEY = 'chameleon_pilot';

export interface AuthToken {
  token: string;
  expires_at: string;
  pilot_id: string;
}

export class AuthService {
  private token: string | null = null;
  private pilot: any | null = null;

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const tokenData = sessionStorage.getItem(TOKEN_KEY);
      const pilotData = sessionStorage.getItem(PILOT_KEY);

      if (tokenData) {
        const parsed = JSON.parse(tokenData);
        // Check if token is expired
        if (new Date(parsed.expires_at) > new Date()) {
          this.token = parsed.token;
        } else {
          this.clearToken();
        }
      }

      if (pilotData) {
        this.pilot = JSON.parse(pilotData);
      }
    } catch (error) {
      console.error('Failed to load auth data from storage:', error);
      this.clearToken();
    }
  }

  setToken(tokenData: AuthToken): void {
    this.token = tokenData.token;
    sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokenData));
  }

  getToken(): string | null {
    return this.token;
  }

  setPilot(pilot: any): void {
    this.pilot = pilot;
    sessionStorage.setItem(PILOT_KEY, JSON.stringify(pilot));
  }

  getPilot(): any | null {
    return this.pilot;
  }

  clearToken(): void {
    this.token = null;
    this.pilot = null;
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(PILOT_KEY);
  }

  isAuthenticated(): boolean {
    return this.token !== null;
  }

  getAuthHeader(): Record<string, string> {
    if (!this.token) {
      return {};
    }
    return {
      'Authorization': `Bearer ${this.token}`,
    };
  }
}

// Singleton instance
export const authService = new AuthService();
