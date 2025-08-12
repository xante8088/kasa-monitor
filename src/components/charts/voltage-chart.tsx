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

interface VoltageChartProps {
  data: any[]
}

export function VoltageChart({ data }: VoltageChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available
      </div>
    )
  }

  const chartData = data.map((item) => ({
    time: format(new Date(item.timestamp), 'HH:mm'),
    voltage: item.voltage || 0,
  }))

  // Calculate average voltage for reference line
  const avgVoltage = chartData.reduce((sum, item) => sum + item.voltage, 0) / chartData.length

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
          domain={['dataMin - 5', 'dataMax + 5']}
          label={{ value: 'Voltage (V)', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip />
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
        />
      </LineChart>
    </ResponsiveContainer>
  )
}