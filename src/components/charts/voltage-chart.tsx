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
  ReferenceLine,
} from 'recharts'
import { format } from 'date-fns'
import { TimeAwareChartProps } from '@/lib/time-period-types'
import { getTimeFormatForRange, calculateDataInterval } from '@/lib/time-period-utils'

interface VoltageChartProps extends Omit<TimeAwareChartProps, 'error'> {
  // Keeping backward compatibility
  data: any[]
}

export function VoltageChart({ data, timeRange, isLoading }: VoltageChartProps) {
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
    voltage: item.voltage || 0,
  }))

  // Calculate average voltage for reference line
  const avgVoltage = chartData.reduce((sum, item) => sum + item.voltage, 0) / chartData.length

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
                {entry.name}: {entry.value.toFixed(1)}V
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
          domain={['dataMin - 5', 'dataMax + 5']}
          label={{ value: 'Voltage (V)', angle: -90, position: 'insideLeft' }}
          tick={{ fontSize: 12 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <ReferenceLine 
          y={120} 
          label="Nominal (120V)" 
          stroke="#666" 
          strokeDasharray="5 5"
        />
        <ReferenceLine 
          y={avgVoltage} 
          label={`Avg (${avgVoltage.toFixed(1)}V)`} 
          stroke="#007F66" 
          strokeDasharray="3 3"
        />
        <Line
          type="monotone"
          dataKey="voltage"
          stroke="#4A90E2"
          strokeWidth={2}
          name="Voltage (V)"
          dot={false}
          opacity={isLoading ? 0.6 : 1}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}