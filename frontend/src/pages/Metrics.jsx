import React, { useEffect, useMemo, useState } from 'react'
import { getMetrics } from '../api.admin'

const Bar = ({ label, value, max }) => (
  <div className="mb-2">
    <div className="flex justify-between text-xs text-gray-600">
      <span>{label}</span>
      <span>{value}</span>
    </div>
    <div className="h-2 bg-gray-100 rounded">
      <div className="h-2 bg-blue-600 rounded" style={{ width: `${max ? Math.min(100, (value / max) * 100) : 0}%` }} />
    </div>
  </div>
)

export default function Metrics() {
  const [data, setData] = useState(null)
  const [since, setSince] = useState(24)

  const load = async (hours) => {
    try {
      const url = (import.meta.env.VITE_API_BASE || 'http://localhost:8000') + `/api/admin/metrics?since_hours=${hours}`
      const res = await fetch(url)
      const json = await res.json()
      setData(json)
    } catch {}
  }

  useEffect(() => { load(since) }, [since])

  const total = data?.total_issues ?? 0
  const san = data?.by_category?.sanitation ?? 0
  const eme = data?.by_category?.emergency ?? 0
  const resolved = data?.resolved ?? 0

  const zones = useMemo(() => {
    const z = Object.entries(data?.by_zone || {}).sort((a,b)=>b[1]-a[1]).slice(0,10)
    const max = z[0]?.[1] || 0
    return { list: z, max }
  }, [data])

  const hourly = data?.hourly || []
  const maxHourly = hourly.reduce((m, r) => Math.max(m, r.count), 0)

  return (
    <div className="p-4 space-y-6">
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">Metrics</div>
        <div className="text-sm flex items-center gap-2">
          <span className="text-gray-600">Window:</span>
          <select className="border rounded px-2 py-1" value={since} onChange={(e)=>setSince(Number(e.target.value))}>
            <option value={6}>6h</option>
            <option value={12}>12h</option>
            <option value={24}>24h</option>
            <option value={48}>48h</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 border rounded">
          <div className="text-xs text-gray-500">Total Issues</div>
          <div className="text-2xl font-semibold">{total}</div>
        </div>
        <div className="p-4 border rounded">
          <div className="text-xs text-gray-500">Sanitation</div>
          <div className="text-2xl font-semibold">{san}</div>
        </div>
        <div className="p-4 border rounded">
          <div className="text-xs text-gray-500">Emergency</div>
          <div className="text-2xl font-semibold">{eme}</div>
        </div>
        <div className="p-4 border rounded">
          <div className="text-xs text-gray-500">Resolved</div>
          <div className="text-2xl font-semibold">{resolved}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="font-semibold mb-2">Top Zones</div>
          {zones.list.length === 0 && <div className="text-sm text-gray-500">No zone data</div>}
          {zones.list.map(([z, c]) => (
            <Bar key={z} label={z} value={c} max={zones.max} />
          ))}
        </div>
        <div>
          <div className="font-semibold mb-2">Issues per hour (last {since}h)</div>
          {hourly.length === 0 && <div className="text-sm text-gray-500">No data</div>}
          <div className="grid grid-cols-6 gap-2 text-xs text-gray-600 mb-1">
            {hourly.slice(-6).map(h => <div key={h.hour} className="truncate">{h.hour.slice(11,16)}</div>)}
          </div>
          <div className="grid grid-cols-6 gap-2">
            {hourly.slice(-6).map(h => (
              <div key={h.hour} className="h-24 bg-gray-100 flex items-end">
                <div className="w-full bg-blue-600" style={{ height: `${maxHourly ? Math.round((h.count / maxHourly) * 100) : 0}%` }} title={`${h.hour}: ${h.count}`} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
