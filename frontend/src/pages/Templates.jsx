import React, { useEffect, useState } from 'react'
import { listTemplates, createTemplate, updateTemplate, deleteTemplate } from '../api.admin'

export default function Templates() {
  const [items, setItems] = useState([])
  const [key, setKey] = useState('')
  const [text, setText] = useState('')
  const [editing, setEditing] = useState(null)
  const [status, setStatus] = useState('')

  const load = async () => { setItems(await listTemplates()) }
  useEffect(() => { load() }, [])

  const onSave = async () => {
    if (!key.trim() || !text.trim()) return
    if (editing) {
      await updateTemplate(editing, { key, text })
    } else {
      await createTemplate({ key, text })
    }
    setKey(''); setText(''); setEditing(null); setStatus('Saved')
    await load()
  }

  const onEdit = (item) => { setEditing(item.id); setKey(item.key); setText(item.text) }
  const onDelete = async (id) => { if (confirm('Delete template?')) { await deleteTemplate(id); await load() } }

  return (
    <div className="p-4 space-y-4">
      <div className="text-lg font-semibold">Templates</div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input className="border rounded px-3 py-2" placeholder="Key (e.g., heat_advisory)" value={key} onChange={(e) => setKey(e.target.value)} />
        <textarea className="border rounded px-3 py-2 md:col-span-2" placeholder="Text" value={text} onChange={(e) => setText(e.target.value)} />
      </div>
      <div className="flex gap-2">
        <button className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50" disabled={!key.trim() || !text.trim()} onClick={onSave}>{editing ? 'Update' : 'Create'}</button>
        {status && <div className="text-sm text-gray-600 self-center">{status}</div>}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th className="py-2 pr-2">ID</th>
            <th className="py-2 pr-2">Key</th>
            <th className="py-2 pr-2">Text</th>
            <th className="py-2 pr-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id} className="border-b">
              <td className="py-2 pr-2">{t.id}</td>
              <td className="py-2 pr-2">{t.key}</td>
              <td className="py-2 pr-2 max-w-[600px] truncate" title={t.text}>{t.text}</td>
              <td className="py-2 pr-2 space-x-2">
                <button className="px-2 py-1 border rounded" onClick={() => onEdit(t)}>Edit</button>
                <button className="px-2 py-1 border rounded" onClick={() => onDelete(t.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
