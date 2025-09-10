import React, { useEffect, useState } from 'react'
import { assignIssue, updateIssueStatus, listFeedbackFallback, listApprovals, listMessagesByPhone } from '../api.admin'

export default function Issues() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ category: '', status: '', zone: '' })
  const [drawer, setDrawer] = useState(null) // selected item for details

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filters.category) params.set('category', filters.category)
      if (filters.status) params.set('status', filters.status)
      if (filters.zone) params.set('zone', filters.zone)
      // Reuse endpoint from fallback path
      const url = '/api/tools/feedback/list' + (params.toString() ? ('?' + params.toString()) : '')
      const data = await fetch((import.meta.env.VITE_API_BASE || 'http://localhost:8000') + url).then(r=>r.json())
      setItems(data.items || [])
    } catch (e) { setError(String(e)) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [filters.category, filters.status, filters.zone])

  const onUpdateStatus = async (id, status) => {
    await updateIssueStatus({ id, status })
    setItems((prev) => prev.map((r) => (r.id === id ? { ...r, status } : r)))
  }

  const onAssign = async (feedback_id) => {
    const assignee = prompt('Assign to (username/team):')
    if (!assignee) return
    await assignIssue({ feedback_id, assignee, note: 'via admin UI' })
    alert('Assigned')
  }

  return (
    <div className="p-4 h-full overflow-auto">
      <div className="text-lg font-semibold mb-3">Issues</div>
      <div className="flex gap-2 mb-3">
        <select className="border rounded px-2 py-1" value={filters.category} onChange={(e)=>setFilters(f=>({...f,category:e.target.value}))}>
          <option value="">All categories</option>
          <option value="sanitation">sanitation</option>
          <option value="emergency">emergency</option>
          <option value="info">info</option>
          <option value="other">other</option>
        </select>
        <select className="border rounded px-2 py-1" value={filters.status} onChange={(e)=>setFilters(f=>({...f,status:e.target.value}))}>
          <option value="">All status</option>
          <option value="new">new</option>
          <option value="in_progress">in_progress</option>
          <option value="resolved">resolved</option>
        </select>
        <input className="border rounded px-2 py-1" placeholder="Zone (e.g., Zone 4)" value={filters.zone} onChange={(e)=>setFilters(f=>({...f,zone:e.target.value}))} />
        <button className="px-2 py-1 border rounded" onClick={load}>Refresh</button>
      </div>
      {loading && <div>Loading…</div>}
      {error && <div className="text-red-600">{error}</div>}
      {!loading && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2 pr-2">ID</th>
              <th className="py-2 pr-2">Phone</th>
              <th className="py-2 pr-2">Category</th>
              <th className="py-2 pr-2">Status</th>
              <th className="py-2 pr-2">Zone</th>
              <th className="py-2 pr-2">Created</th>
              <th className="py-2 pr-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-2">{r.id}</td>
                <td className="py-2 pr-2">{r.phone_number}</td>
                <td className="py-2 pr-2">{r.category}</td>
                <td className="py-2 pr-2">{r.status}</td>
                <td className="py-2 pr-2">{r.zone || '-'}</td>
                <td className="py-2 pr-2">{new Date(r.created_at).toLocaleString()}</td>
                <td className="py-2 pr-2 space-x-2">
                  <button className="px-2 py-1 border rounded" onClick={() => onAssign(r.id)}>Assign</button>
                  <button className="px-2 py-1 border rounded" onClick={() => onUpdateStatus(r.id, 'in_progress')}>In Progress</button>
                  <button className="px-2 py-1 border rounded" onClick={() => onUpdateStatus(r.id, 'resolved')}>Resolved</button>
                  <button className="px-2 py-1 border rounded" onClick={async ()=>{
                    const msgs = await listMessagesByPhone(r.phone_number)
                    setDrawer({ item: r, messages: msgs })
                  }}>Details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && items.length === 0 && (
        <div className="text-gray-500">No issues yet. They will appear as the agent logs them.</div>
      )}
      {drawer && (
        <div className="fixed inset-0 bg-black/30" onClick={()=>setDrawer(null)}>
          <div className="absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-xl p-4" onClick={(e)=>e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold">Issue #{drawer.item.id} — {drawer.item.category}</div>
              <button className="px-2 py-1 border rounded" onClick={()=>setDrawer(null)}>Close</button>
            </div>
            <div className="text-sm text-gray-600 mb-2">Phone: {drawer.item.phone_number} | Zone: {drawer.item.zone || '-'}</div>
            <div className="text-sm mb-3">{drawer.item.message}</div>
            <div className="text-sm font-semibold mb-1">Conversation</div>
            <div className="h-80 overflow-auto border rounded p-2 bg-gray-50">
              {drawer.messages.map(m => (
                <div key={m.id} className="mb-2">
                  <div className="text-xs text-gray-500">{m.is_from_admin ? 'Admin' : 'User'} • {new Date(m.timestamp).toLocaleString()}</div>
                  <div>{m.body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )}
