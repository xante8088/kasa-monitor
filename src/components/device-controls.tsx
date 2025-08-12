'use client'

import { useState } from 'react'
import { Power } from 'lucide-react'
import axios from 'axios'

interface DeviceControlsProps {
  deviceIp: string
  isOn: boolean
  onUpdate: () => void
}

export function DeviceControls({ deviceIp, isOn, onUpdate }: DeviceControlsProps) {
  const [loading, setLoading] = useState(false)

  const handleToggle = async () => {
    setLoading(true)
    try {
      await axios.post(`/api/device/${deviceIp}/control`, {
        action: isOn ? 'off' : 'on'
      })
      setTimeout(onUpdate, 500) // Give device time to update
    } catch (error) {
      console.error('Failed to control device:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
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
  )
}