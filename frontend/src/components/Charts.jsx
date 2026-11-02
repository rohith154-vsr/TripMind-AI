import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, PieChart, Pie, Legend } from 'recharts'

// Weather mini chart
export function WeatherChart({ dailyForecast = [] }) {
  if (!dailyForecast.length) return null

  const data = dailyForecast.slice(0, 7).map(d => ({
    date: d.date ? d.date.slice(5) : '',  // "MM-DD"
    maxTemp: d.temp_max_c ?? 0,
    minTemp: d.temp_min_c ?? 0,
    precipitation: d.precipitation_mm ?? 0,
  }))

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} unit="°C" />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
            formatter={(val) => [`${val}°C`]}
          />
          <Area type="monotone" dataKey="maxTemp" stroke="#f97316" fill="#fed7aa" strokeWidth={2} name="Max Temp" />
          <Area type="monotone" dataKey="minTemp" stroke="#6366f1" fill="#e0e7ff" strokeWidth={2} name="Min Temp" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// Budget breakdown chart
export function BudgetChart({ breakdown = {} }) {
  const items = [
    { name: 'Accommodation', value: breakdown.accommodation?.estimated_total || 0, color: '#6366f1' },
    { name: 'Flights', value: breakdown.flights?.estimated_total || 0, color: '#f97316' },
    { name: 'Food', value: breakdown.food?.estimated_total || 0, color: '#10b981' },
    { name: 'Transport', value: breakdown.local_transport?.estimated_total || 0, color: '#f59e0b' },
    { name: 'Activities', value: breakdown.activities_attractions?.estimated_total || 0, color: '#3b82f6' },
    { name: 'Shopping', value: breakdown.shopping_souvenirs?.estimated_total || 0, color: '#8b5cf6' },
    { name: 'Emergency', value: breakdown.emergency_buffer?.recommended_amount || 0, color: '#6b7280' },
  ].filter(i => i.value > 0)

  if (!items.length) return null

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={items} margin={{ top: 4, right: 4, left: -10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            angle={-35}
            textAnchor="end"
          />
          <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {items.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
