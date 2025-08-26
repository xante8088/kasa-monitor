/**
 * Session Warning Modal Component
 * Shows a modal dialog when the user's session is about to expire
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useSessionWarning } from '@/hooks/use-session-warning';
import { useAuth } from '@/contexts/auth-context';

interface SessionWarningModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExtend: () => void;
  onLogout: () => void;
  minutesRemaining: number;
}

export function SessionWarningModal({
  isOpen,
  onClose,
  onExtend,
  onLogout,
  minutesRemaining
}: SessionWarningModalProps) {
  const [countdown, setCountdown] = useState(minutesRemaining * 60);
  const [isExtending, setIsExtending] = useState(false);

  // Update countdown every second
  useEffect(() => {
    if (!isOpen) return;

    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          // Session expired, auto-logout
          onLogout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, onLogout]);

  // Reset countdown when modal opens
  useEffect(() => {
    if (isOpen) {
      setCountdown(minutesRemaining * 60);
    }
  }, [isOpen, minutesRemaining]);

  const handleExtend = async () => {
    setIsExtending(true);
    try {
      await onExtend();
      onClose();
    } catch (error) {
      console.error('Failed to extend session:', error);
    } finally {
      setIsExtending(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-orange-50 px-6 py-4 border-b border-orange-200">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg 
                className="h-8 w-8 text-orange-600" 
                xmlns="http://www.w3.org/2000/svg" 
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" 
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-semibold text-orange-900">
                Session Expiring Soon
              </h3>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          <div className="text-center">
            {/* Countdown Display */}
            <div className="mb-4">
              <div className="text-3xl font-mono font-bold text-gray-900 mb-2">
                {formatTime(countdown)}
              </div>
              <p className="text-sm text-gray-600">
                Your session will expire automatically
              </p>
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-orange-500 h-full rounded-full transition-all duration-1000 ease-linear"
                  style={{
                    width: `${Math.max(0, (countdown / (minutesRemaining * 60)) * 100)}%`
                  }}
                />
              </div>
            </div>

            <p className="text-gray-700 mb-6">
              For your security, your session will expire due to inactivity.
              <br />
              Would you like to extend your session?
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-gray-50 px-6 py-4 flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-3 space-y-3 space-y-reverse sm:space-y-0">
          <button
            type="button"
            onClick={onLogout}
            disabled={isExtending}
            className="w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Logout Now
          </button>
          
          <button
            type="button"
            onClick={handleExtend}
            disabled={isExtending}
            className="w-full sm:w-auto inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-orange-600 hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExtending ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Extending...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Extend Session
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Auto Session Warning Modal
 * Automatically shows when session is about to expire
 */
export function AutoSessionWarningModal() {
  const { logout } = useAuth();
  const {
    showWarning,
    minutesRemaining,
    extendSession,
    dismissWarning,
    extendingSession
  } = useSessionWarning({
    warningThresholdMinutes: 5,
    checkIntervalMs: 30000 // Check every 30 seconds
  });

  const [modalOpen, setModalOpen] = useState(false);

  // Show modal when warning is triggered
  useEffect(() => {
    if (showWarning && minutesRemaining > 0) {
      setModalOpen(true);
    }
  }, [showWarning, minutesRemaining]);

  const handleClose = () => {
    setModalOpen(false);
    dismissWarning();
  };

  const handleExtend = async () => {
    await extendSession();
    setModalOpen(false);
  };

  const handleLogout = () => {
    setModalOpen(false);
    logout('user_initiated');
  };

  return (
    <SessionWarningModal
      isOpen={modalOpen}
      onClose={handleClose}
      onExtend={handleExtend}
      onLogout={handleLogout}
      minutesRemaining={minutesRemaining}
    />
  );
}

/**
 * Toast Notification Component for Session Warnings
 * Alternative to modal for less intrusive notifications
 */
export function SessionWarningToast({
  isVisible,
  onExtend,
  onDismiss,
  minutesRemaining,
  timeRemaining
}: {
  isVisible: boolean;
  onExtend: () => void;
  onDismiss: () => void;
  minutesRemaining: number;
  timeRemaining: number;
}) {
  if (!isVisible) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full bg-white rounded-lg shadow-lg border border-orange-200 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className="text-sm font-medium text-gray-900">
              Session Expiring
            </p>
            <p className="text-sm text-gray-500">
              Your session will expire in {minutesRemaining} minute{minutesRemaining !== 1 ? 's' : ''}.
            </p>
            <div className="mt-3 flex space-x-3">
              <button
                type="button"
                onClick={onExtend}
                className="text-sm bg-orange-600 hover:bg-orange-700 text-white px-3 py-1 rounded-md font-medium"
              >
                Extend
              </button>
              <button
                type="button"
                onClick={onDismiss}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Dismiss
              </button>
            </div>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500"
              onClick={onDismiss}
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      {/* Progress bar */}
      <div className="bg-gray-200 h-1">
        <div 
          className="bg-orange-500 h-full transition-all duration-1000 ease-linear"
          style={{
            width: `${Math.max(0, (timeRemaining / (minutesRemaining * 60 * 1000)) * 100)}%`
          }}
        />
      </div>
    </div>
  );
}