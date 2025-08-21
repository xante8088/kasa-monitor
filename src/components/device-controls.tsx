'use client'

import { useState } from 'react'
import { Power } from 'lucide-react'
import axios from 'axios'
import { safeConsoleError, safeStorage, createSafeApiUrl } from '@/lib/security-utils'

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
      const token = safeStorage.getItem('token')
      
      // Use safe API URL construction to prevent injection
      const safeUrl = createSafeApiUrl(`/api/device/${encodeURIComponent(deviceIp)}/control`, { action })
      
      await axios.post(safeUrl, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      setTimeout(onUpdate, 500) // Give device time to update
    } catch (error: any) {
      safeConsoleError('Failed to control device', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to control device'
      setError(errorMessage)
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