'use client'

import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { ArrowLeft, Power, Zap, Activity, TrendingUp } from 'lucide-react'
import { PowerChart } from './charts/power-chart'
import { VoltageChart } from './charts/voltage-chart'
import { EnergyChart } from './charts/energy-chart'
import { DeviceControls } from './device-controls'
import { DeviceStats } from './device-stats'

interface DeviceDetailProps {
  deviceIp: string
  onBack: () => void
}

export function DeviceDetail({ deviceIp, onBack }: DeviceDetailProps) {
  const { data: device, isLoading, refetch } = useQuery({
    queryKey: ['device', deviceIp],
    queryFn: async () => {
      const response = await axios.get(`/api/device/${deviceIp}`)
      return response.data
    },
    refetchInterval: 5000,
  })

  const { data: history } = useQuery({
    queryKey: ['device-history', deviceIp],
    queryFn: async () => {
      const response = await axios.get(`/api/device/${deviceIp}/history`)
      return response.data
    },
    refetchInterval: 60000,
  })

  const { data: stats } = useQuery({
    queryKey: ['device-stats', deviceIp],
    queryFn: async () => {
      const response = await axios.get(`/api/device/${deviceIp}/stats`)
      return response.data
    },
    refetchInterval: 60000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-kasa-primary"></div>
      </div>
    )
  }

  if (!device) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Device not found</p>
        <button 
          onClick={onBack}
          className="mt-4 px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
        >
          Go Back
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-5 w-5" />
          <span>Back to Devices</span>
        </button>
        
        <DeviceControls 
          deviceIp={deviceIp} 
          isOn={device.is_on}
          onUpdate={refetch}
        />
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 className="text-2xl font-bold mb-4">{device.alias}</h2>
            <div className="space-y-2 text-sm">
              <p><span className="font-medium">Model:</span> {device.model}</p>
              <p><span className="font-medium">Type:</span> {device.device_type}</p>
              <p><span className="font-medium">IP Address:</span> {device.ip}</p>
              <p><span className="font-medium">MAC Address:</span> {device.mac}</p>
              <p><span className="font-medium">Signal Strength:</span> {device.rssi} dBm</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                <span className="text-sm font-medium">Current Power</span>
              </div>
              <p className="text-2xl font-bold">{(device.current_power_w || 0).toFixed(1)} W</p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Activity className="h-5 w-5 text-blue-500" />
                <span className="text-sm font-medium">Today's Usage</span>
              </div>
              <p className="text-2xl font-bold">{(device.today_energy_kwh || 0).toFixed(3)} kWh</p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <TrendingUp className="h-5 w-5 text-green-500" />
                <span className="text-sm font-medium">This Month</span>
              </div>
              <p className="text-2xl font-bold">{(device.month_energy_kwh || 0).toFixed(2)} kWh</p>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Power className="h-5 w-5 text-purple-500" />
                <span className="text-sm font-medium">Voltage</span>
              </div>
              <p className="text-2xl font-bold">{(device.voltage || 0).toFixed(1)} V</p>
            </div>
          </div>
        </div>
      </div>

      {stats && <DeviceStats stats={stats} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Power Consumption</h3>
          <PowerChart data={history} />
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Voltage</h3>
          <VoltageChart data={history} />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Energy Usage Trend</h3>
        <EnergyChart data={history} />
      </div>
    </div>
  )
}