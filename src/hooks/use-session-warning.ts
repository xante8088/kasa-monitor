/**
 * Session Warning Hook
 * Provides session expiration warnings and management functionality
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { notificationSystem, AuthNotificationTemplates } from '@/lib/notification-system';
import { safeConsoleError } from '@/lib/security-utils';

export interface UseSessionWarningOptions {
  warningThresholdMinutes?: number; // Show warning when this many minutes remain
  checkIntervalMs?: number; // How often to check session status
  autoExtendThresholdMinutes?: number; // Auto-extend when this many minutes remain
  enableAutoExtend?: boolean;
}

export interface SessionWarningState {
  timeRemaining: number | null; // milliseconds remaining
  minutesRemaining: number; // friendly minutes remaining
  isExpiringSoon: boolean; // true if below warning threshold
  isExpired: boolean; // true if token is expired
  showWarning: boolean; // true if warning should be shown
  lastWarningTime: number | null; // timestamp of last warning shown
}

const DEFAULT_OPTIONS: Required<UseSessionWarningOptions> = {
  warningThresholdMinutes: 5,
  checkIntervalMs: 30000, // 30 seconds
  autoExtendThresholdMinutes: 2,
  enableAutoExtend: false
};

export function useSessionWarning(options: UseSessionWarningOptions = {}) {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const { 
    user, 
    isAuthenticated, 
    refreshToken, 
    getTokenExpirationTime, 
    isTokenExpired,
    sessionTimeRemaining 
  } = useAuth();

  const [warningState, setWarningState] = useState<SessionWarningState>({
    timeRemaining: null,
    minutesRemaining: 0,
    isExpiringSoon: false,
    isExpired: false,
    showWarning: false,
    lastWarningTime: null
  });

  const [extendingSession, setExtendingSession] = useState(false);

  // Calculate session state
  const updateWarningState = useCallback(() => {
    if (!isAuthenticated || !user) {
      setWarningState({
        timeRemaining: null,
        minutesRemaining: 0,
        isExpiringSoon: false,
        isExpired: false,
        showWarning: false,
        lastWarningTime: null
      });
      return;
    }

    const expirationTime = getTokenExpirationTime();
    const expired = isTokenExpired();
    
    if (expired) {
      setWarningState(prev => ({
        ...prev,
        timeRemaining: 0,
        minutesRemaining: 0,
        isExpiringSoon: false,
        isExpired: true,
        showWarning: false
      }));
      return;
    }

    if (expirationTime) {
      const timeRemaining = Math.max(0, expirationTime - Date.now());
      const minutesRemaining = Math.floor(timeRemaining / (1000 * 60));
      const isExpiringSoon = minutesRemaining <= config.warningThresholdMinutes;
      
      // Determine if we should show warning
      const now = Date.now();
      const lastWarningAge = warningState.lastWarningTime ? now - warningState.lastWarningTime : Infinity;
      const shouldShowWarning = isExpiringSoon && 
        minutesRemaining > 0 && 
        lastWarningAge > 60000; // Don't show warning more than once per minute

      setWarningState(prev => ({
        ...prev,
        timeRemaining,
        minutesRemaining,
        isExpiringSoon,
        isExpired: false,
        showWarning: shouldShowWarning,
        lastWarningTime: shouldShowWarning ? now : prev.lastWarningTime
      }));

      // Auto-extend session if enabled and threshold reached
      if (config.enableAutoExtend && 
          minutesRemaining <= config.autoExtendThresholdMinutes && 
          minutesRemaining > 0 && 
          !extendingSession) {
        extendSession();
      }
    }
  }, [
    isAuthenticated, 
    user, 
    getTokenExpirationTime, 
    isTokenExpired, 
    config.warningThresholdMinutes, 
    config.autoExtendThresholdMinutes, 
    config.enableAutoExtend,
    warningState.lastWarningTime,
    extendingSession
  ]);

  // Set up periodic checking
  useEffect(() => {
    if (!isAuthenticated) return;

    updateWarningState();
    const interval = setInterval(updateWarningState, config.checkIntervalMs);
    
    return () => clearInterval(interval);
  }, [isAuthenticated, updateWarningState, config.checkIntervalMs]);

  // Show warning notification when needed
  useEffect(() => {
    if (warningState.showWarning && warningState.minutesRemaining > 0) {
      const notificationId = notificationSystem.show(
        AuthNotificationTemplates.sessionWarning(
          warningState.minutesRemaining,
          extendSession
        )
      );

      return () => {
        notificationSystem.dismiss(notificationId);
      };
    }
  }, [warningState.showWarning, warningState.minutesRemaining]);

  // Extend session function
  const extendSession = useCallback(async (): Promise<boolean> => {
    if (extendingSession || !isAuthenticated) return false;

    setExtendingSession(true);
    
    try {
      await refreshToken();
      
      // Clear the warning flag since session was extended
      setWarningState(prev => ({
        ...prev,
        showWarning: false,
        lastWarningTime: null
      }));

      return true;
    } catch (error) {
      safeConsoleError('Failed to extend session', error);
      return false;
    } finally {
      setExtendingSession(false);
    }
  }, [extendingSession, isAuthenticated, refreshToken]);

  // Format time remaining as human-readable string
  const formatTimeRemaining = useCallback((milliseconds: number): string => {
    const minutes = Math.floor(milliseconds / (1000 * 60));
    const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  }, []);

  // Get session status summary
  const sessionStatus = useMemo(() => {
    if (!isAuthenticated) {
      return 'Not authenticated';
    }
    
    if (warningState.isExpired) {
      return 'Session expired';
    }
    
    if (warningState.isExpiringSoon) {
      return `Expires in ${warningState.minutesRemaining} minute${warningState.minutesRemaining !== 1 ? 's' : ''}`;
    }
    
    if (warningState.timeRemaining) {
      const hours = Math.floor(warningState.timeRemaining / (1000 * 60 * 60));
      if (hours > 0) {
        return `${hours} hour${hours !== 1 ? 's' : ''} remaining`;
      } else {
        return `${warningState.minutesRemaining} minute${warningState.minutesRemaining !== 1 ? 's' : ''} remaining`;
      }
    }
    
    return 'Active session';
  }, [isAuthenticated, warningState]);

  // Dismiss current warning
  const dismissWarning = useCallback(() => {
    setWarningState(prev => ({
      ...prev,
      showWarning: false,
      lastWarningTime: Date.now()
    }));
  }, []);

  // Force check session status
  const checkSessionStatus = useCallback(() => {
    updateWarningState();
  }, [updateWarningState]);

  return {
    // Current state
    ...warningState,
    sessionStatus,
    extendingSession,
    
    // Actions
    extendSession,
    dismissWarning,
    checkSessionStatus,
    
    // Utilities
    formatTimeRemaining: (ms?: number) => 
      formatTimeRemaining(ms ?? warningState.timeRemaining ?? 0),
    
    // Configuration (read-only)
    config: { ...config }
  };
}

// Standalone function to show session warning
export function showSessionWarning(
  minutesRemaining: number, 
  onExtend: () => void
): string {
  return notificationSystem.show(
    AuthNotificationTemplates.sessionWarning(minutesRemaining, onExtend)
  );
}

// Type for the hook return value
export type SessionWarningHook = ReturnType<typeof useSessionWarning>;