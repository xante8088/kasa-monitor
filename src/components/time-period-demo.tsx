'use client'

import { useState } from 'react'
import { ChartContainer } from './chart-container'
import { PowerChart } from './charts/power-chart'
import { VoltageChart } from './charts/voltage-chart'
import { EnergyChart } from './charts/energy-chart'
import { TimePeriodSelector } from './time-period-selector'
import { useTimePeriod } from '@/hooks/use-time-period'
import { Clock, TrendingUp, Zap, Power, Activity } from 'lucide-react'

interface TimePeriodDemoProps {
  deviceIp: string
}

export function TimePeriodDemo({ deviceIp }: TimePeriodDemoProps) {
  const {
    timePeriod,
    timeRange,
    isValid,
    setTimePeriod,
    resetToDefault
  } = useTimePeriod({
    persistKey: `demo_${deviceIp}`,
    onPeriodChange: (period, range) => {
      console.log('Time period changed:', { period, range })
    }
  })

  const [activeDemo, setActiveDemo] = useState<'individual' | 'container'>('container')

  return (
    <div className="space-y-6">
      {/* Demo Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <Clock className="h-6 w-6 text-kasa-primary" />
            <h2 className="text-xl font-bold text-gray-900">Time Period Selector Demo</h2>
          </div>
          <button
            onClick={resetToDefault}
            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          >
            Reset to Default
          </button>
        </div>

        {/* Demo Mode Toggle */}
        <div className="flex space-x-4 mb-4">
          <button
            onClick={() => setActiveDemo('container')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeDemo === 'container' 
                ? 'bg-kasa-primary text-white' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Chart Container (Recommended)
          </button>
          <button
            onClick={() => setActiveDemo('individual')}
            className={`px-4 py-2 rounded-lg transition-colors ${
              activeDemo === 'individual' 
                ? 'bg-kasa-primary text-white' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Individual Components
          </button>
        </div>

        {/* Current State Display */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-2">Current Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Period Type:</span>
              <span className="ml-2 font-medium">{timePeriod.type}</span>
            </div>
            <div>
              <span className="text-gray-600">Time Range:</span>
              <span className="ml-2 font-medium">{timeRange.label}</span>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>
              <span className={`ml-2 font-medium ${isValid ? 'text-green-600' : 'text-red-600'}`}>
                {isValid ? 'Valid' : 'Invalid'}
              </span>
            </div>
          </div>
          {timePeriod.customRange && (
            <div className="mt-2 text-xs text-gray-500">
              Custom Range: {timePeriod.customRange.startDate.toLocaleDateString()} - {timePeriod.customRange.endDate.toLocaleDateString()}
            </div>
          )}
        </div>
      </div>

      {/* Demo Content */}
      {activeDemo === 'container' ? (
        // Chart Container Demo (Recommended approach)
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Chart Container Approach</h3>
            <p className="text-gray-600">Each chart has its own time selector and data fetching logic</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartContainer
              title="Power Consumption"
              deviceIp={deviceIp}
              dataEndpoint="/api/device/{deviceIp}/history"
            >
              {({ data, timeRange, isLoading, error }) => (
                <PowerChart 
                  data={data} 
                  timeRange={timeRange}
                  isLoading={isLoading}
                />
              )}
            </ChartContainer>
            
            <ChartContainer
              title="Voltage Monitoring"
              deviceIp={deviceIp}
              dataEndpoint="/api/device/{deviceIp}/history"
            >
              {({ data, timeRange, isLoading, error }) => (
                <VoltageChart 
                  data={data} 
                  timeRange={timeRange}
                  isLoading={isLoading}
                />
              )}
            </ChartContainer>
          </div>

          <ChartContainer
            title="Energy Usage Trends"
            deviceIp={deviceIp}
            dataEndpoint="/api/device/{deviceIp}/history"
            className="col-span-full"
          >
            {({ data, timeRange, isLoading, error }) => (
              <EnergyChart 
                data={data} 
                timeRange={timeRange}
                isLoading={isLoading}
              />
            )}
          </ChartContainer>
        </div>
      ) : (
        // Individual Components Demo
        <div className="space-y-6">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Individual Components Approach</h3>
            <p className="text-gray-600">Shared time selector with manual chart updates</p>
          </div>

          {/* Standalone Time Period Selector */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Shared Time Period Selector</h3>
              <TimePeriodSelector
                value={timePeriod}
                onChange={setTimePeriod}
              />
            </div>
            
            {!isValid && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-600 text-sm">Please select a valid time period to display charts.</p>
              </div>
            )}
          </div>

          {/* Charts with shared time period */}
          {isValid && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Zap className="h-5 w-5 text-kasa-primary" />
                  <h3 className="text-lg font-semibold">Power Consumption</h3>
                </div>
                <div className="text-center text-gray-500 py-8">
                  <p>Chart would display here with:</p>
                  <p className="text-sm mt-1">Time Range: {timeRange.label}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {timeRange.startTime.toLocaleString()} - {timeRange.endTime.toLocaleString()}
                  </p>
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center space-x-2 mb-4">
                  <Power className="h-5 w-5 text-kasa-primary" />
                  <h3 className="text-lg font-semibold">Voltage</h3>
                </div>
                <div className="text-center text-gray-500 py-8">
                  <p>Chart would display here with:</p>
                  <p className="text-sm mt-1">Time Range: {timeRange.label}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {timeRange.startTime.toLocaleString()} - {timeRange.endTime.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}