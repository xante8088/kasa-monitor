'use client'

import { useState, useCallback } from 'react'
import { Calendar, Clock, ChevronDown } from 'lucide-react'
import { 
  TimePeriodType, 
  TimePeriodState, 
  CustomDateRange 
} from '@/lib/time-period-types'
import { 
  TIME_PERIOD_OPTIONS, 
  getDefaultTimePeriod,
  validateCustomDateRange
} from '@/lib/time-period-utils'

interface TimePeriodSelectorProps {
  value: TimePeriodState
  onChange: (state: TimePeriodState) => void
  className?: string
  disabled?: boolean
}

export function TimePeriodSelector({ 
  value, 
  onChange, 
  className = '',
  disabled = false 
}: TimePeriodSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showCustomRange, setShowCustomRange] = useState(false)
  const [customStartDate, setCustomStartDate] = useState<string>('')
  const [customEndDate, setCustomEndDate] = useState<string>('')
  const [customRangeError, setCustomRangeError] = useState<string>('')

  const selectedOption = TIME_PERIOD_OPTIONS.find(option => option.value === value.type)
  const displayLabel = value.type === 'custom' && value.customRange 
    ? `${value.customRange.startDate.toLocaleDateString()} - ${value.customRange.endDate.toLocaleDateString()}`
    : selectedOption?.label || 'Select period'

  const handlePeriodSelect = useCallback((periodType: TimePeriodType) => {
    if (periodType === 'custom') {
      setShowCustomRange(true)
      setIsOpen(false)
      return
    }

    onChange({
      type: periodType,
      customRange: undefined,
      isCustomRangeValid: true
    })
    setIsOpen(false)
  }, [onChange])

  const handleCustomRangeApply = useCallback(() => {
    const startDate = customStartDate ? new Date(customStartDate) : null
    const endDate = customEndDate ? new Date(customEndDate) : null
    
    const validation = validateCustomDateRange(startDate, endDate)
    
    if (!validation.isValid) {
      setCustomRangeError(validation.error || 'Invalid date range')
      return
    }

    const customRange: CustomDateRange = {
      startDate: startDate!,
      endDate: endDate!
    }

    onChange({
      type: 'custom',
      customRange,
      isCustomRangeValid: true
    })
    
    setShowCustomRange(false)
    setCustomRangeError('')
  }, [customStartDate, customEndDate, onChange])

  const handleCustomRangeCancel = useCallback(() => {
    setShowCustomRange(false)
    setCustomRangeError('')
    setCustomStartDate('')
    setCustomEndDate('')
    
    // Reset to default if current selection is invalid custom range
    if (value.type === 'custom' && !value.isCustomRangeValid) {
      onChange({
        type: getDefaultTimePeriod(),
        customRange: undefined,
        isCustomRangeValid: true
      })
    }
  }, [value, onChange])

  return (
    <div className={`relative ${className}`}>
      {/* Main selector button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          flex items-center justify-between min-w-[200px] px-4 py-2 
          bg-white border border-gray-300 rounded-lg shadow-sm
          hover:border-kasa-primary focus:border-kasa-primary focus:ring-2 focus:ring-kasa-primary/20
          disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed
          transition-all duration-200
        `}
      >
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium truncate">{displayLabel}</span>
        </div>
        <ChevronDown className={`h-4 w-4 text-gray-500 transform transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="py-1">
            {TIME_PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handlePeriodSelect(option.value)}
                className={`
                  w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors
                  ${value.type === option.value ? 'bg-kasa-primary/10 text-kasa-secondary' : 'text-gray-700'}
                `}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{option.label}</span>
                  {option.value === 'custom' && (
                    <Calendar className="h-4 w-4 text-gray-400" />
                  )}
                </div>
                {option.description && (
                  <p className="text-xs text-gray-500 mt-0.5">{option.description}</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Custom range modal */}
      {showCustomRange && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center space-x-2">
                <Calendar className="h-5 w-5 text-kasa-primary" />
                <span>Custom Date Range</span>
              </h3>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => setCustomStartDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-kasa-primary focus:ring-2 focus:ring-kasa-primary/20"
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => setCustomEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-kasa-primary focus:ring-2 focus:ring-kasa-primary/20"
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>

              {customRangeError && (
                <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                  {customRangeError}
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={handleCustomRangeCancel}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCustomRangeApply}
                disabled={!customStartDate || !customEndDate}
                className="px-4 py-2 bg-kasa-primary text-white rounded-lg hover:bg-kasa-secondary disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Apply Range
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  )
}