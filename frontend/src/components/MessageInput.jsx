import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState('')
  const { t } = useTranslation()

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  return (
    <div className="p-3 border-t border-gray-200 flex gap-2">
      <input
        type="text"
        className="flex-1 border rounded px-3 py-2 focus:outline-none focus:ring"
        placeholder={t('reply_placeholder')}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        disabled={disabled}
      />
      <button
        onClick={handleSend}
        disabled={disabled}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
      >
        {t('send')}
      </button>
    </div>
  )
}

