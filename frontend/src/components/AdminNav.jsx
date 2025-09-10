import React from 'react'

const NavItem = ({ id, label, active, onClick }) => (
  <button
    onClick={() => onClick(id)}
    className={`w-full text-left px-4 py-2 hover:bg-gray-100 ${active ? 'bg-gray-100 font-semibold' : ''}`}
  >
    {label}
  </button>
)

export default function AdminNav({ route, onNavigate }) {
  return (
    <div className="w-64 border-r border-gray-200 flex flex-col">
      <div className="px-4 py-3 text-gray-600 text-sm">Admin</div>
      <NavItem id="conversations" label="Conversations" active={route==='conversations'} onClick={onNavigate} />
      <NavItem id="issues" label="Issues" active={route==='issues'} onClick={onNavigate} />
      <NavItem id="broadcasts" label="Broadcasts" active={route==='broadcasts'} onClick={onNavigate} />
      <NavItem id="templates" label="Templates" active={route==='templates'} onClick={onNavigate} />
      <NavItem id="zone-config" label="Zone ETAs" active={route==='zone-config'} onClick={onNavigate} />
      <NavItem id="metrics" label="Metrics" active={route==='metrics'} onClick={onNavigate} />
      <div className="mt-auto px-4 py-3 text-xs text-gray-400">Simhastha Admin</div>
    </div>
  )
}

