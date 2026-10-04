import {
  CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'
import { formatMetric } from '../api'

interface ParetoPoint {
  cost: number
  aqi: number
  scenario_id: string
}

export default function ParetoChart({ points }: { points: ParetoPoint[] }) {
  return (
    <div className="pareto-plot">
      <ResponsiveContainer width="100%" height={235}>
        <ScatterChart margin={{ top: 12, right: 16, bottom: 15, left: 4 }}>
          <CartesianGrid stroke="#e7ece7" strokeDasharray="3 4" />
          <XAxis type="number" dataKey="aqi" name="AQI" stroke="#9ba69e" tick={{ fontSize: 8 }} tickLine={false} axisLine={false} />
          <YAxis type="number" dataKey="cost" name="Estimated cost" stroke="#9ba69e" tick={{ fontSize: 8 }} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value) => formatMetric(value)} />
          <Scatter name="Pareto strategy" data={points} fill="#8dae6e" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
