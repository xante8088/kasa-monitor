/**
 * Utility functions for time period calculations and data filtering
 */

import { 
  TimePeriodType, 
  TimePeriodOption, 
  CustomDateRange, 
  ChartTimeRange,
  TimeFilteredApiParams,
  ChartDataPoint
} from './time-period-types'
import { 
  subHours, 
  subDays, 
  startOfDay, 
  endOfDay, 
  isAfter, 
  isBefore,
  format,
  isValid 
} from 'date-fns'

/**
 * Available time period options for the selector
 */
export const TIME_PERIOD_OPTIONS: TimePeriodOption[] = [
  { 
    value: '1h', 
    label: 'Last Hour',
    description: 'Past 60 minutes'
  },
  { 
    value: '6h', 
    label: 'Last 6 Hours',
    description: 'Past 6 hours'
  },
  { 
    value: '24h', 
    label: 'Last 24 Hours',
    description: 'Past day',
    isDefault: true
  },
  { 
    value: '3d', 
    label: 'Last 3 Days',
    description: 'Past 3 days'
  },
  { 
    value: '7d', 
    label: 'Last 7 Days',
    description: 'Past week'
  },
  { 
    value: '30d', 
    label: 'Last 30 Days',
    description: 'Past month'
  },
  { 
    value: 'custom', 
    label: 'Custom Range',
    description: 'Select specific dates'
  }
]

/**
 * Get the default time period
 */
export function getDefaultTimePeriod(): TimePeriodType {
  const defaultOption = TIME_PERIOD_OPTIONS.find(option => option.isDefault)
  return defaultOption?.value || '24h'
}

/**
 * Calculate time range from period type
 */
export function calculateTimeRange(
  type: TimePeriodType, 
  customRange?: CustomDateRange
): ChartTimeRange {
  const now = new Date()
  let startTime: Date
  let endTime = now
  let label: string

  switch (type) {
    case '1h':
      startTime = subHours(now, 1)
      label = 'Last Hour'
      break
    case '6h':
      startTime = subHours(now, 6)
      label = 'Last 6 Hours'
      break
    case '24h':
      startTime = subHours(now, 24)
      label = 'Last 24 Hours'
      break
    case '3d':
      startTime = subDays(now, 3)
      label = 'Last 3 Days'
      break
    case '7d':
      startTime = subDays(now, 7)
      label = 'Last 7 Days'
      break
    case '30d':
      startTime = subDays(now, 30)
      label = 'Last 30 Days'
      break
    case 'custom':
      if (!customRange) {
        // Fallback to last 24 hours if custom range not provided
        startTime = subHours(now, 24)
        label = 'Last 24 Hours'
      } else {
        startTime = startOfDay(customRange.startDate)
        endTime = endOfDay(customRange.endDate)
        label = `${format(customRange.startDate, 'MMM dd')} - ${format(customRange.endDate, 'MMM dd')}`
      }
      break
    default:
      startTime = subHours(now, 24)
      label = 'Last 24 Hours'
  }

  return {
    startTime,
    endTime,
    type,
    label
  }
}

/**
 * Convert time range to API parameters
 */
export function timeRangeToApiParams(timeRange: ChartTimeRange): TimeFilteredApiParams {
  return {
    start_time: timeRange.startTime.toISOString(),
    end_time: timeRange.endTime.toISOString(),
    time_period: timeRange.type
  }
}

/**
 * Validate custom date range
 */
export function validateCustomDateRange(
  startDate: Date | null, 
  endDate: Date | null
): { isValid: boolean; error?: string } {
  if (!startDate || !endDate) {
    return { isValid: false, error: 'Both start and end dates are required' }
  }

  if (!isValid(startDate) || !isValid(endDate)) {
    return { isValid: false, error: 'Invalid date format' }
  }

  if (isAfter(startDate, endDate)) {
    return { isValid: false, error: 'Start date must be before end date' }
  }

  const now = new Date()
  if (isAfter(startDate, now)) {
    return { isValid: false, error: 'Start date cannot be in the future' }
  }

  if (isAfter(endDate, now)) {
    return { isValid: false, error: 'End date cannot be in the future' }
  }

  // Check if range is not too large (e.g., max 90 days)
  const maxDays = 90
  const daysDifference = (endDate.getTime() - startDate.getTime()) / (1000 * 3600 * 24)
  if (daysDifference > maxDays) {
    return { isValid: false, error: `Date range cannot exceed ${maxDays} days` }
  }

  return { isValid: true }
}

/**
 * Filter chart data by time range
 */
export function filterDataByTimeRange(
  data: ChartDataPoint[], 
  timeRange: ChartTimeRange
): ChartDataPoint[] {
  if (!data || data.length === 0) {
    return []
  }

  return data.filter(item => {
    const itemDate = new Date(item.timestamp)
    return (
      isValid(itemDate) &&
      !isBefore(itemDate, timeRange.startTime) &&
      !isAfter(itemDate, timeRange.endTime)
    )
  })
}

/**
 * Get appropriate time format for chart axis based on time range
 */
export function getTimeFormatForRange(type: TimePeriodType): string {
  switch (type) {
    case '1h':
    case '6h':
      return 'HH:mm'
    case '24h':
      return 'MMM dd HH:mm'
    case '3d':
    case '7d':
      return 'MMM dd'
    case '30d':
    case 'custom':
      return 'MMM dd'
    default:
      return 'MMM dd HH:mm'
  }
}

/**
 * Calculate appropriate data point interval for chart display
 */
export function calculateDataInterval(
  dataLength: number, 
  type: TimePeriodType
): number {
  // Aim for approximately 50-100 points on the chart
  const targetPoints = 75
  
  if (dataLength <= targetPoints) {
    return 1 // Show all points
  }
  
  return Math.ceil(dataLength / targetPoints)
}

/**
 * Get refresh interval in milliseconds based on time period
 */
export function getRefreshInterval(type: TimePeriodType): number {
  switch (type) {
    case '1h':
    case '6h':
      return 30000 // 30 seconds for short periods
    case '24h':
      return 60000 // 1 minute for daily view
    case '3d':
    case '7d':
      return 300000 // 5 minutes for longer periods
    case '30d':
    case 'custom':
      return 600000 // 10 minutes for long periods
    default:
      return 60000 // Default 1 minute
  }
}