'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { safeConsoleError, safeStorage } from '@/lib/security-utils';
import { apiClient, AuthEvent } from '@/lib/api-client';
import { notificationSystem, AuthNotificationTemplates } from '@/lib/notification-system';

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, userData: User, refreshToken?: string) => void;
  logout: (reason?: string) => void;
  hasPermission: (permission: string) => boolean;
  isAuthenticated: boolean;
  refreshToken: () => Promise<void>;
  isTokenExpired: () => boolean;
  getTokenExpirationTime: () => number | null;
  sessionTimeRemaining: number | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

// Public routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/setup'];

// Routes that require authentication
const PROTECTED_ROUTES = ['/admin'];

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionTimeRemaining, setSessionTimeRemaining] = useState<number | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    initializeAuth();
    setupAuthEventHandlers();
  }, []);

  useEffect(() => {
    // Set up session monitoring
    if (user) {
      const interval = setInterval(updateSessionTimeRemaining, 60000); // Update every minute
      updateSessionTimeRemaining(); // Initial update
      return () => clearInterval(interval);
    } else {
      setSessionTimeRemaining(null);
    }
  }, [user]);

  useEffect(() => {
    // Handle route protection
    if (!loading) {
      handleRouteProtection();
    }
  }, [pathname, loading, user]);

  const initializeAuth = async () => {
    try {
      const token = safeStorage.getItem('token');
      const userData = safeStorage.getItem('user');

      if (!token || !userData) {
        setLoading(false);
        return;
      }

      // Check if token is expired
      if (apiClient.isTokenExpired(token)) {
        // Try to refresh the token
        try {
          await apiClient.refreshToken();
          // Get updated user data after refresh
          const currentUser = await apiClient.get('/api/auth/me');
          setUser(currentUser);
        } catch (refreshError) {
          // Refresh failed, clear storage and redirect to login
          clearAuthState();
        }
      } else {
        // Token is still valid, verify with server
        try {
          const currentUser = await apiClient.get('/api/auth/me');
          setUser(currentUser);
        } catch (error) {
          // API call failed, clear storage
          clearAuthState();
        }
      }
    } catch (error) {
      safeConsoleError('Auth initialization error', error);
      clearAuthState();
    } finally {
      setLoading(false);
    }
  };

  const clearAuthState = () => {
    apiClient.clearAuth();
    setUser(null);
    setSessionTimeRemaining(null);
  };

  const setupAuthEventHandlers = () => {
    return apiClient.onAuthEvent((event: AuthEvent) => {
      switch (event.type) {
        case apiClient.AuthEvents.TOKEN_REFRESHED:
          notificationSystem.show(AuthNotificationTemplates.tokenRefreshed());
          updateSessionTimeRemaining();
          break;
          
        case apiClient.AuthEvents.TOKEN_REFRESH_FAILED:
          notificationSystem.show(AuthNotificationTemplates.refreshFailed());
          handleAuthFailure('refresh_failed');
          break;
          
        case apiClient.AuthEvents.SESSION_EXPIRED:
          notificationSystem.show(AuthNotificationTemplates.sessionExpired(pathname));
          handleAuthFailure('session_expired');
          break;
          
        case apiClient.AuthEvents.AUTHENTICATION_REQUIRED:
          notificationSystem.show(AuthNotificationTemplates.authenticationRequired(pathname));
          handleAuthFailure('authentication_required');
          break;
      }
    });
  };

  const handleAuthFailure = useCallback((reason: string) => {
    clearAuthState();
    
    // Redirect to login with appropriate parameters
    const searchParams = new URLSearchParams();
    if (pathname && pathname !== '/login') {
      searchParams.set('returnUrl', pathname);
    }
    if (reason === 'session_expired') {
      searchParams.set('sessionExpired', 'true');
    }
    
    const loginUrl = `/login${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    router.push(loginUrl);
  }, [pathname, router]);

  const updateSessionTimeRemaining = useCallback(() => {
    const expirationTime = apiClient.getTokenExpirationTime();
    if (expirationTime) {
      const timeRemaining = Math.max(0, expirationTime - Date.now());
      setSessionTimeRemaining(timeRemaining);
      
      // Show warning if less than 5 minutes remaining
      const minutesRemaining = Math.floor(timeRemaining / (1000 * 60));
      if (minutesRemaining <= 5 && minutesRemaining > 0) {
        const warningShown = sessionStorage.getItem('session-warning-shown');
        if (!warningShown) {
          notificationSystem.show(AuthNotificationTemplates.sessionWarning(
            minutesRemaining,
            () => {
              refreshToken();
              sessionStorage.removeItem('session-warning-shown');
            }
          ));
          sessionStorage.setItem('session-warning-shown', 'true');
        }
      } else if (minutesRemaining > 5) {
        // Reset warning flag when session has more than 5 minutes
        sessionStorage.removeItem('session-warning-shown');
      }
    } else {
      setSessionTimeRemaining(null);
    }
  }, []);

  const handleRouteProtection = async () => {
    const isPublicRoute = PUBLIC_ROUTES.includes(pathname);
    const isProtectedRoute = PROTECTED_ROUTES.some(route => pathname.startsWith(route));

    // Check if setup is required first
    if (pathname !== '/setup') {
      try {
        const response = await fetch('/api/auth/setup-required');
        const data = await response.json();
        if (data.setup_required) {
          router.push('/setup');
          return;
        }
      } catch (error) {
        safeConsoleError('Setup check error', error);
      }
    }

    // Allow access to public routes without authentication
    if (isPublicRoute) {
      // Only redirect authenticated users away from login page
      if (user && pathname === '/login') {
        router.push('/');
      }
      return;
    }

    // For all other routes, require authentication
    if (!user) {
      router.push('/login');
      return;
    }

    // Check admin routes specifically
    if (pathname.startsWith('/admin') && user.role !== 'admin') {
      router.push('/');
      return;
    }
  };

  const login = useCallback((token: string, userData: User, refreshToken?: string) => {
    safeStorage.setItem('token', token);
    safeStorage.setItem('user', JSON.stringify(userData));
    if (refreshToken) {
      safeStorage.setItem('refresh_token', refreshToken);
    }
    setUser(userData);
    
    // Show welcome notification
    notificationSystem.show(AuthNotificationTemplates.loginSuccess(userData.username));
    
    // Handle return URL
    const searchParams = new URLSearchParams(window.location.search);
    const returnUrl = searchParams.get('returnUrl');
    
    if (returnUrl && returnUrl !== '/login') {
      router.push(decodeURIComponent(returnUrl));
    } else {
      router.push('/');
    }
  }, [router]);

  const logout = useCallback((reason?: string) => {
    clearAuthState();
    
    // Show logout notification if it was intentional
    if (!reason || reason === 'user_initiated') {
      notificationSystem.show(AuthNotificationTemplates.logoutSuccess());
    }
    
    // Clear session warning flag
    sessionStorage.removeItem('session-warning-shown');
    
    router.push('/login');
  }, [router]);

  const refreshToken = useCallback(async (): Promise<void> => {
    try {
      await apiClient.refreshToken();
      // Get updated user data after refresh
      const currentUser = await apiClient.get('/api/auth/me');
      setUser(currentUser);
      updateSessionTimeRemaining();
    } catch (error) {
      safeConsoleError('Token refresh failed', error);
      handleAuthFailure('refresh_failed');
      throw error;
    }
  }, [handleAuthFailure]);

  const isTokenExpired = useCallback((): boolean => {
    return apiClient.isTokenExpired();
  }, []);

  const getTokenExpirationTime = useCallback((): number | null => {
    return apiClient.getTokenExpirationTime();
  }, []);

  const hasPermission = useCallback((permission: string): boolean => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    return user.permissions?.includes(permission) || false;
  }, [user]);

  const isAuthenticated = !!user;

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    hasPermission,
    isAuthenticated,
    refreshToken,
    isTokenExpired,
    getTokenExpirationTime,
    sessionTimeRemaining
  };

  // Show loading spinner while initializing
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protecting routes
export function withAuth<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  requiredPermission?: string
) {
  return function AuthenticatedComponent(props: P) {
    const { user, hasPermission, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading) {
        if (!user) {
          router.push('/login');
          return;
        }

        if (requiredPermission && !hasPermission(requiredPermission)) {
          router.push('/');
          return;
        }
      }
    }, [user, loading, hasPermission, router]);

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!user) {
      return null;
    }

    if (requiredPermission && !hasPermission(requiredPermission)) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="text-red-400 text-6xl mb-4">🚫</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
            <p className="text-gray-600">You don't have permission to access this page.</p>
          </div>
        </div>
      );
    }

    return <WrappedComponent {...props} />;
  };
}