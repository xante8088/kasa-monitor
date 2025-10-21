'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient, ApiError } from '@/lib/api-client'
import { DollarSign, TrendingUp, Calendar, Zap } from 'lucide-react'
import { useState } from 'react'

export function CostSummary() {
  const [timeRange, setTimeRange] = useState('30d')
  
  const { data: costs, isLoading } = useQuery({
    queryKey: ['costs', timeRange],
    queryFn: async () => {
      const endDate = new Date()
      const startDate = new Date()

      switch (timeRange) {
        case '7d':
          startDate.setDate(startDate.getDate() - 7)
          break
        case '30d':
          startDate.setDate(startDate.getDate() - 30)
          break
        case '90d':
          startDate.setDate(startDate.getDate() - 90)
          break
        case 'ytd':
          startDate.setMonth(0, 1)
          break
      }

      const params = new URLSearchParams({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      })
      return apiClient.get(`/api/costs?${params.toString()}`)
    },
    refetchInterval: 300000, // Refresh every 5 minutes
  })

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded w-1/3"></div>
        </div>
      </div>
    )
  }

  if (!costs || costs.error) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
        <div className="flex items-center space-x-2 text-yellow-800">
          <DollarSign className="h-6 w-6" />
          <p>Configure electricity rates to see cost analysis</p>
        </div>
      </div>
    )
  }

  const topConsumers = costs.device_costs?.slice(0, 3) || []
  const currencySymbol = costs.currency === 'EUR' ? '€' : costs.currency === 'GBP' ? '£' : '$'

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Electricity Cost Summary</h2>
        
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-kasa-primary"
        >
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
          <option value="ytd">Year to Date</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <DollarSign className="h-5 w-5 text-green-600" />
            <span className="text-sm font-medium text-green-800">Total Cost</span>
          </div>
          <p className="text-2xl font-bold text-green-900">
            {currencySymbol}{(costs.total_cost || 0).toFixed(2)}
          </p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Zap className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-800">Total Energy</span>
          </div>
          <p className="text-2xl font-bold text-blue-900">
            {(costs.total_energy || 0).toFixed(2)} kWh
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <TrendingUp className="h-5 w-5 text-purple-600" />
            <span className="text-sm font-medium text-purple-800">Rate</span>
          </div>
          <p className="text-2xl font-bold text-purple-900">
            {costs.rate_per_kwh
              ? `${currencySymbol}${costs.rate_per_kwh.toFixed(4)}/kWh`
              : costs.rate_type || 'Variable'}
          </p>
        </div>

        <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <Calendar className="h-5 w-5 text-orange-600" />
            <span className="text-sm font-medium text-orange-800">Devices</span>
          </div>
          <p className="text-2xl font-bold text-orange-900">
            {costs.device_costs?.length || 0}
          </p>
        </div>
      </div>

      {topConsumers.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Top Energy Consumers</h3>
          <div className="space-y-2">
            {topConsumers.map((device: any, index: number) => (
              <div key={device.device_ip} className="flex items-center justify-between py-2 border-b last:border-0">
                <div className="flex items-center space-x-3">
                  <span className="text-lg font-bold text-gray-400">#{index + 1}</span>
                  <span className="text-sm font-medium">{device.device_ip}</span>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">{currencySymbol}{device.cost.toFixed(2)}</p>
                  <p className="text-xs text-gray-500">{device.total_kwh.toFixed(2)} kWh</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}