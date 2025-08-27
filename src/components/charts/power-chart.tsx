'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import { TimeAwareChartProps } from '@/lib/time-period-types'
import { getTimeFormatForRange, calculateDataInterval } from '@/lib/time-period-utils'

interface PowerChartProps extends Omit<TimeAwareChartProps, 'error'> {
  // Keeping backward compatibility
  data: any[]
}

export function PowerChart({ data, timeRange, isLoading }: PowerChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available
      </div>
    )
  }

  // Get appropriate time format based on time range
  const timeFormat = timeRange ? getTimeFormatForRange(timeRange.type) : 'HH:mm'
  
  // Calculate data interval for performance
  const dataInterval = timeRange ? calculateDataInterval(data.length, timeRange.type) : 1

  const chartData = data.map((item) => ({
    time: format(new Date(item.timestamp), timeFormat),
    fullTime: new Date(item.timestamp).toLocaleString(),
    power: item.current_power_w || 0,
    current: item.current || 0,
  }))

  // Custom tooltip with more detailed time information
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm font-medium text-gray-900">{data.fullTime}</p>
          <div className="space-y-1 mt-1">
            {payload.map((entry: any, index: number) => (
              <p key={index} className="text-sm" style={{ color: entry.color }}>
                {entry.name}: {entry.value.toFixed(2)}
              </p>
            ))}
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis 
          dataKey="time" 
          tick={{ fontSize: 12 }}
          interval={Math.max(0, Math.floor(dataInterval - 1))}
          angle={timeRange?.type === '30d' || timeRange?.type === 'custom' ? -45 : 0}
          textAnchor={timeRange?.type === '30d' || timeRange?.type === 'custom' ? 'end' : 'middle'}
          height={timeRange?.type === '30d' || timeRange?.type === 'custom' ? 60 : 30}
        />
        <YAxis 
          yAxisId="left"
          label={{ value: 'Power (W)', angle: -90, position: 'insideLeft' }}
          tick={{ fontSize: 12 }}
        />
        <YAxis 
          yAxisId="right"
          orientation="right"
          label={{ value: 'Current (A)', angle: 90, position: 'insideRight' }}
          tick={{ fontSize: 12 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="power"
          stroke="#00D4AA"
          strokeWidth={2}
          name="Power (W)"
          dot={false}
          opacity={isLoading ? 0.6 : 1}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="current"
          stroke="#FF6B6B"
          strokeWidth={2}
          name="Current (A)"
          dot={false}
          opacity={isLoading ? 0.6 : 1}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}