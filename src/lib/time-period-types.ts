/**
 * Time period selector types and interfaces
 */

export type TimePeriodType = 
  | '1h'    // Last hour
  | '6h'    // Last 6 hours
  | '24h'   // Last 24 hours
  | '3d'    // Last 3 days
  | '7d'    // Last 7 days
  | '30d'   // Last 30 days
  | 'custom' // Custom date range

export interface TimePeriodOption {
  value: TimePeriodType
  label: string
  description?: string
  isDefault?: boolean
}

export interface CustomDateRange {
  startDate: Date
  endDate: Date
}

export interface TimePeriodState {
  type: TimePeriodType
  customRange?: CustomDateRange
  isCustomRangeValid: boolean
}

export interface ChartTimeRange {
  startTime: Date
  endTime: Date
  type: TimePeriodType
  label: string
}

export interface TimeFilteredApiParams {
  start_time?: string // ISO string
  end_time?: string   // ISO string
  time_period?: TimePeriodType
}

// Chart data with timestamp
export interface ChartDataPoint {
  timestamp: string | Date
  [key: string]: any
}

// Enhanced chart props that accept time range
export interface TimeAwareChartProps {
  data: ChartDataPoint[]
  timeRange: ChartTimeRange
  isLoading?: boolean
  error?: string | null
}