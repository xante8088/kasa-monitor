'use client'

import { ReactNode, useState, useCallback, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, AlertCircle, TrendingUp } from 'lucide-react'
import { TimePeriodSelector } from './time-period-selector'
import { 
  TimePeriodState, 
  ChartTimeRange,
  TimeFilteredApiParams
} from '@/lib/time-period-types'
import { 
  getDefaultTimePeriod,
  calculateTimeRange,
  timeRangeToApiParams,
  getRefreshInterval,
  filterDataByTimeRange
} from '@/lib/time-period-utils'
import { queryConfig } from '@/lib/api-integration'

interface ChartContainerProps {
  title: string
  deviceIp: string
  dataEndpoint: string // e.g., '/api/device/{deviceIp}/history'
  children: (props: {
    data: any[]
    timeRange: ChartTimeRange
    isLoading: boolean
    error: string | null
  }) => ReactNode
  className?: string
  showSelector?: boolean
  defaultPeriod?: TimePeriodState
}

export function ChartContainer({
  title,
  deviceIp,
  dataEndpoint,
  children,
  className = '',
  showSelector = true,
  defaultPeriod
}: ChartContainerProps) {
  const [timePeriod, setTimePeriod] = useState<TimePeriodState>(
    defaultPeriod || {
      type: getDefaultTimePeriod(),
      customRange: undefined,
      isCustomRangeValid: true
    }
  )

  // Add debouncing for time period changes to prevent excessive API calls
  const [debouncedTimePeriod, setDebouncedTimePeriod] = useState(timePeriod)
  
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      setDebouncedTimePeriod(timePeriod)
    }, 500) // 500ms debounce

    return () => clearTimeout(debounceTimer)
  }, [timePeriod])

  // Calculate stable time range with debouncing
  const timeRange = useMemo(() => {
    return calculateTimeRange(debouncedTimePeriod.type, debouncedTimePeriod.customRange)
  }, [debouncedTimePeriod.type, debouncedTimePeriod.customRange])
  
  // Get refresh interval based on time period
  const refreshInterval = useMemo(() => getRefreshInterval(debouncedTimePeriod.type), [debouncedTimePeriod.type])

  // Create stable query key to prevent excessive refetches
  const queryKey = useMemo(() => {
    // Round timestamps to nearest minute for non-realtime data to prevent excessive queries
    const shouldRoundTime = !['1h', '6h'].includes(debouncedTimePeriod.type)
    const roundToMinutes = (date: Date) => {
      const rounded = new Date(date)
      rounded.setSeconds(0, 0)
      return rounded.toISOString()
    }
    
    const startTime = shouldRoundTime ? roundToMinutes(timeRange.startTime) : timeRange.startTime.toISOString()
    const endTime = shouldRoundTime ? roundToMinutes(timeRange.endTime) : timeRange.endTime.toISOString()
    
    // Create deduplicated key for device history calls
    return ['device-history', deviceIp, debouncedTimePeriod.type, startTime, endTime]
  }, [deviceIp, debouncedTimePeriod.type, timeRange.startTime, timeRange.endTime])

  // Fetch data with time filtering
  const { 
    data: rawData, 
    isLoading, 
    error, 
    refetch,
    isRefetching 
  } = useQuery({
    queryKey,
    queryFn: async () => {
      const apiParams = timeRangeToApiParams(timeRange)
      const url = new URL(dataEndpoint.replace('{deviceIp}', deviceIp), window.location.origin)
      
      // Add time filtering parameters
      if (apiParams.start_time) {
        url.searchParams.set('start_time', apiParams.start_time)
      }
      if (apiParams.end_time) {
        url.searchParams.set('end_time', apiParams.end_time)
      }
      if (apiParams.time_period) {
        url.searchParams.set('time_period', apiParams.time_period)
      }

      const response = await fetch(url.toString())
      if (!response.ok) {
        throw new Error(`Failed to fetch chart data: ${response.statusText}`)
      }
      
      const result = await response.json()
      // Handle both array response and object with data property
      return Array.isArray(result) ? result : (result.data || [])
    },
    // Use history-optimized configuration for better performance
    ...queryConfig.history,
    // Override with time-period specific refresh intervals only for realtime data
    refetchInterval: ['1h', '6h'].includes(debouncedTimePeriod.type) ? refreshInterval : false,
    enabled: debouncedTimePeriod.isCustomRangeValid
  })

  // Filter data by time range (client-side backup if API doesn't support filtering)
  // Ensure rawData is an array before passing to filterDataByTimeRange
  const dataArray = Array.isArray(rawData) ? rawData : []
  const filteredData = filterDataByTimeRange(dataArray, timeRange)

  const handleTimePeriodChange = useCallback((newPeriod: TimePeriodState) => {
    setTimePeriod(newPeriod)
  }, [])

  const handleRefresh = useCallback(() => {
    refetch()
  }, [refetch])

  // Auto-refresh indication
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  
  useEffect(() => {
    if (!isLoading && !error) {
      setLastRefresh(new Date())
    }
  }, [rawData, isLoading, error])

  const errorMessage = error instanceof Error ? error.message : 'An error occurred loading chart data'

  return (
    <div className={`bg-white rounded-lg shadow-md ${className}`}>
      {/* Chart header with title and controls */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <TrendingUp className="h-5 w-5 text-kasa-primary" />
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {(isLoading || isRefetching) && (
            <RefreshCw className="h-4 w-4 text-kasa-primary animate-spin" />
          )}
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Last update indicator */}
          {!error && (
            <span className="text-xs text-gray-500">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          
          {/* Manual refresh button */}
          <button
            onClick={handleRefresh}
            disabled={isRefetching}
            className="p-1 text-gray-400 hover:text-kasa-primary transition-colors disabled:cursor-not-allowed"
            title="Refresh data"
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
          </button>
          
          {/* Time period selector */}
          {showSelector && (
            <TimePeriodSelector
              value={timePeriod}
              onChange={handleTimePeriodChange}
              disabled={isLoading}
            />
          )}
        </div>
      </div>

      {/* Chart content */}
      <div className="p-4">
        {error ? (
          <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
            <AlertCircle className="h-12 w-12 text-red-500" />
            <div>
              <p className="text-red-600 font-medium">Failed to load chart data</p>
              <p className="text-sm text-gray-500 mt-1">{errorMessage}</p>
              <button
                onClick={handleRefresh}
                className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        ) : !debouncedTimePeriod.isCustomRangeValid ? (
          <div className="flex items-center justify-center h-64 text-center">
            <div className="space-y-2">
              <AlertCircle className="h-8 w-8 text-yellow-500 mx-auto" />
              <p className="text-yellow-600">Invalid date range selected</p>
              <p className="text-sm text-gray-500">Please select a valid time period</p>
            </div>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-kasa-primary mx-auto"></div>
              <p className="text-sm text-gray-500">Loading {timeRange.label.toLowerCase()}...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Time range indicator */}
            <div className="mb-4 text-center">
              <p className="text-sm text-gray-600">
                Showing data for: <span className="font-medium text-gray-900">{timeRange.label}</span>
              </p>
              {filteredData.length === 0 && (
                <p className="text-xs text-yellow-600 mt-1">No data available for selected time period</p>
              )}
            </div>
            
            {/* Render chart component */}
            {children({
              data: filteredData,
              timeRange,
              isLoading: isLoading || isRefetching,
              error: errorMessage
            })}
          </>
        )}
      </div>
    </div>
  )
}