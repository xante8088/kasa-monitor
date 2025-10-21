'use client'

import { useState } from 'react'
import { Power } from 'lucide-react'
import { apiClient, ApiError } from '@/lib/api-client'
import { safeConsoleError, createSafeApiUrl } from '@/lib/security-utils'

interface DeviceControlsProps {
  deviceIp: string
  isOn: boolean
  onUpdate: () => void
}

export function DeviceControls({ deviceIp, isOn, onUpdate }: DeviceControlsProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleToggle = async () => {
    setLoading(true)
    setError(null)
    try {
      const action = isOn ? 'off' : 'on'

      // Use safe API URL construction to prevent injection
      const safeUrl = createSafeApiUrl(`/api/device/${encodeURIComponent(deviceIp)}/control`, { action })

      await apiClient.post(safeUrl, {})
      setTimeout(onUpdate, 500) // Give device time to update
    } catch (error: any) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          setError('Authentication failed. Please log in again.')
        } else if (error.status === 403) {
          setError('You do not have permission to control this device.')
        } else {
          setError(error.message || 'Failed to control device')
        }
        safeConsoleError(`Failed to control device: ${error.message}`, error)
      } else {
        setError('Network error. Please check your connection.')
        safeConsoleError('Failed to control device', error)
      }
      // Clear error after 3 seconds
      setTimeout(() => setError(null), 3000)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-end space-y-2">
      <button
        onClick={handleToggle}
        disabled={loading}
        className={`
          flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all
          ${isOn 
            ? 'bg-red-500 hover:bg-red-600 text-white' 
            : 'bg-green-500 hover:bg-green-600 text-white'}
          ${loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <Power className="h-5 w-5" />
        <span>{loading ? 'Processing...' : (isOn ? 'Turn Off' : 'Turn On')}</span>
      </button>
      {error && (
        <div className="text-red-500 text-sm bg-red-50 px-3 py-1 rounded border border-red-200">
          {error}
        </div>
      )}
    </div>
  )
}