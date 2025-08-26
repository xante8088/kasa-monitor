'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode, useState } from 'react'
import { AuthProvider } from '../contexts/auth-context'
import { ToastNotifications } from './toast-notifications'
import { AutoSessionWarningModal } from './session-warning-modal'
import { createEnhancedQueryClient } from '@/lib/api-integration'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => createEnhancedQueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
        {/* Global notification and session management components */}
        <ToastNotifications />
        <AutoSessionWarningModal />
      </AuthProvider>
    </QueryClientProvider>
  )
}