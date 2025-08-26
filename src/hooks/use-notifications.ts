/**
 * React hooks for notification system
 */

'use client';

import { useState, useEffect } from 'react';
import { notificationSystem, ToastNotification, NotificationOptions } from '@/lib/notification-system';

// Hook for using the notification system in React components
export function useNotifications() {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  useEffect(() => {
    return notificationSystem.subscribe(setToasts);
  }, []);

  return {
    toasts,
    show: (options: NotificationOptions) => notificationSystem.show(options),
    dismiss: (id: string) => notificationSystem.dismiss(id),
    clear: () => notificationSystem.clear(),
    showAuth: (event: any) => notificationSystem.showAuthNotification(event)
  };
}