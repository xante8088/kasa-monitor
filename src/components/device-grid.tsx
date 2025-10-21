'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient, ApiError } from '@/lib/api-client'
import { Power, Wifi, Zap } from 'lucide-react'
import { DeviceCard } from './device-card'

interface Device {
  ip: string
  alias: string
  model: string
  device_type: string
  is_on: boolean
  mac: string
  current_power_w?: number
  today_energy_kwh?: number
}

interface DeviceGridProps {
  onDeviceSelect: (deviceIp: string) => void
}

export function DeviceGrid({ onDeviceSelect }: DeviceGridProps) {
  const { data: devices, isLoading, error } = useQuery<Device[]>({
    queryKey: ['devices'],
    queryFn: async () => {
      return apiClient.get<Device[]>('/api/devices')
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-kasa-primary"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center text-red-500 py-8">
        Error loading devices. Please check the backend connection.
      </div>
    )
  }

  if (!devices || devices.length === 0) {
    return (
      <div className="text-center py-12">
        <Wifi className="h-16 w-16 mx-auto text-gray-400 mb-4" />
        <h3 className="text-xl font-semibold mb-2">No Devices Found</h3>
        <p className="text-gray-600">Click "Discover Devices" to find your Kasa smart devices.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-8">
      {devices.map((device) => (
        <DeviceCard
          key={device.ip}
          device={device}
          onClick={() => onDeviceSelect(device.ip)}
        />
      ))}
    </div>
  )
}