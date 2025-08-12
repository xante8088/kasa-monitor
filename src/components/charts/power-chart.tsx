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

interface PowerChartProps {
  data: any[]
}

export function PowerChart({ data }: PowerChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available
      </div>
    )
  }

  const chartData = data.map((item) => ({
    time: format(new Date(item.timestamp), 'HH:mm'),
    power: item.current_power_w || 0,
    current: item.current || 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="time" 
          tick={{ fontSize: 12 }}
          interval="preserveStartEnd"
        />
        <YAxis 
          yAxisId="left"
          label={{ value: 'Power (W)', angle: -90, position: 'insideLeft' }}
        />
        <YAxis 
          yAxisId="right"
          orientation="right"
          label={{ value: 'Current (A)', angle: 90, position: 'insideRight' }}
        />
        <Tooltip />
        <Legend />
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="power"
          stroke="#00D4AA"
          strokeWidth={2}
          name="Power (W)"
          dot={false}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="current"
          stroke="#FF6B6B"
          strokeWidth={2}
          name="Current (A)"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}