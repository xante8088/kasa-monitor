/**
 * Custom hook for managing time period state with persistence and synchronization
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import { 
  TimePeriodType, 
  TimePeriodState, 
  ChartTimeRange,
  CustomDateRange 
} from '@/lib/time-period-types'
import { 
  getDefaultTimePeriod,
  calculateTimeRange,
  validateCustomDateRange
} from '@/lib/time-period-utils'

interface UseTimePeriodOptions {
  defaultPeriod?: TimePeriodType
  persistKey?: string // For localStorage persistence
  onPeriodChange?: (period: TimePeriodState, range: ChartTimeRange) => void
}

export function useTimePeriod(options: UseTimePeriodOptions = {}) {
  const { 
    defaultPeriod = getDefaultTimePeriod(), 
    persistKey,
    onPeriodChange 
  } = options

  // Initialize state from localStorage if available
  const [timePeriod, setTimePeriodState] = useState<TimePeriodState>(() => {
    if (typeof window !== 'undefined' && persistKey) {
      try {
        const stored = localStorage.getItem(`timePeriod_${persistKey}`)
        if (stored) {
          const parsed = JSON.parse(stored)
          // Validate and restore custom dates
          if (parsed.customRange) {
            parsed.customRange.startDate = new Date(parsed.customRange.startDate)
            parsed.customRange.endDate = new Date(parsed.customRange.endDate)
            const validation = validateCustomDateRange(
              parsed.customRange.startDate, 
              parsed.customRange.endDate
            )
            if (!validation.isValid) {
              // Fall back to default if stored custom range is invalid
              return {
                type: defaultPeriod,
                customRange: undefined,
                isCustomRangeValid: true
              }
            }
          }
          return parsed
        }
      } catch (error) {
        console.warn('Failed to restore time period from localStorage:', error)
      }
    }
    
    return {
      type: defaultPeriod,
      customRange: undefined,
      isCustomRangeValid: true
    }
  })

  // Calculate current time range
  const timeRange = useMemo(() => 
    calculateTimeRange(timePeriod.type, timePeriod.customRange),
    [timePeriod.type, timePeriod.customRange]
  )

  // Update state and persist to localStorage
  const setTimePeriod = useCallback((newPeriod: TimePeriodState) => {
    setTimePeriodState(newPeriod)
    
    // Persist to localStorage if key is provided
    if (typeof window !== 'undefined' && persistKey) {
      try {
        localStorage.setItem(`timePeriod_${persistKey}`, JSON.stringify(newPeriod))
      } catch (error) {
        console.warn('Failed to persist time period to localStorage:', error)
      }
    }
  }, [persistKey])

  // Helper to change just the period type
  const setPeriodType = useCallback((type: TimePeriodType) => {
    const newPeriod: TimePeriodState = {
      type,
      customRange: type === 'custom' ? timePeriod.customRange : undefined,
      isCustomRangeValid: type === 'custom' ? (timePeriod.customRange ? true : false) : true
    }
    setTimePeriod(newPeriod)
  }, [timePeriod.customRange, setTimePeriod])

  // Helper to set custom range
  const setCustomRange = useCallback((customRange: CustomDateRange) => {
    const validation = validateCustomDateRange(customRange.startDate, customRange.endDate)
    const newPeriod: TimePeriodState = {
      type: 'custom',
      customRange: validation.isValid ? customRange : undefined,
      isCustomRangeValid: validation.isValid
    }
    setTimePeriod(newPeriod)
    return validation
  }, [setTimePeriod])

  // Reset to default period
  const resetToDefault = useCallback(() => {
    const newPeriod: TimePeriodState = {
      type: defaultPeriod,
      customRange: undefined,
      isCustomRangeValid: true
    }
    setTimePeriod(newPeriod)
  }, [defaultPeriod, setTimePeriod])

  // Check if current period is valid
  const isValid = useMemo(() => {
    if (timePeriod.type === 'custom') {
      return timePeriod.isCustomRangeValid && !!timePeriod.customRange
    }
    return true
  }, [timePeriod])

  // Call onChange callback when period changes
  useEffect(() => {
    if (onPeriodChange && isValid) {
      onPeriodChange(timePeriod, timeRange)
    }
  }, [timePeriod, timeRange, onPeriodChange, isValid])

  return {
    timePeriod,
    timeRange,
    isValid,
    setTimePeriod,
    setPeriodType,
    setCustomRange,
    resetToDefault
  }
}