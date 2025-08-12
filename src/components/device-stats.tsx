'use client'

import { TrendingUp, TrendingDown, Activity, Zap } from 'lucide-react'

interface DeviceStatsProps {
  stats: {
    avg_power: number
    max_power: number
    min_power: number
    total_energy: number
    reading_count: number
  }
}

export function DeviceStats({ stats }: DeviceStatsProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Statistics (Last 30 Days)</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <Activity className="h-8 w-8 text-blue-500" />
          </div>
          <p className="text-sm text-gray-600">Average Power</p>
          <p className="text-xl font-bold">{(stats.avg_power || 0).toFixed(1)} W</p>
        </div>
        
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <TrendingUp className="h-8 w-8 text-red-500" />
          </div>
          <p className="text-sm text-gray-600">Max Power</p>
          <p className="text-xl font-bold">{(stats.max_power || 0).toFixed(1)} W</p>
        </div>
        
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <TrendingDown className="h-8 w-8 text-green-500" />
          </div>
          <p className="text-sm text-gray-600">Min Power</p>
          <p className="text-xl font-bold">{(stats.min_power || 0).toFixed(1)} W</p>
        </div>
        
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <Zap className="h-8 w-8 text-yellow-500" />
          </div>
          <p className="text-sm text-gray-600">Total Energy</p>
          <p className="text-xl font-bold">{(stats.total_energy || 0).toFixed(2)} kWh</p>
        </div>
        
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <Activity className="h-8 w-8 text-purple-500" />
          </div>
          <p className="text-sm text-gray-600">Data Points</p>
          <p className="text-xl font-bold">{stats.reading_count || 0}</p>
        </div>
      </div>
    </div>
  )
}