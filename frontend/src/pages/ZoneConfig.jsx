import React, { useEffect, useState } from 'react'
import { getZoneConfig, upsertZoneConfig } from '../api.admin'

export default function ZoneConfig() {
  const [rows, setRows] = useState([])
  const [zone, setZone] = useState('')
  const [sanitation, setSanitation] = useState('')
  const [medical, setMedical] = useState('')
  const [status, setStatus] = useState('')

  const load = async () => {
    const data = await getZoneConfig()
    setRows(data)
  }

  useEffect(() => { load() }, [])

  const onSave = async () => {
    const payload = {
      zone: zone.trim(),
      sanitation_eta_minutes: sanitation ? Number(sanitation) : null,
      medical_eta_minutes: medical ? Number(medical) : null,
    }
    await upsertZoneConfig(payload)
    setZone(''); setSanitation(''); setMedical('')
    setStatus('Saved')
    await load()
  }

  return (
    <div className="p-4 space-y-4">
      <div className="text-lg font-semibold">Zone ETA Config</div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input className="border rounded px-3 py-2" placeholder="Zone (e.g., 4)" value={zone} onChange={(e) => setZone(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Sanitation ETA (min)" value={sanitation} onChange={(e) => setSanitation(e.target.value)} />
        <input className="border rounded px-3 py-2" placeholder="Medical ETA (min)" value={medical} onChange={(e) => setMedical(e.target.value)} />
        <button className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50" disabled={!zone.trim()} onClick={onSave}>Save</button>
      </div>
      {status && <div className="text-sm text-gray-600">{status}</div>}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-2">Zone</th>
            <th className="py-2 pr-2">Sanitation ETA</th>
            <th className="py-2 pr-2">Medical ETA</th>
            <th className="py-2 pr-2">Updated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.zone} className="border-b">
              <td className="py-2 pr-2">{r.zone}</td>
              <td className="py-2 pr-2">{r.sanitation_eta_minutes ?? '-'}</td>
              <td className="py-2 pr-2">{r.medical_eta_minutes ?? '-'}</td>
              <td className="py-2 pr-2">{new Date(r.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

