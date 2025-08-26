'use client'

import { Power, Zap, Activity } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { io, Socket } from 'socket.io-client'
import { CompactExportButton } from './export-button'
import { DataExportModal } from './data-export-modal'

interface DeviceCardProps {
  device: {
    ip: string
    alias: string
    model: string
    device_type: string
    is_on: boolean
    mac: string
  }
  onClick: () => void
}

export function DeviceCard({ device, onClick }: DeviceCardProps) {
  const [realtimeData, setRealtimeData] = useState<any>(null)
  const [socket, setSocket] = useState<Socket | null>(null)
  const [showExportModal, setShowExportModal] = useState(false)

  const { data: deviceData } = useQuery({
    queryKey: ['device', device.ip],
    queryFn: async () => {
      const response = await axios.get(`/api/device/${device.ip}`)
      return response.data
    },
    refetchInterval: 30000,
  })

  useEffect(() => {
    const newSocket = io('http://localhost:5272')
    
    newSocket.on('connect', () => {
      newSocket.emit('subscribe_device', { device_ip: device.ip })
    })

    newSocket.on('device_update', (data: any) => {
      if (data.ip === device.ip) {
        setRealtimeData(data)
      }
    })

    setSocket(newSocket)

    return () => {
      if (newSocket) {
        newSocket.emit('unsubscribe_device', { device_ip: device.ip })
        newSocket.close()
      }
    }
  }, [device.ip])

  const currentData = realtimeData || deviceData || device
  const powerW = currentData.current_power_w || 0
  const todayKwh = currentData.today_energy_kwh || 0
  
  const handleDeviceQuickExport = () => {
    setShowExportModal(true)
  }
  
  const handleDeviceQuickExportWithStop = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering device detail navigation
    handleDeviceQuickExport()
  }

  return (
    <div 
      onClick={onClick}
      className="device-card cursor-pointer hover:border-kasa-primary transition-all"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-lg">{device.alias}</h3>
          <p className="text-sm text-gray-600">{device.model}</p>
        </div>
        <div className={`status-indicator ${currentData.is_on ? 'status-online' : 'status-offline'}`} />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Power className="h-4 w-4 text-gray-500" />
            <span className="text-sm">Status</span>
          </div>
          <span className={`text-sm font-medium ${currentData.is_on ? 'text-green-600' : 'text-gray-500'}`}>
            {currentData.is_on ? 'ON' : 'OFF'}
          </span>
        </div>

        {powerW !== null && (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              <span className="text-sm">Power</span>
            </div>
            <span className="text-sm font-medium">{powerW.toFixed(1)} W</span>
          </div>
        )}

        {todayKwh !== null && (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-blue-500" />
              <span className="text-sm">Today</span>
            </div>
            <span className="text-sm font-medium">{todayKwh.toFixed(3)} kWh</span>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500">{device.mac}</p>
            <p className="text-xs text-gray-500">{device.ip}</p>
          </div>
          <div className="device-actions" onClick={handleDeviceQuickExportWithStop}>
            <CompactExportButton
              onClick={handleDeviceQuickExport}
              title={`Export data for ${device.alias}`}
              className="opacity-70 hover:opacity-100"
            />
          </div>
        </div>
      </div>
      
      {/* Device-specific export modal */}
      {showExportModal && (
        <DataExportModal
          isOpen={showExportModal}
          onClose={() => setShowExportModal(false)}
          preselectedDevices={[device.ip]}
          deviceContext={{
            deviceId: device.ip,
            deviceName: device.alias
          }}
        />
      )}
    </div>
  )
}