/**
 * Authentication Notification System
 * Provides user-friendly notifications for authentication events
 * Uses native browser APIs and custom toast system
 */

import { safeConsoleError } from './security-utils';

// Notification types
export type NotificationType = 'success' | 'warning' | 'error' | 'info';

export interface NotificationOptions {
  title: string;
  message: string;
  type: NotificationType;
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  action: () => void;
  style?: 'primary' | 'secondary';
}

// Toast notification component data
export interface ToastNotification extends NotificationOptions {
  id: string;
  timestamp: number;
  dismissed: boolean;
}

class NotificationSystem {
  private toasts: Map<string, ToastNotification> = new Map();
  private listeners: Set<(toasts: ToastNotification[]) => void> = new Set();
  private nextId = 1;

  // Show a notification
  public show(options: NotificationOptions): string {
    const id = `notification-${this.nextId++}`;
    const toast: ToastNotification = {
      ...options,
      id,
      timestamp: Date.now(),
      dismissed: false,
      duration: options.duration ?? this.getDefaultDuration(options.type)
    };

    this.toasts.set(id, toast);
    this.notifyListeners();

    // Auto-dismiss non-persistent notifications
    if (!options.persistent && toast.duration > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, toast.duration);
    }

    return id;
  }

  // Dismiss a notification
  public dismiss(id: string): void {
    const toast = this.toasts.get(id);
    if (toast) {
      toast.dismissed = true;
      this.toasts.delete(id);
      this.notifyListeners();
    }
  }

  // Clear all notifications
  public clear(): void {
    this.toasts.clear();
    this.notifyListeners();
  }

  // Subscribe to toast updates
  public subscribe(listener: (toasts: ToastNotification[]) => void): () => void {
    this.listeners.add(listener);
    
    // Send current state
    listener(Array.from(this.toasts.values()));

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  // Get current toasts
  public getToasts(): ToastNotification[] {
    return Array.from(this.toasts.values()).sort((a, b) => b.timestamp - a.timestamp);
  }

  private notifyListeners(): void {
    const toasts = this.getToasts();
    this.listeners.forEach(listener => {
      try {
        listener(toasts);
      } catch (error) {
        safeConsoleError('Notification listener error', error);
      }
    });
  }

  private getDefaultDuration(type: NotificationType): number {
    switch (type) {
      case 'error':
        return 8000; // 8 seconds for errors
      case 'warning':
        return 6000; // 6 seconds for warnings
      case 'success':
        return 4000; // 4 seconds for success
      case 'info':
      default:
        return 5000; // 5 seconds for info
    }
  }

  // Authentication-specific notification methods
  public showAuthNotification(event: AuthenticationEvent): string {
    switch (event.type) {
      case 'session_expired':
        return this.show({
          title: 'Session Expired',
          message: 'Your session has expired. Please log in again.',
          type: 'warning',
          duration: 8000,
          actions: [
            {
              label: 'Login',
              action: () => window.location.href = '/login?sessionExpired=true',
              style: 'primary'
            }
          ]
        });

      case 'token_refreshed':
        return this.show({
          title: 'Session Renewed',
          message: 'Your session has been automatically renewed.',
          type: 'success',
          duration: 3000
        });

      case 'token_refresh_failed':
        return this.show({
          title: 'Session Refresh Failed',
          message: 'Could not renew your session. Please log in again.',
          type: 'error',
          duration: 8000,
          actions: [
            {
              label: 'Login',
              action: () => window.location.href = '/login?sessionExpired=true',
              style: 'primary'
            }
          ]
        });

      case 'authentication_required':
        return this.show({
          title: 'Authentication Required',
          message: 'Please log in to access this feature.',
          type: 'info',
          duration: 6000,
          actions: [
            {
              label: 'Login',
              action: () => window.location.href = `/login?returnUrl=${encodeURIComponent(window.location.pathname)}`,
              style: 'primary'
            }
          ]
        });

      case 'session_warning':
        return this.show({
          title: 'Session Expiring Soon',
          message: `Your session will expire in ${event.timeRemaining} minutes.`,
          type: 'warning',
          persistent: true,
          actions: [
            {
              label: 'Extend Session',
              action: event.onExtend || (() => {}),
              style: 'primary'
            },
            {
              label: 'Logout',
              action: event.onLogout || (() => {}),
              style: 'secondary'
            }
          ]
        });

      case 'authentication_error':
        return this.show({
          title: 'Authentication Error',
          message: event.message || 'An authentication error occurred.',
          type: 'error',
          duration: 8000
        });

      default:
        return this.show({
          title: 'Authentication Notice',
          message: event.message || 'Authentication event occurred.',
          type: 'info',
          duration: 5000
        });
    }
  }
}

// Authentication event types
export interface AuthenticationEvent {
  type: string;
  message?: string;
  timeRemaining?: number;
  onExtend?: () => void;
  onLogout?: () => void;
}

// Predefined notification templates
export const AuthNotificationTemplates = {
  sessionExpired: (returnUrl?: string): NotificationOptions => ({
    title: 'Session Expired',
    message: 'Your session has expired. Please log in again.',
    type: 'warning',
    duration: 8000,
    actions: [
      {
        label: 'Login',
        action: () => {
          const url = returnUrl 
            ? `/login?returnUrl=${encodeURIComponent(returnUrl)}&sessionExpired=true`
            : '/login?sessionExpired=true';
          window.location.href = url;
        },
        style: 'primary'
      }
    ]
  }),

  sessionWarning: (minutesRemaining: number, onExtend: () => void): NotificationOptions => ({
    title: 'Session Expiring Soon',
    message: `Your session will expire in ${minutesRemaining} minute${minutesRemaining !== 1 ? 's' : ''}. Would you like to extend it?`,
    type: 'warning',
    persistent: true,
    actions: [
      {
        label: 'Extend Session',
        action: onExtend,
        style: 'primary'
      },
      {
        label: 'Logout',
        action: () => window.location.href = '/login',
        style: 'secondary'
      }
    ]
  }),

  tokenRefreshed: (): NotificationOptions => ({
    title: 'Session Renewed',
    message: 'Your session has been automatically renewed.',
    type: 'success',
    duration: 3000
  }),

  refreshFailed: (): NotificationOptions => ({
    title: 'Session Refresh Failed',
    message: 'Could not renew your session. Please log in again.',
    type: 'error',
    duration: 8000,
    actions: [
      {
        label: 'Login',
        action: () => window.location.href = '/login?sessionExpired=true',
        style: 'primary'
      }
    ]
  }),

  authenticationRequired: (returnUrl?: string): NotificationOptions => ({
    title: 'Authentication Required',
    message: 'Please log in to access this feature.',
    type: 'info',
    duration: 6000,
    actions: [
      {
        label: 'Login',
        action: () => {
          const url = returnUrl 
            ? `/login?returnUrl=${encodeURIComponent(returnUrl)}`
            : '/login';
          window.location.href = url;
        },
        style: 'primary'
      }
    ]
  }),

  loginSuccess: (username: string): NotificationOptions => ({
    title: 'Welcome Back!',
    message: `Successfully logged in as ${username}.`,
    type: 'success',
    duration: 4000
  }),

  logoutSuccess: (): NotificationOptions => ({
    title: 'Logged Out',
    message: 'You have been successfully logged out.',
    type: 'info',
    duration: 3000
  })
};

// Export singleton instance
export const notificationSystem = new NotificationSystem();

// Hook for React components (to be used in .tsx files)
// Note: This is just the interface - actual hook implementation should be in a React component file

// Utility function to create notification from error
export function createErrorNotification(error: unknown, title = 'Error Occurred'): NotificationOptions {
  let message = 'An unknown error occurred';
  
  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'string') {
    message = error;
  } else if (error && typeof error === 'object' && 'message' in error) {
    message = String((error as any).message);
  }

  return {
    title,
    message,
    type: 'error',
    duration: 8000
  };
}