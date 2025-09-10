import React, { useEffect, useRef } from 'react'

export default function ChatWindow({ messages }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.map((m) => (
        <div key={m.id} className={`flex ${m.is_from_admin ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-[70%] rounded-lg px-3 py-2 shadow text-sm ${
              m.is_from_admin ? 'bg-blue-600 text-white' : 'bg-white'
            }`}
            title={`${m.language || ''}`}
          >
            <div>{m.body}</div>
            <div className="mt-1 text-[10px] opacity-70">
              {new Date(m.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}

