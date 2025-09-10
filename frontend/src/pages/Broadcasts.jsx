import React, { useEffect, useState } from 'react'
import { broadcastNotice, listTemplates } from '../api.admin'

const presets = [
  {
    key: 'heat',
    label: 'Heat Advisory',
    message: 'Heat Advisory: Temperature is rising. Drink water every 20 mins. Stay in shaded areas. Visit First Aid tents if feeling dizzy.'
  },
  {
    key: 'crowd',
    label: 'Crowd Redirect',
    message: '⚠️ Entry Gate 2 is overcrowded. Please use Gate 5 for faster access.'
  },
  {
    key: 'water',
    label: 'Drinking Water Update',
    message: '🔔 Important Update: New safe drinking water refill station opened near Ghat 3. Please avoid using Tap 4 due to contamination alert.'
  },
  {
    key: 'waste',
    label: 'Waste Disposal Reminder',
    message: '🗑️ Thank you for keeping Simhastha clean. Nearest waste bin: 50 meters ahead on your right.'
  },
]

export default function Broadcasts() {
  const [message, setMessage] = useState('')
  const [zones, setZones] = useState('')
  const [phones, setPhones] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const [templates, setTemplates] = useState([])
  const [templateId, setTemplateId] = useState('')

  useEffect(() => { listTemplates().then(setTemplates).catch(()=>{}) }, [])

  const applyPreset = (p) => setMessage(p.message)

  const onSend = async () => {
    setBusy(true); setStatus('')
    try {
      const z = zones.split(',').map(s => s.trim()).filter(Boolean)
      const pn = phones.split(',').map(s => s.trim()).filter(Boolean)
      await broadcastNotice({ message, zones: z.length ? z : null, phone_numbers: pn.length ? pn : null })
      setStatus('Broadcast queued')
    } catch (e) {
      setStatus(String(e))
    } finally { setBusy(false) }
  }

  return (
    <div className="p-4 space-y-4">
      <div className="text-lg font-semibold">Broadcasts</div>
      <div className="flex gap-2 flex-wrap">
        {presets.map(p => (
          <button key={p.key} className="px-3 py-1 border rounded" onClick={() => applyPreset(p)}>{p.label}</button>
        ))}
      </div>
      <div className="flex gap-2 items-center">
        <select className="border rounded px-2 py-1" value={templateId} onChange={(e) => {
          const id = e.target.value; setTemplateId(id)
          const t = templates.find(x => String(x.id) === id); if (t) setMessage(t.text)
        }}>
          <option value="">Select template…</option>
          {templates.map(t => <option key={t.id} value={t.id}>{t.key}</option>)}
        </select>
        <div className="text-xs text-gray-500">or use presets below</div>
      </div>
      <div className="space-y-2">
        <textarea className="w-full border rounded p-2 h-32" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Message" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <input className="border rounded px-3 py-2" placeholder="Zones (comma-separated, optional)" value={zones} onChange={(e) => setZones(e.target.value)} />
          <input className="border rounded px-3 py-2" placeholder="Phone numbers (comma-separated, optional)" value={phones} onChange={(e) => setPhones(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50" disabled={busy || !message.trim()} onClick={onSend}>Send Broadcast</button>
          {status && <div className="text-sm text-gray-600 self-center">{status}</div>}
        </div>
      </div>
    </div>
  )
}
