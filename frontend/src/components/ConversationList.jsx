import React from 'react'

export default function ConversationList({ conversations, selected, onSelect }) {
  return (
    <div className="h-full overflow-y-auto divide-y divide-gray-100">
      {conversations.map((c) => (
        <button
          key={c.phone}
          onClick={() => onSelect(c.phone)}
          className={`w-full text-left px-4 py-3 hover:bg-gray-100 ${
            selected === c.phone ? 'bg-gray-100' : ''
          }`}
        >
          <div className="font-semibold">{c.phone}</div>
          <div className="text-sm text-gray-600 truncate">{c.lastMessage}</div>
        </button>
      ))}
    </div>
  )
}

