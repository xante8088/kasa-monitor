'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'

interface EnergyChartProps {
  data: any[]
}

export function EnergyChart({ data }: EnergyChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No data available
      </div>
    )
  }

  const chartData = data.map((item) => ({
    time: format(new Date(item.timestamp), 'MMM dd HH:mm'),
    daily: item.today_energy_kwh || 0,
    monthly: item.month_energy_kwh || 0,
    total: item.total_energy_kwh || 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="time" 
          tick={{ fontSize: 12 }}
          interval="preserveStartEnd"
        />
        <YAxis 
          label={{ value: 'Energy (kWh)', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip />
        <Legend />
        <Area
          type="monotone"
          dataKey="daily"
          stackId="1"
          stroke="#00D4AA"
          fill="#00D4AA"
          fillOpacity={0.6}
          name="Daily (kWh)"
        />
        <Area
          type="monotone"
          dataKey="monthly"
          stackId="2"
          stroke="#007F66"
          fill="#007F66"
          fillOpacity={0.4}
          name="Monthly (kWh)"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}