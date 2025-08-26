/**
 * Toast Notifications Component
 * Renders toast notifications from the notification system
 */

'use client';

import React, { useState, useEffect } from 'react';
import { notificationSystem, ToastNotification, NotificationType } from '@/lib/notification-system';
import { useNotifications } from '@/hooks/use-notifications';

// Icon components for different notification types
const NotificationIcon = ({ type }: { type: NotificationType }) => {
  const baseClasses = "h-6 w-6";
  
  switch (type) {
    case 'success':
      return (
        <svg className={`${baseClasses} text-green-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'error':
      return (
        <svg className={`${baseClasses} text-red-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case 'warning':
      return (
        <svg className={`${baseClasses} text-orange-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      );
    case 'info':
    default:
      return (
        <svg className={`${baseClasses} text-blue-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
  }
};

// Get styling classes for different notification types
const getNotificationClasses = (type: NotificationType): string => {
  const baseClasses = "max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden";
  
  switch (type) {
    case 'success':
      return `${baseClasses} border-l-4 border-green-500`;
    case 'error':
      return `${baseClasses} border-l-4 border-red-500`;
    case 'warning':
      return `${baseClasses} border-l-4 border-orange-500`;
    case 'info':
    default:
      return `${baseClasses} border-l-4 border-blue-500`;
  }
};

// Individual toast component
function ToastItem({ toast, onDismiss }: { toast: ToastNotification; onDismiss: (id: string) => void }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Animate in
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const handleDismiss = () => {
    setIsLeaving(true);
    setTimeout(() => onDismiss(toast.id), 300); // Wait for exit animation
  };

  const handleActionClick = (action: () => void) => {
    action();
    handleDismiss();
  };

  return (
    <div
      className={`transform transition-all duration-300 ease-in-out ${
        isVisible && !isLeaving
          ? 'translate-x-0 opacity-100'
          : 'translate-x-full opacity-0'
      } mb-4`}
    >
      <div className={getNotificationClasses(toast.type)}>
        <div className="p-4">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <NotificationIcon type={toast.type} />
            </div>
            <div className="ml-3 w-0 flex-1 pt-0.5">
              <p className="text-sm font-medium text-gray-900">
                {toast.title}
              </p>
              <p className="mt-1 text-sm text-gray-500">
                {toast.message}
              </p>
              
              {/* Action buttons */}
              {toast.actions && toast.actions.length > 0 && (
                <div className="mt-3 flex space-x-3">
                  {toast.actions.map((action, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => handleActionClick(action.action)}
                      className={`text-sm font-medium px-3 py-1 rounded-md transition-colors ${
                        action.style === 'primary'
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : 'text-gray-600 hover:text-gray-800 bg-gray-100 hover:bg-gray-200'
                      }`}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="ml-4 flex-shrink-0 flex">
              <button
                className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                onClick={handleDismiss}
              >
                <span className="sr-only">Close</span>
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main toast container component
export function ToastNotifications() {
  const { toasts } = useNotifications();

  const handleDismiss = (id: string) => {
    notificationSystem.dismiss(id);
  };

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="assertive"
      className="fixed inset-0 flex items-end justify-center px-4 py-6 pointer-events-none sm:p-6 sm:items-start sm:justify-end z-50"
    >
      <div className="w-full flex flex-col items-center space-y-4 sm:items-end">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={handleDismiss}
          />
        ))}
      </div>
    </div>
  );
}

// Hook to use toast notifications
export function useToastNotifications() {
  return useNotifications();
}

// Utility component for showing authentication-related toasts
export function AuthToastHelper() {
  useEffect(() => {
    // This component doesn't render anything, it just sets up auth event listeners
    // The actual toasts are handled by the ToastNotifications component
    return () => {};
  }, []);

  return null;
}