import React, { useEffect, useMemo, useState } from 'react'
import { fetchMessages, sendReply } from '../api'
import ConversationList from '../components/ConversationList'
import ChatWindow from '../components/ChatWindow'
import MessageInput from '../components/MessageInput'
import { classifyIntent, summarizeConversation, setContactMetadata, resolveContext } from '../api.admin'

const WS_URL = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000') + '/ws'

export default function Conversations() {
  const [messages, setMessages] = useState([])
  const [selectedPhone, setSelectedPhone] = useState(null)
  const [filter, setFilter] = useState('')
  const [context, setContext] = useState(null)

  useEffect(() => {
    fetchMessages().then(setMessages)
    const ws = new WebSocket(WS_URL)
    ws.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data)
        if (payload.type === 'message') {
          setMessages((prev) => [...prev, payload.data])
        }
      } catch {}
    }
    const ping = setInterval(() => {
      try { ws.readyState === 1 && ws.send('ping') } catch {}
    }, 30000)
    return () => { clearInterval(ping); ws.close() }
  }, [])

  const conversations = useMemo(() => {
    const byPhone = new Map()
    messages.forEach((m) => {
      if (!byPhone.has(m.phone_number)) byPhone.set(m.phone_number, [])
      byPhone.get(m.phone_number).push(m)
    })
    const list = Array.from(byPhone.entries()).map(([phone, msgs]) => ({
      phone,
      lastMessage: msgs[msgs.length - 1]?.body || '',
      messages: msgs,
    }))
    return list
      .filter((c) => !filter || c.phone.includes(filter))
      .sort((a, b) => a.phone.localeCompare(b.phone))
  }, [messages, filter])

  const activeMessages = useMemo(() => {
    return conversations.find((c) => c.phone === selectedPhone)?.messages || []
  }, [conversations, selectedPhone])

  const handleSend = async (text) => {
    if (!selectedPhone) return
    const saved = await sendReply({ phone_number: selectedPhone, body: text })
    setMessages((prev) => [...prev, saved])
  }

  useEffect(() => {
    if (!selectedPhone) { setContext(null); return }
    resolveContext(selectedPhone).then(setContext).catch(()=>setContext(null))
  }, [selectedPhone, messages.length])

  return (
    <div className="h-full flex">
      <div className="w-80 border-r border-gray-200 flex flex-col">
        <div className="px-3 pt-3 pb-2">
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Search phone..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <ConversationList
          conversations={conversations}
          selected={selectedPhone}
          onSelect={setSelectedPhone}
        />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        {selectedPhone ? (
          <>
            <div className="border-b px-4 py-3 flex items-center justify-between">
              <div className="font-semibold truncate">{selectedPhone}</div>
              {context && (
                <div className="text-xs text-gray-600">
                  {context.zone ? `Zone: ${context.zone} • ` : ''}
                  San ETA: {context.sanitation_eta_minutes}m • Med ETA: {context.medical_eta_minutes}m
                </div>
              )}
              <div className="flex gap-2">
                <button className="px-2 py-1 border rounded" onClick={async ()=>{
                  if (!activeMessages.length) return
                  const last = activeMessages[activeMessages.length-1]
                  const { intent, confidence } = await classifyIntent(last.body)
                  alert(`Intent: ${intent} (${(confidence*100).toFixed(0)}%)`)
                }}>Classify</button>
                <button className="px-2 py-1 border rounded" onClick={async ()=>{
                  const { summary } = await summarizeConversation({ phone_number: selectedPhone, max_messages: 50 })
                  alert(summary)
                }}>Summarize</button>
                <button className="px-2 py-1 border rounded" onClick={async ()=>{
                  const zone = prompt('Set zone (e.g., Zone 4):')
                  if (!zone) return
                  await setContactMetadata({ phone_number: selectedPhone, zone })
                  setContext(await resolveContext(selectedPhone))
                }}>Set Zone</button>
              </div>
            </div>
            <ChatWindow messages={activeMessages} />
            <MessageInput onSend={handleSend} disabled={!selectedPhone} />
          </>
        ) : (
          <div className="m-auto text-gray-500">Select a conversation</div>
        )}
      </div>
    </div>
  )
}
