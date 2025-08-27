/**
 * API Client with Authentication Interceptor
 * Handles automatic token refresh, 401 responses, and provides typed responses
 */

import { safeStorage, safeConsoleError, getSafeErrorMessage } from './security-utils';

// Types for authentication responses
export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  user: {
    id: number;
    username: string;
    email: string;
    full_name: string;
    role: string;
    permissions: string[];
    is_active: boolean;
  };
}

export interface RefreshResponse {
  access_token: string;
  refresh_token?: string;
}

export interface AuthError {
  error: string;
  detail: string;
  timestamp: string;
}

// Custom error class for API errors
export class ApiError extends Error {
  public status: number;
  public code?: string;
  public data?: any;

  constructor(message: string, status: number, code?: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

// Request configuration
interface RequestConfig extends RequestInit {
  requiresAuth?: boolean;
  skipRetry?: boolean;
}

class ApiClient {
  private baseURL: string = '';
  private refreshPromise: Promise<string> | null = null;
  private authEventHandlers: Set<(event: AuthEvent) => void> = new Set();

  // Authentication events
  public readonly AuthEvents = {
    TOKEN_REFRESHED: 'token_refreshed',
    TOKEN_REFRESH_FAILED: 'token_refresh_failed',
    SESSION_EXPIRED: 'session_expired',
    AUTHENTICATION_REQUIRED: 'authentication_required',
  } as const;

  public async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<T> {
    const { requiresAuth = true, skipRetry = false, ...requestConfig } = config;

    // Prepare request configuration
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
    const headers = new Headers(requestConfig.headers);

    // Add authentication header if required and available
    if (requiresAuth) {
      const token = safeStorage.getItem('token');
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    }

    // Ensure content-type is set for POST/PUT requests
    if (['POST', 'PUT', 'PATCH'].includes(requestConfig.method || 'GET') && 
        !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const requestOptions: RequestInit = {
      ...requestConfig,
      headers,
    };

    try {
      const response = await fetch(url, requestOptions);
      
      // Handle 401 responses
      if (response.status === 401 && requiresAuth && !skipRetry) {
        return this.handleUnauthorized(endpoint, config);
      }

      // Handle other HTTP errors
      if (!response.ok) {
        await this.handleHttpError(response);
      }

      // Parse response
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return response.text() as T;
    } catch (error) {
      safeConsoleError(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  private async handleUnauthorized<T>(
    endpoint: string,
    originalConfig: RequestConfig
  ): Promise<T> {
    try {
      // Try to refresh the token
      await this.refreshToken();
      
      // Retry the original request
      return this.request(endpoint, { ...originalConfig, skipRetry: true });
    } catch (refreshError) {
      // Refresh failed, emit session expired event
      this.emitAuthEvent({
        type: this.AuthEvents.SESSION_EXPIRED,
        message: 'Session expired. Please log in again.',
        code: 'session_expired'
      });
      
      throw new ApiError(
        'Authentication failed',
        401,
        'authentication_required',
        refreshError
      );
    }
  }

  private async handleHttpError(response: Response): Promise<void> {
    let errorData: any;
    
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        errorData = await response.json();
      } else {
        errorData = { message: await response.text() };
      }
    } catch {
      errorData = { message: 'Unknown error occurred' };
    }

    // Emit specific authentication events based on error codes
    if (response.status === 401) {
      const errorCode = errorData.error || 'authentication_required';
      
      switch (errorCode) {
        case 'authentication_expired':
          this.emitAuthEvent({
            type: this.AuthEvents.SESSION_EXPIRED,
            message: 'Your session has expired',
            code: errorCode
          });
          break;
        case 'authentication_required':
          this.emitAuthEvent({
            type: this.AuthEvents.AUTHENTICATION_REQUIRED,
            message: 'Authentication is required',
            code: errorCode
          });
          break;
      }
    }

    throw new ApiError(
      errorData.detail || errorData.message || `HTTP ${response.status}`,
      response.status,
      errorData.error,
      errorData
    );
  }

  public async refreshToken(): Promise<string> {
    // Prevent multiple simultaneous refresh requests
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.performTokenRefresh();
    
    try {
      const newToken = await this.refreshPromise;
      this.refreshPromise = null;
      return newToken;
    } catch (error) {
      this.refreshPromise = null;
      throw error;
    }
  }

  private async performTokenRefresh(): Promise<string> {
    const refreshToken = safeStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          errorData.detail || 'Token refresh failed',
          response.status,
          errorData.error,
          errorData
        );
      }

      const data: RefreshResponse = await response.json();
      
      // Store the new tokens
      safeStorage.setItem('token', data.access_token);
      if (data.refresh_token) {
        safeStorage.setItem('refresh_token', data.refresh_token);
      }

      // Emit token refreshed event
      this.emitAuthEvent({
        type: this.AuthEvents.TOKEN_REFRESHED,
        message: 'Session refreshed successfully',
        code: 'token_refreshed'
      });

      return data.access_token;
    } catch (error) {
      // Clear stored tokens on refresh failure
      safeStorage.removeItem('token');
      safeStorage.removeItem('refresh_token');
      
      // Emit token refresh failed event
      this.emitAuthEvent({
        type: this.AuthEvents.TOKEN_REFRESH_FAILED,
        message: 'Failed to refresh session',
        code: 'refresh_failed'
      });

      throw error;
    }
  }

  // Authentication event management
  public onAuthEvent(handler: (event: AuthEvent) => void): () => void {
    this.authEventHandlers.add(handler);
    
    // Return cleanup function
    return () => {
      this.authEventHandlers.delete(handler);
    };
  }

  private emitAuthEvent(event: AuthEvent): void {
    this.authEventHandlers.forEach(handler => {
      try {
        handler(event);
      } catch (error) {
        safeConsoleError('Auth event handler error', error);
      }
    });
  }

  // Convenience methods
  public get<T = any>(endpoint: string, config?: Omit<RequestConfig, 'method'>): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' });
  }

  public post<T = any>(endpoint: string, data?: any, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  public put<T = any>(endpoint: string, data?: any, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  public delete<T = any>(endpoint: string, config?: Omit<RequestConfig, 'method'>): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' });
  }

  // Token utilities
  public isTokenExpired(token?: string): boolean {
    const tokenToCheck = token || safeStorage.getItem('token');
    if (!tokenToCheck) return true;

    try {
      const payload = JSON.parse(atob(tokenToCheck.split('.')[1]));
      const currentTime = Math.floor(Date.now() / 1000);
      return payload.exp < currentTime;
    } catch {
      return true;
    }
  }

  public getTokenExpirationTime(token?: string): number | null {
    const tokenToCheck = token || safeStorage.getItem('token');
    if (!tokenToCheck) return null;

    try {
      const payload = JSON.parse(atob(tokenToCheck.split('.')[1]));
      return payload.exp * 1000; // Convert to milliseconds
    } catch {
      return null;
    }
  }

  // Clear authentication state
  public clearAuth(): void {
    safeStorage.removeItem('token');
    safeStorage.removeItem('refresh_token');
    safeStorage.removeItem('user');
  }
}

// Authentication event type
export interface AuthEvent {
  type: string;
  message: string;
  code: string;
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { RequestConfig };