import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import AdminNav from './components/AdminNav'
import Conversations from './pages/Conversations'
import Issues from './pages/Issues'
import Broadcasts from './pages/Broadcasts'
import Templates from './pages/Templates'
import ZoneConfig from './pages/ZoneConfig'
import Metrics from './pages/Metrics'

export default function App() {
  const { t, i18n } = useTranslation()
  const [route, setRoute] = useState('conversations')

  const renderPage = () => {
    switch (route) {
      case 'issues':
        return <Issues />
      case 'broadcasts':
        return <Broadcasts />
      case 'templates':
        return <Templates />
      case 'zone-config':
        return <ZoneConfig />
      case 'metrics':
        return <Metrics />
      case 'conversations':
      default:
        return <Conversations />
    }
  }

  return (
    <div className="h-screen flex">
      <AdminNav route={route} onNavigate={setRoute} />
      <div className="flex-1 flex flex-col">
        <div className="border-b px-4 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold">{t('title')}</h1>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={i18n.language}
            onChange={(e) => i18n.changeLanguage(e.target.value)}
            title={t('language')}
          >
            <option value="en">EN</option>
            <option value="hi">HI</option>
          </select>
        </div>
        <div className="flex-1 min-h-0">{renderPage()}</div>
      </div>
    </div>
  )
}
