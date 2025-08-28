/**
 * API Integration Utilities
 * Provides utilities to integrate new API client with existing React Query setup
 */

import { QueryClient } from '@tanstack/react-query';
import { apiClient, ApiError } from './api-client';
import { safeConsoleError } from './security-utils';

// Enhanced query client that uses our API client
export function createEnhancedQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30000, // Increased from 5 seconds to 30 seconds
        refetchInterval: false, // Disable automatic refetch by default
        gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes (was cacheTime)
        retry: (failureCount, error: any) => {
          // Don't retry on authentication errors
          if (error instanceof ApiError) {
            if (error.status === 401 || error.status === 403) {
              return false;
            }
          }
          
          // Check for other status codes
          if (error?.status === 401 || error?.status === 403) {
            return false;
          }
          
          // Don't retry on 4xx errors except 408, 409, 429
          if (error?.status >= 400 && error?.status < 500) {
            return [408, 409, 429].includes(error.status) && failureCount < 2;
          }
          
          // Retry up to 3 times for 5xx errors and network errors
          return failureCount < 3;
        },
        queryFn: async ({ queryKey, signal }) => {
          // Default query function using our API client
          const [endpoint] = queryKey;
          if (typeof endpoint === 'string') {
            return apiClient.get(endpoint, { signal });
          }
          throw new Error('Invalid query key format');
        }
      },
      mutations: {
        retry: (failureCount, error: any) => {
          // Don't retry mutations on authentication errors
          if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
            return false;
          }
          // Only retry mutations on network errors or 5xx errors
          if (error?.status >= 500 || !error?.status) {
            return failureCount < 2;
          }
          return false;
        }
      }
    }
  });
}

// Utility functions to create authenticated query/mutation functions
export const queryFunctions = {
  // Standard GET request
  get: <T = any>(endpoint: string) => async (): Promise<T> => {
    return apiClient.get<T>(endpoint);
  },

  // GET request with parameters
  getWithParams: <T = any>(endpoint: string, params?: Record<string, any>) => async (): Promise<T> => {
    const url = params ? `${endpoint}?${new URLSearchParams(params).toString()}` : endpoint;
    return apiClient.get<T>(url);
  },

  // POST request
  post: <TData = any, TResponse = any>(endpoint: string) => async (data: TData): Promise<TResponse> => {
    return apiClient.post<TResponse>(endpoint, data);
  },

  // PUT request
  put: <TData = any, TResponse = any>(endpoint: string) => async (data: TData): Promise<TResponse> => {
    return apiClient.put<TResponse>(endpoint, data);
  },

  // DELETE request
  delete: <T = any>(endpoint: string) => async (id?: string | number): Promise<T> => {
    const url = id ? `${endpoint}/${id}` : endpoint;
    return apiClient.delete<T>(url);
  },

  // Custom request with full control
  custom: <TResponse = any>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' = 'GET'
  ) => async (data?: any): Promise<TResponse> => {
    switch (method) {
      case 'GET':
        return apiClient.get<TResponse>(endpoint);
      case 'POST':
        return apiClient.post<TResponse>(endpoint, data);
      case 'PUT':
        return apiClient.put<TResponse>(endpoint, data);
      case 'DELETE':
        return apiClient.delete<TResponse>(endpoint);
      case 'PATCH':
        return apiClient.request<TResponse>(endpoint, { method: 'PATCH', body: JSON.stringify(data) });
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }
};

// Migration helper for existing axios calls
export const migrateApiCall = {
  // Replace axios.get calls
  get: async <T = any>(url: string, config?: any): Promise<{ data: T }> => {
    try {
      const data = await apiClient.get<T>(url, config);
      return { data };
    } catch (error) {
      // Maintain axios-like error structure for backwards compatibility
      throw error;
    }
  },

  // Replace axios.post calls
  post: async <T = any>(url: string, data?: any, config?: any): Promise<{ data: T }> => {
    try {
      const responseData = await apiClient.post<T>(url, data, config);
      return { data: responseData };
    } catch (error) {
      throw error;
    }
  },

  // Replace axios.put calls
  put: async <T = any>(url: string, data?: any, config?: any): Promise<{ data: T }> => {
    try {
      const responseData = await apiClient.put<T>(url, data, config);
      return { data: responseData };
    } catch (error) {
      throw error;
    }
  },

  // Replace axios.delete calls
  delete: async <T = any>(url: string, config?: any): Promise<{ data: T }> => {
    try {
      const data = await apiClient.delete<T>(url, config);
      return { data };
    } catch (error) {
      throw error;
    }
  }
};

// Utility to create query keys with consistent structure
export const createQueryKey = (resource: string, id?: string | number, filters?: Record<string, any>) => {
  const key: (string | number | Record<string, any>)[] = [resource];
  if (id) key.push(id);
  if (filters) key.push(filters);
  return key;
};

// Common query configurations
export const queryConfig = {
  // Real-time data (frequent updates)
  realtime: {
    staleTime: 0,
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
    gcTime: 1 * 60 * 1000 // 1 minute cache for realtime data
  },

  // Static data (infrequent updates)
  static: {
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: false,
    gcTime: 30 * 60 * 1000 // 30 minutes cache for static data
  },

  // User data (medium frequency updates)
  user: {
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000 // 5 minutes cache
  },

  // Device data (regular updates)
  device: {
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000 // 5 minutes cache
  },

  // Historical data (optimized for minimal refetches)
  history: {
    staleTime: 2 * 60 * 1000, // 2 minutes - historical data doesn't change rapidly
    refetchInterval: false, // Don't auto-refetch historical data
    gcTime: 15 * 60 * 1000, // 15 minutes cache for history data
    refetchOnWindowFocus: false, // Don't refetch on window focus
    refetchOnReconnect: false // Don't refetch on reconnect
  }
};

// Error boundary helper for API errors
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function getApiErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unknown error occurred';
}

// Helper to create authenticated requests that handle token refresh automatically
export const createAuthenticatedRequest = <T = any>(
  endpoint: string,
  options?: { method?: string; requiresAuth?: boolean }
) => {
  const { method = 'GET', requiresAuth = true } = options || {};
  
  return async (data?: any): Promise<T> => {
    return apiClient.request<T>(endpoint, {
      method,
      body: data ? JSON.stringify(data) : undefined,
      requiresAuth
    });
  };
};