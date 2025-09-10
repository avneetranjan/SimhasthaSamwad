import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      title: 'Samwad Admin',
      search_placeholder: 'Search phone...',
      reply_placeholder: 'Type a reply...',
      send: 'Send',
      no_conversation: 'Select a conversation',
      language: 'Language'
    },
  },
  hi: {
    translation: {
      title: 'संवाद व्यवस्थापक',
      search_placeholder: 'फ़ोन खोजें...',
      reply_placeholder: 'उत्तर लिखें...',
      send: 'भेजें',
      no_conversation: 'वार्ता चुनें',
      language: 'भाषा'
    },
  },
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: 'en',
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

export default i18n

